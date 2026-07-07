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
        description="Luxury candle e-commerce API",
        version="0.1.0",
        lifespan=lifespan,
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

    # Health endpoint
    @application.get("/v1/health")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    # Routers
    application.include_router(products.router, prefix="/v1/products", tags=["products"])
    application.include_router(cart.router, prefix="/v1/cart", tags=["cart"])
    application.include_router(orders.router, prefix="/v1/orders", tags=["orders"])
    application.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
    application.include_router(admin.router, prefix="/v1/admin", tags=["admin"])

    return application


app = create_app()
