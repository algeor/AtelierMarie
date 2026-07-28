"""Admin endpoints — product CRUD, CSV import, order management, dashboard stats."""

import csv
import io
import re
from typing import get_args

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import JSONResponse, Response

from app.constants import MAX_CSV_ROWS, MAX_CSV_UPLOAD_BYTES, MAX_PRICE_CENTS, MAX_STOCK
from app.database import get_db
from app.dependencies.auth import require_admin
from app.models.admin import DashboardResponse, LowStockProductsResponse
from app.models.comments import AdminCommentListResponse, AdminCommentResponse
from app.models.common import PRODUCT_ID_PATTERN
from app.models.orders import (
    OrderEmailAudit,
    OrderEmailAuditResponse,
    OrderListResponse,
    OrderResponse,
    OrderStatus,
    UpdateOrderStatusRequest,
)
from app.models.products import (
    MAX_CATEGORY_LENGTH,
    MAX_DAYS_TO_CRAFT,
    MAX_DESCRIPTION_LENGTH,
    MAX_IMAGE_URL_LENGTH,
    MAX_MATERIALS_LENGTH,
    MAX_NAME_LENGTH,
    MAX_WEIGHT_GRAMS,
    CreateProductRequest,
    CSVImportError,
    CSVImportResponse,
    ProductAdminListResponse,
    ProductAdminResponse,
    ProductImage,
    ReorderProductImagesRequest,
    UpdateProductRequest,
)
from app.models.promotions import BulkDiscountRequest, BulkDiscountResponse
from app.services import admin_service, product_image_service, product_service
from app.services.auth_service import get_oauth_circuit_breaker
from app.services.comment_service import CommentNotFoundError, list_all_comments
from app.services.comment_service import delete_comment as delete_comment_service
from app.services.email_service import event_for_status, queue_order_email
from app.services.image_service import (
    MAX_FILE_SIZE,
    FileTooLargeError,
    ImageProcessingError,
    InvalidImageTypeError,
    InvalidProductIdError,
    validate_image_file,
)
from app.services.order_service import (
    get_order_admin,
    list_orders_admin,
    update_status,
)
from app.services.product_service import (
    BulkTargetLimitError,
    DiscountValidationError,
    DuplicateError,
    NotFoundError,
)

router = APIRouter(dependencies=[Depends(require_admin)])


@router.post(
    "/products",
    response_model=ProductAdminResponse,
    status_code=201,
    summary="Create product",
    description="Create a new product with a unique slug ID. Returns 409 if the ID already exists.",
    responses={
        409: {"description": "Product with this ID already exists"},
        422: {"description": "Validation error"},
    },
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
    "/products/low-stock",
    response_model=LowStockProductsResponse,
    summary="List products with low stock (admin)",
    description="Return active products whose stock is at or below the given threshold.",
)
async def admin_list_low_stock_products(
    threshold: int = Query(default=5, ge=0, description="Stock threshold (inclusive)"),
) -> LowStockProductsResponse:
    """List admin products at or below the given stock threshold."""
    products = product_service.get_low_stock_products(threshold=threshold)
    return LowStockProductsResponse(
        products=[ProductAdminResponse(**p) for p in products],
        total=len(products),
        threshold=threshold,
    )


@router.patch(
    "/products/bulk-discount",
    response_model=BulkDiscountResponse,
    summary="Bulk apply/remove product discount",
    description="Apply or clear the discount on many products at once, targeted by "
    "explicit product IDs or an admin product-list filter. Capped at 500 resolved "
    "targets. Returns per-product results with success/failure counts.",
    responses={
        422: {"description": "Validation error or target set exceeds the 500-product cap"},
    },
)
async def admin_bulk_discount(body: BulkDiscountRequest) -> BulkDiscountResponse | JSONResponse:
    """Apply or clear a discount across many products via the shared bulk logic."""
    try:
        target_ids = product_service.resolve_bulk_target(
            product_ids=body.product_ids,
            filter=body.filter.model_dump() if body.filter is not None else None,
        )
    except BulkTargetLimitError as e:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "BULK_TARGET_LIMIT_EXCEEDED", "message": str(e)}},
        )

    if not target_ids:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "target resolves to no products",
                }
            },
        )

    result = product_service.bulk_update_discount(
        operation=body.operation,
        product_ids=target_ids,
        discount_percent=body.discount_percent,
        discount_starts_at=body.discount_starts_at,
        discount_ends_at=body.discount_ends_at,
    )
    return BulkDiscountResponse(**result)


@router.get(
    "/products/{product_id}",
    response_model=ProductAdminResponse,
    summary="Get product (admin)",
    description="Get any product by ID regardless of active status.",
    responses={404: {"description": "Product not found"}},
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
    responses={
        404: {"description": "Product not found"},
        422: {"description": "Validation error"},
    },
)
@router.patch(
    "/products/{product_id}",
    response_model=ProductAdminResponse,
    summary="Update product",
    description="Partially update a product. Only provided fields are modified; "
    "omitted fields remain unchanged.",
    responses={
        404: {"description": "Product not found"},
        422: {"description": "Validation error"},
    },
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
    except DiscountValidationError as e:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "VALIDATION_ERROR", "message": str(e)}},
        )

    return ProductAdminResponse(**product)


@router.delete(
    "/products/{product_id}",
    response_model=ProductAdminResponse,
    summary="Delete product (soft)",
    description="Soft-delete a product by setting is_active=0. "
    "The product remains in the database for order history integrity.",
    responses={404: {"description": "Product not found"}},
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


# Accepted case-insensitive boolean literals for CSV boolean columns.
_CSV_BOOL_TRUE = {"true", "1", "yes"}
_CSV_BOOL_FALSE = {"false", "0", "no"}


def _parse_csv_bool(value: str) -> bool:
    """Parse a CSV boolean cell. Raises ValueError on anything unrecognized.

    Accepts (case-insensitive): true/false, 1/0, yes/no. Rejecting unknown
    values means a typo can't silently deactivate a product.
    """
    normalized = value.strip().lower()
    if normalized in _CSV_BOOL_TRUE:
        return True
    if normalized in _CSV_BOOL_FALSE:
        return False
    msg = "must be one of true/false/1/0/yes/no"
    raise ValueError(msg)


def _parse_csv_image_url(value: str) -> str | None:
    """Validate a CSV image URL using the same rule as product request models."""
    stripped = value.strip()
    if not stripped:
        return None
    if not stripped.startswith(("http://", "https://", "/")):
        msg = "must be a valid URL (http://, https://, or relative path)"
        raise ValueError(msg)
    return stripped


def _parse_csv_image_url(value: str) -> str | None:
    """Validate a CSV image URL before any product write happens."""
    stripped = value.strip()
    if not stripped:
        return None
    if not stripped.startswith(("http://", "https://", "/")):
        msg = "image_url must be http(s) or an absolute relative path"
        raise ValueError(msg)
    return stripped


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
        "Legacy columns (name, description) are treated as English equivalents. "
        "Optional columns: weight_grams, is_active, is_featured (true/false/1/0/yes/no), "
        "materials, days_to_craft."
    ),
)
async def admin_import_products(
    file: UploadFile = File(..., description="CSV file with product data"),
) -> CSVImportResponse | JSONResponse:
    """Bulk import products via CSV upload with upsert semantics.

    Required columns: id, name_en (or legacy 'name'), price_cents
    Optional columns: name_bg, description_en (or legacy 'description'),
                      description_bg, category, stock, image_url,
                      weight_grams, is_active, is_featured, materials,
                      days_to_craft

    weight_grams defaults to 300 for newly-created products when the column
    is absent; existing products keep their current weight. Boolean columns
    (is_active, is_featured) accept true/false/1/0/yes/no (case-insensitive).

    Rows with validation errors are skipped; valid rows are upserted.
    """
    # Read file content (bounded — avoid buffering an unbounded request body)
    content = await file.read()
    if len(content) > MAX_CSV_UPLOAD_BYTES:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "INVALID_CSV",
                    "message": f"CSV file exceeds maximum size ({MAX_CSV_UPLOAD_BYTES} bytes)",
                }
            },
        )
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
        # Cap the number of data rows to bound DB round-trips per upload.
        if row_num - 1 > MAX_CSV_ROWS:
            errors.append(
                CSVImportError(
                    row=row_num,
                    message=f"row limit exceeded (max {MAX_CSV_ROWS}); remaining rows skipped",
                )
            )
            break

        # Validate required fields have values
        row_errors: list[str] = []

        product_id = (row.get("id") or "").strip()

        # Resolve name_en from either column (prefer name_en over legacy name)
        name_en = (row.get("name_en") or row.get("name") or "").strip()
        price_str = (row.get("price_cents") or "").strip()

        if not product_id:
            row_errors.append("id is required")
        elif not re.match(PRODUCT_ID_PATTERN, product_id):
            row_errors.append("id must be a lowercase slug (letters, digits, hyphens)")
        if not name_en:
            row_errors.append("name_en is required")
        elif len(name_en) > MAX_NAME_LENGTH:
            row_errors.append(f"name_en exceeds maximum length ({MAX_NAME_LENGTH})")

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

        # Validate weight_grams if provided (int, 1..MAX_WEIGHT_GRAMS)
        weight_grams: int | None = None
        weight_str = (row.get("weight_grams") or "").strip()
        if weight_str:
            try:
                weight_grams = int(weight_str)
                if weight_grams < 1:
                    row_errors.append("weight_grams must be at least 1")
                elif weight_grams > MAX_WEIGHT_GRAMS:
                    row_errors.append(f"weight_grams exceeds maximum ({MAX_WEIGHT_GRAMS})")
            except ValueError:
                row_errors.append("weight_grams must be an integer")

        # Validate days_to_craft if provided (int, 0..MAX_DAYS_TO_CRAFT)
        days_to_craft: int | None = None
        days_str = (row.get("days_to_craft") or "").strip()
        if days_str:
            try:
                days_to_craft = int(days_str)
                if days_to_craft < 0:
                    row_errors.append("days_to_craft must be non-negative")
                elif days_to_craft > MAX_DAYS_TO_CRAFT:
                    row_errors.append(f"days_to_craft exceeds maximum ({MAX_DAYS_TO_CRAFT})")
            except ValueError:
                row_errors.append("days_to_craft must be an integer")

        # Validate boolean columns if provided
        is_active: bool | None = None
        is_active_str = (row.get("is_active") or "").strip()
        if is_active_str:
            try:
                is_active = _parse_csv_bool(is_active_str)
            except ValueError as e:
                row_errors.append(f"is_active {e}")

        is_featured: bool | None = None
        is_featured_str = (row.get("is_featured") or "").strip()
        if is_featured_str:
            try:
                is_featured = _parse_csv_bool(is_featured_str)
            except ValueError as e:
                row_errors.append(f"is_featured {e}")

        # Validate optional string-field lengths (the CSV path bypasses Pydantic,
        # so mirror the model max_length bounds here).
        for column, max_length in (
            ("name_bg", MAX_NAME_LENGTH),
            ("description_en", MAX_DESCRIPTION_LENGTH),
            ("description", MAX_DESCRIPTION_LENGTH),
            ("description_bg", MAX_DESCRIPTION_LENGTH),
            ("materials", MAX_MATERIALS_LENGTH),
            ("category", MAX_CATEGORY_LENGTH),
            ("image_url", MAX_IMAGE_URL_LENGTH),
        ):
            if len((row.get(column) or "").strip()) > max_length:
                row_errors.append(f"{column} exceeds maximum length ({max_length})")

        imported_image_url: str | None = None
        if "image_url" in headers and row.get("image_url"):
            try:
                imported_image_url = _parse_csv_image_url(row["image_url"])
            except ValueError as e:
                row_errors.append(f"image_url {e}")

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
        if weight_grams is not None:
            data["weight_grams"] = weight_grams
        if days_to_craft is not None:
            data["days_to_craft"] = days_to_craft
        if is_active is not None:
            data["is_active"] = is_active
        if is_featured is not None:
            data["is_featured"] = is_featured
        if "materials" in headers and row.get("materials"):
            data["materials"] = row["materials"].strip()

        # Check if product exists to track created vs updated
        try:
            product_service.get_product_admin(product_id)
            is_existing = True
        except NotFoundError:
            is_existing = False

        try:
            product_service.upsert_product(product_id, data)
            if imported_image_url:
                product_image_service.add_existing_image_url(product_id, imported_image_url)
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
def admin_get_order_detail(order_id: str) -> OrderResponse:
    """Get full order detail for admin (no ownership check)."""
    with get_db() as conn:
        order_data = get_order_admin(conn=conn, order_id=order_id)

    return OrderResponse.model_validate(order_data)


@router.get(
    "/orders/{order_id}/emails",
    response_model=OrderEmailAuditResponse,
    summary="Order email audit trail (admin)",
    description="Read the order_emails send-attempt log for an order — status, "
    "attempts, and skip/error reason per event. Backs the deferred re-send UI.",
)
def admin_get_order_emails(order_id: str) -> OrderEmailAuditResponse:
    """Return the email audit trail for an order (admin-only)."""
    with get_db() as conn:
        # Confirm the order exists (404 via OrderNotFoundError otherwise).
        get_order_admin(conn=conn, order_id=order_id)
        rows = conn.execute(
            "SELECT event, recipient, status, reason, attempts, sent_at "
            "FROM order_emails WHERE order_id = ? ORDER BY id",
            (order_id,),
        ).fetchall()

    return OrderEmailAuditResponse(
        order_id=order_id,
        emails=[
            OrderEmailAudit(
                event=r["event"],
                recipient=r["recipient"],
                status=r["status"],
                reason=r["reason"],
                attempts=r["attempts"],
                sent_at=r["sent_at"],
            )
            for r in rows
        ],
    )


@router.patch(
    "/orders/{order_id}/status",
    response_model=OrderResponse,
    summary="Update order status (admin)",
    description="Update order status with state machine validation. "
    "Restores stock on cancellation.",
    responses={
        404: {"description": "Order not found"},
        422: {"description": "Invalid state transition or validation error"},
    },
)
def admin_update_order_status(
    order_id: str,
    body: UpdateOrderStatusRequest,
) -> OrderResponse:
    """Update order status (admin-only, state machine enforced)."""
    with get_db() as conn:
        order_data = update_status(
            conn=conn,
            order_id=order_id,
            new_status=body.status,
            tracking_number=body.tracking_number,
            tracking_carrier=body.tracking_carrier,
            tracking_url=body.tracking_url,
        )
        # Durable outbox: queue the customer email for this transition in the
        # SAME connection/commit as the status UPDATE (email-notifications 8.3).
        # The map returns None for 'confirmed' (internal step — no email).
        event = event_for_status(body.status)
        if event is not None:
            queue_order_email(conn, order_id, event, order_data["customer_email"])

    return OrderResponse.model_validate(order_data)


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="Admin dashboard stats",
    description="Returns aggregate statistics: product counts (total/active), "
    "order counts by status, total revenue, and low-stock alerts.",
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Admin access required"},
    },
)
async def admin_dashboard(response: Response) -> DashboardResponse:
    """Admin dashboard with basic store statistics.

    Returns product counts, order counts, revenue, and low-stock alerts.
    All monetary values are in cents.
    """
    # Sensitive business data — never cache in proxies or browsers.
    response.headers["Cache-Control"] = "no-store, no-cache"
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
            raise FileTooLargeError("File size exceeds maximum of 25MB")
    return bytes(chunks)


@router.post(
    "/products/{product_id}/images",
    response_model=ProductImage,
    status_code=201,
    summary="Append product image",
    description="Upload a JPEG or PNG image for a product gallery. Image is resized, "
    "stripped of EXIF metadata, converted to WebP, and appended without overwriting.",
    responses={
        201: {"description": "Image uploaded successfully"},
        400: {"description": "Invalid product ID"},
        404: {"description": "Product not found"},
        409: {"description": "Product already has the maximum number of images"},
        422: {"description": "Invalid image type, file too large, or processing failed"},
    },
)
async def admin_append_product_image(
    product_id: str,
    file: UploadFile = File(..., description="JPEG or PNG image file"),
) -> ProductImage | JSONResponse:
    """Upload and append a processed image to a product gallery.

    Validates the file (type, size, slug), processes it (resize, strip EXIF,
    convert to WebP), saves main + thumbnail + zoom, and stores a product_images row.
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
                    "message": "File size exceeds maximum of 25MB",
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
                    "message": "File size exceeds maximum of 25MB",
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

    try:
        image = product_image_service.add_image(product_id, file_bytes)
    except product_image_service.ProductNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "product_not_found", "message": "Product not found"}},
        )
    except product_image_service.ProductImageLimitError:
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "max_product_images",
                    "message": "Product already has the maximum number of images",
                }
            },
        )
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
    return ProductImage(**image)


@router.delete(
    "/products/{product_id}/images/{image_id}",
    status_code=204,
    response_class=Response,
    summary="Delete product image",
    responses={404: {"description": "Product image not found"}},
)
async def admin_delete_product_image(product_id: str, image_id: str) -> Response:
    """Delete one product image and promote another primary when needed."""
    try:
        product_image_service.delete_image(product_id, image_id)
    except product_image_service.ProductImageNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "image_not_found", "message": "Product image not found"}},
        )
    return Response(status_code=204)


@router.patch(
    "/products/{product_id}/images/reorder",
    response_model=list[ProductImage],
    summary="Reorder product images",
    responses={
        404: {"description": "Product not found"},
        422: {"description": "ordered_ids does not match the product image set"},
    },
)
async def admin_reorder_product_images(
    product_id: str,
    body: ReorderProductImagesRequest,
) -> list[ProductImage] | JSONResponse:
    """Replace the gallery display order without changing the primary image."""
    try:
        images = product_image_service.reorder_images(product_id, body.ordered_ids)
    except product_image_service.ProductNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "product_not_found", "message": "Product not found"}},
        )
    except product_image_service.ProductImageOrderError:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "invalid_image_order",
                    "message": "ordered_ids must match all images for the product",
                }
            },
        )
    return [ProductImage(**image) for image in images]


@router.patch(
    "/products/{product_id}/images/{image_id}/primary",
    response_model=ProductImage,
    summary="Set primary product image",
    responses={404: {"description": "Product image not found"}},
)
async def admin_set_primary_product_image(
    product_id: str,
    image_id: str,
) -> ProductImage | JSONResponse:
    """Set one product image as the sole primary image."""
    try:
        image = product_image_service.set_primary(product_id, image_id)
    except product_image_service.ProductImageNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "image_not_found", "message": "Product image not found"}},
        )
    return ProductImage(**image)
