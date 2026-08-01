"""Admin response models — dashboard stats."""

from pydantic import BaseModel, Field

from app.models.products import ProductAdminResponse


class ProductStats(BaseModel):
    """Product-level statistics."""

    total: int = Field(..., description="Total products (active + inactive)")
    active: int = Field(..., description="Currently active/visible products")


class OrderStats(BaseModel):
    """Order-level statistics."""

    total: int = Field(..., description="Total orders placed")
    revenue_cents: int = Field(..., description="Paid-order revenue in cents")
    by_status: dict[str, int] = Field(
        default_factory=dict, description="Order count grouped by status"
    )
    by_payment_status: dict[str, int] = Field(
        default_factory=dict, description="Order count grouped by payment status"
    )


class DashboardResponse(BaseModel):
    """Admin dashboard overview statistics."""

    products: ProductStats
    orders: OrderStats
    low_stock_count: int = Field(..., description="Active products with stock <= 5")
    orders_today: int = Field(..., description="Orders created today")
    revenue_this_week_cents: int = Field(
        ..., description="Paid-order revenue from the last 7 days"
    )
    active_product_count: int = Field(..., description="Currently active products")
    contact_messages_needing_attention: int = Field(
        default=0,
        description="Contact messages whose owner notification is not successfully sent",
    )


class AdminAlertResponse(BaseModel):
    """One in-app admin alert."""

    id: str
    alert_type: str
    order_id: str | None = None
    source: str
    severity: str
    title: str
    message: str
    details: dict = Field(default_factory=dict)
    is_read: bool
    created_at: str


class AdminAlertListResponse(BaseModel):
    """Recent admin alerts."""

    alerts: list[AdminAlertResponse]
    total: int


class LowStockProductsResponse(BaseModel):
    """Low-stock products list."""

    products: list[ProductAdminResponse]
    total: int
    threshold: int
