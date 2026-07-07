"""Admin authentication dependency."""

import hmac

from fastapi import HTTPException, Request

from app.config import get_settings


async def require_admin(request: Request) -> None:
    """Verify the request has valid admin credentials.

    Checks Bearer API key against the configured admin_api_key.
    JWT path deferred to Day 5 (auth implementation).

    Raises 401 if:
    - No Authorization header present
    - Token format invalid
    - API key does not match
    - admin_api_key is not configured (empty string never matches)
    """
    settings = get_settings()

    # If admin_api_key is not configured, deny all access
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
