"""Order endpoints — checkout, list, detail."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from app.database import get_db
from app.dependencies.session import require_session
from app.models.orders import (
    CreateOrderRequest,
    OrderListResponse,
    OrderResponse,
)
from app.services.order_service import (
    EmptyCartError,
    InsufficientStockError,
    OrderNotFoundError,
    ProductUnavailableError,
    checkout,
    get_order,
    list_orders,
)

router = APIRouter()


@router.post(
    "",
    response_model=OrderResponse,
    status_code=201,
    summary="Place an order",
    description="Convert the current session's cart into an order. "
    "Validates stock, snapshots prices, decrements stock, and clears cart atomically.",
)
def create_order(
    request: Request,
    body: CreateOrderRequest,
    session_id: Annotated[str, Depends(require_session)],
) -> OrderResponse | JSONResponse:
    """Place a new order from the current cart."""
    # Defense-in-depth: reject non-JSON requests
    # Primary CSRF protection: SameSite=Lax session cookie
    content_type = request.headers.get("content-type", "").lower()
    if "application/json" not in content_type:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "INVALID_CONTENT_TYPE",
                    "message": "Content-Type must be application/json",
                }
            },
        )

    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT user_id, preferred_locale FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            user_id = row["user_id"] if row else None
            locale = (
                row["preferred_locale"] if row and row["preferred_locale"] in {"en", "bg"} else "en"
            )

            order_data = checkout(
                conn=conn,
                session_id=session_id,
                customer_email=str(body.customer_email),
                customer_name=body.customer_name,
                shipping_address=body.shipping_address,
                notes=body.notes,
                user_id=user_id,
                locale=locale,
            )
    except EmptyCartError:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "EMPTY_CART",
                    "message": "Cart is empty",
                }
            },
        )
    except InsufficientStockError as e:
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "INSUFFICIENT_STOCK",
                    "message": str(e),
                    "details": e.failures,
                }
            },
        )
    except ProductUnavailableError as e:
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "PRODUCT_UNAVAILABLE",
                    "message": str(e),
                    "details": e.failures,
                }
            },
        )

    return OrderResponse.model_validate(order_data)


@router.get(
    "",
    response_model=OrderListResponse,
    summary="List my orders",
    description="List orders belonging to the current session or authenticated user. "
    "Sorted newest-first with pagination.",
)
def list_my_orders(
    session_id: Annotated[str, Depends(require_session)],
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> OrderListResponse:
    """List orders for the current session/user."""
    with get_db() as conn:
        row = conn.execute("SELECT user_id FROM sessions WHERE id = ?", (session_id,)).fetchone()
        user_id = row["user_id"] if row else None

        result = list_orders(
            conn=conn,
            session_id=session_id,
            user_id=user_id,
            page=page,
            limit=limit,
        )

    return OrderListResponse(
        items=[OrderResponse.model_validate(o) for o in result["items"]],
        total=result["total"],
        page=result["page"],
        limit=result["limit"],
    )


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Get order detail",
    description="Get full order details including items. "
    "Only accessible by the session/user that owns the order.",
)
def get_order_detail(
    order_id: str,
    session_id: Annotated[str, Depends(require_session)],
) -> OrderResponse | JSONResponse:
    """Get a specific order by ID (with ownership check)."""
    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT user_id FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            user_id = row["user_id"] if row else None

            order_data = get_order(
                conn=conn,
                order_id=order_id,
                session_id=session_id,
                user_id=user_id,
            )
    except OrderNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "NOT_FOUND", "message": "Order not found"}},
        )

    return OrderResponse.model_validate(order_data)
