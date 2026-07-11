"""Product request and response models."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.common import PRODUCT_ID_PATTERN

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
    category: str | None = None
    image_url: str | None = None
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
    category: str | None = None
    image_url: str | None = None
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
    image_url: str | None = Field(default=None, max_length=500)
    stock: int = Field(..., ge=0, le=MAX_STOCK)
    is_active: bool = True
    is_featured: bool = False

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
        stripped = v.strip()
        if not stripped and v:
            msg = "must not be blank (whitespace-only)"
            raise ValueError(msg)
        return stripped if stripped else None

    @field_validator("image_url", mode="before")
    @classmethod
    def validate_image_url(cls, v: str | None) -> str | None:
        """Strip whitespace and validate URL format."""
        if v is None:
            return None
        stripped = v.strip()
        if not stripped:
            return None
        if not stripped.startswith(("http://", "https://", "/")):
            msg = "must be a valid URL (http://, https://, or relative path)"
            raise ValueError(msg)
        return stripped


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
    image_url: str | None = Field(default=None, max_length=500)
    stock: int | None = Field(default=None, ge=0, le=MAX_STOCK)
    is_active: bool | None = None
    is_featured: bool | None = None

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
        stripped = v.strip()
        if not stripped and v:
            msg = "must not be blank (whitespace-only)"
            raise ValueError(msg)
        return stripped if stripped else None

    @field_validator("image_url", mode="before")
    @classmethod
    def validate_image_url(cls, v: str | None) -> str | None:
        """Strip whitespace and validate URL format."""
        if v is None:
            return None
        stripped = v.strip()
        if not stripped:
            return None
        if not stripped.startswith(("http://", "https://", "/")):
            msg = "must be a valid URL (http://, https://, or relative path)"
            raise ValueError(msg)
        return stripped


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
