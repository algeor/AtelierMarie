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
from app.database import cleanup_expired_sessions, init_db
from app.exceptions import register_exception_handlers
from app.logging_config import configure_logging
from app.middleware.request_id import RequestIdMiddleware
from app.middleware.session import SessionMiddleware
from app.routes import admin, auth, cart, comments, locale, orders, products, reactions

logger = structlog.get_logger(__name__)
SESSION_CLEANUP_INTERVAL_SECONDS = 3600


async def session_cleanup_loop(
    *,
    interval_seconds: float = SESSION_CLEANUP_INTERVAL_SECONDS,
    sleep: Callable[[float], Awaitable[object]] | None = None,
    cleanup: Callable[[], int] | None = None,
) -> None:
    """Periodically remove expired sessions until cancelled."""
    sleep_fn = sleep or asyncio.sleep
    cleanup_fn = cleanup or cleanup_expired_sessions

    while True:
        await sleep_fn(interval_seconds)
        try:
            count = cleanup_fn()
            if count:
                logger.info("Cleaned up expired sessions", count=count)
        except Exception:
            logger.exception("Session cleanup failed")


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
    yield
    task.cancel()
    try:
        await asyncio.wait_for(task, timeout=5.0)
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
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
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
    application.include_router(reactions.router, prefix="/v1/products", tags=["reactions"])
    application.include_router(comments.router, prefix="/v1/products", tags=["comments"])
    application.include_router(locale.router, prefix="/v1/locale", tags=["locale"])

    # Global exception handlers for consistent error format
    register_exception_handlers(application)

    return application


app = create_app()
