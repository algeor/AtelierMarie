"""Cart endpoints — add, update, remove items, view cart."""

from typing import Annotated

from fastapi import APIRouter, Path, Query, Request, Response

from app.database import get_db
from app.models.cart import (
    AddToCartRequest,
    CartItemResponse,
    CartResponse,
    UnavailableItem,
    UpdateCartItemRequest,
)
from app.models.common import PRODUCT_ID_PATTERN
from app.models.products import Locale, ProductResponse
from app.services.cart_service import (
    CartData,
    add_item,
    get_cart,
    remove_item,
    update_quantity,
)

router = APIRouter()

# Annotated path parameter with validation
ProductIdPath = Annotated[str, Path(..., pattern=PRODUCT_ID_PATTERN, max_length=100)]


def _cart_data_to_response(data: CartData) -> CartResponse:
    """Convert internal CartData to the Pydantic response model."""
    items = [
        CartItemResponse(
            product_id=item.product_id,
            product=ProductResponse(**item.product),
            quantity=item.quantity,
            added_at=item.added_at,
        )
        for item in data.items
    ]
    unavailable = [
        UnavailableItem(
            product_id=u.product_id,
            product_name=u.product_name,
            reason=u.reason,
        )
        for u in data.unavailable_items
    ]
    return CartResponse(
        items=items,
        total_cents=data.total_cents,
        item_count=data.item_count,
        unavailable_items=unavailable,
    )


@router.get("", response_model=CartResponse)
async def view_cart(
    request: Request,
    locale: Locale = Query(default="en", description="Content locale (en or bg)"),
) -> CartResponse:
    """Get the current session's cart contents."""
    session_id = request.state.session_id
    with get_db() as conn:
        data = get_cart(conn, session_id, locale=locale)
    return _cart_data_to_response(data)


@router.post("", response_model=CartResponse)
async def add_to_cart(
    request: Request,
    body: AddToCartRequest,
    response: Response,
    locale: Locale = Query(default="en", description="Content locale (en or bg)"),
) -> CartResponse:
    """Add a product to the cart or increment existing quantity.

    Service exceptions (ProductNotFoundError, InsufficientStockError,
    QuantityLimitError, CartFullError) propagate to global exception handlers.
    """
    session_id = request.state.session_id
    with get_db() as conn:
        result = add_item(conn, session_id, body.product_id, body.quantity, locale=locale)

    response.status_code = 201 if result.created else 200
    return _cart_data_to_response(result.cart)


@router.patch("/{product_id}", response_model=CartResponse)
async def update_cart_item(
    request: Request,
    product_id: ProductIdPath,
    body: UpdateCartItemRequest,
    locale: Locale = Query(default="en", description="Content locale (en or bg)"),
) -> CartResponse:
    """Update the quantity of a cart item. Quantity 0 removes it.

    Service exceptions (CartItemNotFoundError, InsufficientStockError,
    QuantityLimitError, ProductNotFoundError) propagate to global exception handlers.
    """
    session_id = request.state.session_id
    with get_db() as conn:
        data = update_quantity(conn, session_id, product_id, body.quantity, locale=locale)

    return _cart_data_to_response(data)


@router.delete("/{product_id}", response_model=CartResponse)
async def remove_from_cart(
    request: Request,
    product_id: ProductIdPath,
    locale: Locale = Query(default="en", description="Content locale (en or bg)"),
) -> CartResponse:
    """Remove an item from the cart entirely.

    CartItemNotFoundError propagates to global exception handler → 404.
    """
    session_id = request.state.session_id
    with get_db() as conn:
        data = remove_item(conn, session_id, product_id, locale=locale)

    return _cart_data_to_response(data)
