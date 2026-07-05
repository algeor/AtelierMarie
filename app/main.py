"""FastAPI application factory and lifespan management."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db
from app.middleware.session import SessionMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: initialize database on startup."""
    init_db(settings.database_path)
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="Atelier Marie",
        description="Luxury candle e-commerce API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Middleware
    application.add_middleware(SessionMiddleware)

    # Health endpoint
    @application.get("/v1/health")
    async def health() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    return application


app = create_app()
