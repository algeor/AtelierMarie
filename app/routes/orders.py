"""Order endpoints — checkout, list, detail."""

from typing import Annotated, Literal

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
from app.services import analytics_service
from app.services.order_service import (
    DeliveryMethodUnavailableError,
    EmptyCartError,
    InsufficientStockError,
    InvalidDeliveryOfficeError,
    InvalidShippingPriceError,
    OrderNotFoundError,
    PayOnDeliveryLimitError,
    ProductUnavailableError,
    checkout,
    get_order,
    list_orders,
)
from app.services.payment_rate_limit_service import (
    PaymentRateLimitExceededError,
    assert_stripe_session_rate_limit_available,
    consume_checkout_order_rate_limit,
    consume_pay_on_delivery_rate_limit,
    consume_payment_status_poll_rate_limit,
    consume_stripe_session_rate_limit,
)
from app.services.payment_service import (
    InvalidRetryStateError,
    InvalidRetryTokenError,
    PaymentAlreadyPaidError,
    StripeSessionError,
    create_checkout_session_async,
    create_retry_checkout_session_async,
    prepare_retry_session,
)
from app.services.payment_settings_service import get_payment_settings, payment_method_available

router = APIRouter()


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _public_order_response(order_data: object) -> OrderResponse:
    """Build customer-safe order responses without operational courier internals."""
    return OrderResponse.model_validate(order_data).model_copy(
        update={
            "courier_order_id": None,
            "courier_label_url": None,
            "courier_last_error": None,
        }
    )


@router.post(
    "",
    response_model=OrderResponse,
    status_code=201,
    summary="Place an order",
    description="Convert the current session's cart into an order. "
    "Validates stock, snapshots prices, decrements stock, and clears cart atomically. "
    "For card payments, returns stripe_checkout_url to redirect the customer.",
)
async def create_order(
    request: Request,
    body: CreateOrderRequest,
    session_id: Annotated[str, Depends(require_session)],
) -> OrderResponse | JSONResponse:
    """Place a new order from the current cart."""
    content_type = request.headers.get("content-type", "").lower()
    if "application/json" not in content_type:
        return error_response(422, "INVALID_CONTENT_TYPE", "Content-Type must be application/json")

    try:
        with get_db() as conn:
            consume_checkout_order_rate_limit(
                conn,
                session_id=session_id,
                ip_address=_client_ip(request),
            )
    except PaymentRateLimitExceededError as exc:
        return error_response(
            429,
            "RATE_LIMITED",
            str(exc),
            {
                "scope": exc.scope,
                "limit": exc.limit,
                "window_seconds": exc.window_seconds,
            },
        )

    settings = get_settings()

    with get_db() as conn:
        is_available = payment_method_available(conn, settings, body.payment_method)
        # payment_method_available() may lazily insert default settings.
        conn.commit()

    if not is_available:
        return error_response(
            422,
            "PAYMENT_METHOD_UNAVAILABLE",
            "Selected payment method is not currently available",
        )

    # Validate card payments: Stripe must be configured.
    if body.payment_method == "card" and not settings.stripe_secret_key:
        return error_response(422, "PAYMENT_METHOD_UNAVAILABLE", "Card payments are not configured")
    # Validate bank_transfer: IBAN must be configured.
    if body.payment_method == "bank_transfer" and not settings.bank_iban:
        return error_response(422, "PAYMENT_METHOD_UNAVAILABLE", "Bank transfer is not configured")

    if body.payment_method == "cod":
        try:
            with get_db() as conn:
                consume_pay_on_delivery_rate_limit(
                    conn,
                    session_id=session_id,
                    ip_address=_client_ip(request),
                )
        except PaymentRateLimitExceededError as exc:
            return error_response(
                429,
                "RATE_LIMITED",
                str(exc),
                {
                    "scope": exc.scope,
                    "limit": exc.limit,
                    "window_seconds": exc.window_seconds,
                },
            )

    if body.payment_method == "card":
        try:
            with get_db() as conn:
                assert_stripe_session_rate_limit_available(conn, session_id=session_id)
        except PaymentRateLimitExceededError as exc:
            return error_response(
                429,
                "RATE_LIMITED",
                str(exc),
                {
                    "scope": exc.scope,
                    "limit": exc.limit,
                    "window_seconds": exc.window_seconds,
                },
            )

    # Read analytics consent BEFORE opening the order connection. It runs its
    # own get_db(); nesting it inside the order's held connection would need two
    # pooled connections at once for a single request and dead-locks the psycopg
    # pool. The consent read is independent of the order transaction, so hoisting
    # it out does not affect checkout atomicity.
    analytics_consent = analytics_service.has_current_analytics_consent(session_id)

    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT s.user_id, s.preferred_locale, u.email AS user_email "
                "FROM sessions s LEFT JOIN users u ON u.id = s.user_id "
                "WHERE s.id = %s",
                (session_id,),
            ).fetchone()
            user_id = row["user_id"] if row else None
            preferred_locale = row["preferred_locale"] if row else None
            locale: Literal["en", "bg"] = "bg" if preferred_locale == "bg" else "en"

            # Resolve the order's contact email. A logged-in user may omit it and
            # fall back to their account email; anyone may supply a different one
            # (gift, work address). Anonymous checkout with neither is rejected.
            resolved_email = (
                str(body.customer_email)
                if body.customer_email
                else (row["user_email"] if row else None)
            )
            if not resolved_email:
                return JSONResponse(
                    status_code=422,
                    content={
                        "error": {
                            "code": "EMAIL_REQUIRED",
                            "message": "An email is required to place an order",
                        }
                    },
                )

            payment_settings = get_payment_settings(conn)
            pay_on_delivery_max_cents = (
                int(payment_settings["pay_on_delivery_max_cents"])
                if body.payment_method == "cod"
                else None
            )
            # get_payment_settings() may lazily insert defaults; close that
            # transaction before checkout() opens its own transaction block.
            conn.commit()

            order_data = checkout(
                conn=conn,
                session_id=session_id,
                customer_email=resolved_email,
                delivery=body.delivery,
                customer_name=body.customer_name,
                notes=body.notes,
                user_id=user_id,
                locale=locale,
                admin_notification_email=settings.admin_notification_email,
                payment_method=body.payment_method,
                analytics_consent=analytics_consent,
                shipping_cents=body.shipping_cents,
                shipping_price_source=body.shipping_price_source,
                shipping_is_fallback=body.shipping_is_fallback,
                shipping_quoted_at=body.shipping_quoted_at,
                invoice_profile=body.invoice_profile,
                pay_on_delivery_max_cents=pay_on_delivery_max_cents,
            )

            stripe_checkout_url: str | None = None
            if body.payment_method == "card":
                try:
                    consume_stripe_session_rate_limit(
                        conn,
                        order_id=order_data["id"],
                        session_id=session_id,
                    )
                    stripe_checkout_url = await create_checkout_session_async(
                        conn=conn,
                        order=order_data,
                        success_url=settings.stripe_success_url,
                        cancel_url=settings.stripe_cancel_url,
                        stripe_secret_key=settings.stripe_secret_key,
                    )
                except PaymentRateLimitExceededError as exc:
                    return error_response(
                        429,
                        "RATE_LIMITED",
                        str(exc),
                        {
                            "scope": exc.scope,
                            "limit": exc.limit,
                            "window_seconds": exc.window_seconds,
                        },
                    )
                except StripeSessionError as exc:
                    # Order was created; return it without a checkout URL so retry flow works.
                    import structlog

                    structlog.get_logger(__name__).error(
                        "stripe_session_create_failed",
                        order_id=order_data["id"],
                        error_type=type(exc).__name__,
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
    except DeliveryMethodUnavailableError as e:
        return error_response(
            422,
            "DELIVERY_METHOD_UNAVAILABLE",
            str(e),
            {"courier": e.courier, "method": e.method},
        )
    except InvalidShippingPriceError as e:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "INVALID_SHIPPING_PRICE",
                    "message": str(e),
                    "details": {"shipping_cents": e.shipping_cents, "max_cents": e.max_cents},
                }
            },
        )
    except PayOnDeliveryLimitError as e:
        return error_response(
            422,
            "PAY_ON_DELIVERY_LIMIT_EXCEEDED",
            str(e),
            {"total_cents": e.total_cents, "max_cents": e.max_cents},
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

    # Emit the purchase-confirmed analytics event AFTER the order connection is
    # released. record_purchase_confirmed runs its own get_db(); calling it inside
    # the held checkout connection would need two pooled connections for one
    # request and can dead-lock the psycopg pool (same reasoning as the consent
    # read hoisted above). Analytics is fire-and-forget and swallows its own
    # exceptions, so this never affects the order that already committed.
    analytics_service.record_purchase_confirmed(
        order_id=order_data["id"],
        session_id=session_id,
        user_id=user_id,
        locale=locale,
        total_cents=order_data["total_cents"],
        payment_method=body.payment_method,
        delivery_method=order_data["delivery_method"],
        delivery_courier=order_data["delivery_courier"],
        analytics_consent=analytics_consent,
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
async def create_stripe_retry_session(
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

    try:
        payload = await request.json()
    except ValueError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    payment_return_token = payload.get("payment_return_token") or payload.get("token") or ""

    with get_db() as conn:
        # Ownership check.
        row = conn.execute("SELECT user_id FROM sessions WHERE id = %s", (session_id,)).fetchone()
        user_id = row["user_id"] if row else None
        try:
            get_order(conn=conn, order_id=order_id, session_id=session_id, user_id=user_id)
        except OrderNotFoundError:
            return error_response(404, "NOT_FOUND", "Order not found")

        if not payment_method_available(conn, settings, "card"):
            return error_response(
                422,
                "PAYMENT_METHOD_UNAVAILABLE",
                "Card payments are not currently available",
            )
        # payment_method_available() may lazily insert default settings; close
        # that transaction before the rate limiter opens its own transaction.
        conn.commit()

        try:
            order, existing_url = prepare_retry_session(conn, order_id, payment_return_token)
            if existing_url:
                url = existing_url
            else:
                consume_stripe_session_rate_limit(conn, order_id=order_id, session_id=session_id)
                url = await create_retry_checkout_session_async(
                    conn=conn,
                    order=order,
                    success_url=settings.stripe_success_url,
                    cancel_url=settings.stripe_cancel_url,
                    stripe_secret_key=settings.stripe_secret_key,
                )
        except OrderNotFoundError:
            return error_response(404, "NOT_FOUND", "Order not found")
        except PaymentAlreadyPaidError:
            return error_response(409, "ALREADY_PAID", "Order is already paid")
        except InvalidRetryTokenError:
            return error_response(404, "NOT_FOUND", "Order not found")
        except InvalidRetryStateError as e:
            return error_response(409, "INVALID_PAYMENT_STATE", str(e))
        except PaymentRateLimitExceededError as e:
            return error_response(
                429,
                "RATE_LIMITED",
                str(e),
                {"scope": e.scope, "limit": e.limit, "window_seconds": e.window_seconds},
            )
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
        row = conn.execute("SELECT user_id FROM sessions WHERE id = %s", (session_id,)).fetchone()
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
    request: Request,
    session_id: Annotated[str, Depends(require_session)],
) -> OrderResponse | JSONResponse:
    """Get a specific order by ID (with ownership check)."""
    return_token = request.query_params.get("payment_return_token") or request.query_params.get(
        "token"
    )
    if return_token:
        try:
            with get_db() as conn:
                consume_payment_status_poll_rate_limit(
                    conn,
                    session_id=session_id,
                    ip_address=_client_ip(request),
                )
        except PaymentRateLimitExceededError as exc:
            return error_response(
                429,
                "RATE_LIMITED",
                str(exc),
                {"scope": exc.scope, "limit": exc.limit, "window_seconds": exc.window_seconds},
            )

    with get_db() as conn:
        row = conn.execute("SELECT user_id FROM sessions WHERE id = %s", (session_id,)).fetchone()
        user_id = row["user_id"] if row else None

        order_data = get_order(
            conn=conn,
            order_id=order_id,
            session_id=session_id,
            user_id=user_id,
        )

    return _public_order_response(order_data)
