"""Session cookie middleware — assigns anonymous identity to every request."""

import uuid
from datetime import datetime, timedelta, timezone

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.config import get_settings
from app.database import get_db


class SessionMiddleware(BaseHTTPMiddleware):
    """Reads or creates a session cookie, sets request.state.session_id."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = get_settings()
        session_id = request.cookies.get(settings.session_cookie_name)
        is_new = session_id is None

        if is_new:
            session_id = str(uuid.uuid4())
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.session_max_age)
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO sessions (id, expires_at) VALUES (?, ?)",
                    (session_id, expires_at.isoformat()),
                )

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
