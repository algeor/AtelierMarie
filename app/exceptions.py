"""Global exception handlers for consistent error responses.

All API errors return the same envelope:
    {"error": {"code": "<CODE>", "message": "<human-readable>", "details": {...} | null}}
"""

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.services.cart_service import (
    CartFullError,
    CartItemNotFoundError,
    InsufficientStockError,
    ProductNotFoundError,
    QuantityLimitError,
)

logger = structlog.get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the app instance."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Turn Pydantic/FastAPI validation errors into our standard format."""
        # Extract the first error for a human-readable message
        errors = exc.errors()

        # Sanitize errors for JSON serialization — Pydantic includes non-serializable
        # objects (ValueError instances) in the 'ctx' field
        sanitized_errors = []
        for err in errors:
            # Ensure input is JSON-serializable (bytes from form data isn't)
            raw_input = err.get("input")
            if isinstance(raw_input, bytes):
                raw_input = raw_input.decode("utf-8", errors="replace")
            elif not isinstance(raw_input, str | int | float | bool | list | dict | type(None)):
                raw_input = str(raw_input)

            sanitized = {
                "type": err.get("type"),
                "loc": err.get("loc"),
                "msg": err.get("msg"),
                "input": raw_input,
            }
            sanitized_errors.append(sanitized)

        if sanitized_errors:
            first = sanitized_errors[0]
            location = " → ".join(str(loc) for loc in first.get("loc", []))
            message = f"Validation error at {location}: {first.get('msg', 'invalid input')}"
        else:
            message = "Request validation failed"

        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": message,
                    "details": {"errors": sanitized_errors},
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """Wrap Starlette/FastAPI HTTPExceptions in our standard envelope."""
        # Map common status codes to error codes
        code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            409: "CONFLICT",
            413: "PAYLOAD_TOO_LARGE",
            422: "VALIDATION_ERROR",
            429: "RATE_LIMITED",
            500: "INTERNAL_ERROR",
            501: "NOT_IMPLEMENTED",
            503: "SERVICE_UNAVAILABLE",
        }

        error_code = code_map.get(exc.status_code, "ERROR")
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": error_code,
                    "message": detail,
                    "details": None,
                }
            },
        )

    # --- Cart service exception handlers ---

    @app.exception_handler(ProductNotFoundError)
    async def product_not_found_handler(
        request: Request, exc: ProductNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "PRODUCT_NOT_FOUND", "message": str(exc), "details": None}},
        )

    @app.exception_handler(CartItemNotFoundError)
    async def cart_item_not_found_handler(
        request: Request, exc: CartItemNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={
                "error": {"code": "CART_ITEM_NOT_FOUND", "message": str(exc), "details": None}
            },
        )

    @app.exception_handler(InsufficientStockError)
    async def insufficient_stock_handler(
        request: Request, exc: InsufficientStockError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "INSUFFICIENT_STOCK",
                    "message": str(exc),
                    "details": {
                        "product_id": exc.product_id,
                        "requested": exc.requested,
                        "available": exc.available,
                    },
                }
            },
        )

    @app.exception_handler(QuantityLimitError)
    async def quantity_limit_handler(request: Request, exc: QuantityLimitError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "QUANTITY_LIMIT_EXCEEDED",
                    "message": str(exc),
                    "details": {"max_quantity": exc.max_quantity},
                }
            },
        )

    @app.exception_handler(CartFullError)
    async def cart_full_handler(request: Request, exc: CartFullError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "CART_FULL",
                    "message": str(exc),
                    "details": {"max_items": exc.max_items},
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Catch-all for unhandled exceptions. Log the error, return a generic 500."""
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)

        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "details": None,
                }
            },
        )
