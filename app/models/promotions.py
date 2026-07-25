"""Pydantic schemas for promotion campaigns, bulk product discounts, and the
managed site announcement banner.

Discount fields reuse the same validation and datetime normalization as
single-product discounts (`app/services/pricing.py`) so campaigns and bulk
operations can never diverge from the per-product discount rules.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.services.pricing import normalize_discount_datetime

CampaignStatus = Literal["draft", "scheduled", "active", "ended", "removed"]
BulkOperation = Literal["apply", "remove"]
BulkItemStatus = Literal["updated", "skipped", "failed"]


class ProductFilter(BaseModel):
    """Admin product-list filter descriptor used as a bulk/campaign target."""

    q: str | None = Field(default=None, max_length=200)
    category: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None
    in_stock: bool | None = None


def _validate_discount_window(
    percent: int | None, starts_at: str | None, ends_at: str | None
) -> None:
    """Shared window validation: percent required with dates, start before end."""
    if (starts_at is not None or ends_at is not None) and percent is None:
        msg = "discount_percent is required when a discount date is set"
        raise ValueError(msg)
    if starts_at is not None and ends_at is not None and starts_at >= ends_at:
        msg = "discount_starts_at must be earlier than discount_ends_at"
        raise ValueError(msg)


# --- Bulk product discount -------------------------------------------------


class BulkDiscountRequest(BaseModel):
    """Apply or remove a discount across many products in one request."""

    operation: BulkOperation
    product_ids: list[str] | None = Field(default=None, max_length=500)
    filter: ProductFilter | None = None
    discount_percent: int | None = Field(default=None, ge=1, le=99)
    discount_starts_at: str | None = None
    discount_ends_at: str | None = None

    @field_validator("discount_starts_at", "discount_ends_at")
    @classmethod
    def _normalize_dt(cls, v: str | None) -> str | None:
        return normalize_discount_datetime(v)

    @model_validator(mode="after")
    def _validate(self) -> "BulkDiscountRequest":
        has_ids = self.product_ids is not None
        has_filter = self.filter is not None
        if has_ids == has_filter:
            msg = "exactly one of product_ids or filter must be provided"
            raise ValueError(msg)
        if has_ids and len(self.product_ids) == 0:
            msg = "product_ids must not be empty"
            raise ValueError(msg)
        if self.operation == "apply":
            if self.discount_percent is None:
                msg = "discount_percent is required for operation=apply"
                raise ValueError(msg)
            _validate_discount_window(
                self.discount_percent, self.discount_starts_at, self.discount_ends_at
            )
        return self


class BulkResultItem(BaseModel):
    """Per-product outcome of a bulk/campaign discount operation."""

    id: str
    status: BulkItemStatus
    error: str | None = None


class BulkDiscountResponse(BaseModel):
    success_count: int
    failure_count: int
    results: list[BulkResultItem]


# --- Campaigns -------------------------------------------------------------


class CampaignCreateRequest(BaseModel):
    """Create a campaign management record (does not apply until applied)."""

    name: str = Field(..., min_length=1, max_length=200)
    note: str | None = Field(default=None, max_length=2000)
    discount_percent: int = Field(..., ge=1, le=99)
    discount_starts_at: str | None = None
    discount_ends_at: str | None = None
    product_ids: list[str] | None = Field(default=None, max_length=500)
    filter: ProductFilter | None = None

    @field_validator("discount_starts_at", "discount_ends_at")
    @classmethod
    def _normalize_dt(cls, v: str | None) -> str | None:
        return normalize_discount_datetime(v)

    @model_validator(mode="after")
    def _validate(self) -> "CampaignCreateRequest":
        has_ids = self.product_ids is not None
        has_filter = self.filter is not None
        if has_ids == has_filter:
            msg = "exactly one of product_ids or filter must be provided"
            raise ValueError(msg)
        if has_ids and len(self.product_ids) == 0:
            msg = "product_ids must not be empty"
            raise ValueError(msg)
        _validate_discount_window(
            self.discount_percent, self.discount_starts_at, self.discount_ends_at
        )
        return self


class CampaignUpdateRequest(BaseModel):
    """Update a draft campaign's metadata, discount, or target. Partial."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    note: str | None = Field(default=None, max_length=2000)
    discount_percent: int | None = Field(default=None, ge=1, le=99)
    discount_starts_at: str | None = None
    discount_ends_at: str | None = None
    product_ids: list[str] | None = Field(default=None, max_length=500)
    filter: ProductFilter | None = None

    @field_validator("discount_starts_at", "discount_ends_at")
    @classmethod
    def _normalize_dt(cls, v: str | None) -> str | None:
        return normalize_discount_datetime(v)

    @model_validator(mode="after")
    def _validate(self) -> "CampaignUpdateRequest":
        if self.product_ids is not None and self.filter is not None:
            msg = "provide at most one of product_ids or filter"
            raise ValueError(msg)
        if self.product_ids is not None and len(self.product_ids) == 0:
            msg = "product_ids must not be empty"
            raise ValueError(msg)
        # Window sanity when both dates present (percent merge validated in service).
        if (
            self.discount_starts_at is not None
            and self.discount_ends_at is not None
            and self.discount_starts_at >= self.discount_ends_at
        ):
            msg = "discount_starts_at must be earlier than discount_ends_at"
            raise ValueError(msg)
        return self


class CampaignResponse(BaseModel):
    id: str
    name: str
    note: str | None = None
    discount_percent: int
    discount_starts_at: str | None = None
    discount_ends_at: str | None = None
    target_type: Literal["ids", "filter"]
    target_count: int
    status: CampaignStatus
    applied_at: str | None = None
    removed_at: str | None = None
    created_at: str
    updated_at: str
    last_result: BulkDiscountResponse | None = None


class CampaignListResponse(BaseModel):
    items: list[CampaignResponse]
    total: int


# --- Site banner -----------------------------------------------------------


class BannerUpdateRequest(BaseModel):
    """Admin update of the managed announcement banner."""

    message_en: str | None = Field(default=None, max_length=500)
    message_bg: str | None = Field(default=None, max_length=500)
    link_label_en: str | None = Field(default=None, max_length=100)
    link_label_bg: str | None = Field(default=None, max_length=100)
    link_url: str | None = Field(default=None, max_length=2000)
    is_enabled: bool = False
    starts_at: str | None = None
    ends_at: str | None = None

    @field_validator("starts_at", "ends_at")
    @classmethod
    def _normalize_dt(cls, v: str | None) -> str | None:
        return normalize_discount_datetime(v)

    @model_validator(mode="after")
    def _validate(self) -> "BannerUpdateRequest":
        if self.is_enabled and not (self.message_en and self.message_en.strip()):
            msg = "message_en is required to enable the banner"
            raise ValueError(msg)
        if (
            self.starts_at is not None
            and self.ends_at is not None
            and self.starts_at >= self.ends_at
        ):
            msg = "starts_at must be earlier than ends_at"
            raise ValueError(msg)
        return self


class BannerAdminResponse(BaseModel):
    message_en: str | None = None
    message_bg: str | None = None
    link_label_en: str | None = None
    link_label_bg: str | None = None
    link_url: str | None = None
    is_enabled: bool
    starts_at: str | None = None
    ends_at: str | None = None
    version: int
    updated_at: str


class PublicBanner(BaseModel):
    """The single active banner, localized for the requested locale."""

    message: str
    link_label: str | None = None
    link_url: str | None = None
    dismiss_key: str


class PublicBannerResponse(BaseModel):
    banner: PublicBanner | None = None
