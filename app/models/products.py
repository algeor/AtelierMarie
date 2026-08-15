"""Product request and response models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.common import PRODUCT_ID_PATTERN
from app.services.pricing import normalize_discount_datetime

# Maximum stock value — prevents absurd inventory numbers
MAX_STOCK = 99999

# Maximum shipping weight in grams — 100 kg, generous headroom over the ~800g
# max real candle. Local to this module, mirroring MAX_STOCK above.
MAX_WEIGHT_GRAMS = 100_000

# Field bounds shared between the Pydantic models and the CSV import parser
# (which bypasses Pydantic and must re-apply the same limits manually).
MAX_NAME_LENGTH = 200
MAX_MATERIALS_LENGTH = 1000
MAX_DAYS_TO_CRAFT = 365
MAX_DESCRIPTION_LENGTH = 5000
MAX_SAFETY_TEXT_LENGTH = 2000
MAX_CATEGORY_LENGTH = 100
MAX_IMAGE_URL_LENGTH = 500

# Supported locales
Locale = Literal["en", "bg"]


class ProductLabelRef(BaseModel):
    """A label assigned to a product: slug for filtering, localized name for display."""

    slug: str
    name: str


class ProductResponse(BaseModel):
    """Public product representation (locale-resolved name/description)."""

    id: str
    name: str
    description: str | None = None
    safety_warnings: str | None = None
    care_instructions: str | None = None
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
    # `category` now carries the managed category/tier slug (was legacy free text).
    category: str | None
    category_name: str | None
    product_type: str
    product_type_name: str
    labels: list[ProductLabelRef]
    images: list[ProductImage] = Field(default_factory=list)
    video: ProductVideo | None = None
    primary_image_url: str | None = None
    primary_thumbnail_url: str | None = None
    stock: int
    can_order: bool = True
    available_now: bool = True
    availability_status: Literal["in_stock", "crafted_later"] = "in_stock"
    ships_when_complete: bool = True
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
    safety_warnings_en: str | None = None
    safety_warnings_bg: str | None = None
    care_instructions_en: str | None = None
    care_instructions_bg: str | None = None
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
    # Managed taxonomy slugs for prefilling admin form controls.
    category: str | None = None
    product_type: str = "candles"
    labels: list[str] = Field(default_factory=list)
    images: list[ProductImage] = Field(default_factory=list)
    video: ProductVideo | None = None
    primary_image_url: str | None = None
    primary_thumbnail_url: str | None = None
    stock: int
    inventory_mode: Literal["legacy", "fallback", "ledger_managed"] = "legacy"
    stock_source: Literal["product_stock", "inventory_ledger", "mixed"] = "product_stock"
    ledger_managed: bool = False
    valuation_readiness: Literal["setup_required", "estimate_only", "ready", "blocked"] = (
        "setup_required"
    )
    active_recipe_id: str | None = None
    active_recipe_status: Literal["missing", "draft", "active", "archived"] = "missing"
    active_recipe_review_state: str | None = None
    latest_batch_id: str | None = None
    latest_batch_number: str | None = None
    latest_batch_status: str | None = None
    latest_batch_date: str | None = None
    inventory_exception_count: int = 0
    inventory_exceptions: list[dict] = Field(default_factory=list)
    inventory_links: dict[str, str | None] | None = None
    weight_grams: int
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


class SavedProductStatusResponse(BaseModel):
    """Saved-product status for one product."""

    product_id: str
    saved: bool


class SavedProductListResponse(ProductListResponse):
    """Saved product list plus IDs for fast client-side bookmark state."""

    product_ids: list[str]


class ProductAdminListResponse(BaseModel):
    """Paginated list of products for admin (includes both language fields)."""

    products: list[ProductAdminResponse]
    total: int
    page: int
    limit: int
    applied_filters: dict[str, str | int | bool | list[str] | None] = Field(default_factory=dict)


class ProductImage(BaseModel):
    """One image belonging to a product gallery."""

    id: str
    image_url: str
    thumbnail_url: str
    zoom_url: str | None = None
    sort_order: int
    is_primary: bool


class ProductVideo(BaseModel):
    """One video belonging to a product gallery."""

    id: str
    product_id: str
    status: Literal["queued", "transcoding", "ready", "failed"]
    video_url: str | None = None
    poster_url: str | None = None
    sort_order: int = 0
    duration_secs: float | None = None
    failure_reason: str | None = None
    created_at: str
    updated_at: str


class UpdateProductVideoRequest(BaseModel):
    """Input for setting a product video's gallery position."""

    sort_order: int = Field(..., ge=0, le=100)


class ReorderProductImagesRequest(BaseModel):
    """Input for replacing a product gallery's display order."""

    ordered_ids: list[str] = Field(..., min_length=0, max_length=6)


class ProductImageImportRequest(BaseModel):
    """Input for registering already-generated image variant URLs."""

    image_url: str = Field(..., min_length=1, max_length=MAX_IMAGE_URL_LENGTH)
    thumbnail_url: str = Field(..., min_length=1, max_length=MAX_IMAGE_URL_LENGTH)
    zoom_url: str | None = Field(default=None, max_length=MAX_IMAGE_URL_LENGTH)

    @field_validator("image_url", "thumbnail_url", "zoom_url", mode="before")
    @classmethod
    def strip_and_reject_blank_urls(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not isinstance(v, str):
            return v
        stripped = v.strip()
        if not stripped:
            msg = "must not be blank"
            raise ValueError(msg)
        return stripped

    @field_validator("image_url", "thumbnail_url", "zoom_url")
    @classmethod
    def validate_media_urls(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not v.startswith(("http://", "https://", "/")):
            msg = "must be http(s) or an absolute relative path"
            raise ValueError(msg)
        return v


class CreateProductRequest(BaseModel):
    """Input for creating a new product."""

    id: str = Field(..., min_length=1, max_length=100, pattern=PRODUCT_ID_PATTERN)
    name_en: str = Field(..., min_length=1, max_length=MAX_NAME_LENGTH)
    name_bg: str | None = Field(default=None, max_length=MAX_NAME_LENGTH)
    description_en: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    description_bg: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    safety_warnings_en: str | None = Field(default=None, max_length=MAX_SAFETY_TEXT_LENGTH)
    safety_warnings_bg: str | None = Field(default=None, max_length=MAX_SAFETY_TEXT_LENGTH)
    care_instructions_en: str | None = Field(default=None, max_length=MAX_SAFETY_TEXT_LENGTH)
    care_instructions_bg: str | None = Field(default=None, max_length=MAX_SAFETY_TEXT_LENGTH)
    materials: str | None = Field(default=None, max_length=MAX_MATERIALS_LENGTH)
    days_to_craft: int | None = Field(default=None, ge=0, le=MAX_DAYS_TO_CRAFT)
    price_cents: int = Field(..., gt=0, le=99_999_99)
    category: str | None = Field(default=None, max_length=MAX_CATEGORY_LENGTH)
    # Optional: when omitted, the service assigns the default active product type
    # (lowest sort_order) rather than a hardcoded slug.
    product_type: str | None = Field(default=None, min_length=1, max_length=100)
    labels: list[str] = Field(default_factory=list, max_length=50)
    discount_percent: int | None = Field(default=None, ge=1, le=99)
    discount_starts_at: str | None = None
    discount_ends_at: str | None = None
    stock: int = Field(..., ge=0, le=MAX_STOCK)
    weight_grams: int = Field(default=300, ge=1, le=MAX_WEIGHT_GRAMS)
    is_active: bool = True
    is_featured: bool = False

    @field_validator("discount_starts_at", "discount_ends_at")
    @classmethod
    def _normalize_discount_datetime(cls, v: str | None) -> str | None:
        """Normalize datetime input to canonical UTC; reject timezone-less input."""
        return normalize_discount_datetime(v)

    @model_validator(mode="after")
    def _validate_discount_window(self) -> CreateProductRequest:
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
        "safety_warnings_en",
        "safety_warnings_bg",
        "care_instructions_en",
        "care_instructions_bg",
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

    name_en: str | None = Field(default=None, min_length=1, max_length=MAX_NAME_LENGTH)
    name_bg: str | None = Field(default=None, max_length=MAX_NAME_LENGTH)
    description_en: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    description_bg: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    safety_warnings_en: str | None = Field(default=None, max_length=MAX_SAFETY_TEXT_LENGTH)
    safety_warnings_bg: str | None = Field(default=None, max_length=MAX_SAFETY_TEXT_LENGTH)
    care_instructions_en: str | None = Field(default=None, max_length=MAX_SAFETY_TEXT_LENGTH)
    care_instructions_bg: str | None = Field(default=None, max_length=MAX_SAFETY_TEXT_LENGTH)
    materials: str | None = Field(default=None, max_length=MAX_MATERIALS_LENGTH)
    days_to_craft: int | None = Field(default=None, ge=0, le=MAX_DAYS_TO_CRAFT)
    price_cents: int | None = Field(default=None, gt=0, le=99_999_99)
    category: str | None = Field(default=None, max_length=MAX_CATEGORY_LENGTH)
    product_type: str | None = Field(default=None, min_length=1, max_length=100)
    labels: list[str] | None = Field(default=None, max_length=50)
    discount_percent: int | None = Field(default=None, ge=1, le=99)
    discount_starts_at: str | None = None
    discount_ends_at: str | None = None
    stock: int | None = Field(default=None, ge=0, le=MAX_STOCK)
    weight_grams: int | None = Field(default=None, ge=1, le=MAX_WEIGHT_GRAMS)
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
        "safety_warnings_en",
        "safety_warnings_bg",
        "care_instructions_en",
        "care_instructions_bg",
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
