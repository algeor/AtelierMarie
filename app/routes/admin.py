"""Admin endpoints — product CRUD, CSV import, order management, dashboard stats."""

import csv
import io
from typing import get_args

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import JSONResponse, Response

from app.constants import MAX_PRICE_CENTS, MAX_STOCK
from app.database import get_db
from app.dependencies.auth import require_admin
from app.models.admin import DashboardResponse
from app.models.comments import AdminCommentListResponse, AdminCommentResponse
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
    ProductAdminListResponse,
    ProductAdminResponse,
    UpdateProductRequest,
)
from app.services import admin_service, product_service
from app.services.auth_service import get_oauth_circuit_breaker
from app.services.comment_service import CommentNotFoundError, list_all_comments
from app.services.comment_service import delete_comment as delete_comment_service
from app.services.image_service import (
    MAX_FILE_SIZE,
    FileTooLargeError,
    ImageProcessingError,
    InvalidImageTypeError,
    InvalidProductIdError,
    process_image,
    validate_image_file,
)
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
    response_model=ProductAdminResponse,
    status_code=201,
    summary="Create product",
    description="Create a new product with a unique slug ID. Returns 409 if the ID already exists.",
)
async def admin_create_product(body: CreateProductRequest) -> ProductAdminResponse | JSONResponse:
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

    return ProductAdminResponse(**product)


@router.get(
    "/products",
    response_model=ProductAdminListResponse,
    summary="List all products (admin)",
    description="List all products including inactive ones. Supports pagination.",
)
async def admin_list_products(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> ProductAdminListResponse:
    """List all products (active and inactive) with pagination."""
    limit = min(limit, 100)
    products, total = product_service.list_products_admin(page=page, limit=limit)

    return ProductAdminListResponse(
        products=[ProductAdminResponse(**p) for p in products],
        total=total,
        page=page,
        limit=limit,
    )


@router.get(
    "/products/{product_id}",
    response_model=ProductAdminResponse,
    summary="Get product (admin)",
    description="Get any product by ID regardless of active status.",
)
async def admin_get_product(product_id: str) -> ProductAdminResponse | JSONResponse:
    """Get any product (active or inactive) by ID."""
    try:
        product = product_service.get_product_admin(product_id)
    except NotFoundError:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "NOT_FOUND", "message": "Product not found"}},
        )

    return ProductAdminResponse(**product)


@router.put(
    "/products/{product_id}",
    response_model=ProductAdminResponse,
    summary="Update product",
    description="Partially update a product. Only provided fields are modified; "
    "omitted fields remain unchanged.",
)
async def admin_update_product(
    product_id: str, body: UpdateProductRequest
) -> ProductAdminResponse | JSONResponse:
    """Partially update a product. Only provided fields are modified."""
    update_data = body.model_dump(exclude_unset=True)

    try:
        product = product_service.update_product(product_id, update_data)
    except NotFoundError:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "NOT_FOUND", "message": "Product not found"}},
        )

    return ProductAdminResponse(**product)


@router.delete(
    "/products/{product_id}",
    response_model=ProductAdminResponse,
    summary="Delete product (soft)",
    description="Soft-delete a product by setting is_active=0. "
    "The product remains in the database for order history integrity.",
)
async def admin_delete_product(product_id: str) -> ProductAdminResponse | JSONResponse:
    """Soft-delete a product (set is_active=0)."""
    try:
        product = product_service.deactivate_product(product_id)
    except NotFoundError:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "NOT_FOUND", "message": "Product not found"}},
        )

    return ProductAdminResponse(**product)


# Required CSV headers — accept both legacy (name/description) and new (name_en/description_en)
_REQUIRED_CSV_HEADERS_NEW = {"id", "name_en", "price_cents"}
_REQUIRED_CSV_HEADERS_LEGACY = {"id", "name", "price_cents"}
_OPTIONAL_CSV_HEADERS = {
    "description",
    "description_en",
    "description_bg",
    "name_bg",
    "category",
    "stock",
    "image_url",
}


@router.post(
    "/products/import",
    response_model=CSVImportResponse,
    summary="Bulk import products (CSV)",
    description=(
        "Upload a CSV file to create/update products in bulk. "
        "Uses upsert semantics — existing product IDs are updated, "
        "new ones are created. Rows with validation errors are skipped; "
        "results report created/updated counts and per-row errors. "
        "Supports bilingual columns: name_en, name_bg, description_en, description_bg. "
        "Legacy columns (name, description) are treated as English equivalents."
    ),
)
async def admin_import_products(
    file: UploadFile = File(..., description="CSV file with product data"),
) -> CSVImportResponse | JSONResponse:
    """Bulk import products via CSV upload with upsert semantics.

    Required columns: id, name_en (or legacy 'name'), price_cents
    Optional columns: name_bg, description_en (or legacy 'description'),
                      description_bg, category, stock, image_url

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

    # Accept either new (name_en) or legacy (name) column for required name field
    has_name_en = "name_en" in headers
    has_name_legacy = "name" in headers
    has_required_name = has_name_en or has_name_legacy

    # Check basic required columns (id, price_cents always required, plus one name variant)
    base_missing = {"id", "price_cents"} - headers
    if base_missing or not has_required_name:
        missing_cols = sorted(base_missing)
        if not has_required_name:
            missing_cols.append("name_en (or name)")
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "INVALID_CSV",
                    "message": f"Missing required columns: {', '.join(missing_cols)}",
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

        # Resolve name_en from either column (prefer name_en over legacy name)
        name_en = (row.get("name_en") or row.get("name") or "").strip()
        price_str = (row.get("price_cents") or "").strip()

        if not product_id:
            row_errors.append("id is required")
        if not name_en:
            row_errors.append("name_en is required")

        price_cents: int | None = None
        if not price_str:
            row_errors.append("price_cents is required")
        else:
            try:
                price_cents = int(price_str)
                if price_cents <= 0:
                    row_errors.append("price_cents must be positive")
                elif price_cents > MAX_PRICE_CENTS:
                    row_errors.append(f"price_cents exceeds maximum ({MAX_PRICE_CENTS})")
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
                elif stock > MAX_STOCK:
                    row_errors.append(f"stock exceeds maximum ({MAX_STOCK})")
            except ValueError:
                row_errors.append("stock must be an integer")

        if row_errors:
            errors.append(CSVImportError(row=row_num, message="; ".join(row_errors)))
            continue

        # Build data dict — bilingual fields
        data: dict = {
            "name_en": name_en,
            "price_cents": price_cents,
        }

        # Bulgarian name (optional)
        name_bg = (row.get("name_bg") or "").strip()
        if name_bg:
            data["name_bg"] = name_bg

        # Description: prefer _en/_bg columns, fall back to legacy 'description'
        description_en = (row.get("description_en") or row.get("description") or "").strip()
        if description_en:
            data["description_en"] = description_en

        description_bg = (row.get("description_bg") or "").strip()
        if description_bg:
            data["description_bg"] = description_bg

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
        except Exception as e:
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


@router.get(
    "/health/oauth",
    summary="OAuth circuit breaker health",
    description="Returns the current state of the Google OAuth circuit breaker, "
    "including failure count and recovery timing. Admin-only.",
)
async def admin_health_oauth() -> JSONResponse:
    """Expose Google OAuth circuit breaker state for admin diagnostics."""
    breaker = get_oauth_circuit_breaker()
    return JSONResponse(content=breaker.get_health())


# --- Comment moderation endpoints ---


@router.delete(
    "/comments/{comment_id}",
    status_code=204,
    response_class=Response,
    summary="Delete comment (admin)",
    description="Hard-delete any comment by ID. No '[deleted]' placeholder remains.",
    responses={404: {"description": "Comment not found"}},
)
async def admin_delete_comment(comment_id: str) -> Response:
    """Delete any comment (admin moderation)."""
    try:
        delete_comment_service(comment_id)
    except CommentNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "NOT_FOUND", "message": "Comment not found"}},
        )
    return Response(status_code=204)


@router.get(
    "/comments",
    response_model=AdminCommentListResponse,
    summary="List all comments (admin)",
    description="List all comments across products for moderation. "
    "Includes product context. Supports optional product_id filter and pagination.",
)
async def admin_list_comments(
    product_id: str | None = Query(default=None, description="Filter by product ID"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, description="Items per page (max 100)"),
) -> AdminCommentListResponse:
    """List all comments for admin moderation."""
    limit = min(limit, 100)
    comments, total = list_all_comments(page=page, limit=limit, product_id=product_id)

    return AdminCommentListResponse(
        items=[AdminCommentResponse(**c) for c in comments],
        total=total,
        page=page,
        limit=limit,
    )


# --- Image upload endpoint ---


async def _read_upload_with_limit(file: UploadFile) -> bytes:
    """Read an UploadFile without buffering unbounded request bodies."""
    chunks = bytearray()
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        chunks.extend(chunk)
        if len(chunks) > MAX_FILE_SIZE:
            raise FileTooLargeError("File size exceeds maximum of 5MB")
    return bytes(chunks)


@router.post(
    "/products/{product_id}/image",
    summary="Upload product image",
    description="Upload a JPEG or PNG image for a product. Image is resized, "
    "stripped of EXIF metadata, and converted to WebP. Overwrites any existing image.",
    responses={
        200: {"description": "Image uploaded successfully"},
        400: {"description": "Invalid product ID"},
        404: {"description": "Product not found"},
        422: {"description": "Invalid image type, file too large, or processing failed"},
    },
)
async def admin_upload_product_image(
    product_id: str,
    file: UploadFile = File(..., description="JPEG or PNG image file"),
) -> JSONResponse:
    """Upload and process a product image.

    Validates the file (type, size, slug), processes it (resize, strip EXIF,
    convert to WebP), saves main + thumbnail, and updates the product's image_url.
    """
    # Read file bytes with an application-level limit. Nginx should reject
    # larger production uploads first; this is defense-in-depth for app access.
    try:
        file_bytes = await _read_upload_with_limit(file)
    except FileTooLargeError:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "file_too_large",
                    "message": "File size exceeds maximum of 5MB",
                }
            },
        )

    # Validate image file and product_id slug
    try:
        validate_image_file(file_bytes, product_id)
    except InvalidProductIdError:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "invalid_product_id",
                    "message": "Product ID must be a valid slug (lowercase alphanumeric + hyphens)",
                }
            },
        )
    except FileTooLargeError:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "file_too_large",
                    "message": "File size exceeds maximum of 5MB",
                }
            },
        )
    except InvalidImageTypeError:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "invalid_image_type",
                    "message": "Unsupported image format. Only JPEG and PNG are accepted.",
                }
            },
        )

    # Verify product exists
    try:
        product_service.get_product_admin(product_id)
    except NotFoundError:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "product_not_found", "message": "Product not found"}},
        )

    # Process image (resize, strip EXIF, save as WebP)
    try:
        result = process_image(file_bytes, product_id)
    except ImageProcessingError as e:
        error_message = str(e)
        if error_message == "image_dimensions_too_large":
            return JSONResponse(
                status_code=422,
                content={
                    "error": {
                        "code": "image_dimensions_too_large",
                        "message": "Image dimensions exceed the maximum allowed (25 megapixels)",
                    }
                },
            )
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "image_processing_failed",
                    "message": "Image could not be processed. The file may be corrupted.",
                }
            },
        )

    # Update product's image_url in database
    with get_db() as conn:
        conn.execute(
            "UPDATE products SET image_url = ? WHERE id = ?",
            (result["image_url"], product_id),
        )

    return JSONResponse(
        status_code=200,
        content=result,
    )
