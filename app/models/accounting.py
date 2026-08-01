"""Pydantic models for Accounting & Finance Hub admin APIs."""

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
    severity: Literal["blocking", "warning"] = "blocking"
    message: str


class AccountingConfigurationResponse(BaseModel):
    """Complete admin accounting configuration snapshot."""

    seller_profile: SellerLegalProfileResponse | None = None
    vat_fiscal_settings: VatFiscalSettingsResponse | None = None
    category_mappings: list[CategoryMappingResponse]
    export_schema: ExportSchemaSettingsResponse
    expense_settings: ExpenseEvidenceSettingsResponse
    product_cost_settings: ProductCostSettingsResponse
    setup_exceptions: list[AccountingSetupException]
