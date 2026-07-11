"""Authentication dependencies for route handlers."""

import hmac

from fastapi import HTTPException, Request

from app.config import get_settings
from app.database import get_db
from app.services import auth_service


async def require_admin(request: Request) -> None:
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
    if jwt_token:
        claims = auth_service.verify_jwt(jwt_token)
        if claims:
            # JWT is valid — check actual admin status in DB (not just claim)
            with get_db() as conn:
                row = conn.execute(
                    "SELECT is_admin FROM users WHERE id = ?", (claims["user_id"],)
                ).fetchone()
                if row and row["is_admin"]:
                    return  # Authorized via JWT
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
