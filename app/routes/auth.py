"""Auth endpoints — Google OAuth login, callback, profile, logout."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response

from app.config import get_settings
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.session import require_session
from app.models.users import UserResponse
from app.services import auth_service

logger = structlog.get_logger(__name__)

router = APIRouter()

_SQLITE_DT_FMT = "%Y-%m-%d %H:%M:%S"


@router.get("/login")
async def login(
    request: Request,
    session_id: Annotated[str, Depends(require_session)],
    redirect_to: str = Query(default="/"),
) -> RedirectResponse:
    """Initiate Google OAuth login flow.

    Builds a signed state JWT (PKCE + session binding) and redirects
    the user to Google's authorization endpoint.
    """
    settings = get_settings()

    if not settings.google_client_id or not settings.google_redirect_uri:
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "AUTH_NOT_CONFIGURED",
                    "message": "Google OAuth is not configured",
                    "details": None,
                }
            },
        )

    validated_path = auth_service.validate_redirect_path(redirect_to)
    auth_url = auth_service.build_google_auth_url(session_id, return_to=validated_path)
    return RedirectResponse(url=auth_url, status_code=302)


@router.get("/callback")
async def callback(
    request: Request,
    session_id: Annotated[str, Depends(require_session)],
    code: str = Query(...),
    state: str = Query(...),
) -> Response:
    """Handle Google OAuth callback.

    Validates state, exchanges code for tokens, verifies the ID token,
    upserts the user, links the session, and redirects to the frontend.
    """
    settings = get_settings()
    frontend_base = settings.frontend_url

    try:
        # Validate state (CSRF + session binding)
        state_claims = auth_service.validate_state(state, session_id)
        code_verifier = state_claims["code_verifier"]
        return_to = auth_service.validate_redirect_path(state_claims.get("return_to"))

        # Exchange code for tokens
        id_token = await auth_service.exchange_code_for_tokens(code, code_verifier)

        # Verify Google ID token (signature, aud, iss, email_verified)
        google_claims = await auth_service.verify_google_id_token(id_token)

        # Upsert user + link session
        with get_db() as conn:
            user = auth_service.upsert_user(
                conn,
                google_claims["sub"],
                google_claims["email"],
                google_claims.get("name"),
                google_claims.get("picture"),
            )
            # Link session to user
            conn.execute(
                "UPDATE sessions SET user_id = ? WHERE id = ?",
                (user.id, session_id),
            )
            # Backfill anonymous orders to this user
            conn.execute(
                "UPDATE orders SET user_id = ? WHERE session_id = ? AND user_id IS NULL",
                (user.id, session_id),
            )

        # Create JWT for cookie
        jwt_token = auth_service.create_jwt(user, session_id)

        # Redirect to frontend callback handler
        redirect_url = f"{frontend_base}/auth/callback?success=true&redirect_to={return_to}"
        response = RedirectResponse(url=redirect_url, status_code=302)

        # Set JWT as HttpOnly cookie
        response.set_cookie(
            key=settings.jwt_cookie_name,
            value=jwt_token,
            max_age=settings.jwt_expiry_hours * 3600,
            httponly=True,
            secure=settings.session_cookie_secure and settings.environment != "development",
            samesite="lax",
            path="/",
        )
        return response

    except auth_service.InvalidStateError:
        logger.warning("OAuth callback: invalid state from session %s", session_id[:8])
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "invalid_state", "message": "Invalid OAuth state"}},
        )

    except auth_service.TokenExchangeError:
        logger.error("OAuth callback: token exchange failed for session %s", session_id[:8])
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "token_exchange_failed",
                    "message": "Token exchange failed",
                }
            },
        )

    except auth_service.EmailNotVerifiedError:
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "email_not_verified", "message": "Email is not verified"}},
        )

    except auth_service.AuthServiceUnavailableError:
        logger.error("OAuth callback: auth service unavailable (JWKS fetch failed)")
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "authentication_service_unavailable",
                    "message": "Authentication service unavailable",
                }
            },
        )

    except Exception:
        logger.exception("OAuth callback: unexpected error")
        return RedirectResponse(
            f"{frontend_base}/auth/callback?error=internal_error", status_code=302
        )


@router.get("/me")
async def get_me(
    request: Request,
    session_id: Annotated[str, Depends(require_session)],
    current_user: Annotated[UserResponse | None, Depends(get_current_user)],
) -> JSONResponse:
    """Get the current authenticated user's profile.

    Reads the JWT cookie, validates it, and confirms the session still
    belongs to that user in the database.
    """
    if current_user is None:
        return JSONResponse(
            status_code=401,
            content={
                "error": {
                    "code": "NOT_AUTHENTICATED",
                    "message": "User not found",
                    "details": None,
                }
            },
        )

    return JSONResponse(status_code=200, content=current_user.model_dump())


@router.post("/logout")
async def logout(
    request: Request,
    session_id: Annotated[str, Depends(require_session)],
) -> JSONResponse:
    """Log out the current user.

    Unlinks the session from the user, creates a fresh anonymous session,
    and clears the JWT cookie. Cart items stay with the old session
    (intentionally not transferred on logout).
    """
    settings = get_settings()

    session_is_new = bool(getattr(request.state, "session_is_new", False))
    preferred_locale = getattr(request.state, "preferred_locale", "en")

    # Middleware-created sessions have no meaningful prior identity to rotate.
    if session_is_new:
        has_existing_session = False
        new_session_id = session_id
    else:
        has_existing_session = True

    with get_db() as conn:
        if not session_is_new:
            row = conn.execute(
                "SELECT user_id, preferred_locale FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            has_existing_session = row is not None
            if row and row["preferred_locale"]:
                preferred_locale = row["preferred_locale"]

        if has_existing_session and not session_is_new:
            # Unlink user from the old session and create a fresh session.
            conn.execute("UPDATE sessions SET user_id = NULL WHERE id = ?", (session_id,))

            new_session_id = str(uuid.uuid4())
            now = datetime.now(UTC)
            expires_at = now + timedelta(seconds=settings.session_max_age)
            conn.execute(
                "INSERT INTO sessions (id, created_at, expires_at, preferred_locale) "
                "VALUES (?, ?, ?, ?)",
                (
                    new_session_id,
                    now.strftime(_SQLITE_DT_FMT),
                    expires_at.strftime(_SQLITE_DT_FMT),
                    preferred_locale,
                ),
            )

    response = JSONResponse(status_code=200, content={"message": "Logged out"})

    # Clear JWT cookie
    response.delete_cookie(
        key=settings.jwt_cookie_name,
        httponly=True,
        secure=settings.session_cookie_secure and settings.environment != "development",
        samesite="lax",
        path="/",
    )

    # Set new session cookie if rotated
    if has_existing_session and not session_is_new:
        response.set_cookie(
            key=settings.session_cookie_name,
            value=new_session_id,
            max_age=settings.session_max_age,
            httponly=True,
            secure=settings.session_cookie_secure and settings.environment != "development",
            samesite="lax",
        )
        response.headers["X-Session-Rotated"] = "true"

    return response
