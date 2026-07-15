"""Order request and response models."""

from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

OrderStatus = Literal["pending", "confirmed", "shipped", "delivered", "cancelled"]


class OrderItemResponse(BaseModel):
    """Single item in an order — snapshot at purchase time."""

    product_id: str
    product_name: str
    price_cents: int
    quantity: int


class OrderResponse(BaseModel):
    """Public order representation."""

    id: str
    status: OrderStatus
    total_cents: int
    customer_email: str
    customer_name: str | None = None
    shipping_address: str | None = None
    notes: str | None = None
    items: list[OrderItemResponse]
    created_at: str
    updated_at: str


class OrderListResponse(BaseModel):
    """Paginated list of orders."""

    items: list[OrderResponse]
    total: int
    page: int
    limit: int


class CreateOrderRequest(BaseModel):
    """Input for placing a new order."""

    customer_email: EmailStr = Field(..., max_length=320)
    customer_name: str | None = Field(default=None, min_length=1, max_length=200)
    shipping_address: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("customer_name", mode="before")
    @classmethod
    def _strip_customer_name(cls, v: str | None) -> str | None:
        """Strip whitespace; reject strings that become empty after trimming."""
        if v is None:
            return None
        if not isinstance(v, str):
            return v
        stripped = v.strip()
        if not stripped:
            msg = "customer_name must not be blank (whitespace-only)"
            raise ValueError(msg)
        return stripped


class UpdateOrderStatusRequest(BaseModel):
    """Input for changing order status."""

    status: OrderStatus = Field(..., description="New order status")
