"""Order endpoints — checkout, list, detail."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import get_db
from app.dependencies.session import require_session
from app.models.orders import (
    CreateOrderRequest,
    OrderListResponse,
    OrderResponse,
)
from app.responses import error_response
from app.services.order_service import (
    EmptyCartError,
    InsufficientStockError,
    InvalidDeliveryOfficeError,
    OrderNotFoundError,
    ProductUnavailableError,
    checkout,
    get_order,
    list_orders,
)
from app.services.payment_service import (
    InvalidRetryStateError,
    PaymentAlreadyPaidError,
    StripeSessionError,
    create_checkout_session,
    create_retry_session,
)

router = APIRouter()


def _public_order_response(order_data: object) -> OrderResponse:
    """Build customer-safe order responses without operational courier ids."""
    return OrderResponse.model_validate(order_data).model_copy(update={"courier_order_id": None})


@router.post(
    "",
    response_model=OrderResponse,
    status_code=201,
    summary="Place an order",
    description="Convert the current session's cart into an order. "
    "Validates stock, snapshots prices, decrements stock, and clears cart atomically. "
    "For card payments, returns stripe_checkout_url to redirect the customer.",
)
def create_order(
    request: Request,
    body: CreateOrderRequest,
    session_id: Annotated[str, Depends(require_session)],
) -> OrderResponse | JSONResponse:
    """Place a new order from the current cart."""
    content_type = request.headers.get("content-type", "").lower()
    if "application/json" not in content_type:
        return error_response(422, "INVALID_CONTENT_TYPE", "Content-Type must be application/json")

    settings = get_settings()

    # Validate card payments: Stripe must be configured.
    if body.payment_method == "card" and not settings.stripe_secret_key:
        return error_response(422, "PAYMENT_METHOD_UNAVAILABLE", "Card payments are not configured")
    # Validate bank_transfer: IBAN must be configured.
    if body.payment_method == "bank_transfer" and not settings.bank_iban:
        return error_response(422, "PAYMENT_METHOD_UNAVAILABLE", "Bank transfer is not configured")

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
                delivery=body.delivery,
                customer_name=body.customer_name,
                notes=body.notes,
                user_id=user_id,
                locale=locale,
                admin_notification_email=settings.admin_notification_email,
                payment_method=body.payment_method,
            )

            stripe_checkout_url: str | None = None
            if body.payment_method == "card":
                try:
                    stripe_checkout_url = create_checkout_session(
                        conn=conn,
                        order=order_data,
                        success_url=settings.stripe_success_url,
                        cancel_url=settings.stripe_cancel_url,
                        stripe_secret_key=settings.stripe_secret_key,
                    )
                except StripeSessionError as exc:
                    # Order was created; return it without a checkout URL so retry flow works.
                    import structlog

                    structlog.get_logger(__name__).error(
                        "stripe_session_create_failed", order_id=order_data["id"], error=str(exc)
                    )

    except EmptyCartError:
        return error_response(400, "EMPTY_CART", "Cart is empty")
    except InvalidDeliveryOfficeError as e:
        return error_response(
            422,
            "INVALID_DELIVERY_OFFICE",
            str(e),
            {"courier": e.courier, "office_id": e.office_id, "reason": e.reason},
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

    response = _public_order_response(order_data)
    if stripe_checkout_url:
        response = response.model_copy(update={"stripe_checkout_url": stripe_checkout_url})
    return response


@router.post(
    "/{order_id}/stripe-session",
    summary="Create a new Stripe Checkout Session (retry payment)",
    description="Create a fresh Stripe session for a card order whose previous session expired. "
    "Requires session ownership. Returns {stripe_checkout_url}.",
)
def create_stripe_retry_session(
    order_id: str,
    request: Request,
    session_id: Annotated[str, Depends(require_session)],
) -> JSONResponse:
    """Retry payment: create a new Stripe Checkout Session for an existing card order."""
    content_type = request.headers.get("content-type", "").lower()
    if "application/json" not in content_type:
        return error_response(422, "INVALID_CONTENT_TYPE", "Content-Type must be application/json")

    settings = get_settings()
    if not settings.stripe_secret_key:
        return error_response(422, "PAYMENT_METHOD_UNAVAILABLE", "Card payments are not configured")

    with get_db() as conn:
        # Ownership check.
        row = conn.execute("SELECT user_id FROM sessions WHERE id = ?", (session_id,)).fetchone()
        user_id = row["user_id"] if row else None
        try:
            get_order(conn=conn, order_id=order_id, session_id=session_id, user_id=user_id)
        except OrderNotFoundError:
            return error_response(404, "NOT_FOUND", "Order not found")

        try:
            url = create_retry_session(
                conn=conn,
                order_id=order_id,
                success_url=settings.stripe_success_url,
                cancel_url=settings.stripe_cancel_url,
                stripe_secret_key=settings.stripe_secret_key,
            )
        except PaymentAlreadyPaidError:
            return error_response(409, "ALREADY_PAID", "Order is already paid")
        except InvalidRetryStateError as e:
            return error_response(409, "INVALID_PAYMENT_STATE", str(e))
        except StripeSessionError as e:
            return error_response(502, "STRIPE_ERROR", str(e))

    return JSONResponse(status_code=200, content={"stripe_checkout_url": url})


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
        items=[_public_order_response(o) for o in result["items"]],
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
) -> OrderResponse:
    """Get a specific order by ID (with ownership check)."""
    with get_db() as conn:
        row = conn.execute("SELECT user_id FROM sessions WHERE id = ?", (session_id,)).fetchone()
        user_id = row["user_id"] if row else None

        order_data = get_order(
            conn=conn,
            order_id=order_id,
            session_id=session_id,
            user_id=user_id,
        )

    return _public_order_response(order_data)
