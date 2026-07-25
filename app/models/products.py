"""Product request and response models."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.common import PRODUCT_ID_PATTERN
from app.services.pricing import normalize_discount_datetime

# Maximum stock value — prevents absurd inventory numbers
MAX_STOCK = 99999

# Supported locales
Locale = Literal["en", "bg"]


class ProductResponse(BaseModel):
    """Public product representation (locale-resolved name/description)."""

    id: str
    name: str
    description: str | None = None
    materials: str | None = None
    days_to_craft: int | None = None
    price_cents: int
    # Discount display fields (computed via the pricing helper):
    #   effective_price_cents = discounted price (== price_cents when inactive)
    #   discount_percent       = active display percent, or null when inactive
    #   discount_active        = whether a discount is currently applied
    # Discount window timestamps are intentionally NOT exposed publicly.
    effective_price_cents: int
    discount_percent: int | None = None
    discount_active: bool = False
    category: str | None = None
    images: list["ProductImage"] = Field(default_factory=list)
    primary_image_url: str | None = None
    primary_thumbnail_url: str | None = None
    stock: int
    is_active: bool
    is_featured: bool
    created_at: str
    updated_at: str


class ProductAdminResponse(BaseModel):
    """Admin product representation with both language fields and staleness info."""

    id: str
    name_en: str
    name_bg: str | None = None
    description_en: str | None = None
    description_bg: str | None = None
    materials: str | None = None
    days_to_craft: int | None = None
    price_cents: int
    # Raw discount configuration (admin sees the full schedule) plus a computed
    # live preview (effective_price_cents / discount_active) for the sale price.
    discount_percent: int | None = None
    discount_starts_at: str | None = None
    discount_ends_at: str | None = None
    effective_price_cents: int
    discount_active: bool = False
    category: str | None = None
    images: list["ProductImage"] = Field(default_factory=list)
    primary_image_url: str | None = None
    primary_thumbnail_url: str | None = None
    stock: int
    is_active: bool
    is_featured: bool
    translation_stale_bg: bool = False
    translation_stale_en: bool = False
    created_at: str
    updated_at: str


class ProductListResponse(BaseModel):
    """Paginated list of products."""

    products: list[ProductResponse]
    total: int
    page: int
    limit: int


class ProductAdminListResponse(BaseModel):
    """Paginated list of products for admin (includes both language fields)."""

    products: list[ProductAdminResponse]
    total: int
    page: int
    limit: int


class ProductImage(BaseModel):
    """One image belonging to a product gallery."""

    id: str
    image_url: str
    thumbnail_url: str
    sort_order: int
    is_primary: bool


class ReorderProductImagesRequest(BaseModel):
    """Input for replacing a product gallery's display order."""

    ordered_ids: list[str] = Field(..., min_length=0, max_length=6)


class CreateProductRequest(BaseModel):
    """Input for creating a new product."""

    id: str = Field(..., min_length=1, max_length=100, pattern=PRODUCT_ID_PATTERN)
    name_en: str = Field(..., min_length=1, max_length=200)
    name_bg: str | None = Field(default=None, max_length=200)
    description_en: str | None = Field(default=None, max_length=5000)
    description_bg: str | None = Field(default=None, max_length=5000)
    materials: str | None = Field(default=None, max_length=1000)
    days_to_craft: int | None = Field(default=None, ge=0, le=365)
    price_cents: int = Field(..., gt=0, le=99_999_99)
    category: str | None = Field(default=None, max_length=100)
    discount_percent: int | None = Field(default=None, ge=1, le=99)
    discount_starts_at: str | None = None
    discount_ends_at: str | None = None
    stock: int = Field(..., ge=0, le=MAX_STOCK)
    is_active: bool = True
    is_featured: bool = False

    @field_validator("discount_starts_at", "discount_ends_at")
    @classmethod
    def _normalize_discount_datetime(cls, v: str | None) -> str | None:
        """Normalize datetime input to canonical UTC; reject timezone-less input."""
        return normalize_discount_datetime(v)

    @model_validator(mode="after")
    def _validate_discount_window(self) -> "CreateProductRequest":
        """Self-contained discount validation for a full create payload.

        (Update merge validation lives in the service, which has the existing
        persisted row to merge against.)
        """
        if (
            self.discount_starts_at is not None or self.discount_ends_at is not None
        ) and self.discount_percent is None:
            msg = "discount_percent is required when a discount date is set"
            raise ValueError(msg)
        if (
            self.discount_starts_at is not None
            and self.discount_ends_at is not None
            and self.discount_starts_at >= self.discount_ends_at
        ):
            msg = "discount_starts_at must be earlier than discount_ends_at"
            raise ValueError(msg)
        return self

    @field_validator(
        "name_en",
        "name_bg",
        "description_en",
        "description_bg",
        "materials",
        "category",
        mode="before",
    )
    @classmethod
    def strip_and_reject_blank(cls, v: str | None) -> str | None:
        """Strip whitespace; reject strings that become empty after trimming."""
        if v is None:
            return None
        # Type-guard: let Pydantic emit a clean type error for non-strings instead
        # of raising TypeError from .strip() inside the validator.
        if not isinstance(v, str):
            return v
        stripped = v.strip()
        if not stripped and v:
            msg = "must not be blank (whitespace-only)"
            raise ValueError(msg)
        return stripped if stripped else None


class UpdateProductRequest(BaseModel):
    """Input for partially updating a product. All fields optional.

    Use model_dump(exclude_unset=True) in services to distinguish
    'client sent null' from 'client did not send this field'.
    """

    name_en: str | None = Field(default=None, min_length=1, max_length=200)
    name_bg: str | None = Field(default=None, max_length=200)
    description_en: str | None = Field(default=None, max_length=5000)
    description_bg: str | None = Field(default=None, max_length=5000)
    materials: str | None = Field(default=None, max_length=1000)
    days_to_craft: int | None = Field(default=None, ge=0, le=365)
    price_cents: int | None = Field(default=None, gt=0, le=99_999_99)
    category: str | None = Field(default=None, max_length=100)
    discount_percent: int | None = Field(default=None, ge=1, le=99)
    discount_starts_at: str | None = None
    discount_ends_at: str | None = None
    stock: int | None = Field(default=None, ge=0, le=MAX_STOCK)
    is_active: bool | None = None
    is_featured: bool | None = None

    @field_validator("discount_starts_at", "discount_ends_at")
    @classmethod
    def _normalize_discount_datetime(cls, v: str | None) -> str | None:
        """Normalize datetime input to canonical UTC; reject timezone-less input.

        Cross-field validation (percent-required-with-date, start < end) is
        deferred to the service, which merges this patch with the persisted row.
        """
        return normalize_discount_datetime(v)

    @model_validator(mode="before")
    @classmethod
    def reject_explicit_null_name_en(cls, data: dict) -> dict:
        """Reject explicit null for name_en — DB column is NOT NULL."""
        if isinstance(data, dict) and "name_en" in data and data["name_en"] is None:
            msg = "name_en cannot be explicitly set to null"
            raise ValueError(msg)
        return data

    @field_validator(
        "name_en",
        "name_bg",
        "description_en",
        "description_bg",
        "materials",
        "category",
        mode="before",
    )
    @classmethod
    def strip_and_reject_blank(cls, v: str | None) -> str | None:
        """Strip whitespace; reject strings that become empty after trimming."""
        if v is None:
            return None
        # Type-guard: let Pydantic emit a clean type error for non-strings instead
        # of raising TypeError from .strip() inside the validator.
        if not isinstance(v, str):
            return v
        stripped = v.strip()
        if not stripped and v:
            msg = "must not be blank (whitespace-only)"
            raise ValueError(msg)
        return stripped if stripped else None


class ProductImportRequest(BaseModel):
    """Bulk product import payload."""

    products: list[CreateProductRequest]


class CSVImportError(BaseModel):
    """A single row-level error from CSV import."""

    row: int
    message: str


class CSVImportResponse(BaseModel):
    """Response from the CSV bulk import endpoint."""

    created: int
    updated: int
    errors: list[CSVImportError]
