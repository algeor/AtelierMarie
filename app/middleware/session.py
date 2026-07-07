"""Session cookie middleware — assigns anonymous identity to every request."""

import logging
import re
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.config import get_settings
from app.database import get_db

logger = logging.getLogger(__name__)

# Paths that don't need a session (monitoring, health checks, docs)
_SESSION_SKIP_PATHS = frozenset({"/v1/health", "/docs", "/redoc", "/openapi.json", "/metrics"})

# Bug #1 fix: UUID v4 format validation — reject garbage before DB lookup
_UUID4_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")

# SQLite-compatible datetime format (no T separator, no timezone suffix)
_SQLITE_DT_FMT = "%Y-%m-%d %H:%M:%S"


def _format_dt(dt: datetime) -> str:
    """Format a datetime as SQLite-compatible string (UTC, no timezone suffix)."""
    return dt.strftime(_SQLITE_DT_FMT)


def _parse_dt(s: str) -> datetime:
    """Parse a SQLite datetime string into a timezone-aware UTC datetime."""
    return datetime.strptime(s, _SQLITE_DT_FMT).replace(tzinfo=UTC)


class SessionMiddleware(BaseHTTPMiddleware):
    """Reads or creates a session cookie, sets request.state.session_id."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip session creation for CORS pre-flight requests
        if request.method == "OPTIONS":
            return await call_next(request)

        # Skip session for health/monitoring/docs endpoints
        if request.url.path in _SESSION_SKIP_PATHS:
            request.state.session_id = None
            return await call_next(request)

        settings = get_settings()
        session_id = request.cookies.get(settings.session_cookie_name)
        is_new = session_id is None

        # Bug #1 fix: reject non-UUID4 cookies without hitting the DB
        if session_id and not _UUID4_RE.match(session_id):
            session_id = None
            is_new = True

        try:
            # Bug #10 fix: single DB connection for validation + creation
            with get_db() as conn:
                if not is_new:
                    # Bug #2 fix: fetch created_at alongside expires_at for absolute cap
                    row = conn.execute(
                        "SELECT expires_at, created_at FROM sessions WHERE id = ?",
                        (session_id,),
                    ).fetchone()

                    now = datetime.now(UTC)

                    if not row:
                        # Session unknown — issue fresh
                        session_id = None
                        is_new = True
                    else:
                        expires_at = _parse_dt(row["expires_at"])
                        created_at = _parse_dt(row["created_at"])

                        # Bug #13 fix: use strict less-than (spec: "reject if expires_at < now")
                        expired = expires_at < now

                        # Bug #2 fix: enforce 180-day absolute lifetime
                        absolute_limit = created_at + timedelta(
                            seconds=settings.session_absolute_lifetime
                        )
                        past_absolute = absolute_limit < now

                        if expired or past_absolute:
                            # Delete the stale session row
                            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
                            session_id = None
                            is_new = True
                        else:
                            # Bug #4 fix: sliding expiry — only extend when within threshold
                            remaining = expires_at - now
                            if remaining <= timedelta(seconds=settings.session_sliding_threshold):
                                new_expires = now + timedelta(seconds=settings.session_max_age)
                                # Don't extend past absolute lifetime
                                if new_expires > absolute_limit:
                                    new_expires = absolute_limit
                                conn.execute(
                                    "UPDATE sessions SET expires_at = ? WHERE id = ?",
                                    (_format_dt(new_expires), session_id),
                                )

                if is_new:
                    session_id = str(uuid.uuid4())
                    now = datetime.now(UTC)
                    expires_at = now + timedelta(seconds=settings.session_max_age)
                    # Bug #5 fix: use SQLite-compatible datetime format
                    conn.execute(
                        "INSERT INTO sessions (id, created_at, expires_at) VALUES (?, ?, ?)",
                        (session_id, _format_dt(now), _format_dt(expires_at)),
                    )
        except sqlite3.Error:
            # Bug #9 fix: return 503 instead of silently proceeding with None
            logger.exception("Session middleware DB error")
            return Response(
                content='{"detail":"Service temporarily unavailable"}',
                status_code=503,
                media_type="application/json",
            )

        request.state.session_id = session_id

        response = await call_next(request)

        # Bug #3 fix: Set-Cookie on EVERY response (spec Decision 2 — prevents timing side-channel)
        response.set_cookie(
            key=settings.session_cookie_name,
            value=session_id,
            max_age=settings.session_max_age,
            httponly=True,
            secure=settings.environment != "development",
            samesite="lax",
        )

        return response
