"""Pydantic request/response models — the API contract layer."""

from app.models.cart import (
    AddToCartRequest,
    CartItemResponse,
    CartResponse,
    UpdateCartItemRequest,
)
from app.models.common import (
    PRODUCT_ID_PATTERN,
    ErrorDetail,
    ErrorResponse,
    LimitParam,
    PageParam,
    PaginationParams,
)
from app.models.orders import (
    CreateOrderRequest,
    OrderItemResponse,
    OrderListResponse,
    OrderResponse,
    UpdateOrderStatusRequest,
)
from app.models.products import (
    CreateProductRequest,
    ProductImportRequest,
    ProductListResponse,
    ProductResponse,
    UpdateProductRequest,
)
from app.models.users import UserResponse

__all__ = [
    # Common
    "ErrorDetail",
    "ErrorResponse",
    "LimitParam",
    "PageParam",
    "PaginationParams",
    "PRODUCT_ID_PATTERN",
    # Products
    "CreateProductRequest",
    "ProductImportRequest",
    "ProductListResponse",
    "ProductResponse",
    "UpdateProductRequest",
    # Cart
    "AddToCartRequest",
    "CartItemResponse",
    "CartResponse",
    "UpdateCartItemRequest",
    # Orders
    "CreateOrderRequest",
    "OrderItemResponse",
    "OrderListResponse",
    "OrderResponse",
    "UpdateOrderStatusRequest",
    # Users
    "UserResponse",
]
