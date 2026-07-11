"""Session cookie middleware — assigns anonymous identity to every request."""

import re
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.config import get_settings
from app.constants import SQLITE_DATETIME_FORMAT
from app.database import get_db

logger = structlog.get_logger(__name__)

# Bug #1 fix: UUID v4 format validation — reject garbage before DB lookup
_UUID4_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")

# Locale detection — look for 'bg' in Accept-Language header
_BG_ACCEPT_LANG_RE = re.compile(r"\bbg\b", re.IGNORECASE)


def _detect_locale_from_accept_language(request: Request) -> str:
    """Detect preferred locale from the Accept-Language header.

    Returns 'bg' if Bulgarian is listed in the header, otherwise 'en'.
    """
    accept_lang = request.headers.get("accept-language", "")
    if _BG_ACCEPT_LANG_RE.search(accept_lang):
        return "bg"
    return "en"


def _format_dt(dt: datetime) -> str:
    """Format a datetime as SQLite-compatible string (UTC, no timezone suffix)."""
    return dt.strftime(SQLITE_DATETIME_FORMAT)


def _parse_dt(s: str) -> datetime:
    """Parse a SQLite datetime string into a timezone-aware UTC datetime."""
    return datetime.strptime(s, SQLITE_DATETIME_FORMAT).replace(tzinfo=UTC)


def _should_skip_path(path: str, skip_paths: list[str]) -> bool:
    """Determine if a request path should skip session processing.

    Matching semantics (from design Decision 8):
    - Exact match for leaf paths (/health, /docs, /openapi.json)
    - Prefix-with-trailing-slash for directory paths (/docs/, /metrics/)
    - /health-records does NOT match /health (exact match only)
    - /docs matches exactly AND /docs/swagger matches /docs/ prefix
    """
    for skip_path in skip_paths:
        # Exact match (handles leaf paths like /health, /openapi.json)
        if path == skip_path:
            return True
        # Prefix match with trailing slash (handles sub-paths like /docs/swagger)
        if path.startswith(skip_path + "/"):
            return True
    return False


class SessionMiddleware(BaseHTTPMiddleware):
    """Reads or creates a session cookie, sets request.state.session_id."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip session creation for CORS pre-flight requests
        if request.method == "OPTIONS":
            return await call_next(request)

        settings = get_settings()

        # Skip session for health/monitoring/docs endpoints (config-driven)
        if _should_skip_path(request.url.path, settings.session_skip_paths):
            request.state.session_id = None
            request.state.preferred_locale = "en"
            return await call_next(request)

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
                        "SELECT expires_at, created_at, preferred_locale"
                        " FROM sessions WHERE id = ?",
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
                        preferred_locale = row["preferred_locale"] or "en"

                        # Bug #13 fix: use strict less-than (spec: "reject if expires_at < now")
                        expired = expires_at < now

                        # Bug #2 fix: enforce 180-day absolute lifetime
                        absolute_limit = created_at + timedelta(
                            seconds=settings.session_absolute_lifetime
                        )
                        past_absolute = absolute_limit < now

                        if expired or past_absolute:
                            # Expired/past-absolute — issue fresh session.
                            # Do NOT delete old row (deferred to cleanup job).
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
                    # Detect locale from browser Accept-Language on new sessions
                    preferred_locale = _detect_locale_from_accept_language(request)
                    # Bug #5 fix: use SQLite-compatible datetime format
                    conn.execute(
                        "INSERT INTO sessions (id, created_at, expires_at, preferred_locale) "
                        "VALUES (?, ?, ?, ?)",
                        (session_id, _format_dt(now), _format_dt(expires_at), preferred_locale),
                    )
        except sqlite3.Error:
            # DB unavailable — return error without exposing internals
            logger.exception("Session middleware DB error")
            return Response(
                content=(
                    '{"error":{"code":"INTERNAL_ERROR",'
                    '"message":"An unexpected error occurred",'
                    '"details":null}}'
                ),
                status_code=500,
                media_type="application/json",
            )

        request.state.session_id = session_id
        request.state.session_is_new = is_new
        request.state.preferred_locale = preferred_locale

        response = await call_next(request)

        # Bug #3 fix: Set-Cookie on EVERY response (spec Decision 2 — prevents timing side-channel)
        response.set_cookie(
            key=settings.session_cookie_name,
            value=session_id,
            max_age=settings.session_max_age,
            httponly=True,
            secure=settings.session_cookie_secure and settings.environment != "development",
            samesite="lax",
        )

        return response


def rotate_session(conn: "sqlite3.Connection", old_session_id: str, user_id: str) -> str:
    """Rotate session ID on login to prevent session fixation.

    IMPORTANT: Caller must pass a connection with NO active transaction.
    This function manages its own BEGIN IMMEDIATE / COMMIT / ROLLBACK.
    Do NOT call this inside a ``with get_db() as conn:`` block — pass a raw
    ``sqlite3.connect()`` connection instead (with row_factory and FK enabled).

    Steps executed atomically:
    1. INSERT new session with user_id
    2. UPDATE cart_items to new session_id
    3. DELETE old session row

    Returns the new session ID.
    """
    settings = get_settings()
    new_session_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=settings.session_max_age)

    conn.execute("BEGIN IMMEDIATE")
    try:
        # Step 1: Insert new session row with user_id
        conn.execute(
            "INSERT INTO sessions (id, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (new_session_id, user_id, _format_dt(now), _format_dt(expires_at)),
        )
        # Step 2: Migrate cart items (UPDATE before DELETE to avoid FK issues)
        conn.execute(
            "UPDATE cart_items SET session_id = ? WHERE session_id = ?",
            (new_session_id, old_session_id),
        )
        # Step 3: Delete old session
        conn.execute("DELETE FROM sessions WHERE id = ?", (old_session_id,))
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    return new_session_id
