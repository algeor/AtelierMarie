"""Authentication dependencies for route handlers."""

import hmac
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from app.config import get_settings
from app.database import get_db
from app.dependencies.session import require_session
from app.models.users import UserResponse
from app.services import auth_service


async def get_current_user(
    request: Request,
    session_id: Annotated[str, Depends(require_session)],
) -> UserResponse | None:
    """Return the authenticated user for the current request, if any.

    A JWT is valid only when it belongs to the current session and the session
    row is still linked to the token's user. This makes logout/session rotation
    invalidate previously issued cookies immediately.
    """
    settings = get_settings()
    jwt_token = request.cookies.get(settings.jwt_cookie_name)
    if not jwt_token:
        return None

    claims = auth_service.verify_jwt(jwt_token)
    if not claims:
        return None

    if claims.get("session_id") != session_id:
        return None

    user_id = claims.get("user_id")
    if not user_id:
        return None

    with get_db() as conn:
        row = conn.execute(
            "SELECT u.id, u.email, u.name, u.avatar_url, u.is_admin "
            "FROM sessions s JOIN users u ON s.user_id = u.id "
            "WHERE s.id = ? AND s.user_id = ?",
            (session_id, user_id),
        ).fetchone()

    if not row:
        return None

    return UserResponse(
        id=row["id"],
        email=row["email"],
        name=row["name"],
        avatar_url=row["avatar_url"],
        is_admin=bool(row["is_admin"]),
    )


async def require_auth(
    user: Annotated[UserResponse | None, Depends(get_current_user)],
) -> UserResponse:
    """Require a valid authenticated user."""
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def require_admin(
    request: Request,
    current_user: Annotated[UserResponse | None, Depends(get_current_user)],
) -> UserResponse | None:
    """Verify the request has valid admin credentials.

    Authentication precedence:
    1. Valid JWT cookie with is_admin=true in DB → grant
    2. Valid JWT cookie but not admin in DB → 403 Forbidden
    3. No valid JWT + valid Bearer API key → grant
    4. No valid JWT + no/invalid API key → 401 Unauthorized
    """
    settings = get_settings()

    # Path 1: Try JWT cookie (browser sessions)
    jwt_token = request.cookies.get(settings.jwt_cookie_name)
    if jwt_token and current_user is not None:
        if current_user.is_admin:
            return current_user  # Authorized via JWT
        # JWT valid but not admin → 403 (don't fall through to API key)
        raise HTTPException(status_code=403, detail="Admin access required")

    # Path 2: Try Bearer API key (scripts/automation)
    if not settings.admin_api_key:
        raise HTTPException(
            status_code=401,
            detail="Admin access not configured",
        )

    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing credentials")

    # Expect "Bearer <token>"
    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = parts[1]

    # Reject empty tokens
    if not token:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(token.encode(), settings.admin_api_key.encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return None
