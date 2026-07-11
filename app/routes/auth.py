"""Auth endpoints — Google OAuth login, callback, profile, logout."""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.config import get_settings
from app.database import get_db
from app.dependencies.session import require_session
from app.services import auth_service

logger = logging.getLogger(__name__)

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
) -> RedirectResponse:
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
        return RedirectResponse(
            f"{frontend_base}/auth/callback?error=invalid_state", status_code=302
        )

    except auth_service.TokenExchangeError:
        logger.error("OAuth callback: token exchange failed for session %s", session_id[:8])
        return RedirectResponse(
            f"{frontend_base}/auth/callback?error=token_exchange_failed", status_code=302
        )

    except auth_service.EmailNotVerifiedError:
        return RedirectResponse(
            f"{frontend_base}/auth/callback?error=email_not_verified", status_code=302
        )

    except auth_service.AuthServiceUnavailableError:
        logger.error("OAuth callback: auth service unavailable (JWKS fetch failed)")
        return RedirectResponse(
            f"{frontend_base}/auth/callback?error=service_unavailable", status_code=302
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
) -> JSONResponse:
    """Get the current authenticated user's profile.

    Reads the JWT cookie, validates it, and confirms the session still
    belongs to that user in the database.
    """
    settings = get_settings()
    jwt_token = request.cookies.get(settings.jwt_cookie_name)

    if not jwt_token:
        return JSONResponse(
            status_code=401,
            content={
                "error": {
                    "code": "NOT_AUTHENTICATED",
                    "message": "Not authenticated",
                    "details": None,
                }
            },
        )

    claims = auth_service.verify_jwt(jwt_token)
    if not claims:
        return JSONResponse(
            status_code=401,
            content={
                "error": {
                    "code": "NOT_AUTHENTICATED",
                    "message": "Invalid or expired token",
                    "details": None,
                }
            },
        )

    # Verify session still linked to user in DB
    with get_db() as conn:
        row = conn.execute(
            "SELECT user_id FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()

        if not row or row["user_id"] != claims["user_id"]:
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": "NOT_AUTHENTICATED",
                        "message": "Session not linked to user",
                        "details": None,
                    }
                },
            )

        user = auth_service.get_user_from_session(conn, session_id)

    if not user:
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

    return JSONResponse(status_code=200, content=user.model_dump())


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

    # Check if session is linked to a user (i.e., authenticated)
    with get_db() as conn:
        row = conn.execute(
            "SELECT user_id FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        has_user = row and row["user_id"] is not None

        if has_user:
            # Unlink user from session and create a fresh session
            conn.execute("UPDATE sessions SET user_id = NULL WHERE id = ?", (session_id,))

            # Create new empty session (cart not migrated — intentional)
            new_session_id = str(uuid.uuid4())
            now = datetime.now(UTC)
            expires_at = now + timedelta(seconds=settings.session_max_age)
            conn.execute(
                "INSERT INTO sessions (id, created_at, expires_at) VALUES (?, ?, ?)",
                (new_session_id, now.strftime(_SQLITE_DT_FMT), expires_at.strftime(_SQLITE_DT_FMT)),
            )
        else:
            new_session_id = session_id  # Already anonymous — keep it

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
    if has_user:
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
