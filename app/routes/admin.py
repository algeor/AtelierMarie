"""Admin endpoints — product CRUD, CSV import, order management, dashboard stats."""

import csv
import io
import sqlite3
from typing import get_args

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import JSONResponse

from app.database import get_db
from app.dependencies.auth import require_admin
from app.models.admin import DashboardResponse
from app.models.orders import (
    OrderListResponse,
    OrderResponse,
    OrderStatus,
    UpdateOrderStatusRequest,
)
from app.models.products import (
    CreateProductRequest,
    CSVImportError,
    CSVImportResponse,
    ProductListResponse,
    ProductResponse,
    UpdateProductRequest,
)
from app.services import admin_service, product_service
from app.services.order_service import (
    InvalidStateTransitionError,
    OrderNotFoundError,
    get_order_admin,
    list_orders_admin,
    update_status,
)
from app.services.product_service import DuplicateError, NotFoundError

router = APIRouter(dependencies=[Depends(require_admin)])


@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=201,
    summary="Create product",
    description="Create a new product with a unique slug ID. Returns 409 if the ID already exists.",
)
async def admin_create_product(body: CreateProductRequest) -> ProductResponse | JSONResponse:
    """Create a new product."""
    try:
        product = product_service.create_product(body.model_dump())
    except DuplicateError:
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "DUPLICATE",
                    "message": "Product with this ID already exists",
                }
            },
        )

    return ProductResponse(**product)


@router.get(
    "/products",
    response_model=ProductListResponse,
    summary="List all products (admin)",
    description="List all products including inactive ones. Supports pagination.",
)
async def admin_list_products(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> ProductListResponse:
    """List all products (active and inactive) with pagination."""
    limit = min(limit, 100)
    products, total = product_service.list_products_admin(page=page, limit=limit)

    return ProductListResponse(
        products=[ProductResponse(**p) for p in products],
        total=total,
        page=page,
        limit=limit,
    )


@router.get(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Get product (admin)",
    description="Get any product by ID regardless of active status.",
)
async def admin_get_product(product_id: str) -> ProductResponse | JSONResponse:
    """Get any product (active or inactive) by ID."""
    try:
        product = product_service.get_product_admin(product_id)
    except NotFoundError:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "NOT_FOUND", "message": "Product not found"}},
        )

    return ProductResponse(**product)


@router.put(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Update product",
    description="Partially update a product. Only provided fields are modified; "
    "omitted fields remain unchanged.",
)
async def admin_update_product(
    product_id: str, body: UpdateProductRequest
) -> ProductResponse | JSONResponse:
    """Partially update a product. Only provided fields are modified."""
    update_data = body.model_dump(exclude_unset=True)

    try:
        product = product_service.update_product(product_id, update_data)
    except NotFoundError:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "NOT_FOUND", "message": "Product not found"}},
        )

    return ProductResponse(**product)


@router.delete(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Delete product (soft)",
    description="Soft-delete a product by setting is_active=0. "
    "The product remains in the database for order history integrity.",
)
async def admin_delete_product(product_id: str) -> ProductResponse | JSONResponse:
    """Soft-delete a product (set is_active=0)."""
    try:
        product = product_service.deactivate_product(product_id)
    except NotFoundError:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "NOT_FOUND", "message": "Product not found"}},
        )

    return ProductResponse(**product)


# Required CSV headers
_REQUIRED_CSV_HEADERS = {"id", "name", "price_cents"}
_OPTIONAL_CSV_HEADERS = {"description", "category", "stock", "image_url"}
_ALL_CSV_HEADERS = _REQUIRED_CSV_HEADERS | _OPTIONAL_CSV_HEADERS


@router.post(
    "/products/import",
    response_model=CSVImportResponse,
    summary="Bulk import products (CSV)",
    description=(
        "Upload a CSV file to create/update products in bulk. "
        "Uses upsert semantics — existing product IDs are updated, new ones are created. "
        "Rows with validation errors are skipped; results report created/updated counts "
        "and per-row errors."
    ),
)
async def admin_import_products(
    file: UploadFile = File(..., description="CSV file with product data"),
) -> CSVImportResponse | JSONResponse:
    """Bulk import products via CSV upload with upsert semantics.

    Required columns: id, name, price_cents
    Optional columns: description, category, stock, image_url

    Rows with validation errors are skipped; valid rows are upserted.
    """
    # Read file content
    content = await file.read()
    text = content.decode("utf-8-sig")  # Handle BOM

    reader = csv.DictReader(io.StringIO(text))

    # Validate headers
    if reader.fieldnames is None:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "INVALID_CSV",
                    "message": "CSV file is empty or has no headers",
                }
            },
        )

    headers = set(reader.fieldnames)
    missing = _REQUIRED_CSV_HEADERS - headers
    if missing:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "INVALID_CSV",
                    "message": f"Missing required columns: {', '.join(sorted(missing))}",
                }
            },
        )

    created = 0
    updated = 0
    errors: list[CSVImportError] = []

    for row_num, row in enumerate(reader, start=2):  # Row 1 is headers
        # Validate required fields have values
        row_errors: list[str] = []

        product_id = (row.get("id") or "").strip()
        name = (row.get("name") or "").strip()
        price_str = (row.get("price_cents") or "").strip()

        if not product_id:
            row_errors.append("id is required")
        if not name:
            row_errors.append("name is required")

        price_cents: int | None = None
        if not price_str:
            row_errors.append("price_cents is required")
        else:
            try:
                price_cents = int(price_str)
                if price_cents <= 0:
                    row_errors.append("price_cents must be positive")
            except ValueError:
                row_errors.append("price_cents must be an integer")

        # Validate stock if provided
        stock: int | None = None
        stock_str = (row.get("stock") or "").strip()
        if stock_str:
            try:
                stock = int(stock_str)
                if stock < 0:
                    row_errors.append("stock must be non-negative")
            except ValueError:
                row_errors.append("stock must be an integer")

        if row_errors:
            errors.append(CSVImportError(row=row_num, message="; ".join(row_errors)))
            continue

        # Build data dict from CSV columns present
        data: dict = {
            "name": name,
            "price_cents": price_cents,
        }

        if "description" in headers and row.get("description"):
            data["description"] = row["description"].strip()
        if "category" in headers and row.get("category"):
            data["category"] = row["category"].strip()
        if stock is not None:
            data["stock"] = stock
        if "image_url" in headers and row.get("image_url"):
            data["image_url"] = row["image_url"].strip()

        # Check if product exists to track created vs updated
        try:
            product_service.get_product_admin(product_id)
            is_existing = True
        except NotFoundError:
            is_existing = False

        try:
            product_service.upsert_product(product_id, data)
            if is_existing:
                updated += 1
            else:
                created += 1
        except (ValueError, sqlite3.Error) as e:
            errors.append(CSVImportError(row=row_num, message=str(e)))

    return CSVImportResponse(created=created, updated=updated, errors=errors)


@router.get(
    "/orders",
    response_model=OrderListResponse,
    summary="List all orders (admin)",
    description="List all orders with optional status filter and pagination. "
    "Requires admin authentication.",
)
def admin_list_orders(
    status: str | None = Query(default=None, description="Filter by order status"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> OrderListResponse | JSONResponse:
    """List all orders with optional status filter."""
    # Validate status value against OrderStatus literal
    if status is not None:
        valid_statuses = get_args(OrderStatus)
        if status not in valid_statuses:
            return JSONResponse(
                status_code=422,
                content={
                    "error": {
                        "code": "INVALID_STATUS",
                        "message": (
                            f"Invalid status '{status}'. "
                            f"Must be one of: {', '.join(valid_statuses)}"
                        ),
                    }
                },
            )

    with get_db() as conn:
        result = list_orders_admin(conn=conn, status=status, page=page, limit=limit)

    return OrderListResponse(
        items=[OrderResponse.model_validate(o) for o in result["items"]],
        total=result["total"],
        page=result["page"],
        limit=result["limit"],
    )


@router.get(
    "/orders/{order_id}",
    response_model=OrderResponse,
    summary="Get order detail (admin)",
    description="Get full order details including items, customer info, shipping address, "
    "and notes. No ownership check — admin can view any order.",
)
def admin_get_order_detail(order_id: str) -> OrderResponse | JSONResponse:
    """Get full order detail for admin (no ownership check)."""
    try:
        with get_db() as conn:
            order_data = get_order_admin(conn=conn, order_id=order_id)
    except OrderNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "NOT_FOUND", "message": "Order not found"}},
        )

    return OrderResponse.model_validate(order_data)


@router.patch(
    "/orders/{order_id}/status",
    response_model=OrderResponse,
    summary="Update order status (admin)",
    description="Update order status with state machine validation. "
    "Restores stock on cancellation.",
)
def admin_update_order_status(
    order_id: str,
    body: UpdateOrderStatusRequest,
) -> OrderResponse | JSONResponse:
    """Update order status (admin-only, state machine enforced)."""
    try:
        with get_db() as conn:
            order_data = update_status(conn=conn, order_id=order_id, new_status=body.status)
    except OrderNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "NOT_FOUND", "message": "Order not found"}},
        )
    except InvalidStateTransitionError as e:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "INVALID_TRANSITION",
                    "message": str(e),
                    "details": {
                        "order_id": e.order_id,
                        "current_status": e.current_status,
                        "requested_status": e.requested_status,
                    },
                }
            },
        )

    return OrderResponse.model_validate(order_data)


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="Admin dashboard stats",
    description="Returns aggregate statistics: product counts (total/active), "
    "order counts by status, total revenue, and low-stock alerts.",
)
async def admin_dashboard() -> DashboardResponse:
    """Admin dashboard with basic store statistics.

    Returns product counts, order counts, revenue, and low-stock alerts.
    All monetary values are in cents.
    """
    stats = admin_service.get_dashboard_stats()
    return DashboardResponse(**stats)
