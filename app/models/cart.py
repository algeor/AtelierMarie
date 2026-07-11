"""Cart request and response models."""

from pydantic import BaseModel, Field

from app.models.common import PRODUCT_ID_PATTERN
from app.models.products import ProductResponse


class UnavailableItem(BaseModel):
    """A cart item referencing a product that is no longer available."""

    product_id: str
    product_name: str
    reason: str


class CartItemResponse(BaseModel):
    """Single item in the cart with embedded product details."""

    product_id: str
    product: ProductResponse
    quantity: int
    added_at: str


class CartResponse(BaseModel):
    """Full cart contents with computed totals."""

    items: list[CartItemResponse]
    total_cents: int
    item_count: int
    unavailable_items: list[UnavailableItem] = []


class AddToCartRequest(BaseModel):
    """Input for adding a product to the cart."""

    product_id: str = Field(..., pattern=PRODUCT_ID_PATTERN)
    quantity: int = Field(default=1, ge=1, le=99)


class UpdateCartItemRequest(BaseModel):
    """Input for updating cart item quantity. Quantity 0 means remove."""

    quantity: int = Field(..., ge=0, le=99)
