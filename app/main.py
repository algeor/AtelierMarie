"""FastAPI application factory and lifespan management."""

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.constants import VIDEO_SWEEPER_INTERVAL_SECONDS
from app.database import cleanup_expired_sessions, get_db, init_db
from app.exceptions import register_exception_handlers
from app.logging_config import configure_logging
from app.middleware.request_id import RequestIdMiddleware
from app.middleware.session import SessionMiddleware
from app.routes import (
    about,
    admin,
    analytics,
    auth,
    cart,
    comments,
    contact,
    cookies,
    delivery,
    faq,
    inventory,
    legal,
    locale,
    orders,
    payment_settings,
    products,
    promotions,
    reactions,
    taxonomy,
    terms,
    webhooks,
)
from app.services.analytics_service import (
    cleanup_expired_events,
    initialize_storage,
    load_jsonl_to_duckdb,
)
from app.services.contact_service import cleanup_old_contact_messages, drain_contact_message_emails
from app.services.courier_polling_service import poll_due_shipments_from_settings
from app.services.email_service import drain_email_outbox
from app.services.product_video_service import drain_video_transcodes

logger = structlog.get_logger(__name__)
SESSION_CLEANUP_INTERVAL_SECONDS = 3600
PAYMENT_RESERVATION_CLEANUP_INTERVAL_SECONDS = 60
_DT_FMT = "%Y-%m-%d %H:%M:%S"
# Poll interval for the email outbox sweeper. ~15s keeps "shipped" mail prompt
# without hammering the DB (design Decision 25); not 60s.
EMAIL_OUTBOX_INTERVAL_SECONDS = 15
VIDEO_TRANSCODE_INTERVAL_SECONDS = VIDEO_SWEEPER_INTERVAL_SECONDS


async def courier_status_polling_loop(
    *,
    interval_seconds: float | None = None,
    sleep: Callable[[float], Awaitable[object]] | None = None,
    poll: Callable[[], Awaitable[dict[str, int]]] | None = None,
) -> None:
    """Poll courier statuses on a fixed async tick without thread offload."""
    sleep_fn = sleep or asyncio.sleep
    poll_fn = poll or poll_due_shipments_from_settings

    while True:
        await sleep_fn(interval_seconds or get_settings().courier_polling_interval_seconds)
        try:
            result = await poll_fn()
            if result.get("succeeded") or result.get("failed"):
                logger.info("Polled courier statuses", **result)
        except Exception:
            logger.exception("Courier status polling failed")


def ensure_video_temp_path_is_private(static_path: Path, temp_path: Path) -> None:
    """Reject raw video staging inside the public /static mount."""
    static_root = static_path.resolve()
    temp_root = temp_path.resolve()
    try:
        temp_root.relative_to(static_root)
    except ValueError:
        return
    raise RuntimeError("VIDEO_UPLOAD_TEMP_PATH must not be inside STATIC_FILE_PATH")


def drain_all_email_outboxes() -> int:
    """Drain every durable email queue owned by the app."""
    return drain_email_outbox() + drain_contact_message_emails()


def cleanup_runtime_records() -> int:
    """Remove expired runtime records and enforce configured retention windows."""
    settings = get_settings()
    count = cleanup_expired_sessions() + cleanup_old_contact_messages(
        settings.contact_message_retention_days
    )
    count += cleanup_expired_events(settings.analytics_retention_days)
    return count


def _cancel_abandoned_card_orders() -> int:
    """Review or close expired/abandoned unpaid card orders.

    Must NOT touch COD or bank_transfer orders, and must not send anything to a
    courier. First expiry creates an admin callback window; if that review
    window expires without confirmation, the system cancels the order and
    releases the stock reservation without creating a refund.
    """
    from app.services.payment_service import expire_checkout_session
    from app.services.order_service import update_status

    reviewed = 0
    settings = get_settings()
    with get_db() as conn:
        close_rows = conn.execute(
            """
            SELECT id, status, payment_status, stripe_checkout_session_id
            FROM orders
            WHERE payment_method = 'card'
              AND payment_status = 'review_required'
              AND reserved_until IS NOT NULL
              AND reserved_until < datetime('now')
              AND status IN ('pending', 'confirmed')
            """
        ).fetchall()

        for row in close_rows:
            order_id = row["id"]
            payment_row = conn.execute(
                """
                SELECT id FROM payments
                WHERE order_id = ? AND provider = 'stripe'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (order_id,),
            ).fetchone()
            payment_id = payment_row["id"] if payment_row else None

            update_status(conn, order_id, "cancelled")
            conn.execute(
                """
                UPDATE orders
                SET payment_status = 'failed', reserved_until = NULL,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (order_id,),
            )
            if payment_id:
                conn.execute(
                    """
                    UPDATE payments
                    SET provider_status = 'failed', updated_at = datetime('now')
                    WHERE id = ?
                    """,
                    (payment_id,),
                )
            conn.execute(
                """
                INSERT INTO payment_events (
                    id, order_id, payment_id, event_type, source, provider,
                    provider_status, processing_status, details
                ) VALUES (?, ?, ?, 'reservation_closed', 'system', 'stripe',
                          'failed', 'processed', ?)
                """,
                (
                    str(uuid.uuid4()),
                    order_id,
                    payment_id,
                    json.dumps(
                        {
                            "old_order_status": row["status"],
                            "old_payment_status": row["payment_status"],
                            "new_order_status": "cancelled",
                            "new_payment_status": "failed",
                            "stock_released": True,
                            "refund_created": False,
                            "stripe_checkout_session_id": row["stripe_checkout_session_id"],
                        },
                        separators=(",", ":"),
                    ),
                ),
            )
            reviewed += 1
            logger.info("closed_unconfirmed_abandoned_card_order", order_id=order_id)

        review_until = (
            datetime.now(UTC) + timedelta(hours=settings.abandoned_card_review_hours)
        ).strftime(_DT_FMT)
        rows = conn.execute(
            """
            SELECT id, status, payment_status, stripe_checkout_session_id
            FROM orders
            WHERE payment_method = 'card'
              AND payment_status IN ('pending', 'failed')
              AND (
                  (reserved_until IS NOT NULL AND reserved_until < datetime('now'))
                  OR created_at < datetime('now', '-24 hours')
              )
              AND status NOT IN ('cancelled', 'shipped', 'delivered', 'return_in_transit', 'returned')
            """
        ).fetchall()

        for row in rows:
            order_id = row["id"]
            current = row["status"]
            payment_row = conn.execute(
                """
                SELECT id FROM payments
                WHERE order_id = ? AND provider = 'stripe'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (order_id,),
            ).fetchone()
            payment_id = payment_row["id"] if payment_row else None
            stripe_session_id = row["stripe_checkout_session_id"]
            stripe_expire_attempted = bool(stripe_session_id and settings.stripe_secret_key)
            stripe_expired = expire_checkout_session(stripe_session_id, settings.stripe_secret_key)
            conn.execute(
                """
                UPDATE orders
                SET payment_status = 'review_required', reserved_until = ?,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (review_until, order_id),
            )
            if payment_id:
                conn.execute(
                    """
                    UPDATE payments
                    SET provider_status = 'review_required', updated_at = datetime('now')
                    WHERE id = ?
                    """,
                    (payment_id,),
                )
            conn.execute(
                """
                INSERT INTO payment_events (
                    id, order_id, payment_id, event_type, source, provider,
                    provider_status, processing_status, details
                ) VALUES (?, ?, ?, 'reservation_expired', 'system', 'stripe',
                          'review_required', 'requires_review', ?)
                """,
                (
                    str(uuid.uuid4()),
                    order_id,
                    payment_id,
                    json.dumps(
                        {
                            "old_order_status": current,
                            "old_payment_status": row["payment_status"],
                            "new_order_status": current,
                            "new_payment_status": "review_required",
                            "review_expires_at": review_until,
                            "requires_admin_callback": True,
                            "stripe_checkout_session_id": stripe_session_id,
                            "stripe_expire_attempted": stripe_expire_attempted,
                            "stripe_expired": stripe_expired,
                        },
                        separators=(",", ":"),
                    ),
                ),
            )
            reviewed += 1
            logger.info("marked_abandoned_card_order_for_review", order_id=order_id)

    return reviewed


async def session_cleanup_loop(
    *,
    interval_seconds: float = SESSION_CLEANUP_INTERVAL_SECONDS,
    sleep: Callable[[float], Awaitable[object]] | None = None,
    cleanup: Callable[[], int] | None = None,
) -> None:
    """Periodically remove expired sessions until cancelled."""
    sleep_fn = sleep or asyncio.sleep
    cleanup_fn = cleanup or cleanup_runtime_records

    while True:
        await sleep_fn(interval_seconds)
        try:
            count = await asyncio.to_thread(cleanup_fn)
            if count:
                logger.info("Cleaned up expired sessions", count=count)
        except Exception:
            logger.exception("Session cleanup failed")


async def payment_reservation_cleanup_loop(
    *,
    interval_seconds: float = PAYMENT_RESERVATION_CLEANUP_INTERVAL_SECONDS,
    sleep: Callable[[float], Awaitable[object]] | None = None,
    cleanup: Callable[[], int] | None = None,
) -> None:
    """Cancel expired unpaid card reservations on a 60-second tick."""
    sleep_fn = sleep or asyncio.sleep
    cleanup_fn = cleanup or _cancel_abandoned_card_orders

    while True:
        await sleep_fn(interval_seconds)
        try:
            count = await asyncio.to_thread(cleanup_fn)
            if count:
                logger.info("Cleaned up expired payment reservations", count=count)
        except Exception:
            logger.exception("Payment reservation cleanup failed")


async def email_outbox_loop(
    *,
    interval_seconds: float = EMAIL_OUTBOX_INTERVAL_SECONDS,
    sleep: Callable[[float], Awaitable[object]] | None = None,
    drain: Callable[[], int] | None = None,
) -> None:
    """Drain the durable email outbox on a fixed tick (design Decision 25).

    One instance runs per uvicorn worker. The drain does blocking network I/O
    (ZeptoMail HTTP), so it runs in a threadpool to avoid stalling the event
    loop. All exceptions are swallowed/logged so the loop never dies.
    """
    sleep_fn = sleep or asyncio.sleep
    drain_fn = drain or drain_all_email_outboxes

    while True:
        await sleep_fn(interval_seconds)
        try:
            count = await asyncio.to_thread(drain_fn)
            if count:
                logger.info("Drained email outbox", count=count)
        except Exception:
            logger.exception("Email outbox drain failed")


async def video_transcode_loop(
    *,
    interval_seconds: float = VIDEO_TRANSCODE_INTERVAL_SECONDS,
    sleep: Callable[[float], Awaitable[object]] | None = None,
    drain: Callable[[], int] | None = None,
) -> None:
    """Drain queued product video transcodes on a fixed tick."""
    sleep_fn = sleep or asyncio.sleep
    drain_fn = drain or drain_video_transcodes

    while True:
        await sleep_fn(interval_seconds)
        try:
            count = await asyncio.to_thread(drain_fn)
            if count:
                logger.info("Drained product video transcodes", count=count)
        except Exception:
            logger.exception("Product video transcode drain failed")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: initialize database on startup, run background tasks."""
    settings = get_settings()
    configure_logging(settings.environment)
    init_db(settings.database_path)
    if settings.analytics_enabled:
        await asyncio.to_thread(initialize_storage)

    # Ensure static file directories exist
    static_path = Path(settings.static_file_path)
    video_temp_path = Path(settings.video_upload_temp_path)
    ensure_video_temp_path_is_private(static_path, video_temp_path)
    static_path.mkdir(parents=True, exist_ok=True)
    (static_path / "products").mkdir(exist_ok=True)
    video_temp_path.mkdir(parents=True, exist_ok=True)

    # Background task: clean expired sessions every hour
    task = asyncio.create_task(session_cleanup_loop())
    payment_task = asyncio.create_task(payment_reservation_cleanup_loop())
    courier_polling_task = asyncio.create_task(
        courier_status_polling_loop(interval_seconds=settings.courier_polling_interval_seconds)
    )
    # Background task: drain the durable email outbox (~15s tick, per worker)
    email_task = asyncio.create_task(email_outbox_loop())
    video_task = asyncio.create_task(video_transcode_loop())
    yield
    if settings.analytics_enabled:
        await asyncio.to_thread(load_jsonl_to_duckdb)
    for background_task in (task, payment_task, courier_polling_task, email_task, video_task):
        background_task.cancel()
        try:
            await asyncio.wait_for(background_task, timeout=5.0)
        except (TimeoutError, asyncio.CancelledError):
            pass


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    ensure_video_temp_path_is_private(
        Path(settings.static_file_path), Path(settings.video_upload_temp_path)
    )

    application = FastAPI(
        title="Atelier Marie",
        description=(
            "Luxury candle e-commerce API.\n\n"
            "## Authentication\n\n"
            "- **Public endpoints** (products, cart): Require a session cookie "
            "(automatically issued on first request).\n"
            "- **Admin endpoints** (`/v1/admin/*`): Require a Bearer token via "
            "the `Authorization` header.\n\n"
            "## Error Responses\n\n"
            "All errors return a consistent JSON envelope:\n"
            "```json\n"
            '{"error": {"code": "ERROR_CODE", "message": "Human-readable message", '
            '"details": null}}\n'
            "```\n\n"
            "## Pagination\n\n"
            "List endpoints accept `page` (1-based) and `limit` (1–100, default 20) "
            "query parameters. Responses include `total`, `page`, and `limit` fields."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/v1/docs",
        redoc_url="/v1/redoc",
        openapi_url="/v1/openapi.json",
        openapi_tags=[
            {
                "name": "products",
                "description": "Public product catalog — browse, search, and filter candles.",
            },
            {
                "name": "cart",
                "description": "Shopping cart — add, update, remove items. Session-based.",
            },
            {
                "name": "orders",
                "description": "Order placement and tracking.",
            },
            {
                "name": "auth",
                "description": "Authentication — Google OAuth 2.0, session management.",
            },
            {
                "name": "analytics",
                "description": "First-party consented storefront funnel analytics.",
            },
            {
                "name": "admin",
                "description": (
                    "Admin operations — product CRUD, CSV import, order management, "
                    "dashboard stats. Requires admin Bearer token."
                ),
            },
        ],
    )

    # SessionMiddleware added first (runs closest to routes);
    # RequestIdMiddleware added second (runs before session — Starlette is LIFO);
    # CORSMiddleware added last (runs first on incoming requests)
    application.add_middleware(SessionMiddleware)
    application.add_middleware(RequestIdMiddleware)

    # CORS middleware (outermost — handles pre-flight OPTIONS before session creation)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
        max_age=3600,
    )

    # Health endpoint (non-versioned — excluded from session middleware)
    @application.get("/health", tags=["health"], summary="Health check")
    async def health() -> JSONResponse:
        """Simple liveness probe. Returns 200 with status ok."""
        return JSONResponse({"status": "ok"})

    # Legacy versioned health endpoint (kept for backward compatibility)
    @application.get("/v1/health", tags=["health"], summary="Health check (versioned)")
    async def health_v1() -> JSONResponse:
        """Versioned health check — kept for backward compatibility."""
        return JSONResponse({"status": "ok"})

    # Routers
    application.mount(
        "/static",
        StaticFiles(directory=settings.static_file_path, check_dir=False),
        name="static",
    )
    application.include_router(products.router, prefix="/v1/products", tags=["products"])
    application.include_router(cart.router, prefix="/v1/cart", tags=["cart"])
    application.include_router(orders.router, prefix="/v1/orders", tags=["orders"])
    application.include_router(
        payment_settings.public_router, prefix="/v1/settings", tags=["settings"]
    )
    application.include_router(analytics.router, prefix="/v1/analytics", tags=["analytics"])
    application.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
    application.include_router(admin.router, prefix="/v1/admin", tags=["admin"])
    application.include_router(
        payment_settings.admin_router,
        prefix="/v1/admin/settings",
        tags=["admin-settings"],
    )
    application.include_router(about.public_router, prefix="/v1/about", tags=["about"])
    application.include_router(about.admin_router, prefix="/v1/admin/about", tags=["admin-about"])
    application.include_router(taxonomy.public_router, prefix="/v1/taxonomy", tags=["taxonomy"])
    application.include_router(taxonomy.admin_router, prefix="/v1/admin/taxonomy", tags=["admin"])
    application.include_router(faq.public_router, prefix="/v1/faq", tags=["faq"])
    application.include_router(faq.admin_router, prefix="/v1/admin/faq", tags=["admin-faq"])
    application.include_router(terms.public_router, prefix="/v1/terms", tags=["terms"])
    application.include_router(terms.admin_router, prefix="/v1/admin/terms", tags=["admin-terms"])
    application.include_router(cookies.public_router, prefix="/v1/cookies", tags=["cookies"])
    application.include_router(
        cookies.admin_router, prefix="/v1/admin/cookies", tags=["admin-cookies"]
    )
    application.include_router(legal.router, prefix="/v1/legal", tags=["legal"])
    application.include_router(
        inventory.admin_router, prefix="/v1/admin/inventory", tags=["admin-inventory"]
    )
    application.include_router(
        promotions.admin_router, prefix="/v1/admin/promotions", tags=["admin-promotions"]
    )
    application.include_router(
        promotions.public_router, prefix="/v1/promotions", tags=["promotions"]
    )
    application.include_router(reactions.router, prefix="/v1/products", tags=["reactions"])
    application.include_router(comments.router, prefix="/v1/products", tags=["comments"])
    application.include_router(contact.router, prefix="/v1/contact", tags=["contact"])
    application.include_router(locale.router, prefix="/v1/locale", tags=["locale"])
    application.include_router(delivery.router, prefix="/v1/delivery", tags=["delivery"])
    application.include_router(webhooks.router, prefix="/v1/webhooks", tags=["webhooks"])

    # Global exception handlers for consistent error format
    register_exception_handlers(application)

    return application


app = create_app()
