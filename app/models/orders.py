"""Order request and response models."""

from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

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
    tracking_number: str | None = None
    tracking_carrier: str | None = None
    tracking_url: str | None = None
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

    customer_email: EmailStr = Field(..., max_length=320)
    customer_name: str | None = Field(default=None, min_length=1, max_length=200)
    delivery: DeliveryInfo
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
    """Input for changing order status.

    Tracking fields are optional at the schema level and required only when
    `status == "shipped"` — that conditional check lives in the service layer
    (see order_service.TrackingRequiredError) so it can use the standard error
    envelope, not Pydantic's RequestValidationError shape.
    """

    status: OrderStatus = Field(..., description="New order status")
    tracking_number: str | None = Field(default=None, max_length=100)
    tracking_carrier: str | None = Field(default=None, max_length=50)
    tracking_url: str | None = Field(default=None, max_length=500)


class OrderEmailAudit(BaseModel):
    """One row of the order_emails send-attempt audit trail."""

    event: str
    recipient: str
    status: str
    reason: str | None = None
    attempts: int
    sent_at: str


class OrderEmailAuditResponse(BaseModel):
    """Audit trail for an order's email send attempts (admin-only)."""

    order_id: str
    emails: list[OrderEmailAudit]
