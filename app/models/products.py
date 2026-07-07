"""Product request and response models."""

from pydantic import BaseModel, Field, model_validator

from app.models.common import PRODUCT_ID_PATTERN


class ProductResponse(BaseModel):
    """Public product representation."""

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


class ProductListResponse(BaseModel):
    """Paginated list of products."""

    products: list[ProductResponse]
    total: int
    page: int
    limit: int


class CreateProductRequest(BaseModel):
    """Input for creating a new product."""

    id: str = Field(..., min_length=1, pattern=PRODUCT_ID_PATTERN)
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    materials: str | None = Field(default=None, max_length=1000)
    days_to_craft: int | None = Field(default=None, ge=0)
    price_cents: int = Field(..., gt=0)
    category: str | None = Field(default=None, max_length=100)
    image_url: str | None = Field(default=None, max_length=500)
    stock: int = Field(..., ge=0)
    is_active: bool = True
    is_featured: bool = False


class UpdateProductRequest(BaseModel):
    """Input for partially updating a product. All fields optional.

    Use model_dump(exclude_unset=True) in services to distinguish
    'client sent null' from 'client did not send this field'.
    """

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    materials: str | None = Field(default=None, max_length=1000)
    days_to_craft: int | None = Field(default=None, ge=0)
    price_cents: int | None = Field(default=None, gt=0)
    category: str | None = Field(default=None, max_length=100)
    image_url: str | None = Field(default=None, max_length=500)
    stock: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    is_featured: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_explicit_null_name(cls, data: dict) -> dict:
        """Reject explicit null for name — DB column is NOT NULL."""
        if isinstance(data, dict) and "name" in data and data["name"] is None:
            msg = "name cannot be explicitly set to null"
            raise ValueError(msg)
        return data


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
