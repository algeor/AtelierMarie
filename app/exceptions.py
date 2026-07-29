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
from app.services.order_service import (
    InvalidStateTransitionError,
    OrderNotFoundError,
    TrackingRequiredError,
)
from app.services.product_video_service import ProductVideoProcessingConflictError
from app.services.video_service import (
    FfmpegUnavailableError,
    InvalidVideoTypeError,
    VideoTooLongError,
)
from app.services.video_service import (
    FileTooLargeError as VideoFileTooLargeError,
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

        # Log the failing fields so a 422 is diagnosable from the server console
        # (e.g. an office-mode /calculate arriving with an empty city). The raw
        # inputs are user-supplied request data, already sanitized above.
        logger.warning(
            "request_validation_failed",
            method=request.method,
            path=request.url.path,
            fields=[
                {"loc": e.get("loc"), "msg": e.get("msg")} for e in sanitized_errors
            ],
        )

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
        """Wrap Starlette/FastAPI HTTPExceptions in our standard envelope.

        Dict-detail passthrough: if `detail` is a dict containing both `code` and
        `message`, use them directly and put any remaining keys into `details`.
        Otherwise fall back to a status-derived code with the raw detail in
        `message` (or `details` for non-string dicts).
        """
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

        default_code = code_map.get(exc.status_code, "ERROR")

        if isinstance(exc.detail, dict) and "code" in exc.detail and "message" in exc.detail:
            extra = {k: v for k, v in exc.detail.items() if k not in ("code", "message")}
            envelope = {
                "code": exc.detail["code"],
                "message": exc.detail["message"],
                "details": extra or None,
            }
        elif isinstance(exc.detail, dict):
            envelope = {
                "code": default_code,
                "message": code_map.get(exc.status_code, "Error"),
                "details": exc.detail,
            }
        else:
            envelope = {
                "code": default_code,
                "message": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
                "details": None,
            }

        return JSONResponse(status_code=exc.status_code, content={"error": envelope})

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

    # --- Order service exception handlers ---

    @app.exception_handler(OrderNotFoundError)
    async def order_not_found_handler(request: Request, exc: OrderNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "ORDER_NOT_FOUND",
                    "message": str(exc),
                    "details": {"order_id": exc.order_id},
                }
            },
        )

    @app.exception_handler(InvalidStateTransitionError)
    async def invalid_state_transition_handler(
        request: Request, exc: InvalidStateTransitionError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "INVALID_TRANSITION",
                    "message": str(exc),
                    "details": {
                        "order_id": exc.order_id,
                        "current_status": exc.current_status,
                        "requested_status": exc.requested_status,
                    },
                }
            },
        )

    @app.exception_handler(TrackingRequiredError)
    async def tracking_required_handler(
        request: Request, exc: TrackingRequiredError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "TRACKING_REQUIRED",
                    "message": str(exc),
                    "details": {"missing": exc.missing},
                }
            },
        )

    # --- Product video exception handlers ---

    @app.exception_handler(ProductVideoProcessingConflictError)
    async def product_video_conflict_handler(
        request: Request, exc: ProductVideoProcessingConflictError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={"error": {"code": "VIDEO_PROCESSING", "message": str(exc), "details": None}},
        )

    @app.exception_handler(VideoFileTooLargeError)
    async def video_file_too_large_handler(
        request: Request, exc: VideoFileTooLargeError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "VIDEO_TOO_LARGE", "message": str(exc), "details": None}},
        )

    @app.exception_handler(VideoTooLongError)
    async def video_too_long_handler(request: Request, exc: VideoTooLongError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "VIDEO_TOO_LONG", "message": str(exc), "details": None}},
        )

    @app.exception_handler(InvalidVideoTypeError)
    async def invalid_video_type_handler(
        request: Request, exc: InvalidVideoTypeError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "INVALID_VIDEO", "message": str(exc), "details": None}},
        )

    @app.exception_handler(FfmpegUnavailableError)
    async def ffmpeg_unavailable_handler(
        request: Request, exc: FfmpegUnavailableError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"error": {"code": "VIDEO_UNAVAILABLE", "message": str(exc), "details": None}},
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
