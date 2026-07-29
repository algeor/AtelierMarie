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
    revenue_cents: int = Field(..., description="Total revenue in cents")
    by_status: dict[str, int] = Field(
        default_factory=dict, description="Order count grouped by status"
    )


class DashboardResponse(BaseModel):
    """Admin dashboard overview statistics."""

    products: ProductStats
    orders: OrderStats
    low_stock_count: int = Field(..., description="Active products with stock <= 5")
    orders_today: int = Field(..., description="Orders created today")
    revenue_this_week_cents: int = Field(
        ..., description="Non-cancelled revenue from the last 7 days"
    )
    active_product_count: int = Field(..., description="Currently active products")


class LowStockProductsResponse(BaseModel):
    """Low-stock products list."""

    products: list[ProductAdminResponse]
    total: int
    threshold: int
