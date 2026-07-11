"""Admin response models — dashboard stats."""

from pydantic import BaseModel, Field


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
