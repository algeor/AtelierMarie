"""Admin endpoints — product CRUD, CSV import, order management, dashboard stats."""

import csv
import io
import re
import sqlite3
from pathlib import Path
from typing import Annotated, cast, get_args

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse, Response

from app.config import get_settings
from app.constants import MAX_CSV_ROWS, MAX_CSV_UPLOAD_BYTES, MAX_PRICE_CENTS, MAX_STOCK
from app.database import get_db
from app.dependencies.auth import require_admin
from app.middleware.request_id import request_id_var
from app.models.accounting import (
    AccountantAcceptanceRequest,
    AccountingConfigurationResponse,
    AccountingDocumentListResponse,
    AccountingDocumentRequest,
    AccountingDocumentResponse,
    AccountingLedgerResponse,
    CategoryMappingRequest,
    CategoryMappingResponse,
    ExpenseEvidenceListResponse,
    ExpenseEvidenceRequest,
    ExpenseEvidenceResponse,
    ExpenseEvidenceSettingsRequest,
    ExpenseEvidenceSettingsResponse,
    ExpensePaymentStatusRequest,
    ExportSchemaSettingsRequest,
    ExportSchemaSettingsResponse,
    FinanceExceptionActionRequest,
    FinanceExceptionListResponse,
    FinanceExceptionResponse,
    FinanceExportPackageListResponse,
    FinanceExportPackageResponse,
    FinancePeriodActionRequest,
    FinancePeriodCreateRequest,
    FinancePeriodListResponse,
    FinancePeriodResponse,
    MissingProductCostDiagnosticsResponse,
    ProductCostSettingsRequest,
    ProductCostSettingsResponse,
    ProductCostVersionListResponse,
    ProductCostVersionRequest,
    ProductCostVersionResponse,
    SellerLegalProfileRequest,
    SellerLegalProfileResponse,
    StripeBalanceImportResponse,
    StripePayoutImportStatusResponse,
    StripePayoutMatchReviewRequest,
    VatFiscalSettingsRequest,
    VatFiscalSettingsResponse,
)
from app.models.admin import (
    AdminAlertListResponse,
    AdminAlertResponse,
    DashboardResponse,
    LowStockProductsResponse,
)
from app.models.analytics import (
    AnalyticsFunnelResponse,
    AnalyticsHealthResponse,
    AnalyticsSummaryResponse,
    CheckoutAnalyticsResponse,
    ProductAnalyticsResponse,
)
from app.models.comments import AdminCommentListResponse, AdminCommentResponse
from app.models.common import PRODUCT_ID_PATTERN
from app.models.delivery import DeliverySettingsResponse, DeliverySettingsUpdate
from app.models.econt import (
    EcontConnectionTestResponse,
    EcontFulfillmentActionResponse,
    EcontManualStatusRequest,
    EcontOrderFulfillmentResponse,
    EcontOrderRepairRequest,
    EcontSettingsResponse,
    EcontSettingsUpdate,
)
from app.models.orders import (
    AdminOrderDetailResponse,
    ManualPaymentActionRequest,
    MarkPaymentPaidRequest,
    OrderEmailAudit,
    OrderEmailAuditResponse,
    OrderListResponse,
    OrderResponse,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    UpdateOrderStatusRequest,
)
from app.models.products import (
    MAX_CATEGORY_LENGTH,
    MAX_DAYS_TO_CRAFT,
    MAX_DESCRIPTION_LENGTH,
    MAX_IMAGE_URL_LENGTH,
    MAX_MATERIALS_LENGTH,
    MAX_NAME_LENGTH,
    MAX_SAFETY_TEXT_LENGTH,
    MAX_WEIGHT_GRAMS,
    CreateProductRequest,
    CSVImportError,
    CSVImportResponse,
    ProductAdminListResponse,
    ProductAdminResponse,
    ProductImage,
    ProductVideo,
    ReorderProductImagesRequest,
    UpdateProductRequest,
    UpdateProductVideoRequest,
)
from app.models.promotions import BulkDiscountRequest, BulkDiscountResponse
from app.models.returns import (
    CodSettlementResponse,
    CreateReturnCaseRequest,
    CreateStripeRefundRequest,
    InspectReturnCaseRequest,
    PaymentRefundResponse,
    RecordCodSettlementRequest,
    ReturnCaseResponse,
    UpdateReturnAccountingRequest,
)
from app.models.speedy import (
    SpeedyActionResponse,
    SpeedyAdminOverviewResponse,
    SpeedyCancelShipmentRequest,
    SpeedyEventResponse,
    SpeedyHealthResponse,
    SpeedyMetricsResponse,
    SpeedyOfficeRefreshStatusResponse,
    SpeedyPickupRequest,
    SpeedyPickupResponse,
    SpeedyPickupTermsRequest,
    SpeedyPickupTermsResponse,
    SpeedyQueuesResponse,
    SpeedyShipmentInfoRequest,
    SpeedyShipmentInfoResponse,
    SpeedyShipmentSearchRequest,
    SpeedyShipmentSearchResponse,
)
from app.models.users import UserResponse
from app.responses import error_response
from app.services import (
    accounting_config_service,
    accounting_document_service,
    accounting_export_service,
    accounting_ledger_service,
    accounting_report_service,
    admin_alert_service,
    admin_service,
    analytics_service,
    courier_polling_service,
    delivery_settings_service,
    econt_fulfillment_service,
    econt_settings_service,
    expense_product_cost_service,
    finance_period_service,
    product_image_service,
    product_service,
    product_video_service,
    speedy_admin_service,
    stripe_reconciliation_service,
    video_service,
)
from app.services.auth_service import get_oauth_circuit_breaker
from app.services.comment_service import CommentNotFoundError, list_all_comments
from app.services.comment_service import delete_comment as delete_comment_service
from app.services.econt_delivery_client import EcontDeliveryError, get_econt_circuit_breaker
from app.services.econt_fulfillment_service import EcontFulfillmentValidationError
from app.services.email_service import event_for_status, queue_order_email
from app.services.image_service import (
    MAX_FILE_SIZE,
    ImageProcessingError,
    InvalidImageTypeError,
    InvalidProductIdError,
    validate_image_file,
)
from app.services.image_service import (
    FileTooLargeError as ImageFileTooLargeError,
)
from app.services.order_service import (
    ADMIN_ACCOUNTING_FILTERS,
    ADMIN_REVIEW_FILTERS,
    InvalidStateTransitionError,
    ManualPaymentActionError,
    OrderNotFoundError,
    PaymentAlreadyPaidError,
    WrongPaymentMethodError,
    apply_manual_payment_action,
    get_order_admin,
    get_order_inventory_context,
    list_orders_admin,
    list_payment_events,
    mark_bank_transfer_paid,
    update_status,
    update_status_async,
)
from app.services.payment_service import StripeRefundActionError, create_stripe_refund_async
from app.services.product_service import (
    BulkTargetLimitError,
    DiscountValidationError,
    DuplicateError,
    LedgerManagedStockEditError,
    NotFoundError,
)
from app.services.return_service import (
    InvalidRestockQuantityError,
    InvalidReturnTransitionError,
    InvalidReturnValueError,
    ReturnCaseNotFoundError,
    close_return_case,
    cod_settlement_required_for_order,
    create_return_case,
    get_cod_settlement_for_order,
    get_return_case,
    inspect_return_case,
    list_refunds_for_order,
    list_return_cases_for_order,
    list_return_events_for_order,
    receive_return_case,
    record_cod_settlement,
    update_return_accounting,
)
from app.services.speedy_admin_service import SpeedyAdminValidationError
from app.services.speedy_client import (
    LabelPrintError,
    SpeedyError,
    get_speedy_circuit_breaker,
    print_label,
)
from app.services.speedy_client import (
    track_shipment_with_details as track_shipment,
)
from app.services.taxonomy_service import TaxonomyValidationError
from app.services.video_service import (
    FfmpegUnavailableError,
    InvalidVideoTypeError,
    VideoProcessingError,
    VideoTooLongError,
)
from app.services.video_service import (
    FileTooLargeError as VideoFileTooLargeError,
)
from app.services.video_service import (
    InvalidProductIdError as InvalidVideoProductIdError,
)

router = APIRouter(dependencies=[Depends(require_admin)])

_MAX_ADMIN_LABEL_FILTERS = 50
_ADMIN_PRODUCT_STATUS_FILTERS = {"all", "active", "inactive"}
_ADMIN_PRODUCT_MEDIA_FILTERS = {"any", "ready", "missing_image", "has_video", "missing_video"}
_ADMIN_PRODUCT_STOCK_FILTERS = {"any", "in_stock", "out_of_stock", "low"}
_ADMIN_PRODUCT_DISCOUNT_FILTERS = {"any", "active", "scheduled", "none"}
_ADMIN_PRODUCT_INVENTORY_MODE_FILTERS = {"legacy", "fallback", "ledger_managed"}
_ADMIN_PRODUCT_RECIPE_STATUS_FILTERS = {"active", "missing", "draft", "archived"}
_ADMIN_PRODUCT_SORTS = {
    "created_desc",
    "created_asc",
    "updated_desc",
    "updated_asc",
    "name_asc",
    "name_desc",
    "price_asc",
    "price_desc",
    "stock_asc",
    "stock_desc",
}


def _parse_admin_label_filters(labels: str | None, label: list[str] | None) -> list[str] | None:
    """Merge comma-separated and repeated admin label filters."""
    slugs: list[str] = []
    raw_values = [labels] if labels else []
    if label:
        raw_values.extend(label)

    for raw_value in raw_values:
        for raw in raw_value.split(","):
            slug = raw.strip()
            if slug and slug not in slugs:
                slugs.append(slug)
            if len(slugs) >= _MAX_ADMIN_LABEL_FILTERS:
                return slugs

    return slugs or None


def _validate_admin_product_filter(
    *, name: str, value: str | None, allowed: set[str]
) -> JSONResponse | None:
    if value is None or value in allowed:
        return None
    return error_response(
        422,
        "INVALID_PRODUCT_FILTER",
        f"Invalid {name} '{value}'. Must be one of: {', '.join(sorted(allowed))}",
    )


def _admin_products_applied_filters(
    *,
    q: str | None,
    status: str | None,
    media: str | None,
    stock: str | None,
    product_type: str | None,
    category: str | None,
    labels: list[str] | None,
    featured: bool | None,
    discount: str | None,
    inventory_mode: str | None,
    recipe_status: str | None,
    has_inventory_exceptions: bool | None,
    low_stock_threshold: int,
    sort: str | None,
) -> dict[str, str | int | bool | list[str] | None]:
    filters: dict[str, str | int | bool | list[str] | None] = {}
    if q and q.strip():
        filters["q"] = q.strip()
    if status and status != "all":
        filters["status"] = status
    if media and media != "any":
        filters["media"] = media
    if stock and stock != "any":
        filters["stock"] = stock
        if stock == "low":
            filters["low_stock_threshold"] = low_stock_threshold
    if product_type:
        filters["product_type"] = product_type
    if category:
        filters["category"] = category
    if labels:
        filters["label"] = labels
    if featured is not None:
        filters["featured"] = featured
    if discount and discount != "any":
        filters["discount"] = discount
    if inventory_mode:
        filters["inventory_mode"] = inventory_mode
    if recipe_status:
        filters["recipe_status"] = recipe_status
    if has_inventory_exceptions is not None:
        filters["has_inventory_exceptions"] = has_inventory_exceptions
    if sort:
        filters["sort"] = sort
    return filters


def _csv_cell(value: object) -> object:
    return "" if value is None else value


def _csv_response(filename: str, headers: list[str], rows: list[dict]) -> Response:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([_csv_cell(row.get(header)) for header in headers])
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={
            "Cache-Control": "no-store, no-cache",
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get(
    "/delivery-settings",
    response_model=DeliverySettingsResponse,
    summary="Get delivery method availability settings",
)
async def admin_get_delivery_settings() -> DeliverySettingsResponse:
    """Return admin-managed Speedy/Econt office/door availability switches."""
    return DeliverySettingsResponse(**delivery_settings_service.get_delivery_settings())


@router.put(
    "/delivery-settings",
    response_model=DeliverySettingsResponse,
    summary="Update delivery method availability settings",
)
async def admin_update_delivery_settings(
    body: DeliverySettingsUpdate,
) -> DeliverySettingsResponse:
    """Persist admin-managed Speedy/Econt office/door availability switches."""
    settings = delivery_settings_service.update_delivery_settings(body.model_dump())
    return DeliverySettingsResponse(**settings)


@router.get(
    "/accounting/config",
    response_model=AccountingConfigurationResponse,
    summary="Get Accounting & Finance Hub configuration",
)
def admin_get_accounting_config(response: Response) -> AccountingConfigurationResponse:
    """Return accounting settings, reviewed state, and setup exceptions."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    return accounting_config_service.get_accounting_configuration()


@router.post(
    "/accounting/config/seller-profile",
    response_model=SellerLegalProfileResponse,
    summary="Create seller legal profile version",
)
def admin_create_seller_profile(
    body: SellerLegalProfileRequest,
    request: Request,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> SellerLegalProfileResponse:
    """Create an audited seller legal profile settings version."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    return accounting_config_service.create_seller_legal_profile(
        body,
        actor_user_id=_admin_actor_id(current_admin),
        actor_email=current_admin.email if current_admin else None,
        request_id=request_id_var.get() or request.headers.get("x-request-id"),
    )


@router.post(
    "/accounting/config/vat-fiscal",
    response_model=VatFiscalSettingsResponse,
    summary="Create VAT/fiscal settings version",
)
def admin_create_vat_fiscal_settings(
    body: VatFiscalSettingsRequest,
    request: Request,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> VatFiscalSettingsResponse:
    """Create an audited accountant-reviewed VAT/fiscal settings version."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    return accounting_config_service.create_vat_fiscal_settings(
        body,
        actor_user_id=_admin_actor_id(current_admin),
        actor_email=current_admin.email if current_admin else None,
        request_id=request_id_var.get() or request.headers.get("x-request-id"),
    )


@router.put(
    "/accounting/config/category-mappings/{mapping_key}",
    response_model=CategoryMappingResponse,
    summary="Upsert accounting category mapping",
)
def admin_upsert_accounting_category_mapping(
    mapping_key: str,
    body: CategoryMappingRequest,
    request: Request,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> CategoryMappingResponse | JSONResponse:
    """Create or update an audited accountant category mapping."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    try:
        return accounting_config_service.upsert_category_mapping(
            mapping_key,
            body,
            actor_user_id=_admin_actor_id(current_admin),
            actor_email=current_admin.email if current_admin else None,
            request_id=request_id_var.get() or request.headers.get("x-request-id"),
        )
    except ValueError as exc:
        return error_response(422, "INVALID_MAPPING_KEY", str(exc))


@router.put(
    "/accounting/config/export-schema",
    response_model=ExportSchemaSettingsResponse,
    summary="Update accounting export schema settings",
)
def admin_update_accounting_export_schema(
    body: ExportSchemaSettingsRequest,
    request: Request,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> ExportSchemaSettingsResponse:
    """Update audited export schema settings for future packages."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    return accounting_config_service.update_export_schema_settings(
        body,
        actor_user_id=_admin_actor_id(current_admin),
        actor_email=current_admin.email if current_admin else None,
        request_id=request_id_var.get() or request.headers.get("x-request-id"),
    )


@router.put(
    "/accounting/config/expense-settings",
    response_model=ExpenseEvidenceSettingsResponse,
    summary="Update expense evidence settings",
)
def admin_update_expense_evidence_settings(
    body: ExpenseEvidenceSettingsRequest,
    request: Request,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> ExpenseEvidenceSettingsResponse:
    """Update audited expense evidence close/review settings."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    return accounting_config_service.update_expense_evidence_settings(
        body,
        actor_user_id=_admin_actor_id(current_admin),
        actor_email=current_admin.email if current_admin else None,
        request_id=request_id_var.get() or request.headers.get("x-request-id"),
    )


@router.put(
    "/accounting/config/product-cost-settings",
    response_model=ProductCostSettingsResponse,
    summary="Update product-cost estimate settings",
)
def admin_update_product_cost_settings(
    body: ProductCostSettingsRequest,
    request: Request,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> ProductCostSettingsResponse:
    """Update audited optional product-cost estimate settings."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    return accounting_config_service.update_product_cost_settings(
        body,
        actor_user_id=_admin_actor_id(current_admin),
        actor_email=current_admin.email if current_admin else None,
        request_id=request_id_var.get() or request.headers.get("x-request-id"),
    )


def _finance_error_response(exc: finance_period_service.FinancePeriodError) -> JSONResponse:
    return error_response(exc.status_code, exc.code, str(exc), exc.details)


@router.get(
    "/accounting/periods",
    response_model=FinancePeriodListResponse,
    summary="List finance periods",
)
def admin_list_finance_periods(
    response: Response,
    status: str | None = Query(default=None, description="Optional finance period status"),
) -> FinancePeriodListResponse:
    """Return finance periods for the Accounting & Finance Hub."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    return finance_period_service.list_periods(status=status)


@router.post(
    "/accounting/periods",
    response_model=FinancePeriodResponse,
    summary="Create finance period",
)
def admin_create_finance_period(
    body: FinancePeriodCreateRequest,
    request: Request,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> FinancePeriodResponse | JSONResponse:
    """Create an audited open finance period."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    try:
        return finance_period_service.create_period(
            body,
            actor_user_id=_admin_actor_id(current_admin),
            actor_email=current_admin.email if current_admin else None,
            request_id=request_id_var.get() or request.headers.get("x-request-id"),
        )
    except finance_period_service.FinancePeriodError as exc:
        return _finance_error_response(exc)


@router.get(
    "/accounting/periods/{period_id}",
    response_model=FinancePeriodResponse,
    summary="Get finance period",
)
def admin_get_finance_period(
    period_id: str,
    response: Response,
) -> FinancePeriodResponse | JSONResponse:
    """Return one finance period."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    try:
        return finance_period_service.get_period(period_id)
    except finance_period_service.FinancePeriodError as exc:
        return _finance_error_response(exc)


@router.post(
    "/accounting/periods/{period_id}/review",
    response_model=FinancePeriodResponse,
    summary="Start finance period review",
)
def admin_review_finance_period(
    period_id: str,
    request: Request,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> FinancePeriodResponse | JSONResponse:
    """Move a period into review, refresh exceptions, and compute totals."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    try:
        return finance_period_service.start_review(
            period_id,
            actor_user_id=_admin_actor_id(current_admin),
            actor_email=current_admin.email if current_admin else None,
            request_id=request_id_var.get() or request.headers.get("x-request-id"),
        )
    except finance_period_service.FinancePeriodError as exc:
        return _finance_error_response(exc)


@router.post(
    "/accounting/periods/{period_id}/close",
    response_model=FinancePeriodResponse,
    summary="Close finance period",
)
def admin_close_finance_period(
    period_id: str,
    request: Request,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> FinancePeriodResponse | JSONResponse:
    """Close a finance period when no blocking exceptions are open."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    try:
        return finance_period_service.close_period(
            period_id,
            actor_user_id=_admin_actor_id(current_admin),
            actor_email=current_admin.email if current_admin else None,
            request_id=request_id_var.get() or request.headers.get("x-request-id"),
        )
    except finance_period_service.FinancePeriodError as exc:
        return _finance_error_response(exc)


@router.post(
    "/accounting/periods/{period_id}/mark-exported",
    response_model=FinancePeriodResponse,
    summary="Mark finance period exported",
)
def admin_mark_finance_period_exported(
    period_id: str,
    request: Request,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> FinancePeriodResponse | JSONResponse:
    """Move a closed period to exported after package generation."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    try:
        return finance_period_service.mark_exported(
            period_id,
            actor_user_id=_admin_actor_id(current_admin),
            actor_email=current_admin.email if current_admin else None,
            request_id=request_id_var.get() or request.headers.get("x-request-id"),
        )
    except finance_period_service.FinancePeriodError as exc:
        return _finance_error_response(exc)


@router.post(
    "/accounting/periods/{period_id}/accept",
    response_model=FinancePeriodResponse,
    summary="Accept finance period",
)
def admin_accept_finance_period(
    period_id: str,
    body: FinancePeriodActionRequest,
    request: Request,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> FinancePeriodResponse | JSONResponse:
    """Record accountant acceptance for an exported period."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    try:
        return finance_period_service.accept_period(
            period_id,
            body,
            actor_user_id=_admin_actor_id(current_admin),
            actor_email=current_admin.email if current_admin else None,
            request_id=request_id_var.get() or request.headers.get("x-request-id"),
        )
    except finance_period_service.FinancePeriodError as exc:
        return _finance_error_response(exc)


@router.post(
    "/accounting/periods/{period_id}/reopen",
    response_model=FinancePeriodResponse,
    summary="Reopen finance period",
)
def admin_reopen_finance_period(
    period_id: str,
    body: FinancePeriodActionRequest,
    request: Request,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> FinancePeriodResponse | JSONResponse:
    """Reopen a period with a required reason and preserved export history."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    try:
        return finance_period_service.reopen_period(
            period_id,
            body,
            actor_user_id=_admin_actor_id(current_admin),
            actor_email=current_admin.email if current_admin else None,
            request_id=request_id_var.get() or request.headers.get("x-request-id"),
        )
    except finance_period_service.FinancePeriodError as exc:
        return _finance_error_response(exc)


@router.get(
    "/accounting/periods/{period_id}/exceptions",
    response_model=FinanceExceptionListResponse,
    summary="List finance period exceptions",
)
def admin_list_finance_exceptions(
    period_id: str,
    response: Response,
    status: str | None = Query(default=None, description="Optional exception status"),
) -> FinanceExceptionListResponse | JSONResponse:
    """Return period exceptions after refreshing engine-managed rows."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    try:
        return finance_period_service.list_exceptions(period_id, status=status)
    except finance_period_service.FinancePeriodError as exc:
        return _finance_error_response(exc)


@router.get(
    "/accounting/periods/{period_id}/ledgers/{ledger_name}",
    response_model=AccountingLedgerResponse,
    summary="Get accounting ledger",
)
def admin_get_accounting_ledger(
    period_id: str,
    ledger_name: str,
    response: Response,
    date_basis: str | None = Query(default=None, description="Ledger-specific date basis"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=100, ge=1, le=500),
) -> AccountingLedgerResponse | JSONResponse:
    """Return paginated accounting ledger rows and cent totals."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    try:
        return accounting_ledger_service.get_ledger(
            period_id,
            ledger_name,  # type: ignore[arg-type]
            date_basis=date_basis,
            page=page,
            limit=limit,
        )
    except finance_period_service.FinancePeriodError as exc:
        return _finance_error_response(exc)


@router.get(
    "/accounting/documents",
    response_model=AccountingDocumentListResponse,
    summary="List accounting documents",
)
def admin_list_accounting_documents(
    response: Response,
    order_id: str | None = Query(default=None),
    refund_id: str | None = Query(default=None),
    period_id: str | None = Query(default=None),
) -> AccountingDocumentListResponse:
    """List accounting document references with optional linked-object filters."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    return accounting_document_service.list_documents(
        order_id=order_id,
        refund_id=refund_id,
        period_id=period_id,
    )


@router.get(
    "/accounting/orders/{order_id}/documents",
    response_model=AccountingDocumentListResponse,
    summary="List accounting documents for order",
)
def admin_list_order_accounting_documents(
    order_id: str,
    response: Response,
) -> AccountingDocumentListResponse:
    """List invoice/fiscal/external document references linked to an order."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    return accounting_document_service.list_documents(order_id=order_id)


@router.post(
    "/accounting/documents",
    response_model=AccountingDocumentResponse,
    summary="Create accounting document reference",
)
def admin_create_accounting_document(
    body: AccountingDocumentRequest,
    request: Request,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> AccountingDocumentResponse | JSONResponse:
    """Create an audited accounting document reference."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    try:
        return accounting_document_service.create_document(
            body,
            actor_user_id=_admin_actor_id(current_admin),
            actor_email=current_admin.email if current_admin else None,
            request_id=request_id_var.get() or request.headers.get("x-request-id"),
        )
    except finance_period_service.FinancePeriodError as exc:
        return _finance_error_response(exc)


@router.put(
    "/accounting/documents/{document_id}",
    response_model=AccountingDocumentResponse,
    summary="Update accounting document reference",
)
def admin_update_accounting_document(
    document_id: str,
    body: AccountingDocumentRequest,
    request: Request,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> AccountingDocumentResponse | JSONResponse:
    """Replace an audited accounting document reference."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    try:
        return accounting_document_service.update_document(
            document_id,
            body,
            actor_user_id=_admin_actor_id(current_admin),
            actor_email=current_admin.email if current_admin else None,
            request_id=request_id_var.get() or request.headers.get("x-request-id"),
        )
    except finance_period_service.FinancePeriodError as exc:
        return _finance_error_response(exc)


@router.get(
    "/accounting/expenses",
    response_model=ExpenseEvidenceListResponse,
    summary="List expense evidence",
)
def admin_list_expense_evidence(
    response: Response,
    category_key: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
) -> ExpenseEvidenceListResponse:
    """List supplier invoice/receipt evidence records."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    return expense_product_cost_service.list_expenses(
        category_key=category_key,
        review_status=review_status,
    )


@router.post(
    "/accounting/expenses",
    response_model=ExpenseEvidenceResponse,
    summary="Create expense evidence",
)
def admin_create_expense_evidence(
    body: ExpenseEvidenceRequest,
    request: Request,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> ExpenseEvidenceResponse | JSONResponse:
    """Create audited supplier purchase/expense evidence."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    try:
        return expense_product_cost_service.create_expense(
            body,
            actor_user_id=_admin_actor_id(current_admin),
            actor_email=current_admin.email if current_admin else None,
            request_id=request_id_var.get() or request.headers.get("x-request-id"),
        )
    except finance_period_service.FinancePeriodError as exc:
        return _finance_error_response(exc)


@router.put(
    "/accounting/expenses/{expense_id}",
    response_model=ExpenseEvidenceResponse,
    summary="Update expense evidence",
)
def admin_update_expense_evidence(
    expense_id: str,
    body: ExpenseEvidenceRequest,
    request: Request,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> ExpenseEvidenceResponse | JSONResponse:
    """Replace audited supplier purchase/expense evidence."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    try:
        return expense_product_cost_service.update_expense(
            expense_id,
            body,
            actor_user_id=_admin_actor_id(current_admin),
            actor_email=current_admin.email if current_admin else None,
            request_id=request_id_var.get() or request.headers.get("x-request-id"),
        )
    except finance_period_service.FinancePeriodError as exc:
        return _finance_error_response(exc)


@router.patch(
    "/accounting/expenses/{expense_id}/payment-status",
    response_model=ExpenseEvidenceResponse,
    summary="Update expense payment status",
)
def admin_update_expense_payment_status(
    expense_id: str,
    body: ExpensePaymentStatusRequest,
    request: Request,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> ExpenseEvidenceResponse | JSONResponse:
    """Update an expense payment status with an audited reason."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    try:
        return expense_product_cost_service.update_expense_payment_status(
            expense_id,
            body,
            actor_user_id=_admin_actor_id(current_admin),
            actor_email=current_admin.email if current_admin else None,
            request_id=request_id_var.get() or request.headers.get("x-request-id"),
        )
    except finance_period_service.FinancePeriodError as exc:
        return _finance_error_response(exc)


@router.get(
    "/accounting/product-costs",
    response_model=ProductCostVersionListResponse,
    summary="List product-cost versions",
)
def admin_list_product_cost_versions(
    response: Response,
    product_id: str | None = Query(default=None),
) -> ProductCostVersionListResponse:
    """List manual/recipe/imported product-cost estimate versions."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    return expense_product_cost_service.list_product_costs(product_id=product_id)


@router.post(
    "/accounting/product-costs",
    response_model=ProductCostVersionResponse,
    summary="Create product-cost version",
)
def admin_create_product_cost_version(
    body: ProductCostVersionRequest,
    request: Request,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> ProductCostVersionResponse:
    """Create audited product-cost estimate version."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    return expense_product_cost_service.create_product_cost(
        body,
        actor_user_id=_admin_actor_id(current_admin),
        actor_email=current_admin.email if current_admin else None,
        request_id=request_id_var.get() or request.headers.get("x-request-id"),
    )


@router.put(
    "/accounting/product-costs/{cost_version_id}",
    response_model=ProductCostVersionResponse,
    summary="Update product-cost version",
)
def admin_update_product_cost_version(
    cost_version_id: str,
    body: ProductCostVersionRequest,
    request: Request,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> ProductCostVersionResponse | JSONResponse:
    """Replace audited product-cost estimate version and components."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    try:
        return expense_product_cost_service.update_product_cost(
            cost_version_id,
            body,
            actor_user_id=_admin_actor_id(current_admin),
            actor_email=current_admin.email if current_admin else None,
            request_id=request_id_var.get() or request.headers.get("x-request-id"),
        )
    except finance_period_service.FinancePeriodError as exc:
        return _finance_error_response(exc)


@router.get(
    "/accounting/product-costs/effective",
    response_model=ProductCostVersionResponse | None,
    summary="Lookup effective product-cost version",
)
def admin_get_effective_product_cost(
    response: Response,
    product_id: str = Query(...),
    effective_date: str = Query(...),
) -> ProductCostVersionResponse | None:
    """Return the latest product-cost version effective on a date."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    return expense_product_cost_service.effective_product_cost(product_id, effective_date)


@router.get(
    "/accounting/product-costs/missing",
    response_model=MissingProductCostDiagnosticsResponse,
    summary="Get missing product-cost diagnostics",
)
def admin_get_missing_product_costs(
    response: Response,
    period_id: str = Query(...),
) -> MissingProductCostDiagnosticsResponse | JSONResponse:
    """List sold products in a period without an effective cost version."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    try:
        return expense_product_cost_service.missing_product_costs(period_id)
    except finance_period_service.FinancePeriodError as exc:
        return _finance_error_response(exc)


@router.get(
    "/accounting/exports",
    response_model=FinanceExportPackageListResponse,
    summary="List accounting export packages",
)
def admin_list_accounting_exports(
    response: Response,
    period_id: str | None = Query(default=None),
) -> FinanceExportPackageListResponse:
    """List generated accountant export packages."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    return accounting_export_service.list_export_packages(period_id=period_id)


@router.post(
    "/accounting/periods/{period_id}/exports",
    response_model=FinanceExportPackageResponse,
    summary="Generate accounting export package",
)
def admin_generate_accounting_export(
    period_id: str,
    request: Request,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> FinanceExportPackageResponse | JSONResponse:
    """Generate immutable XLSX/CSV/manifest package for a closed period."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    try:
        return accounting_export_service.generate_export_package(
            period_id,
            actor_user_id=_admin_actor_id(current_admin),
            actor_email=current_admin.email if current_admin else None,
            request_id=request_id_var.get() or request.headers.get("x-request-id"),
        )
    except finance_period_service.FinancePeriodError as exc:
        return _finance_error_response(exc)


@router.get(
    "/accounting/exports/{export_id}/download",
    response_model=None,
    summary="Download accounting export package file",
)
def admin_download_accounting_export(
    export_id: str,
    response: Response,
    file: str = Query(default="xlsx", description="xlsx, manifest, or a CSV file name"),
) -> FileResponse | JSONResponse:
    """Download one file from an export package by export id."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    try:
        path = accounting_export_service.resolve_download_path(export_id, file)
    except finance_period_service.FinancePeriodError as exc:
        return _finance_error_response(exc)
    return FileResponse(
        path,
        filename=path.name,
        headers={"Cache-Control": "no-store, no-cache"},
    )


@router.post(
    "/accounting/exports/{export_id}/accept",
    response_model=FinanceExportPackageResponse,
    summary="Accept accounting export package",
)
def admin_accept_accounting_export(
    export_id: str,
    body: AccountantAcceptanceRequest,
    request: Request,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> FinanceExportPackageResponse | JSONResponse:
    """Record accountant acceptance for the current export package."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    try:
        return accounting_export_service.accept_export_package(
            export_id,
            body,
            actor_user_id=_admin_actor_id(current_admin),
            actor_email=current_admin.email if current_admin else None,
            request_id=request_id_var.get() or request.headers.get("x-request-id"),
        )
    except finance_period_service.FinancePeriodError as exc:
        return _finance_error_response(exc)


@router.get(
    "/accounting/stripe/import-status",
    response_model=StripePayoutImportStatusResponse,
    summary="Get Stripe payout import status",
)
def admin_get_stripe_import_status(response: Response) -> StripePayoutImportStatusResponse:
    """Return aggregate Stripe balance transaction reconciliation status."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    return stripe_reconciliation_service.import_status()


@router.post(
    "/accounting/stripe/sync",
    response_model=StripeBalanceImportResponse,
    summary="Sync Stripe balance transactions",
)
async def admin_sync_stripe_balance_transactions(
    request: Request,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
    limit: int = Query(default=100, ge=1, le=500),
) -> StripeBalanceImportResponse | JSONResponse:
    """Import Stripe balance transactions through the Stripe SDK when configured."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    try:
        return await run_in_threadpool(
            stripe_reconciliation_service.sync_from_stripe,
            limit=limit,
            actor_user_id=_admin_actor_id(current_admin),
            actor_email=current_admin.email if current_admin else None,
            request_id=request_id_var.get() or request.headers.get("x-request-id"),
        )
    except finance_period_service.FinancePeriodError as exc:
        return _finance_error_response(exc)


@router.post(
    "/accounting/stripe/manual-import",
    response_model=StripeBalanceImportResponse,
    summary="Import Stripe balance transactions from CSV",
)
async def admin_import_stripe_balance_csv(
    request: Request,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
    file: UploadFile = File(...),
) -> StripeBalanceImportResponse | JSONResponse:
    """Import Stripe balance/payout rows from an admin-uploaded CSV file."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    content = await file.read()
    try:
        return await run_in_threadpool(
            stripe_reconciliation_service.import_balance_csv,
            content,
            actor_user_id=_admin_actor_id(current_admin),
            actor_email=current_admin.email if current_admin else None,
            request_id=request_id_var.get() or request.headers.get("x-request-id"),
        )
    except finance_period_service.FinancePeriodError as exc:
        return _finance_error_response(exc)


@router.post(
    "/accounting/stripe/matches/{balance_transaction_id}/review",
    response_model=None,
    summary="Review Stripe balance transaction match",
)
def admin_review_stripe_balance_match(
    balance_transaction_id: str,
    body: StripePayoutMatchReviewRequest,
    request: Request,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> dict[str, object] | JSONResponse:
    """Manually update reconciliation status for one Stripe balance transaction."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    try:
        return stripe_reconciliation_service.review_match(
            balance_transaction_id,
            body,
            actor_user_id=_admin_actor_id(current_admin),
            actor_email=current_admin.email if current_admin else None,
            request_id=request_id_var.get() or request.headers.get("x-request-id"),
        )
    except finance_period_service.FinancePeriodError as exc:
        return _finance_error_response(exc)


@router.post(
    "/accounting/exceptions/{exception_id}/resolve",
    response_model=FinanceExceptionResponse,
    summary="Resolve finance exception",
)
def admin_resolve_finance_exception(
    exception_id: str,
    body: FinanceExceptionActionRequest,
    request: Request,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> FinanceExceptionResponse | JSONResponse:
    """Resolve an exception with an audited admin reason."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    try:
        return finance_period_service.resolve_exception(
            exception_id,
            body,
            actor_user_id=_admin_actor_id(current_admin),
            actor_email=current_admin.email if current_admin else None,
            request_id=request_id_var.get() or request.headers.get("x-request-id"),
        )
    except finance_period_service.FinancePeriodError as exc:
        return _finance_error_response(exc)


@router.post(
    "/accounting/exceptions/{exception_id}/waive",
    response_model=FinanceExceptionResponse,
    summary="Waive finance exception",
)
def admin_waive_finance_exception(
    exception_id: str,
    body: FinanceExceptionActionRequest,
    request: Request,
    response: Response,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> FinanceExceptionResponse | JSONResponse:
    """Waive an exception with an audited admin reason."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    try:
        return finance_period_service.waive_exception(
            exception_id,
            body,
            actor_user_id=_admin_actor_id(current_admin),
            actor_email=current_admin.email if current_admin else None,
            request_id=request_id_var.get() or request.headers.get("x-request-id"),
        )
    except finance_period_service.FinancePeriodError as exc:
        return _finance_error_response(exc)


@router.get(
    "/econt/settings",
    response_model=EcontSettingsResponse,
    summary="Get Econt integration settings",
    description="Return admin-safe Econt settings and credential configured state. "
    "Raw private keys are never returned.",
)
def admin_get_econt_settings() -> EcontSettingsResponse:
    """Read Econt settings for the admin settings panel."""
    return econt_settings_service.get_econt_settings()


@router.patch(
    "/econt/settings",
    response_model=EcontSettingsResponse,
    summary="Update Econt integration settings",
    description="Patch non-secret Econt settings. Private keys remain env-backed or encrypted "
    "through separate secret storage.",
)
def admin_update_econt_settings(body: EcontSettingsUpdate) -> EcontSettingsResponse:
    """Update non-secret Econt settings."""
    return econt_settings_service.update_econt_settings(body)


@router.post(
    "/econt/test-connection",
    response_model=EcontConnectionTestResponse,
    summary="Validate Econt configuration",
    description="Validate current Econt settings without creating a shipment and store the "
    "admin-safe health result.",
)
async def admin_test_econt_connection() -> EcontConnectionTestResponse:
    """Run a safe Econt configuration readiness check."""
    return await econt_settings_service.test_econt_configuration()


def _econt_error_response(exc: EcontDeliveryError) -> JSONResponse:
    if exc.category in {"config", "auth", "validation"}:
        status_code = 422
    elif exc.category == "unexpected_response":
        status_code = 502
    else:
        status_code = 503
    return error_response(
        status_code,
        f"ECONT_{exc.category.upper()}",
        str(exc),
        exc.to_safe_dict(),
    )


def _admin_actor_id(current_admin: UserResponse | None) -> str | None:
    return current_admin.id if current_admin else None


def _speedy_error_response(exc: SpeedyError) -> JSONResponse:
    if isinstance(exc, LabelPrintError):
        return error_response(502, "LABEL_PRINT_FAILED", str(exc), exc.to_safe_dict())
    if exc.category in {"config", "auth", "validation"}:
        status_code = 422
    elif exc.category == "unexpected_response":
        status_code = 502
    else:
        status_code = 503
    return error_response(
        status_code,
        f"SPEEDY_{exc.category.upper()}",
        str(exc),
        exc.to_safe_dict(),
    )


def _speedy_validation_response(exc: SpeedyAdminValidationError) -> JSONResponse:
    if "no_speedy_waybill" in exc.blockers:
        return error_response(404, "NO_SPEEDY_WAYBILL", str(exc), {"blockers": exc.blockers})
    return error_response(422, "SPEEDY_NOT_READY", str(exc), {"blockers": exc.blockers})


@router.get(
    "/speedy",
    response_model=SpeedyAdminOverviewResponse,
    summary="Speedy admin overview",
)
async def admin_get_speedy_overview(
    order_id: str | None = Query(default=None, description="Optional local order focus"),
) -> SpeedyAdminOverviewResponse:
    with get_db() as conn:
        overview = await speedy_admin_service.get_overview(conn, order_id=order_id)
    return SpeedyAdminOverviewResponse(**overview)


@router.get(
    "/speedy/health",
    response_model=SpeedyHealthResponse,
    summary="Speedy integration health",
)
async def admin_get_speedy_health() -> SpeedyHealthResponse:
    with get_db() as conn:
        health = await speedy_admin_service.get_health(conn)
    return SpeedyHealthResponse(**health)


@router.get(
    "/speedy/orders",
    response_model=SpeedyQueuesResponse,
    summary="Speedy operational order queues",
)
def admin_get_speedy_orders(
    order_id: str | None = Query(default=None, description="Optional local order focus"),
) -> SpeedyQueuesResponse:
    with get_db() as conn:
        queues = speedy_admin_service.get_queues(conn, order_id=order_id)
    return SpeedyQueuesResponse(**queues)


@router.get(
    "/speedy/events",
    response_model=list[SpeedyEventResponse],
    summary="Recent Speedy operation events",
)
def admin_get_speedy_events(
    limit: int = Query(default=25, ge=1, le=100),
) -> list[SpeedyEventResponse]:
    with get_db() as conn:
        events = speedy_admin_service.list_events(conn, limit=limit)
    return [SpeedyEventResponse(**event) for event in events]


@router.get(
    "/speedy/metrics",
    response_model=SpeedyMetricsResponse,
    summary="Speedy operational metrics",
)
def admin_get_speedy_metrics() -> SpeedyMetricsResponse:
    with get_db() as conn:
        metrics = speedy_admin_service.get_metrics(conn)
    return SpeedyMetricsResponse(**metrics)


@router.get(
    "/speedy/offices/refresh-status",
    response_model=SpeedyOfficeRefreshStatusResponse,
    summary="Speedy office refresh status",
)
def admin_get_speedy_office_refresh_status() -> SpeedyOfficeRefreshStatusResponse:
    with get_db() as conn:
        status = speedy_admin_service.get_office_refresh_status(conn)
    return SpeedyOfficeRefreshStatusResponse(**status)


@router.post(
    "/speedy/orders/{order_id}/ship",
    response_model=SpeedyActionResponse,
    summary="Create/reuse Speedy waybill and mark order shipped",
)
async def admin_speedy_create_waybill(
    order_id: str,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> SpeedyActionResponse | JSONResponse:
    with get_db() as conn:
        try:
            result = await speedy_admin_service.create_or_reuse_waybill(
                conn,
                order_id,
                actor_user_id=_admin_actor_id(current_admin),
            )
        except SpeedyAdminValidationError as exc:
            return _speedy_validation_response(exc)
        except SpeedyError as exc:
            return _speedy_error_response(exc)

        event = event_for_status("shipped")
        if event is not None and result.get("status_updated_to") == "shipped":
            order_data = get_order_admin(conn, order_id)
            queue_order_email(conn, order_id, event, order_data["customer_email"])
    return SpeedyActionResponse(**result)


@router.get(
    "/speedy/orders/{order_id}/label",
    response_model=None,
    summary="Print Speedy label from Speedy admin API",
)
async def admin_speedy_print_label(
    order_id: str,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> Response | JSONResponse:
    with get_db() as conn:
        try:
            shipment_number, pdf = await speedy_admin_service.print_order_label(
                conn,
                order_id,
                actor_user_id=_admin_actor_id(current_admin),
                print_label_func=print_label,
            )
        except SpeedyAdminValidationError as exc:
            return _speedy_validation_response(exc)
        except SpeedyError as exc:
            return _speedy_error_response(exc)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="label-{shipment_number}.pdf"'},
    )


@router.post(
    "/speedy/orders/{order_id}/track",
    response_model=SpeedyActionResponse,
    summary="Refresh Speedy tracking from Speedy admin API",
)
async def admin_speedy_refresh_tracking(
    order_id: str,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> SpeedyActionResponse | JSONResponse:
    with get_db() as conn:
        try:
            result = await courier_polling_service.refresh_order_now(
                conn,
                order_id,
                provider="speedy",
                actor_user_id=_admin_actor_id(current_admin),
                speedy_track_func=track_shipment,
            )
        except courier_polling_service.CourierPollingValidationError as exc:
            if "courier_provider_mismatch" in exc.blockers:
                return _speedy_validation_response(
                    SpeedyAdminValidationError(
                        "Order has no Speedy waybill",
                        blockers=["no_speedy_waybill"],
                    )
                )
            return error_response(
                422,
                "COURIER_REFRESH_BLOCKED",
                str(exc),
                {"blockers": exc.blockers},
            )
        except SpeedyAdminValidationError as exc:
            return _speedy_validation_response(exc)
        except SpeedyError as exc:
            return _speedy_error_response(exc)
    return SpeedyActionResponse(**result)


@router.post(
    "/speedy/shipments/search",
    response_model=SpeedyShipmentSearchResponse,
    summary="Search Speedy shipments by local reference",
)
async def admin_speedy_search_shipments(
    body: SpeedyShipmentSearchRequest,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> SpeedyShipmentSearchResponse | JSONResponse:
    with get_db() as conn:
        try:
            result = await speedy_admin_service.search_shipments(
                conn,
                body.reference,
                include_returns=body.include_returns,
                shipments_only=body.shipments_only,
                actor_user_id=_admin_actor_id(current_admin),
            )
        except SpeedyError as exc:
            return _speedy_error_response(exc)
    return SpeedyShipmentSearchResponse(**result)


@router.post(
    "/speedy/shipments/info",
    response_model=SpeedyShipmentInfoResponse,
    summary="Fetch Speedy shipment information",
)
async def admin_speedy_shipment_info(
    body: SpeedyShipmentInfoRequest,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> SpeedyShipmentInfoResponse | JSONResponse:
    with get_db() as conn:
        try:
            result = await speedy_admin_service.shipment_info(
                conn,
                body.shipment_ids,
                actor_user_id=_admin_actor_id(current_admin),
            )
        except SpeedyError as exc:
            return _speedy_error_response(exc)
    return SpeedyShipmentInfoResponse(**result)


@router.post(
    "/speedy/orders/{order_id}/cancel-shipment",
    response_model=SpeedyActionResponse,
    summary="Cancel Speedy shipment where safe",
)
async def admin_speedy_cancel_shipment(
    order_id: str,
    body: SpeedyCancelShipmentRequest,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> SpeedyActionResponse | JSONResponse:
    with get_db() as conn:
        try:
            result = await speedy_admin_service.cancel_order_shipment(
                conn,
                order_id,
                comment=body.comment,
                actor_user_id=_admin_actor_id(current_admin),
            )
        except SpeedyAdminValidationError as exc:
            return _speedy_validation_response(exc)
        except SpeedyError as exc:
            return _speedy_error_response(exc)
    return SpeedyActionResponse(**result)


@router.post(
    "/speedy/pickup/terms",
    response_model=SpeedyPickupTermsResponse,
    summary="Get Speedy pickup terms",
)
async def admin_speedy_pickup_terms(
    body: SpeedyPickupTermsRequest,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> SpeedyPickupTermsResponse | JSONResponse:
    with get_db() as conn:
        try:
            result = await speedy_admin_service.pickup_terms_for_shipments(
                conn,
                body.shipment_ids,
                starting_date_utc_ms=body.starting_date_utc_ms,
                actor_user_id=_admin_actor_id(current_admin),
            )
        except SpeedyAdminValidationError as exc:
            return _speedy_validation_response(exc)
        except SpeedyError as exc:
            return _speedy_error_response(exc)
    return SpeedyPickupTermsResponse(**result)


@router.post(
    "/speedy/pickup",
    response_model=SpeedyPickupResponse,
    summary="Request Speedy pickup",
)
async def admin_speedy_request_pickup(
    body: SpeedyPickupRequest,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> SpeedyPickupResponse | JSONResponse:
    with get_db() as conn:
        try:
            result = await speedy_admin_service.request_pickup(
                conn,
                shipment_ids=body.shipment_ids,
                pickup_datetime=body.pickup_datetime,
                visit_end_time=body.visit_end_time,
                contact_name=body.contact_name,
                phone=body.phone,
                actor_user_id=_admin_actor_id(current_admin),
            )
        except SpeedyAdminValidationError as exc:
            return _speedy_validation_response(exc)
        except SpeedyError as exc:
            return _speedy_error_response(exc)
    return SpeedyPickupResponse(**result)


@router.get(
    "/orders/{order_id}/econt/readiness",
    response_model=EcontOrderFulfillmentResponse,
    summary="Validate Econt readiness for an order",
    description="Return admin-safe readiness blockers and current Econt shipment metadata.",
)
def admin_get_econt_order_readiness(order_id: str) -> EcontOrderFulfillmentResponse:
    with get_db() as conn:
        state = econt_fulfillment_service.get_fulfillment_state(conn, order_id)
    return EcontOrderFulfillmentResponse(**state)


@router.patch(
    "/orders/{order_id}/econt/repair",
    response_model=EcontOrderFulfillmentResponse,
    summary="Repair Econt fulfillment fields before label creation",
)
def admin_repair_econt_order(
    order_id: str,
    body: EcontOrderRepairRequest,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> EcontOrderFulfillmentResponse | JSONResponse:
    with get_db() as conn:
        try:
            state = econt_fulfillment_service.repair_order_fields(
                conn,
                order_id,
                office_code=body.office_code,
                recipient_phone=body.recipient_phone,
                pack_count=body.pack_count,
                shipment_description=body.shipment_description,
                payment_side=body.payment_side,
                actor_user_id=_admin_actor_id(current_admin),
            )
        except EcontFulfillmentValidationError as exc:
            return error_response(422, "ECONT_REPAIR_BLOCKED", str(exc), {"blockers": exc.blockers})
    return EcontOrderFulfillmentResponse(**state)


@router.post(
    "/orders/{order_id}/econt/sync",
    response_model=EcontFulfillmentActionResponse,
    summary="Sync local order to Econt",
)
async def admin_sync_econt_order(
    order_id: str,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> EcontFulfillmentActionResponse | JSONResponse:
    with get_db() as conn:
        try:
            result = await econt_fulfillment_service.sync_order(
                conn,
                order_id,
                actor_user_id=_admin_actor_id(current_admin),
            )
        except EcontFulfillmentValidationError as exc:
            return error_response(422, "ECONT_NOT_READY", str(exc), {"blockers": exc.blockers})
        except EcontDeliveryError as exc:
            return _econt_error_response(exc)
    return EcontFulfillmentActionResponse(order_id=order_id, action="sync_order", **result)


@router.post(
    "/orders/{order_id}/econt/label",
    response_model=EcontFulfillmentActionResponse,
    summary="Create Econt AWB label",
)
async def admin_create_econt_label(
    order_id: str,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> EcontFulfillmentActionResponse | JSONResponse:
    with get_db() as conn:
        try:
            result = await econt_fulfillment_service.create_label(
                conn,
                order_id,
                actor_user_id=_admin_actor_id(current_admin),
            )
        except EcontFulfillmentValidationError as exc:
            return error_response(422, "ECONT_NOT_READY", str(exc), {"blockers": exc.blockers})
        except EcontDeliveryError as exc:
            return _econt_error_response(exc)
    return EcontFulfillmentActionResponse(order_id=order_id, action="create_label", **result)


@router.post(
    "/orders/{order_id}/econt/ship",
    response_model=EcontFulfillmentActionResponse,
    summary="Create Econt AWB label and mark order shipped",
)
async def admin_create_and_ship_econt_order(
    order_id: str,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> EcontFulfillmentActionResponse | JSONResponse:
    with get_db() as conn:
        try:
            result = await econt_fulfillment_service.create_label_and_mark_shipped(
                conn,
                order_id,
                actor_user_id=_admin_actor_id(current_admin),
            )
        except EcontFulfillmentValidationError as exc:
            return error_response(422, "ECONT_NOT_READY", str(exc), {"blockers": exc.blockers})
        except EcontDeliveryError as exc:
            return _econt_error_response(exc)

        event = event_for_status("shipped")
        if event is not None:
            order_data = get_order_admin(conn, order_id)
            queue_order_email(conn, order_id, event, order_data["customer_email"])

    return EcontFulfillmentActionResponse(
        order_id=order_id,
        action="create_label_and_ship",
        **result,
    )


@router.delete(
    "/orders/{order_id}/econt/label",
    response_model=EcontFulfillmentActionResponse,
    summary="Delete Econt AWB label where safe",
)
async def admin_delete_econt_label(
    order_id: str,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> EcontFulfillmentActionResponse | JSONResponse:
    with get_db() as conn:
        try:
            result = await econt_fulfillment_service.delete_label(
                conn,
                order_id,
                actor_user_id=_admin_actor_id(current_admin),
            )
        except EcontFulfillmentValidationError as exc:
            return error_response(422, "ECONT_NOT_READY", str(exc), {"blockers": exc.blockers})
        except EcontDeliveryError as exc:
            return _econt_error_response(exc)
    return EcontFulfillmentActionResponse(order_id=order_id, action="delete_label", **result)


@router.post(
    "/orders/{order_id}/econt/trace",
    response_model=EcontFulfillmentActionResponse,
    summary="Refresh Econt shipment trace",
)
async def admin_refresh_econt_trace(
    order_id: str,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> EcontFulfillmentActionResponse | JSONResponse:
    with get_db() as conn:
        try:
            result = await courier_polling_service.refresh_order_now(
                conn,
                order_id,
                provider="econt",
                actor_user_id=_admin_actor_id(current_admin),
            )
        except courier_polling_service.CourierPollingValidationError as exc:
            return error_response(
                422,
                "COURIER_REFRESH_BLOCKED",
                str(exc),
                {"blockers": exc.blockers},
            )
        except EcontFulfillmentValidationError as exc:
            return error_response(422, "ECONT_NOT_READY", str(exc), {"blockers": exc.blockers})
        except EcontDeliveryError as exc:
            return _econt_error_response(exc)
    return EcontFulfillmentActionResponse(order_id=order_id, action="refresh_trace", **result)


@router.post(
    "/orders/{order_id}/econt/manual-status",
    response_model=EcontFulfillmentActionResponse,
    summary="Record manual Econt courier status",
)
def admin_record_econt_manual_status(
    order_id: str,
    body: EcontManualStatusRequest,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> EcontFulfillmentActionResponse | JSONResponse:
    with get_db() as conn:
        try:
            result = econt_fulfillment_service.record_manual_status(
                conn,
                order_id,
                courier_status=body.courier_status,
                tracking_number=body.tracking_number,
                tracking_url=body.tracking_url,
                notes=body.notes,
                actor_user_id=_admin_actor_id(current_admin),
            )
        except EcontFulfillmentValidationError as exc:
            return error_response(
                422,
                "ECONT_MANUAL_STATUS_BLOCKED",
                str(exc),
                {"blockers": exc.blockers},
            )
    return EcontFulfillmentActionResponse(order_id=order_id, action="manual_status", **result)


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
        return error_response(409, "DUPLICATE", "Product with this ID already exists")
    except TaxonomyValidationError as e:
        return error_response(422, "INVALID_TAXONOMY", str(e))

    return ProductAdminResponse(**product)


@router.get(
    "/products",
    response_model=ProductAdminListResponse,
    summary="List all products (admin)",
    description=(
        "List products including inactive ones. Supports search, filters, sorting, and pagination."
    ),
)
async def admin_list_products(
    q: str | None = Query(default=None, max_length=200, description="Search product id/name/text"),
    status: str | None = Query(default=None, description="Filter by active status"),
    media: str | None = Query(default=None, description="Filter by image/video readiness"),
    stock: str | None = Query(default=None, description="Filter by stock state"),
    product_type: str | None = Query(default=None, description="Filter by product type slug"),
    category: str | None = Query(default=None, description="Filter by category/tier slug"),
    labels: str | None = Query(
        default=None, description="Comma-separated label slugs (AND semantics)"
    ),
    label: list[str] | None = Query(
        default=None, description="Repeated label slug filter (AND semantics)"
    ),
    featured: bool | None = Query(default=None, description="Filter by featured flag"),
    discount: str | None = Query(default=None, description="Filter by discount state"),
    inventory_mode: str | None = Query(default=None, description="Filter by inventory mode"),
    recipe_status: str | None = Query(default=None, description="Filter by recipe status"),
    has_inventory_exceptions: bool | None = Query(
        default=None, description="Filter products with open inventory exceptions"
    ),
    low_stock_threshold: int = Query(
        default=product_service.DEFAULT_ADMIN_LOW_STOCK_THRESHOLD,
        ge=0,
        le=MAX_STOCK,
        description="Stock threshold used when stock=low",
    ),
    sort: str | None = Query(default=None, description="Sort order"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> ProductAdminListResponse | JSONResponse:
    """List all products (active and inactive) with pagination."""
    limit = min(limit, 100)
    for name, value, allowed in (
        ("status", status, _ADMIN_PRODUCT_STATUS_FILTERS),
        ("media", media, _ADMIN_PRODUCT_MEDIA_FILTERS),
        ("stock", stock, _ADMIN_PRODUCT_STOCK_FILTERS),
        ("discount", discount, _ADMIN_PRODUCT_DISCOUNT_FILTERS),
        ("inventory_mode", inventory_mode, _ADMIN_PRODUCT_INVENTORY_MODE_FILTERS),
        ("recipe_status", recipe_status, _ADMIN_PRODUCT_RECIPE_STATUS_FILTERS),
        ("sort", sort, _ADMIN_PRODUCT_SORTS),
    ):
        invalid = _validate_admin_product_filter(name=name, value=value, allowed=allowed)
        if invalid is not None:
            return invalid

    label_list = _parse_admin_label_filters(labels, label)
    products, total = product_service.list_products_admin(
        q=q.strip() if q and q.strip() else None,
        status=cast(product_service.AdminProductStatusFilter | None, status),
        media=cast(product_service.AdminProductMediaFilter | None, media),
        stock=cast(product_service.AdminProductStockFilter | None, stock),
        product_type=product_type,
        category=category,
        labels=label_list,
        featured=featured,
        discount=cast(product_service.AdminProductDiscountFilter | None, discount),
        inventory_mode=cast(product_service.AdminProductInventoryModeFilter | None, inventory_mode),
        recipe_status=cast(product_service.AdminProductRecipeStatusFilter | None, recipe_status),
        has_inventory_exceptions=has_inventory_exceptions,
        low_stock_threshold=low_stock_threshold,
        sort=cast(product_service.AdminProductSort | None, sort),
        page=page,
        limit=limit,
    )

    return ProductAdminListResponse(
        products=[ProductAdminResponse(**p) for p in products],
        total=total,
        page=page,
        limit=limit,
        applied_filters=_admin_products_applied_filters(
            q=q,
            status=status,
            media=media,
            stock=stock,
            product_type=product_type,
            category=category,
            labels=label_list,
            featured=featured,
            discount=discount,
            inventory_mode=inventory_mode,
            recipe_status=recipe_status,
            has_inventory_exceptions=has_inventory_exceptions,
            low_stock_threshold=low_stock_threshold,
            sort=sort,
        ),
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
        return error_response(422, "BULK_TARGET_LIMIT_EXCEEDED", str(e))

    if not target_ids:
        return error_response(422, "VALIDATION_ERROR", "target resolves to no products")

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
        return error_response(404, "NOT_FOUND", "Product not found")

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
        return error_response(404, "NOT_FOUND", "Product not found")
    except TaxonomyValidationError as e:
        return error_response(422, "INVALID_TAXONOMY", str(e))
    except DiscountValidationError as e:
        return error_response(422, "VALIDATION_ERROR", str(e))
    except LedgerManagedStockEditError as e:
        return error_response(
            422,
            "LEDGER_STOCK_EDIT_BLOCKED",
            str(e),
            details={"product_id": e.product_id},
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
        return error_response(404, "NOT_FOUND", "Product not found")

    return ProductAdminResponse(**product)


# Required CSV headers — accept both legacy (name/description) and new (name_en/description_en)
_REQUIRED_CSV_HEADERS_NEW = {"id", "name_en", "price_cents"}
_REQUIRED_CSV_HEADERS_LEGACY = {"id", "name", "price_cents"}
_OPTIONAL_CSV_HEADERS = {
    "description",
    "description_en",
    "description_bg",
    "name_bg",
    "safety_warnings_en",
    "safety_warnings_bg",
    "care_instructions_en",
    "care_instructions_bg",
    "category",
    "product_type",
    "labels",
    "stock",
    "image_url",
}

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
        "materials, days_to_craft, safety_warnings_en, safety_warnings_bg, "
        "care_instructions_en, care_instructions_bg."
    ),
)
async def admin_import_products(
    file: UploadFile = File(..., description="CSV file with product data"),
) -> CSVImportResponse | JSONResponse:
    """Bulk import products via CSV upload with upsert semantics.

    Required columns: id, name_en (or legacy 'name'), price_cents
    Optional columns: name_bg, description_en (or legacy 'description'),
                      description_bg, category, product_type, labels, stock,
                      image_url, weight_grams, is_active, is_featured, materials,
                      days_to_craft, safety_warnings_en, safety_warnings_bg,
                      care_instructions_en, care_instructions_bg

    Taxonomy columns are managed SLUGS, not free text (breaking change from the
    legacy free-text `category`): `product_type` and `category` must be existing
    active slugs, and `labels` is a comma-separated list of active label slugs.
    Unknown/inactive slugs surface as per-row errors; taxonomy is never
    auto-created on import.

    weight_grams defaults to 300 for newly-created products when the column
    is absent; existing products keep their current weight. Boolean columns
    (is_active, is_featured) accept true/false/1/0/yes/no (case-insensitive).

    Rows with validation errors are skipped; valid rows are upserted.
    """
    # Read file content (bounded — avoid buffering an unbounded request body)
    content = await file.read()
    if len(content) > MAX_CSV_UPLOAD_BYTES:
        return error_response(
            400,
            "INVALID_CSV",
            f"CSV file exceeds maximum size ({MAX_CSV_UPLOAD_BYTES} bytes)",
        )
    try:
        text = content.decode("utf-8-sig")  # Handle BOM
    except UnicodeDecodeError:
        return error_response(400, "INVALID_CSV", "CSV file must be valid UTF-8")

    reader = csv.DictReader(io.StringIO(text))

    # Validate headers
    if reader.fieldnames is None:
        return error_response(400, "INVALID_CSV", "CSV file is empty or has no headers")

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
        return error_response(
            400,
            "INVALID_CSV",
            f"Missing required columns: {', '.join(missing_cols)}",
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
            ("safety_warnings_en", MAX_SAFETY_TEXT_LENGTH),
            ("safety_warnings_bg", MAX_SAFETY_TEXT_LENGTH),
            ("care_instructions_en", MAX_SAFETY_TEXT_LENGTH),
            ("care_instructions_bg", MAX_SAFETY_TEXT_LENGTH),
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

        for column in (
            "safety_warnings_en",
            "safety_warnings_bg",
            "care_instructions_en",
            "care_instructions_bg",
        ):
            value = (row.get(column) or "").strip()
            if value:
                data[column] = value

        if "category" in headers and row.get("category"):
            data["category"] = row["category"].strip()
        # Managed taxonomy columns (slugs). Validated against active terms in the
        # service; unknown/inactive slugs surface as row-level errors below.
        if "product_type" in headers and row.get("product_type"):
            data["product_type"] = row["product_type"].strip()
        if "labels" in headers and row.get("labels"):
            data["labels"] = [s.strip() for s in row["labels"].split(",") if s.strip()]
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

        # Check if product exists to track created vs updated (lightweight probe).
        is_existing = product_service.product_exists(product_id)

        if imported_image_url and is_existing:
            image_count = len(product_image_service.list_images(product_id))
            if image_count >= product_image_service.MAX_IMAGES_PER_PRODUCT:
                errors.append(
                    CSVImportError(
                        row=row_num,
                        message=(
                            "image_url skipped: product already has maximum images "
                            f"({product_image_service.MAX_IMAGES_PER_PRODUCT})"
                        ),
                    )
                )
                continue

        try:
            product_service.upsert_product(product_id, data)
            if imported_image_url:
                added_image = product_image_service.add_existing_image_url(
                    product_id, imported_image_url
                )
                if added_image is None:
                    errors.append(
                        CSVImportError(
                            row=row_num,
                            message=(
                                "image_url skipped: product already has maximum images "
                                f"({product_image_service.MAX_IMAGES_PER_PRODUCT})"
                            ),
                        )
                    )
            if is_existing:
                updated += 1
            else:
                created += 1
        except (
            TaxonomyValidationError,
            DuplicateError,
            LedgerManagedStockEditError,
            ValueError,
            sqlite3.IntegrityError,
        ) as e:
            # Expected per-row data errors are reported and the import continues.
            # Unexpected exceptions propagate rather than masquerading as row errors.
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
    payment_status: str | None = Query(default=None, description="Filter by payment status"),
    payment_method: str | None = Query(default=None, description="Filter by payment method"),
    review_filter: str | None = Query(default=None, description="Filter operational review queues"),
    accounting_filter: str | None = Query(
        default=None, description="Filter accounting readiness queues"
    ),
    finance_period_id: str | None = Query(default=None, description="Filter by finance period id"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> OrderListResponse | JSONResponse:
    """List all orders with optional status filter."""
    if status is not None:
        valid_statuses = get_args(OrderStatus)
        if status not in valid_statuses:
            return error_response(
                422,
                "INVALID_STATUS",
                f"Invalid status '{status}'. Must be one of: {', '.join(valid_statuses)}",
            )
    if payment_status is not None:
        valid_payment_statuses = get_args(PaymentStatus)
        if payment_status not in valid_payment_statuses:
            return error_response(
                422,
                "INVALID_PAYMENT_STATUS",
                "Invalid payment_status "
                f"'{payment_status}'. Must be one of: {', '.join(valid_payment_statuses)}",
            )
    if payment_method is not None:
        valid_payment_methods = get_args(PaymentMethod)
        if payment_method not in valid_payment_methods:
            return error_response(
                422,
                "INVALID_PAYMENT_METHOD",
                "Invalid payment_method "
                f"'{payment_method}'. Must be one of: {', '.join(valid_payment_methods)}",
            )
    if review_filter is not None and review_filter not in ADMIN_REVIEW_FILTERS:
        return error_response(
            422,
            "INVALID_REVIEW_FILTER",
            "Invalid review_filter "
            f"'{review_filter}'. Must be one of: {', '.join(sorted(ADMIN_REVIEW_FILTERS))}",
        )
    if accounting_filter is not None and accounting_filter not in ADMIN_ACCOUNTING_FILTERS:
        return error_response(
            422,
            "INVALID_ACCOUNTING_FILTER",
            "Invalid accounting_filter "
            f"'{accounting_filter}'. Must be one of: "
            f"{', '.join(sorted(ADMIN_ACCOUNTING_FILTERS))}",
        )

    with get_db() as conn:
        result = list_orders_admin(
            conn=conn,
            status=cast(OrderStatus | None, status),
            payment_status=payment_status,
            payment_method=payment_method,
            review_filter=review_filter,
            accounting_filter=accounting_filter,
            finance_period_id=finance_period_id,
            page=page,
            limit=limit,
        )

    return OrderListResponse(
        items=[OrderResponse.model_validate(o) for o in result["items"]],
        total=result["total"],
        page=result["page"],
        limit=result["limit"],
    )


@router.get(
    "/orders/{order_id}",
    response_model=AdminOrderDetailResponse,
    summary="Get order detail (admin)",
    description="Get full order details including items, customer info, shipping address, "
    "and notes. No ownership check — admin can view any order.",
)
def admin_get_order_detail(order_id: str) -> AdminOrderDetailResponse:
    """Get full order detail for admin (no ownership check)."""
    with get_db() as conn:
        order_data = get_order_admin(conn=conn, order_id=order_id)
        payment_events = list_payment_events(conn, order_id)
        return_cases = list_return_cases_for_order(conn, order_id)
        return_events = list_return_events_for_order(conn, order_id)
        refund_records = list_refunds_for_order(conn, order_id)
        cod_settlement = get_cod_settlement_for_order(conn, order_id)
        cod_settlement_required = cod_settlement_required_for_order(conn, order_id)
        econt_cod_evidence = econt_fulfillment_service.get_latest_cod_evidence(conn, order_id)
        inventory_context = get_order_inventory_context(conn, order_id)

    payload = dict(order_data)
    raw_item_contexts = inventory_context.get("items", {})
    item_contexts = raw_item_contexts if isinstance(raw_item_contexts, dict) else {}
    payload_items = []
    for item in order_data["items"]:
        context = item_contexts.get(item["product_id"], {})
        payload_items.append({**dict(item), **(context if isinstance(context, dict) else {})})
    payload["items"] = payload_items
    payload["payment_events"] = payment_events
    payload["return_cases"] = return_cases
    payload["return_events"] = return_events
    payload["refund_records"] = refund_records
    payload["cod_settlement"] = cod_settlement
    payload["cod_settlement_required"] = cod_settlement_required
    payload["econt_cod_evidence"] = econt_cod_evidence
    payload["inventory_context"] = {
        key: value for key, value in inventory_context.items() if key != "items"
    }
    return AdminOrderDetailResponse.model_validate(payload)


@router.patch(
    "/orders/{order_id}/payment",
    response_model=OrderResponse,
    summary="Mark bank transfer payment received (admin)",
    description="Mark a bank_transfer order's payment as received. "
    "Only valid when payment_method='bank_transfer' and payment_status='pending'.",
    responses={
        404: {"description": "Order not found"},
        409: {"description": "Already paid or wrong payment method"},
    },
)
def admin_mark_payment_paid(
    order_id: str,
    body: MarkPaymentPaidRequest,
) -> OrderResponse | JSONResponse:
    """Admin marks bank transfer payment received; queues 'placed' email."""
    with get_db() as conn:
        try:
            order_data = mark_bank_transfer_paid(conn=conn, order_id=order_id)
        except PaymentAlreadyPaidError:
            return error_response(409, "ALREADY_PAID", "Order is already paid")
        except WrongPaymentMethodError as e:
            return error_response(409, "WRONG_PAYMENT_METHOD", str(e))
        except ManualPaymentActionError as e:
            return error_response(e.status_code, e.code, str(e))

    return OrderResponse.model_validate(order_data)


@router.post(
    "/orders/{order_id}/payment-actions",
    response_model=OrderResponse,
    summary="Apply a manual payment action (admin)",
    description="Apply note-required manual payment actions using the current payment statuses.",
)
def admin_apply_manual_payment_action(
    order_id: str,
    body: ManualPaymentActionRequest,
    request: Request,
    admin_user: Annotated[UserResponse | None, Depends(require_admin)],
) -> OrderResponse | JSONResponse:
    """Apply a note-required manual payment action and write payment_events audit."""
    request_id = request_id_var.get() or request.headers.get("x-request-id")
    with get_db() as conn:
        try:
            order_data = apply_manual_payment_action(
                conn=conn,
                order_id=order_id,
                action=body.action,
                note=body.note,
                callback_outcome=body.callback_outcome,
                admin_id=admin_user.id if admin_user else None,
                admin_email=admin_user.email if admin_user else None,
                request_id=request_id,
            )
        except PaymentAlreadyPaidError:
            return error_response(409, "ALREADY_PAID", "Order is already paid")
        except WrongPaymentMethodError as e:
            return error_response(422, "WRONG_PAYMENT_METHOD", str(e))
        except InvalidStateTransitionError as e:
            return error_response(422, "INVALID_TRANSITION", str(e))
        except ManualPaymentActionError as e:
            return error_response(e.status_code, e.code, str(e))

    return OrderResponse.model_validate(order_data)


@router.post(
    "/orders/{order_id}/refunds",
    response_model=PaymentRefundResponse,
    summary="Create Stripe refund (admin)",
    description="Create a full or partial Stripe refund with idempotency and local audit.",
)
async def admin_create_stripe_refund(
    order_id: str,
    body: CreateStripeRefundRequest,
    admin_user: Annotated[UserResponse | None, Depends(require_admin)],
) -> PaymentRefundResponse | JSONResponse:
    settings = get_settings()
    with get_db() as conn:
        try:
            refund = await create_stripe_refund_async(
                conn,
                order_id=order_id,
                amount_cents=body.amount_cents,
                reason=body.reason,
                idempotency_key=body.idempotency_key,
                admin_id=admin_user.id if admin_user else None,
                stripe_secret_key=settings.stripe_secret_key,
            )
        except OrderNotFoundError:
            return error_response(404, "ORDER_NOT_FOUND", "Order not found")
        except StripeRefundActionError as e:
            return error_response(e.status_code, e.code, str(e))

    return PaymentRefundResponse.model_validate(refund)


@router.post(
    "/orders/{order_id}/cod-settlement",
    response_model=CodSettlementResponse,
    summary="Record COD settlement (admin)",
    description="Record courier COD payout details and flag amount mismatches for accounting.",
)
def admin_record_cod_settlement(
    order_id: str,
    body: RecordCodSettlementRequest,
    admin_user: Annotated[UserResponse | None, Depends(require_admin)],
) -> CodSettlementResponse | JSONResponse:
    try:
        with get_db() as conn:
            settlement = record_cod_settlement(
                conn,
                order_id=order_id,
                amount_cents=body.amount_cents,
                settlement_date=body.settlement_date,
                courier_reference=body.courier_reference,
                notes=body.notes,
                admin_id=admin_user.id if admin_user else None,
            )
    except InvalidReturnValueError as exc:
        return _return_service_error_response(exc)

    return CodSettlementResponse.model_validate(settlement)


def _return_service_error_response(exc: Exception) -> JSONResponse:
    if isinstance(exc, ReturnCaseNotFoundError):
        return error_response(404, "RETURN_CASE_NOT_FOUND", str(exc))
    if isinstance(exc, InvalidReturnTransitionError):
        return error_response(
            422,
            "INVALID_RETURN_TRANSITION",
            str(exc),
            details={
                "return_id": exc.return_id,
                "current_status": exc.current_status,
                "requested_status": exc.requested_status,
            },
        )
    if isinstance(exc, InvalidRestockQuantityError):
        return error_response(
            422,
            "INVALID_RESTOCK_QUANTITY",
            str(exc),
            details={
                "product_id": exc.product_id,
                "quantity": exc.quantity,
                "max_quantity": exc.max_quantity,
            },
        )
    if isinstance(exc, InvalidReturnValueError):
        return error_response(
            422,
            "INVALID_RETURN_VALUE",
            str(exc),
            details={"field": exc.field, "value": exc.value},
        )
    if isinstance(exc, InvalidStateTransitionError):
        return error_response(
            422,
            "INVALID_TRANSITION",
            str(exc),
            details={
                "order_id": exc.order_id,
                "current_status": exc.current_status,
                "requested_status": exc.requested_status,
            },
        )
    raise exc


def _ensure_return_case_belongs_to_order(
    conn: sqlite3.Connection, *, order_id: str, return_id: str
) -> None:
    case = get_return_case(conn, return_id)
    if case["order_id"] != order_id:
        raise ReturnCaseNotFoundError(return_id)


@router.post(
    "/orders/{order_id}/returns",
    response_model=ReturnCaseResponse,
    summary="Create return case (admin)",
    description="Create an admin-controlled return/uncollected/refused case for an order.",
)
def admin_create_return_case(
    order_id: str,
    body: CreateReturnCaseRequest,
    admin_user: Annotated[UserResponse | None, Depends(require_admin)],
) -> ReturnCaseResponse | JSONResponse:
    try:
        with get_db() as conn:
            get_order_admin(conn=conn, order_id=order_id)
            if body.status == "return_in_transit":
                update_status(conn=conn, order_id=order_id, new_status="return_in_transit")
            case = create_return_case(
                conn,
                order_id=order_id,
                reason=body.reason,
                source=body.source,
                status=body.status,
                notes=body.notes,
                refund_amount_cents=body.refund_amount_cents,
                courier_return_fee_cents=body.courier_return_fee_cents,
                courier_claim_id=body.courier_claim_id,
                courier_claim_status=body.courier_claim_status,
                courier_claim_amount_cents=body.courier_claim_amount_cents,
                admin_id=admin_user.id if admin_user else None,
                admin_email=admin_user.email if admin_user else None,
            )
    except (
        InvalidStateTransitionError,
        InvalidReturnValueError,
        InvalidReturnTransitionError,
        InvalidRestockQuantityError,
        ReturnCaseNotFoundError,
    ) as exc:
        return _return_service_error_response(exc)

    return ReturnCaseResponse.model_validate(case)


@router.post(
    "/orders/{order_id}/returns/{return_id}/receive",
    response_model=ReturnCaseResponse,
    summary="Receive return case (admin)",
)
def admin_receive_return_case(
    order_id: str,
    return_id: str,
    admin_user: Annotated[UserResponse | None, Depends(require_admin)],
) -> ReturnCaseResponse | JSONResponse:
    try:
        with get_db() as conn:
            _ensure_return_case_belongs_to_order(conn, order_id=order_id, return_id=return_id)
            order = get_order_admin(conn=conn, order_id=order_id)
            if order["status"] == "return_in_transit":
                update_status(conn=conn, order_id=order_id, new_status="returned")
            case = receive_return_case(
                conn,
                return_id,
                admin_id=admin_user.id if admin_user else None,
                admin_email=admin_user.email if admin_user else None,
            )
    except (
        InvalidStateTransitionError,
        InvalidReturnValueError,
        InvalidReturnTransitionError,
        InvalidRestockQuantityError,
        ReturnCaseNotFoundError,
    ) as exc:
        return _return_service_error_response(exc)

    return ReturnCaseResponse.model_validate(case)


@router.patch(
    "/orders/{order_id}/returns/{return_id}/accounting",
    response_model=ReturnCaseResponse,
    summary="Update return accounting fields (admin)",
)
def admin_update_return_accounting(
    order_id: str,
    return_id: str,
    body: UpdateReturnAccountingRequest,
    admin_user: Annotated[UserResponse | None, Depends(require_admin)],
) -> ReturnCaseResponse | JSONResponse:
    try:
        with get_db() as conn:
            _ensure_return_case_belongs_to_order(conn, order_id=order_id, return_id=return_id)
            case = update_return_accounting(
                conn,
                return_id,
                courier_return_fee_cents=body.courier_return_fee_cents,
                courier_claim_id=body.courier_claim_id,
                courier_claim_status=body.courier_claim_status,
                courier_claim_amount_cents=body.courier_claim_amount_cents,
                notes=body.notes,
                admin_id=admin_user.id if admin_user else None,
                admin_email=admin_user.email if admin_user else None,
            )
    except (
        InvalidReturnValueError,
        InvalidReturnTransitionError,
        InvalidRestockQuantityError,
        ReturnCaseNotFoundError,
    ) as exc:
        return _return_service_error_response(exc)

    return ReturnCaseResponse.model_validate(case)


@router.patch(
    "/orders/{order_id}/returns/{return_id}/inspect",
    response_model=ReturnCaseResponse,
    summary="Inspect return case (admin)",
)
def admin_inspect_return_case(
    order_id: str,
    return_id: str,
    body: InspectReturnCaseRequest,
    admin_user: Annotated[UserResponse | None, Depends(require_admin)],
) -> ReturnCaseResponse | JSONResponse:
    try:
        with get_db() as conn:
            _ensure_return_case_belongs_to_order(conn, order_id=order_id, return_id=return_id)
            case = inspect_return_case(
                conn,
                return_id,
                restock_decision=body.restock_decision,
                restock_quantities=body.restock_quantities,
                notes=body.notes,
                admin_id=admin_user.id if admin_user else None,
                admin_email=admin_user.email if admin_user else None,
            )
    except (
        InvalidStateTransitionError,
        InvalidReturnValueError,
        InvalidReturnTransitionError,
        InvalidRestockQuantityError,
        ReturnCaseNotFoundError,
    ) as exc:
        return _return_service_error_response(exc)

    return ReturnCaseResponse.model_validate(case)


@router.post(
    "/orders/{order_id}/returns/{return_id}/close",
    response_model=ReturnCaseResponse,
    summary="Close return case (admin)",
)
def admin_close_return_case(
    order_id: str,
    return_id: str,
    admin_user: Annotated[UserResponse | None, Depends(require_admin)],
) -> ReturnCaseResponse | JSONResponse:
    try:
        with get_db() as conn:
            _ensure_return_case_belongs_to_order(conn, order_id=order_id, return_id=return_id)
            case = close_return_case(
                conn,
                return_id,
                admin_id=admin_user.id if admin_user else None,
                admin_email=admin_user.email if admin_user else None,
            )
    except (
        InvalidStateTransitionError,
        InvalidReturnValueError,
        InvalidReturnTransitionError,
        InvalidRestockQuantityError,
        ReturnCaseNotFoundError,
    ) as exc:
        return _return_service_error_response(exc)

    return ReturnCaseResponse.model_validate(case)


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
async def admin_update_order_status(
    order_id: str,
    body: UpdateOrderStatusRequest,
) -> OrderResponse | JSONResponse:
    """Update order status (admin-only, state machine enforced).

    On the Speedy ship transition a waybill is created automatically; a Speedy
    failure surfaces as 502 (the order stays `confirmed`, never shipped without a
    waybill — speedy-integration Decision 3).
    """
    with get_db() as conn:
        try:
            order_data = await update_status_async(
                conn=conn,
                order_id=order_id,
                new_status=body.status,
                tracking_number=body.tracking_number,
                tracking_carrier=body.tracking_carrier,
                tracking_url=body.tracking_url,
            )
        except SpeedyError as exc:
            return JSONResponse(
                status_code=502,
                content={
                    "error": {
                        "code": "SHIPMENT_CREATION_FAILED",
                        "message": str(exc),
                        "details": {"context": exc.context},
                    }
                },
            )
        # Durable outbox: queue the customer email for this transition in the
        # SAME connection/commit as the status UPDATE (email-notifications 8.3).
        # The map returns None for 'confirmed' (internal step — no email).
        event = event_for_status(body.status)
        if event is not None:
            queue_order_email(conn, order_id, event, order_data["customer_email"])

    return OrderResponse.model_validate(order_data)


@router.get(
    "/orders/{order_id}/label",
    response_model=None,
    summary="Print Speedy shipment label (admin)",
    description="Streams the Speedy PDF label for an order's waybill.",
    responses={
        404: {"description": "Order or tracking number not found"},
        502: {"description": "Speedy label print failed"},
    },
)
async def admin_print_order_label(
    order_id: str,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> Response | JSONResponse:
    """Fetch and stream the Speedy PDF label for an order (admin-only)."""
    with get_db() as conn:
        try:
            tracking_number, pdf = await speedy_admin_service.print_order_label(
                conn,
                order_id,
                actor_user_id=_admin_actor_id(current_admin),
                print_label_func=print_label,
            )
        except SpeedyAdminValidationError as exc:
            return _speedy_validation_response(exc)
        except SpeedyError as exc:
            return _speedy_error_response(exc)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="label-{tracking_number}.pdf"'},
    )


@router.post(
    "/orders/{order_id}/track",
    response_model=OrderResponse,
    summary="Refresh Speedy courier status (admin)",
    description="Polls Speedy /track and stores the normalized courier_status. "
    "Read-only: never changes the order's own status (speedy-integration Decision 4).",
    responses={
        404: {"description": "Order or tracking number not found"},
        502: {"description": "Speedy track failed"},
    },
)
async def admin_track_order(
    order_id: str,
    current_admin: Annotated[UserResponse | None, Depends(require_admin)],
) -> OrderResponse | JSONResponse:
    """Refresh the order's courier_status from Speedy (admin-only, display-only)."""
    with get_db() as conn:
        try:
            await courier_polling_service.refresh_order_now(
                conn,
                order_id,
                provider="speedy",
                actor_user_id=_admin_actor_id(current_admin),
                speedy_track_func=track_shipment,
            )
        except courier_polling_service.CourierPollingValidationError as exc:
            if "courier_provider_mismatch" in exc.blockers:
                return _speedy_validation_response(
                    SpeedyAdminValidationError(
                        "Order has no Speedy waybill",
                        blockers=["no_speedy_waybill"],
                    )
                )
            return error_response(
                422,
                "COURIER_REFRESH_BLOCKED",
                str(exc),
                {"blockers": exc.blockers},
            )
        except SpeedyAdminValidationError as exc:
            return _speedy_validation_response(exc)
        except SpeedyError as exc:
            return _speedy_error_response(exc)
        order = get_order_admin(conn, order_id)
    return OrderResponse.model_validate(order)


@router.get(
    "/alerts",
    response_model=AdminAlertListResponse,
    summary="List admin alerts",
    description="Return recent in-app admin alerts such as payment review notices.",
)
async def admin_list_alerts(
    limit: int = Query(default=20, ge=1, le=100),
    unread_only: bool = Query(default=False),
) -> AdminAlertListResponse:
    """List recent admin alerts for the in-app alert surface."""
    with get_db() as conn:
        alerts, total = admin_alert_service.list_admin_alerts(
            conn,
            limit=limit,
            unread_only=unread_only,
        )
    return AdminAlertListResponse(
        alerts=[AdminAlertResponse.model_validate(alert) for alert in alerts],
        total=total,
    )


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
    "/analytics/summary",
    response_model=AnalyticsSummaryResponse,
    summary="Admin analytics summary",
    description="Returns consented analytics coverage beside authoritative backend order totals.",
)
async def admin_analytics_summary(
    response: Response,
    start_date: str | None = Query(default=None, description="Inclusive YYYY-MM-DD start date"),
    end_date: str | None = Query(default=None, description="Inclusive YYYY-MM-DD end date"),
) -> AnalyticsSummaryResponse:
    """Admin-only first-party analytics summary."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    summary = await run_in_threadpool(analytics_service.get_summary, start_date, end_date)
    return AnalyticsSummaryResponse(**summary)


@router.get(
    "/analytics/funnel",
    response_model=AnalyticsFunnelResponse,
    summary="Admin analytics funnel metrics",
)
async def admin_analytics_funnel(
    response: Response,
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> AnalyticsFunnelResponse:
    """Return funnel counts and conversion percentages."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    steps = await run_in_threadpool(analytics_service.get_funnel, start_date, end_date)
    return AnalyticsFunnelResponse(steps=steps)


@router.get(
    "/analytics/products",
    response_model=ProductAnalyticsResponse,
    summary="Admin product analytics metrics",
)
async def admin_analytics_products(
    response: Response,
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> ProductAnalyticsResponse:
    """Return product-level aggregate analytics without customer PII."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    products = await run_in_threadpool(analytics_service.get_product_metrics, start_date, end_date)
    return ProductAnalyticsResponse(products=products)


@router.get(
    "/analytics/checkout",
    response_model=CheckoutAnalyticsResponse,
    summary="Admin checkout, delivery, and payment analytics metrics",
)
async def admin_analytics_checkout(
    response: Response,
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> CheckoutAnalyticsResponse:
    """Return checkout, delivery, and payment aggregates without customer PII."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    metrics = await run_in_threadpool(analytics_service.get_checkout_metrics, start_date, end_date)
    return CheckoutAnalyticsResponse(**metrics)


@router.get(
    "/analytics/health",
    response_model=AnalyticsHealthResponse,
    summary="Admin analytics delivery health",
)
async def admin_analytics_health(response: Response) -> AnalyticsHealthResponse:
    """Return accepted, rejected, duplicate, and load health metrics."""
    response.headers["Cache-Control"] = "no-store, no-cache"
    return await run_in_threadpool(analytics_service.get_health)


@router.get(
    "/analytics/export.csv",
    summary="Export aggregate analytics CSV",
    description="Exports aggregate funnel metrics only. No customer PII is included.",
)
async def admin_analytics_export_csv(
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
) -> Response:
    """Export aggregate funnel metrics as CSV."""
    steps = await run_in_threadpool(analytics_service.get_funnel, start_date, end_date)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["report", "event_type", "count", "conversion_from_previous"])
    for step in steps:
        writer.writerow(
            [
                "funnel",
                step.event_type.value,
                step.count,
                step.conversion_from_previous,
            ]
        )
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={
            "Cache-Control": "no-store, no-cache",
            "Content-Disposition": 'attachment; filename="atelier-analytics-funnel.csv"',
        },
    )


@router.get(
    "/reports/refunds.csv",
    summary="Export Stripe refund reconciliation CSV",
    description=(
        "Exports Stripe refund IDs, amounts, statuses, idempotency keys, and order references."
    ),
)
def admin_refund_reconciliation_report_csv() -> Response:
    """Export Stripe refund reconciliation rows for accounting."""
    headers = [
        "refund_id",
        "order_id",
        "order_number",
        "customer_email",
        "order_payment_status",
        "order_total_cents",
        "payment_id",
        "provider",
        "provider_refund_id",
        "amount_cents",
        "refund_status",
        "reason",
        "idempotency_key",
        "failure_reason",
        "created_by_admin_id",
        "created_at",
        "confirmed_at",
    ]
    with get_db() as conn:
        rows = accounting_report_service.stripe_refund_reconciliation_rows(conn)
    return _csv_response("atelier-stripe-refunds.csv", headers, rows)


@router.get(
    "/reports/cod-settlements.csv",
    summary="Export COD settlement reconciliation CSV",
    description=(
        "Exports unsettled, settled, and mismatch COD orders with Econt COD evidence where present."
    ),
)
def admin_cod_settlement_report_csv() -> Response:
    """Export COD settlement reconciliation rows for accounting."""
    headers = [
        "order_id",
        "order_number",
        "customer_email",
        "order_status",
        "delivery_courier",
        "order_total_cents",
        "courier_status",
        "courier_last_synced_at",
        "settlement_id",
        "settlement_amount_cents",
        "settlement_date",
        "courier_reference",
        "mismatch_review",
        "settlement_notes",
        "created_by_admin_id",
        "settlement_created_at",
        "settlement_updated_at",
        "settlement_state",
        "econt_cd_collected_amount",
        "econt_cd_collected_time",
        "econt_cd_paid_amount",
        "econt_cd_paid_time",
        "econt_evidence_event_id",
        "econt_evidence_action",
        "econt_evidence_recorded_at",
    ]
    with get_db() as conn:
        rows = accounting_report_service.cod_settlement_rows(conn)
    return _csv_response("atelier-cod-settlements.csv", headers, rows)


@router.get(
    "/reports/courier-claims.csv",
    summary="Export courier fees and manual claim CSV",
    description="Exports return courier fees and manually recorded courier claim fields.",
)
def admin_courier_claim_report_csv() -> Response:
    """Export courier fee and manual claim rows for accounting follow-up."""
    headers = [
        "return_id",
        "order_id",
        "order_number",
        "customer_email",
        "delivery_courier",
        "reason",
        "source",
        "return_status",
        "courier_return_fee_cents",
        "courier_claim_id",
        "courier_claim_status",
        "courier_claim_amount_cents",
        "notes",
        "created_at",
        "updated_at",
    ]
    with get_db() as conn:
        rows = accounting_report_service.courier_fee_claim_rows(conn)
    return _csv_response("atelier-courier-claims.csv", headers, rows)


@router.get(
    "/reports/return-reasons.csv",
    summary="Export return reason summary CSV",
    description=(
        "Exports return reason counts for uncollected, refused, damaged, lost, merchant error, "
        "and other cases."
    ),
)
def admin_return_reason_report_csv() -> Response:
    """Export aggregate return reason rows."""
    headers = [
        "reason",
        "source",
        "return_status",
        "return_count",
        "refund_amount_cents",
        "courier_return_fee_cents",
        "claim_count",
        "first_created_at",
        "last_created_at",
    ]
    with get_db() as conn:
        rows = accounting_report_service.return_reason_rows(conn)
    return _csv_response("atelier-return-reasons.csv", headers, rows)


@router.get(
    "/reports/inventory-adjustments.csv",
    summary="Export return inventory adjustment CSV",
    description=(
        "Exports inventory adjustments created by returned/restocked/not-restocked "
        "return decisions."
    ),
)
def admin_inventory_adjustment_report_csv() -> Response:
    """Export return inventory adjustment rows."""
    headers = [
        "adjustment_id",
        "order_id",
        "order_number",
        "return_id",
        "return_reason",
        "restock_decision",
        "product_id",
        "product_name",
        "quantity",
        "adjustment_reason",
        "source",
        "notes",
        "created_by_admin_id",
        "created_at",
    ]
    with get_db() as conn:
        rows = accounting_report_service.inventory_adjustment_rows(conn)
    return _csv_response("atelier-inventory-adjustments.csv", headers, rows)


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


@router.get(
    "/health/econt",
    summary="Econt circuit breaker health",
    description="Returns the current state of the Econt Delivery circuit breaker, "
    "including failure count and recovery timing. Admin-only.",
)
async def admin_health_econt() -> JSONResponse:
    """Expose Econt Delivery circuit breaker state for admin diagnostics."""
    breaker = get_econt_circuit_breaker()
    return JSONResponse(content=breaker.get_health())


@router.get(
    "/health/speedy",
    summary="Speedy circuit breaker health",
    description="Returns the current state of the Speedy operational circuit breaker. Admin-only.",
)
async def admin_health_speedy() -> JSONResponse:
    """Expose Speedy operational circuit breaker state for admin diagnostics."""
    breaker = get_speedy_circuit_breaker()
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
        return error_response(404, "NOT_FOUND", "Comment not found")
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


async def _stream_video_upload_with_limit(file: UploadFile, product_id: str) -> Path:
    """Stream a video UploadFile to private temp storage with a hard size cap."""
    settings = get_settings()
    temp_path = product_video_service.reserve_temp_upload(product_id)
    total = 0
    try:
        with temp_path.open("wb") as output:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > settings.max_video_upload_bytes:
                    raise VideoFileTooLargeError(
                        f"File size exceeds maximum of {settings.max_video_upload_bytes} bytes"
                    )
                output.write(chunk)
    except Exception:
        video_service.unlink_video_files(str(temp_path))
        raise
    return temp_path


def _video_error_response(exc: Exception) -> JSONResponse:
    if isinstance(exc, product_video_service.ProductNotFoundError):
        return error_response(404, "product_not_found", "Product not found")
    if isinstance(exc, product_video_service.ProductVideoNotFoundError):
        return error_response(404, "video_not_found", "Product video not found")
    if isinstance(exc, product_video_service.ProductVideoProcessingConflictError):
        return error_response(409, "video_processing", "video is still processing")
    if isinstance(exc, InvalidVideoProductIdError):
        return error_response(
            400,
            "invalid_product_id",
            "Product ID must be a valid slug (lowercase alphanumeric + hyphens)",
        )
    if isinstance(exc, VideoFileTooLargeError):
        return error_response(422, "file_too_large", str(exc))
    if isinstance(exc, InvalidVideoTypeError | VideoTooLongError):
        return error_response(422, "invalid_video", str(exc))
    if isinstance(exc, FfmpegUnavailableError):
        return error_response(503, "video_unavailable", str(exc))
    if isinstance(exc, VideoProcessingError):
        return error_response(422, "video_processing_failed", str(exc))
    raise exc


@router.post(
    "/products/{product_id}/video",
    response_model=ProductVideo,
    status_code=202,
    summary="Upload product video",
    responses={
        202: {"description": "Video accepted for async processing"},
        404: {"description": "Product not found"},
        409: {"description": "Video is still processing"},
        422: {"description": "Invalid video upload"},
        503: {"description": "ffmpeg/ffprobe unavailable"},
    },
)
async def admin_upload_product_video(
    product_id: str,
    file: UploadFile = File(..., description="Video file to transcode"),
) -> ProductVideo | JSONResponse:
    """Upload or replace one product video and queue background transcoding."""
    try:
        product_video_service.validate_upload_target(product_id)
        temp_path = await _stream_video_upload_with_limit(file, product_id)
        video = product_video_service.queue_video_upload_path(product_id, temp_path)
    except Exception as exc:
        return _video_error_response(exc)
    return ProductVideo(**video)


@router.get(
    "/products/{product_id}/video",
    response_model=ProductVideo,
    summary="Get product video status",
    responses={404: {"description": "Product or video not found"}},
)
async def admin_get_product_video(product_id: str) -> ProductVideo | JSONResponse:
    """Return the product video row, including status and failure reason."""
    try:
        video = product_video_service.get_video(product_id)
    except Exception as exc:
        return _video_error_response(exc)
    return ProductVideo(**video)


@router.delete(
    "/products/{product_id}/video",
    status_code=204,
    response_class=Response,
    summary="Delete product video",
    responses={404: {"description": "Product video not found"}},
)
async def admin_delete_product_video(product_id: str) -> Response:
    """Delete one product video and unlink its files."""
    try:
        product_video_service.delete_video(product_id)
    except Exception as exc:
        response = _video_error_response(exc)
        return response
    return Response(status_code=204)


@router.patch(
    "/products/{product_id}/video",
    response_model=ProductVideo,
    summary="Set product video gallery position",
    responses={404: {"description": "Product video not found"}},
)
async def admin_update_product_video(
    product_id: str,
    body: UpdateProductVideoRequest,
) -> ProductVideo | JSONResponse:
    """Set the product video's insertion index in the image gallery."""
    try:
        video = product_video_service.update_sort_order(product_id, body.sort_order)
    except Exception as exc:
        return _video_error_response(exc)
    return ProductVideo(**video)


async def _read_upload_with_limit(file: UploadFile) -> bytes:
    """Read an UploadFile without buffering unbounded request bodies."""
    chunks = bytearray()
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        chunks.extend(chunk)
        if len(chunks) > MAX_FILE_SIZE:
            raise ImageFileTooLargeError("File size exceeds maximum of 25MB")
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
    except ImageFileTooLargeError:
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
        return error_response(
            400,
            "invalid_product_id",
            "Product ID must be a valid slug (lowercase alphanumeric + hyphens)",
        )
    except ImageFileTooLargeError:
        return error_response(422, "file_too_large", "File size exceeds maximum of 25MB")
    except InvalidImageTypeError:
        return error_response(
            422,
            "invalid_image_type",
            "Unsupported image format. Only JPEG and PNG are accepted.",
        )

    try:
        # Pillow decode/resize/encode is CPU-bound and blocking; run it off the
        # event loop so concurrent Layer-1 requests are not stalled by an upload.
        image = await run_in_threadpool(product_image_service.add_image, product_id, file_bytes)
    except product_image_service.ProductNotFoundError:
        return error_response(404, "product_not_found", "Product not found")
    except product_image_service.ProductImageLimitError:
        return error_response(
            409,
            "max_product_images",
            "Product already has the maximum number of images",
        )
    except ImageProcessingError as e:
        error_message = str(e)
        if error_message == "image_dimensions_too_large":
            return error_response(
                422,
                "image_dimensions_too_large",
                "Image dimensions exceed the maximum allowed (25 megapixels)",
            )
        return error_response(
            422,
            "image_processing_failed",
            "Image could not be processed. The file may be corrupted.",
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
        return error_response(404, "image_not_found", "Product image not found")
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
        return error_response(404, "product_not_found", "Product not found")
    except product_image_service.ProductImageOrderError:
        return error_response(
            422,
            "invalid_image_order",
            "ordered_ids must match all images for the product",
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
        return error_response(404, "image_not_found", "Product image not found")
    return ProductImage(**image)
