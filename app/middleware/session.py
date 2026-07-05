"""Session cookie middleware — assigns anonymous identity to every request."""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings


class SessionMiddleware(BaseHTTPMiddleware):
    """Reads or creates a session cookie, sets request.state.session_id."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        session_id = request.cookies.get(settings.session_cookie_name)
        is_new = session_id is None

        if is_new:
            session_id = str(uuid.uuid4())

        request.state.session_id = session_id

        response = await call_next(request)

        if is_new:
            response.set_cookie(
                key=settings.session_cookie_name,
                value=session_id,
                max_age=settings.session_max_age,
                httponly=True,
                samesite="lax",
            )

        return response
