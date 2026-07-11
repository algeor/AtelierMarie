"""FastAPI application factory and lifespan management."""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import cleanup_expired_sessions, init_db
from app.exceptions import register_exception_handlers
from app.middleware.session import SessionMiddleware
from app.routes import admin, auth, cart, orders, products

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: initialize database on startup, run background tasks."""
    init_db(get_settings().database_path)

    # Background task: clean expired sessions every hour
    async def _session_cleanup_loop() -> None:
        while True:
            await asyncio.sleep(3600)
            try:
                count = cleanup_expired_sessions()
                if count:
                    logger.info("Cleaned up %d expired sessions", count)
            except Exception:
                logger.exception("Session cleanup failed")

    task = asyncio.create_task(_session_cleanup_loop())
    yield
    task.cancel()


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
    # CORSMiddleware added last (Starlette is LIFO — runs first on incoming requests)
    application.add_middleware(SessionMiddleware)

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
        """Simple liveness probe. Returns 200 with `{\"status\": \"ok\"}` when the service is running."""
        return JSONResponse({"status": "ok"})

    # Legacy versioned health endpoint (kept for backward compatibility)
    @application.get("/v1/health", tags=["health"], summary="Health check (versioned)")
    async def health_v1() -> JSONResponse:
        """Versioned health check — kept for backward compatibility."""
        return JSONResponse({"status": "ok"})

    # Routers
    application.include_router(products.router, prefix="/v1/products", tags=["products"])
    application.include_router(cart.router, prefix="/v1/cart", tags=["cart"])
    application.include_router(orders.router, prefix="/v1/orders", tags=["orders"])
    application.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
    application.include_router(admin.router, prefix="/v1/admin", tags=["admin"])

    # Global exception handlers for consistent error format
    register_exception_handlers(application)

    return application


app = create_app()
