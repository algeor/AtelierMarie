"""Request-ID middleware — assigns a correlation ID to every request.

The ID is:
- Read from the `X-Request-ID` header if present and valid UUID4
- Otherwise generated as a new UUID4

Stored in a contextvar so structlog (and any code) can access it
without needing the request object.
"""

import re
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Contextvar accessible from anywhere in the request lifecycle
request_id_var: ContextVar[str] = ContextVar("request_id", default="")

_UUID4_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assigns a request ID to every incoming request.

    - Uses X-Request-ID header if valid UUID4
    - Otherwise generates a new UUID4
    - Sets the contextvar for structured logging
    - Returns the ID in the X-Request-ID response header
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Try to use provided header
        header_value = request.headers.get("x-request-id", "")
        if header_value and _UUID4_RE.match(header_value.lower()):
            rid = header_value.lower()
        else:
            rid = str(uuid.uuid4())

        # Set contextvar for structlog and other code
        token = request_id_var.set(rid)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            request_id_var.reset(token)
