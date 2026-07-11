"""Order request and response models."""

from typing import Literal

from pydantic import BaseModel, EmailStr, Field

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

    customer_email: EmailStr
    customer_name: str | None = Field(default=None, max_length=200)
    shipping_address: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=2000)


class UpdateOrderStatusRequest(BaseModel):
    """Input for changing order status."""

    status: OrderStatus = Field(..., description="New order status")
