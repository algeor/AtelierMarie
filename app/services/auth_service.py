"""Auth service — Google OAuth, JWT management, user operations.

All business logic for authentication. No HTTP concerns.
Functions accept explicit parameters (conn, settings, etc.).
"""

import hashlib
import logging
import secrets
import sqlite3
import threading
import time
import uuid
from base64 import urlsafe_b64encode
from datetime import UTC, datetime
from urllib.parse import urlencode

import httpx
import jwt
from jwt.algorithms import RSAAlgorithm

from app.config import get_settings
from app.models.users import UserResponse
from app.utils.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)

# --- Constants ---
_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_JWKS_TTL_SECONDS = 6 * 60 * 60  # 6 hours
_STATE_EXPIRY_SECONDS = 600  # 10 minutes
_HTTP_TIMEOUT = httpx.Timeout(10.0)
_SQLITE_DT_FMT = "%Y-%m-%d %H:%M:%S"


# --- Exceptions ---


class AuthServiceError(Exception):
    """Base for all auth service errors."""


class InvalidStateError(AuthServiceError):
    """OAuth state token failed validation."""


class TokenExchangeError(AuthServiceError):
    """Google token exchange failed."""


class IdTokenVerificationError(AuthServiceError):
    """Google ID token failed verification."""


class EmailNotVerifiedError(AuthServiceError):
    """Google account email not verified."""


class AuthServiceUnavailableError(AuthServiceError):
    """External auth dependency unavailable (e.g., JWKS fetch)."""


# --- JWKS Cache ---


class _JwksCache:
    """Thread-safe in-memory cache for Google's public keys (RS256).

    Uses a threading.Lock to serialize concurrent refreshes — only one
    thread fetches while others wait and reuse the result.
    """

    def __init__(self) -> None:
        self._keys: dict[str, dict] = {}  # kid -> JWK dict
        self._fetched_at: float = 0.0
        self._lock = threading.Lock()

    @property
    def is_expired(self) -> bool:
        return (time.time() - self._fetched_at) > _JWKS_TTL_SECONDS

    @property
    def is_empty(self) -> bool:
        return not self._keys

    def get_key(self, kid: str) -> dict | None:
        with self._lock:
            return self._keys.get(kid)

    def update(self, jwks_response: dict) -> None:
        with self._lock:
            self._keys = {k["kid"]: k for k in jwks_response.get("keys", [])}
            self._fetched_at = time.time()

    def needs_refresh(self, kid: str) -> bool:
        """Check if a refresh is needed (expired or key not found)."""
        with self._lock:
            return self.is_expired or kid not in self._keys


_jwks_cache = _JwksCache()

# --- Circuit Breaker for Google OAuth ---

_google_oauth_breaker = CircuitBreaker(
    name="google_oauth",
    failure_threshold=3,
    failure_window=30.0,
    recovery_timeout=60.0,
)


# --- Public Functions ---


def build_google_auth_url(session_id: str, return_to: str | None = None) -> str:
    """Build the Google OAuth authorization URL with PKCE and signed state.

    The state JWT contains the code_verifier (tamper-proof since signed),
    eliminating the need for server-side storage.

    Returns:
        The full Google OAuth URL to redirect the user to.
    """
    settings = get_settings()

    # PKCE: generate code_verifier and code_challenge
    code_verifier = secrets.token_urlsafe(32)  # 43 chars
    code_challenge = (
        urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).rstrip(b"=").decode()
    )

    # Build state JWT (contains session binding + PKCE verifier)
    now = time.time()
    state_payload = {
        "type": "oauth_state",
        "session_id": session_id,
        "nonce": secrets.token_hex(16),
        "code_verifier": code_verifier,
        "return_to": validate_redirect_path(return_to),
        "iat": int(now),
        "exp": int(now + _STATE_EXPIRY_SECONDS),
    }
    state_token = jwt.encode(state_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    # Construct Google OAuth URL
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state_token,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "access_type": "online",
        "prompt": "consent",
    }
    return f"{_GOOGLE_AUTH_URL}?{urlencode(params)}"


def validate_state(state_token: str, session_id: str) -> dict:
    """Decode and validate the OAuth state JWT.

    Checks:
        - Signature and expiry
        - Token type is "oauth_state"
        - Session ID matches the current request

    Returns:
        Decoded payload containing code_verifier and return_to.

    Raises:
        InvalidStateError: On any validation failure.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            state_token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "iat"]},
        )
    except jwt.PyJWTError as e:
        raise InvalidStateError(f"State token decode failed: {e}") from e

    if payload.get("type") != "oauth_state":
        raise InvalidStateError("Invalid state token type")

    if payload.get("session_id") != session_id:
        raise InvalidStateError("Session ID mismatch in state token")

    return payload


async def exchange_code_for_tokens(code: str, code_verifier: str) -> str:
    """Exchange the authorization code for tokens at Google's token endpoint.

    Args:
        code: The authorization code from Google's callback.
        code_verifier: The PKCE code verifier from the state JWT.

    Returns:
        The raw id_token string from Google's response.

    Raises:
        TokenExchangeError: On HTTP error or missing id_token.
        AuthServiceUnavailableError: If circuit breaker is open.
    """
    if not _google_oauth_breaker.allow_request():
        raise AuthServiceUnavailableError(
            "Google OAuth circuit breaker is open — service temporarily unavailable"
        )

    settings = get_settings()
    data = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": settings.google_redirect_uri,
        "grant_type": "authorization_code",
        "code_verifier": code_verifier,
    }

    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            response = await client.post(_GOOGLE_TOKEN_URL, data=data)
            # B.13: HTTP 4xx does NOT count toward failure threshold
            if response.status_code >= 500:
                _google_oauth_breaker.record_failure()
                raise httpx.HTTPStatusError(
                    f"Server error: {response.status_code}",
                    request=response.request,
                    response=response,
                )
            response.raise_for_status()
    except httpx.TimeoutException as e:
        _google_oauth_breaker.record_failure()
        logger.error("Google token exchange timed out: %s", e)
        raise TokenExchangeError(f"Token exchange request timed out: {e}") from e
    except httpx.HTTPStatusError as e:
        logger.error("Google token exchange failed: %s", e)
        raise TokenExchangeError(f"Token exchange request failed: {e}") from e
    except httpx.HTTPError as e:
        # Network-level errors (connection refused, DNS, etc.)
        _google_oauth_breaker.record_failure()
        logger.error("Google token exchange failed: %s", e)
        raise TokenExchangeError(f"Token exchange request failed: {e}") from e

    _google_oauth_breaker.record_success()
    body = response.json()
    id_token = body.get("id_token")
    if not id_token:
        raise TokenExchangeError("No id_token in Google response")

    return id_token


async def verify_google_id_token(id_token: str) -> dict:
    """Verify a Google ID token using JWKS-cached RS256 keys.

    Validates signature, issuer, audience, and email_verified claim.

    Returns:
        Dict with keys: sub, email, name (optional), picture (optional).

    Raises:
        IdTokenVerificationError: On signature or claim validation failure.
        EmailNotVerifiedError: If the Google account email is not verified.
        AuthServiceUnavailableError: If JWKS cannot be fetched.
    """
    settings = get_settings()

    # Decode header to get key ID (kid)
    try:
        unverified_header = jwt.get_unverified_header(id_token)
    except jwt.PyJWTError as e:
        raise IdTokenVerificationError(f"Cannot decode token header: {e}") from e

    kid = unverified_header.get("kid")
    if not kid:
        raise IdTokenVerificationError("No kid in token header")

    # Get signing key from cache (refresh if needed)
    if _jwks_cache.needs_refresh(kid):
        await _fetch_jwks()

    jwk_data = _jwks_cache.get_key(kid)
    if jwk_data is None:
        raise IdTokenVerificationError(f"No matching key for kid={kid}")

    # Convert JWK to public key and verify
    try:
        public_key = RSAAlgorithm.from_jwk(jwk_data)
        claims = jwt.decode(
            id_token,
            public_key,
            algorithms=["RS256"],
            audience=settings.google_client_id,
            issuer=["accounts.google.com", "https://accounts.google.com"],
        )
    except jwt.PyJWTError as e:
        raise IdTokenVerificationError(f"ID token verification failed: {e}") from e

    # Require verified email
    if not claims.get("email_verified"):
        raise EmailNotVerifiedError("Google account email is not verified")

    return {
        "sub": claims["sub"],
        "email": claims["email"],
        "name": claims.get("name"),
        "picture": claims.get("picture"),
    }


def upsert_user(
    conn: sqlite3.Connection,
    google_id: str,
    email: str,
    name: str | None,
    avatar_url: str | None,
) -> UserResponse:
    """Create or update a user from Google OAuth claims.

    First user to register is auto-promoted to admin (first-user-is-admin rule).
    Uses BEGIN IMMEDIATE for atomic first-user check.

    Returns:
        UserResponse with user data.
    """
    now = datetime.now(UTC).strftime(_SQLITE_DT_FMT)

    # Check if user already exists
    existing = conn.execute(
        "SELECT id, email, name, avatar_url, is_admin FROM users WHERE google_id = ?",
        (google_id,),
    ).fetchone()

    if existing:
        # Update returning user's profile and last_login_at
        conn.execute(
            "UPDATE users SET name = ?, avatar_url = ?, last_login_at = ? WHERE google_id = ?",
            (name, avatar_url, now, google_id),
        )
        return UserResponse(
            id=existing["id"],
            email=existing["email"],
            name=name or existing["name"],
            avatar_url=avatar_url or existing["avatar_url"],
            is_admin=bool(existing["is_admin"]),
        )

    # New user — atomic first-user-is-admin check
    conn.execute("BEGIN IMMEDIATE")
    try:
        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        is_admin = 1 if user_count == 0 else 0

        user_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO users (id, google_id, email, name, avatar_url, is_admin, last_login_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, google_id, email, name, avatar_url, is_admin, now),
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    return UserResponse(
        id=user_id,
        email=email,
        name=name,
        avatar_url=avatar_url,
        is_admin=bool(is_admin),
    )


def create_jwt(user: UserResponse, session_id: str) -> str:
    """Create a JWT token for the authenticated user.

    The JWT is stored in an HttpOnly cookie and used for subsequent requests.
    Contains user_id, email, is_admin, and session_id for validation.
    """
    settings = get_settings()
    now = time.time()
    payload = {
        "user_id": user.id,
        "email": user.email,
        "is_admin": user.is_admin,
        "session_id": session_id,
        "iss": "atelier-marie",
        "aud": "atelier-marie-web",
        "iat": int(now),
        "exp": int(now + settings.jwt_expiry_hours * 3600),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_jwt(token: str) -> dict | None:
    """Verify and decode a JWT token.

    Returns:
        Decoded claims dict on success, None on any failure.
    """
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            issuer="atelier-marie",
            audience="atelier-marie-web",
            options={"require": ["exp", "iat"]},
        )
    except jwt.PyJWTError:
        return None


def get_user_from_session(conn: sqlite3.Connection, session_id: str) -> UserResponse | None:
    """Look up the authenticated user for a session.

    Returns:
        UserResponse if the session is linked to a user, None otherwise.
    """
    row = conn.execute(
        "SELECT u.id, u.email, u.name, u.avatar_url, u.is_admin "
        "FROM sessions s JOIN users u ON s.user_id = u.id "
        "WHERE s.id = ?",
        (session_id,),
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


def validate_redirect_path(path: str | None) -> str:
    """Validate a redirect path to prevent open redirect attacks.

    Rules:
        - Must start with /
        - Must NOT start with // (protocol-relative URL)

    Returns:
        The validated path, or "/" if invalid.
    """
    if not path:
        return "/"
    if path.startswith("/") and not path.startswith("//"):
        return path
    return "/"


# --- Private Helpers ---


async def _fetch_jwks() -> None:
    """Fetch Google's JWKS (public keys) and update the cache.

    Falls back to stale cache if fetch fails and cache is not empty.
    Raises AuthServiceUnavailableError if fetch fails AND cache is empty.
    Integrates with circuit breaker — 5xx and timeouts count as failures,
    4xx does NOT.
    """
    if not _google_oauth_breaker.allow_request():
        if _jwks_cache.is_empty:
            raise AuthServiceUnavailableError(
                "Google OAuth circuit breaker is open and no cached JWKS available"
            )
        logger.warning("JWKS fetch skipped — circuit breaker open, using stale cache")
        return

    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            response = await client.get(_GOOGLE_JWKS_URL)
            # B.13: 4xx does not count toward failure threshold
            if response.status_code >= 500:
                _google_oauth_breaker.record_failure()
                raise httpx.HTTPStatusError(
                    f"Server error: {response.status_code}",
                    request=response.request,
                    response=response,
                )
            response.raise_for_status()
        _google_oauth_breaker.record_success()
        _jwks_cache.update(response.json())
    except httpx.TimeoutException as e:
        _google_oauth_breaker.record_failure()
        if _jwks_cache.is_empty:
            raise AuthServiceUnavailableError(
                f"Cannot fetch Google JWKS (timeout) and no cached keys available: {e}"
            ) from e
        logger.warning("JWKS fetch timed out, using stale cache: %s", e)
    except httpx.HTTPStatusError as e:
        # Already recorded failure for 5xx above; 4xx falls through here without recording
        if _jwks_cache.is_empty:
            raise AuthServiceUnavailableError(
                f"Cannot fetch Google JWKS and no cached keys available: {e}"
            ) from e
        logger.warning("JWKS fetch failed, using stale cache: %s", e)
    except httpx.HTTPError as e:
        # Network-level errors count as failures
        _google_oauth_breaker.record_failure()
        if _jwks_cache.is_empty:
            raise AuthServiceUnavailableError(
                f"Cannot fetch Google JWKS and no cached keys available: {e}"
            ) from e
        logger.warning("JWKS fetch failed, using stale cache: %s", e)


def get_oauth_circuit_breaker() -> CircuitBreaker:
    """Expose the OAuth circuit breaker for health endpoint access."""
    return _google_oauth_breaker
