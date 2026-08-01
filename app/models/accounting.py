"""Pydantic models for Accounting & Finance Hub admin APIs."""

from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

VatMode = Literal["unknown", "not_registered", "registered", "oss_registered"]
OssMode = Literal["not_applicable", "not_registered", "registered", "review_required"]
FiscalDocumentMode = Literal[
    "external_reference",
    "app_invoice_reference",
    "fiscal_device_reference",
    "alternative_sales_document",
    "not_configured",
]
CloseBehavior = Literal["warn", "block"]
CostingBasis = Literal["manual_snapshot", "recipe_bom", "imported_estimate"]
MissingCostPolicy = Literal["none", "warning", "blocking"]
FinancePeriodStatus = Literal["open", "review", "closed", "exported", "accepted", "reopened"]
FinanceExceptionStatus = Literal["open", "resolved", "waived"]
FinanceExceptionSeverity = Literal["blocking", "warning"]
AccountingLedgerName = Literal[
    "sales",
    "payments",
    "stripe_payouts",
    "cod_settlements",
    "refunds",
    "courier_claims",
    "return_reasons",
    "inventory_adjustments",
    "inventory_movements",
    "documents",
    "expenses",
    "product_costs",
]
AccountingDocumentType = Literal[
    "invoice",
    "credit_note",
    "fiscal_receipt",
    "alternative_sales_document",
    "external_document",
]
AccountingDocumentStatus = Literal[
    "draft",
    "recorded",
    "void",
    "corrected",
    "missing",
    "review_required",
]
ExpensePaymentStatus = Literal["unpaid", "paid", "partially_paid", "reimbursed", "cancelled"]
ExpenseReviewStatus = Literal["unreviewed", "reviewed", "missing_document", "waived", "rejected"]
ProductCostReviewStatus = Literal["estimate", "reviewed", "accountant_reviewed", "archived"]
ProductCostComponentType = Literal["material", "packaging", "labor", "overhead", "waste", "other"]


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class SellerLegalProfileRequest(BaseModel):
    """Admin-created seller legal profile version."""

    model_config = ConfigDict(extra="forbid")

    effective_date: str = Field(..., min_length=10, max_length=32)
    reviewed: bool = False
    company_display_name: str | None = Field(default=None, max_length=200)
    legal_name: str | None = Field(default=None, max_length=200)
    uic_eik: str | None = Field(default=None, max_length=64)
    vat_identification_number: str | None = Field(default=None, max_length=64)
    registered_address: dict[str, object] | None = None
    contact_email: EmailStr | None = None
    bank_details: dict[str, object] | None = None
    default_currency: str = Field(default="EUR", min_length=3, max_length=3)

    @field_validator(
        "company_display_name",
        "legal_name",
        "uic_eik",
        "vat_identification_number",
        mode="before",
    )
    @classmethod
    def _optional_string(cls, value: str | None) -> str | None:
        return _blank_to_none(value)

    @field_validator("default_currency", mode="before")
    @classmethod
    def _currency_upper(cls, value: str) -> str:
        return value.strip().upper()


class SellerLegalProfileResponse(SellerLegalProfileRequest):
    """Seller legal profile version returned to admin users."""

    id: int
    bank_details_configured: bool = False
    created_by_admin_id: str | None = None
    created_at: str


class VatFiscalSettingsRequest(BaseModel):
    """Accountant-reviewed VAT/fiscal settings version."""

    model_config = ConfigDict(extra="forbid")

    effective_date: str = Field(..., min_length=10, max_length=32)
    reviewed: bool = False
    vat_mode: VatMode = "unknown"
    oss_mode: OssMode = "not_applicable"
    default_domestic_vat_treatment: str | None = Field(default=None, max_length=200)
    fiscal_document_mode: FiscalDocumentMode = "external_reference"
    document_rules: dict[str, object] | None = None
    threshold_warnings: dict[str, object] | None = None
    tolerance_cents: int = Field(default=1, ge=0)
    warning_text: str | None = Field(default=None, max_length=1000)

    @field_validator("default_domestic_vat_treatment", "warning_text", mode="before")
    @classmethod
    def _optional_string(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class VatFiscalSettingsResponse(VatFiscalSettingsRequest):
    """VAT/fiscal settings version returned to admin users."""

    id: int
    created_by_admin_id: str | None = None
    created_at: str


class CategoryMappingRequest(BaseModel):
    """One accountant category mapping."""

    model_config = ConfigDict(extra="forbid")

    category_code: str | None = Field(default=None, max_length=100)
    category_label: str = Field(..., min_length=1, max_length=200)
    is_required: bool = False
    reviewed: bool = False

    @field_validator("category_code", mode="before")
    @classmethod
    def _optional_string(cls, value: str | None) -> str | None:
        return _blank_to_none(value)

    @field_validator("category_label", mode="before")
    @classmethod
    def _label(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("category_label must not be blank")
        return stripped


class CategoryMappingResponse(CategoryMappingRequest):
    """Persisted accountant category mapping."""

    id: int
    mapping_key: str
    created_at: str
    updated_at: str


class ExportSchemaSettingsRequest(BaseModel):
    """Settings controlling accountant export package shape."""

    model_config = ConfigDict(extra="forbid")

    workbook_language: Literal["en", "bg"] = "en"
    date_format: str = Field(default="yyyy-mm-dd", min_length=1, max_length=64)
    decimal_separator: Literal[".", ","] = "."
    default_period_range: str = Field(default="monthly", min_length=1, max_length=64)
    included_tabs: list[str] = Field(default_factory=list)
    custom_columns: dict[str, object] | None = None
    reviewed: bool = False


class ExportSchemaSettingsResponse(ExportSchemaSettingsRequest):
    """Persisted export schema singleton."""

    id: str = "default"
    updated_at: str


class ExpenseEvidenceSettingsRequest(BaseModel):
    """Settings for expense evidence review and close behavior."""

    model_config = ConfigDict(extra="forbid")

    required_document_categories: list[str] = Field(default_factory=list)
    allowed_payment_statuses: list[str] = Field(
        default_factory=lambda: ["unpaid", "paid", "partially_paid", "reimbursed"]
    )
    default_category_mappings: dict[str, str] = Field(default_factory=dict)
    close_behavior: CloseBehavior = "warn"
    reviewed: bool = False


class ExpenseEvidenceSettingsResponse(ExpenseEvidenceSettingsRequest):
    """Persisted expense evidence singleton."""

    id: str = "default"
    updated_at: str


class ProductCostSettingsRequest(BaseModel):
    """Settings for optional product-cost estimates."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    costing_basis: CostingBasis = "manual_snapshot"
    include_labor: bool = False
    include_overhead: bool = False
    missing_cost_policy: MissingCostPolicy = "warning"
    reviewed: bool = False
    estimate_label: str = Field(default="management_estimate", min_length=1, max_length=100)

    @field_validator("estimate_label", mode="before")
    @classmethod
    def _estimate_label(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("estimate_label must not be blank")
        return stripped


class ProductCostSettingsResponse(ProductCostSettingsRequest):
    """Persisted product-cost settings singleton."""

    id: str = "default"
    updated_at: str


class AccountingSetupException(BaseModel):
    """Configuration issue that blocks or warns before finance close."""

    code: str
    severity: FinanceExceptionSeverity = "blocking"
    message: str


class FinancePeriodCreateRequest(BaseModel):
    """Admin request to create a finance period."""

    model_config = ConfigDict(extra="forbid")

    period_start: str = Field(..., min_length=10, max_length=10)
    period_end: str = Field(..., min_length=10, max_length=10)
    currency: str = Field(default="EUR", min_length=3, max_length=3)

    @field_validator("currency", mode="before")
    @classmethod
    def _currency_upper(cls, value: str) -> str:
        return value.strip().upper()


class FinancePeriodActionRequest(BaseModel):
    """Optional reason/note for period state changes."""

    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=1000)
    accountant_name: str | None = Field(default=None, max_length=200)
    accountant_reference: str | None = Field(default=None, max_length=200)

    @field_validator("reason", "accountant_name", "accountant_reference", mode="before")
    @classmethod
    def _optional_string(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class FinanceExceptionActionRequest(BaseModel):
    """Reason-bearing exception resolution/waiver request."""

    model_config = ConfigDict(extra="forbid")

    reason: str = Field(..., min_length=1, max_length=1000)

    @field_validator("reason", mode="before")
    @classmethod
    def _reason(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("reason must not be blank")
        return stripped


class FinanceExceptionResponse(BaseModel):
    """Persisted finance review exception."""

    id: str
    period_id: str | None = None
    exception_type: str
    severity: FinanceExceptionSeverity
    target_type: str | None = None
    target_id: str | None = None
    status: FinanceExceptionStatus
    message: str
    details: dict[str, object] | None = None
    waived_by_admin_id: str | None = None
    waiver_reason: str | None = None
    waived_at: str | None = None
    resolved_at: str | None = None
    created_at: str
    updated_at: str


class FinancePeriodResponse(BaseModel):
    """Finance period returned to admin users."""

    id: str
    period_start: str
    period_end: str
    currency: str
    status: FinancePeriodStatus
    summary_totals: dict[str, object] | None = None
    open_exception_count: int = 0
    blocking_exception_count: int = 0
    created_by_admin_id: str | None = None
    updated_by_admin_id: str | None = None
    closed_by_admin_id: str | None = None
    closed_at: str | None = None
    accepted_at: str | None = None
    reopened_from_export_id: str | None = None
    reopen_reason: str | None = None
    created_at: str
    updated_at: str


class FinancePeriodListResponse(BaseModel):
    """Paginated-light finance period list."""

    items: list[FinancePeriodResponse]
    total: int


class FinanceExceptionListResponse(BaseModel):
    """Finance exception list for a period or filtered queue."""

    items: list[FinanceExceptionResponse]
    total: int


class AccountingLedgerResponse(BaseModel):
    """Generic accounting ledger response."""

    period_id: str
    ledger: AccountingLedgerName
    date_basis: str
    rows: list[dict[str, object]]
    totals: dict[str, int]
    total: int
    page: int
    limit: int


class StripeBalanceImportResponse(BaseModel):
    """Result of importing Stripe balance/payout rows."""

    imported: int = 0
    updated: int = 0
    duplicate_provider_ids: int = 0
    matched: int = 0
    unmatched: int = 0
    mismatched: int = 0
    ignored: int = 0
    errors: list[str] = Field(default_factory=list)


class StripePayoutImportStatusResponse(BaseModel):
    """Summary of stored Stripe payout reconciliation state."""

    total_rows: int
    matched: int
    unmatched: int
    mismatched: int
    duplicate: int
    ignored: int
    latest_imported_at: str | None = None


class StripePayoutMatchReviewRequest(BaseModel):
    """Manual review update for a Stripe balance transaction match."""

    model_config = ConfigDict(extra="forbid")

    match_status: Literal["matched", "unmatched", "mismatch", "duplicate", "ignored"]
    reason: str = Field(..., min_length=1, max_length=1000)

    @field_validator("reason", mode="before")
    @classmethod
    def _reason(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("reason must not be blank")
        return stripped


class AccountingDocumentRequest(BaseModel):
    """Create/update payload for accounting document references."""

    model_config = ConfigDict(extra="forbid")

    document_type: AccountingDocumentType
    source_system: str = Field(default="external", min_length=1, max_length=100)
    document_number: str | None = Field(default=None, max_length=100)
    issue_date: str = Field(..., min_length=10, max_length=32)
    order_id: str | None = Field(default=None, max_length=80)
    refund_id: str | None = Field(default=None, max_length=80)
    period_id: str | None = Field(default=None, max_length=80)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    net_amount_cents: int | None = Field(default=None, ge=0)
    tax_amount_cents: int | None = Field(default=None, ge=0)
    gross_amount_cents: int | None = Field(default=None, ge=0)
    vat_summary: dict[str, object] | None = None
    original_document_id: str | None = Field(default=None, max_length=80)
    file_reference: str | None = Field(default=None, max_length=500)
    status: AccountingDocumentStatus = "recorded"
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator(
        "source_system",
        "document_number",
        "order_id",
        "refund_id",
        "period_id",
        "original_document_id",
        "file_reference",
        "notes",
        mode="before",
    )
    @classmethod
    def _optional_string(cls, value: str | None) -> str | None:
        return _blank_to_none(value)

    @field_validator("currency", mode="before")
    @classmethod
    def _currency_upper(cls, value: str) -> str:
        return value.strip().upper()


class AccountingDocumentResponse(AccountingDocumentRequest):
    """Persisted accounting document reference."""

    id: str
    created_by_admin_id: str | None = None
    updated_by_admin_id: str | None = None
    created_at: str
    updated_at: str


class AccountingDocumentListResponse(BaseModel):
    """Accounting document list response."""

    items: list[AccountingDocumentResponse]
    total: int


class ExpenseEvidenceRequest(BaseModel):
    """Supplier purchase/expense evidence payload."""

    model_config = ConfigDict(extra="forbid")

    supplier_name: str = Field(..., min_length=1, max_length=200)
    supplier_identifier: str | None = Field(default=None, max_length=100)
    document_number: str | None = Field(default=None, max_length=100)
    document_date: str | None = Field(default=None, max_length=32)
    purchase_date: str = Field(..., min_length=10, max_length=32)
    payment_date: str | None = Field(default=None, max_length=32)
    payment_status: ExpensePaymentStatus = "unpaid"
    category_key: str | None = Field(default=None, max_length=100)
    net_amount_cents: int | None = Field(default=None, ge=0)
    tax_amount_cents: int = Field(default=0, ge=0)
    gross_amount_cents: int = Field(..., ge=0)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    attachment_reference: str | None = Field(default=None, max_length=500)
    linked_product_id: str | None = Field(default=None, max_length=100)
    linked_material_name: str | None = Field(default=None, max_length=200)
    linked_courier: Literal["speedy", "econt"] | None = None
    linked_order_id: str | None = Field(default=None, max_length=80)
    review_status: ExpenseReviewStatus = "unreviewed"
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator(
        "supplier_name",
        "supplier_identifier",
        "document_number",
        "category_key",
        "attachment_reference",
        "linked_product_id",
        "linked_material_name",
        "linked_order_id",
        "notes",
        mode="before",
    )
    @classmethod
    def _optional_string(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = str(value).strip()
        return stripped or None

    @field_validator("currency", mode="before")
    @classmethod
    def _currency_upper(cls, value: str) -> str:
        return value.strip().upper()


class ExpenseEvidenceResponse(ExpenseEvidenceRequest):
    """Persisted expense evidence record."""

    id: str
    created_by_admin_id: str | None = None
    updated_by_admin_id: str | None = None
    created_at: str
    updated_at: str


class ExpenseEvidenceListResponse(BaseModel):
    """Expense evidence list response."""

    items: list[ExpenseEvidenceResponse]
    total: int


class ExpensePaymentStatusRequest(BaseModel):
    """Payment status update for an expense evidence record."""

    model_config = ConfigDict(extra="forbid")

    payment_status: ExpensePaymentStatus
    payment_date: str | None = Field(default=None, max_length=32)
    reason: str = Field(..., min_length=1, max_length=1000)


class ProductCostComponentRequest(BaseModel):
    """One product-cost component row."""

    model_config = ConfigDict(extra="forbid")

    component_type: ProductCostComponentType
    description: str = Field(..., min_length=1, max_length=200)
    quantity: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, max_length=40)
    unit_cost_cents: int | None = Field(default=None, ge=0)
    total_cost_cents: int = Field(..., ge=0)
    source_expense_id: str | None = Field(default=None, max_length=80)


class ProductCostComponentResponse(ProductCostComponentRequest):
    id: str
    cost_version_id: str
    created_at: str


class ProductCostVersionRequest(BaseModel):
    """Product-cost version payload."""

    model_config = ConfigDict(extra="forbid")
    product_id: str | None = Field(default=None, max_length=100)
    sku: str | None = Field(default=None, max_length=100)
    product_name: str = Field(..., min_length=1, max_length=200)
    effective_date: str = Field(..., min_length=10, max_length=32)
    costing_basis: CostingBasis = "manual_snapshot"
    material_cost_cents: int = Field(default=0, ge=0)
    packaging_cost_cents: int = Field(default=0, ge=0)
    labor_cost_cents: int = Field(default=0, ge=0)
    overhead_cost_cents: int = Field(default=0, ge=0)
    estimated_unit_cost_cents: int | None = Field(default=None, ge=0)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    reviewed: bool = False
    accountant_reviewed: bool = False
    review_status: ProductCostReviewStatus = "estimate"
    source_expense_ids: list[str] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=1000)
    components: Sequence[ProductCostComponentRequest] = Field(default_factory=list)

    @field_validator("currency", mode="before")
    @classmethod
    def _currency_upper(cls, value: str) -> str:
        return value.strip().upper()


class ProductCostVersionResponse(ProductCostVersionRequest):
    id: str
    estimated_unit_cost_cents: int
    components: list[ProductCostComponentResponse] = Field(default_factory=list)
    created_by_admin_id: str | None = None
    updated_by_admin_id: str | None = None
    created_at: str
    updated_at: str


class ProductCostVersionListResponse(BaseModel):
    items: list[ProductCostVersionResponse]
    total: int


class MissingProductCostDiagnostic(BaseModel):
    order_id: str
    order_number: str | None = None
    order_date: str
    product_id: str
    product_name: str


class MissingProductCostDiagnosticsResponse(BaseModel):
    items: list[MissingProductCostDiagnostic]
    total: int


class FinanceExportPackageResponse(BaseModel):
    """Stored accountant export package metadata."""

    id: str
    period_id: str
    version: int
    schema_version: str
    xlsx_path: str | None = None
    csv_dir_path: str | None = None
    manifest_path: str | None = None
    manifest: dict[str, object] | None = None
    generated_by_admin_id: str | None = None
    generated_at: str
    accepted_by_admin_id: str | None = None
    accepted_at: str | None = None
    accountant_name: str | None = None
    accountant_reference: str | None = None
    acceptance_note: str | None = None
    current_final: bool = True


class FinanceExportPackageListResponse(BaseModel):
    items: list[FinanceExportPackageResponse]
    total: int


class AccountantAcceptanceRequest(BaseModel):
    """Acceptance note for an accountant export package."""

    model_config = ConfigDict(extra="forbid")

    accountant_name: str | None = Field(default=None, max_length=200)
    accountant_reference: str | None = Field(default=None, max_length=200)
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("accountant_name", "accountant_reference", "note", mode="before")
    @classmethod
    def _optional_string(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class AccountingConfigurationResponse(BaseModel):
    """Complete admin accounting configuration snapshot."""

    seller_profile: SellerLegalProfileResponse | None = None
    vat_fiscal_settings: VatFiscalSettingsResponse | None = None
    category_mappings: list[CategoryMappingResponse]
    export_schema: ExportSchemaSettingsResponse
    expense_settings: ExpenseEvidenceSettingsResponse
    product_cost_settings: ProductCostSettingsResponse
    setup_exceptions: list[AccountingSetupException]
