"""Global exception handlers for consistent error responses.

All API errors return the same envelope:
    {"error": {"code": "<CODE>", "message": "<human-readable>", "details": {...} | null}}
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


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
            sanitized = {
                "type": err.get("type"),
                "loc": err.get("loc"),
                "msg": err.get("msg"),
                "input": err.get("input"),
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
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
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

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
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
