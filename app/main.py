"""FastAPI application factory and lifespan management."""

import asyncio
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import cleanup_expired_sessions, get_db, init_db
from app.exceptions import register_exception_handlers
from app.logging_config import configure_logging
from app.middleware.request_id import RequestIdMiddleware
from app.middleware.session import SessionMiddleware
from app.routes import (
    admin,
    auth,
    cart,
    comments,
    contact,
    delivery,
    faq,
    locale,
    orders,
    products,
    promotions,
    reactions,
    taxonomy,
    webhooks,
)
from app.services.contact_service import cleanup_old_contact_messages, drain_contact_message_emails
from app.services.email_service import drain_email_outbox

logger = structlog.get_logger(__name__)
SESSION_CLEANUP_INTERVAL_SECONDS = 3600
# Poll interval for the email outbox sweeper. ~15s keeps "shipped" mail prompt
# without hammering the DB (design Decision 25); not 60s.
EMAIL_OUTBOX_INTERVAL_SECONDS = 15


def drain_all_email_outboxes() -> int:
    """Drain every durable email queue owned by the app."""
    return drain_email_outbox() + drain_contact_message_emails()


def cleanup_runtime_records() -> int:
    """Remove expired sessions, aged-out contact inquiries, and abandoned card orders."""
    settings = get_settings()
    count = cleanup_expired_sessions() + cleanup_old_contact_messages(
        settings.contact_message_retention_days
    )
    count += _cancel_abandoned_card_orders()
    return count


def _cancel_abandoned_card_orders() -> int:
    """Auto-cancel card orders with payment_status in ('pending','failed') older than 24h.

    Restores stock for each cancelled order. Must NOT touch COD or bank_transfer orders.
    """
    from app.services.order_service import VALID_TRANSITIONS

    cancelled = 0
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id FROM orders
            WHERE payment_method = 'card'
              AND payment_status IN ('pending', 'failed')
              AND created_at < datetime('now', '-24 hours')
              AND status NOT IN ('cancelled', 'delivered')
            """
        ).fetchall()

        for row in rows:
            order_id = row["id"]
            order_row = conn.execute(
                "SELECT status FROM orders WHERE id = ?", (order_id,)
            ).fetchone()
            if not order_row:
                continue
            current = order_row["status"]
            if "cancelled" not in VALID_TRANSITIONS.get(current, set()):
                continue
            conn.execute("UPDATE orders SET status = 'cancelled' WHERE id = ?", (order_id,))
            item_rows = conn.execute(
                "SELECT product_id, quantity FROM order_items WHERE order_id = ?",
                (order_id,),
            ).fetchall()
            for item in item_rows:
                conn.execute(
                    "UPDATE products SET stock = stock + ? WHERE id = ?",
                    (item["quantity"], item["product_id"]),
                )
            cancelled += 1
            logger.info("auto_cancelled_abandoned_card_order", order_id=order_id)

    return cancelled


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
            count = cleanup_fn()
            if count:
                logger.info("Cleaned up expired sessions", count=count)
        except Exception:
            logger.exception("Session cleanup failed")


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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: initialize database on startup, run background tasks."""
    settings = get_settings()
    configure_logging(settings.environment)
    init_db(settings.database_path)

    # Ensure static file directories exist
    static_path = Path(settings.static_file_path)
    static_path.mkdir(parents=True, exist_ok=True)
    (static_path / "products").mkdir(exist_ok=True)

    # Background task: clean expired sessions every hour
    task = asyncio.create_task(session_cleanup_loop())
    # Background task: drain the durable email outbox (~15s tick, per worker)
    email_task = asyncio.create_task(email_outbox_loop())
    yield
    for background_task in (task, email_task):
        background_task.cancel()
        try:
            await asyncio.wait_for(background_task, timeout=5.0)
        except (TimeoutError, asyncio.CancelledError):
            pass


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

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
    application.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
    application.include_router(admin.router, prefix="/v1/admin", tags=["admin"])
    application.include_router(taxonomy.public_router, prefix="/v1/taxonomy", tags=["taxonomy"])
    application.include_router(taxonomy.admin_router, prefix="/v1/admin/taxonomy", tags=["admin"])
    application.include_router(faq.public_router, prefix="/v1/faq", tags=["faq"])
    application.include_router(faq.admin_router, prefix="/v1/admin/faq", tags=["admin-faq"])
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
