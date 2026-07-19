"""Order request and response models."""

from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.models.delivery import DeliveryInfo

OrderStatus = Literal["pending", "confirmed", "shipped", "delivered", "cancelled"]


class OrderItemResponse(BaseModel):
    """Single item in an order — snapshot at purchase time."""

    product_id: str
    product_name: str
    price_cents: int
    quantity: int


class OrderResponse(BaseModel):
    """Public order representation.

    `items_total_cents` and `shipping_cents` sum to `total_cents`. In this
    change `shipping_cents` is always 0 — the follow-on `shipping-pricing`
    change wires real courier pricing.
    """

    id: str
    status: OrderStatus
    items_total_cents: int
    shipping_cents: int = 0
    total_cents: int
    customer_email: str
    customer_name: str | None = None
    # Structured delivery fields.
    delivery_method: Literal["office", "door"] | None = None
    delivery_courier: Literal["speedy", "econt"] | None = None
    delivery_details: dict | None = None
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
    """Input for placing a new order.

    Delivery is a structured object (method + courier + sub-object). See
    openspec change `shipping-courier-integration` Decision 1.
    """

    customer_email: EmailStr
    customer_name: str | None = Field(default=None, max_length=200)
    delivery: DeliveryInfo
    notes: str | None = Field(default=None, max_length=2000)


class UpdateOrderStatusRequest(BaseModel):
    """Input for changing order status."""

    status: OrderStatus = Field(..., description="New order status")
