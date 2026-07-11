"""Cart endpoints — add, update, remove items, view cart."""

from typing import Annotated

from fastapi import APIRouter, Path, Request, Response
from fastapi.responses import JSONResponse

from app.database import get_db
from app.models.cart import (
    AddToCartRequest,
    CartItemResponse,
    CartResponse,
    UnavailableItem,
    UpdateCartItemRequest,
)
from app.models.common import PRODUCT_ID_PATTERN
from app.models.products import ProductResponse
from app.services.cart_service import (
    CartData,
    CartFullError,
    CartItemNotFoundError,
    InsufficientStockError,
    ProductNotFoundError,
    QuantityLimitError,
    add_item,
    get_cart,
    remove_item,
    update_quantity,
)

router = APIRouter()

# Annotated path parameter with validation
ProductIdPath = Annotated[
    str, Path(..., pattern=PRODUCT_ID_PATTERN, max_length=100)
]


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


def _error_response(status_code: int, code: str, message: str, details: dict | None = None) -> JSONResponse:
    """Build a consistent error response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details,
            }
        },
    )


@router.get("", response_model=CartResponse)
async def view_cart(request: Request) -> CartResponse:
    """Get the current session's cart contents."""
    session_id = request.state.session_id
    with get_db() as conn:
        data = get_cart(conn, session_id)
    return _cart_data_to_response(data)


@router.post("", response_model=CartResponse)
async def add_to_cart(request: Request, body: AddToCartRequest, response: Response) -> CartResponse:
    """Add a product to the cart or increment existing quantity."""
    session_id = request.state.session_id
    try:
        with get_db() as conn:
            result = add_item(conn, session_id, body.product_id, body.quantity)
    except ProductNotFoundError as e:
        return _error_response(404, "PRODUCT_NOT_FOUND", str(e))  # type: ignore[return-value]
    except InsufficientStockError as e:
        return _error_response(  # type: ignore[return-value]
            409,
            "INSUFFICIENT_STOCK",
            str(e),
            {"product_id": e.product_id, "requested": e.requested, "available": e.available},
        )
    except QuantityLimitError as e:
        return _error_response(  # type: ignore[return-value]
            422, "QUANTITY_LIMIT_EXCEEDED", str(e), {"max_quantity": e.max_quantity}
        )
    except CartFullError as e:
        return _error_response(  # type: ignore[return-value]
            422, "CART_FULL", str(e), {"max_items": e.max_items}
        )

    response.status_code = 201 if result.created else 200
    return _cart_data_to_response(result.cart)


@router.patch("/{product_id}", response_model=CartResponse)
async def update_cart_item(
    request: Request, product_id: ProductIdPath, body: UpdateCartItemRequest
) -> CartResponse:
    """Update the quantity of a cart item. Quantity 0 removes it."""
    session_id = request.state.session_id
    try:
        with get_db() as conn:
            data = update_quantity(conn, session_id, product_id, body.quantity)
    except CartItemNotFoundError as e:
        return _error_response(404, "CART_ITEM_NOT_FOUND", str(e))  # type: ignore[return-value]
    except InsufficientStockError as e:
        return _error_response(  # type: ignore[return-value]
            409,
            "INSUFFICIENT_STOCK",
            str(e),
            {"product_id": e.product_id, "requested": e.requested, "available": e.available},
        )
    except QuantityLimitError as e:
        return _error_response(  # type: ignore[return-value]
            422, "QUANTITY_LIMIT_EXCEEDED", str(e), {"max_quantity": e.max_quantity}
        )

    return _cart_data_to_response(data)


@router.delete("/{product_id}", response_model=CartResponse)
async def remove_from_cart(request: Request, product_id: ProductIdPath) -> CartResponse:
    """Remove an item from the cart entirely."""
    session_id = request.state.session_id
    try:
        with get_db() as conn:
            data = remove_item(conn, session_id, product_id)
    except CartItemNotFoundError as e:
        return _error_response(404, "CART_ITEM_NOT_FOUND", str(e))  # type: ignore[return-value]

    return _cart_data_to_response(data)
