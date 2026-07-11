"""Session dependency — ensures a valid session is available."""

from fastapi import HTTPException, Request


def require_session(request: Request) -> str:
    """Return the session_id from request state, or raise 503 if unavailable.

    The session middleware sets request.state.session_id on every request.
    If it's None (DB error or skip-path), the request cannot proceed with
    session-dependent operations.
    """
    session_id = getattr(request.state, "session_id", None)
    if session_id is None:
        raise HTTPException(status_code=503, detail="Service unavailable")
    return session_id
