## Why

The platform tracks anonymous behavior via sessions and events, but has no concept of *who* is behind a session. Cross-session personalization (recommendations, order history, user profiles) requires authenticated identity. Google OAuth provides free, passwordless authentication that layers optional login on top of the existing anonymous-first architecture — users who never log in lose nothing; users who do gain cross-device personalization and account features.

## What Changes

- Add a `users` table in SQLite (google_id, email, name, avatar_url, is_admin, timestamps)
- Implement Google OAuth 2.0 authorization code flow via direct HTTP calls (no third-party OAuth libraries)
- Add four auth endpoints: `GET /v1/auth/google/login`, `GET /v1/auth/google/callback`, `POST /v1/auth/logout`, `GET /v1/auth/me`
- Issue JWT session tokens (HS256, 7-day lifetime) containing user_id + session_id for lightweight session-validated auth
- Integrate with session-identity system: call `POST /v1/sessions/link` on login, trigger session rotation on logout
- Add FastAPI dependencies for optional and required auth (`get_current_user_optional`, `get_current_user`)
- Verify Google ID tokens using RS256 JWKS (fetched from Google, cached in-memory with 6-hour refresh)
- Store OAuth state tokens in-memory with 10-minute TTL for CSRF protection (stash session_id alongside for callback recovery)
- New dependencies: `httpx` (async HTTP), `PyJWT[crypto]` (JWT + RS256 support)
- New env vars: `ATELIER_GOOGLE_CLIENT_ID`, `ATELIER_GOOGLE_CLIENT_SECRET`, `ATELIER_GOOGLE_REDIRECT_URI`, `ATELIER_JWT_SECRET`

## Capabilities

### New Capabilities

- `oauth-flow`: Google OAuth 2.0 authorization code flow — login redirect, callback handling, state token CSRF protection, Google ID token verification via JWKS, and user record upsert
- `jwt-auth`: JWT session token issuance and validation — HS256 signing, session-validated decode, FastAPI auth dependencies (optional and required), and logout/session-rotation integration
- `user-profile`: User management — SQLite users table with is_admin flag, create-or-update on OAuth login, profile read endpoint (`/auth/me`), first-user-as-admin bootstrap logic

### Modified Capabilities

<!-- No existing capabilities are modified at the requirement level. Session-identity's link endpoint is consumed, not changed. -->

## Impact

- **New files**: `app/api/v1/auth.py`, `app/models/users.py`, `app/services/auth_service.py`, `app/services/user_service.py`
- **Modified files**: `app/dependencies/auth.py` (add user auth deps alongside existing API key auth), `app/db/sqlite.py` (add users table schema)
- **SQLite schema**: New `users` table in `app/data/atelier.db`
- **API surface**: 4 new endpoints under `/v1/auth/`
- **Dependencies**: `httpx`, `PyJWT[crypto]` (includes `cryptography` for RS256)
- **Environment**: 4 new env vars required for Google OAuth configuration
- **Dependency on session-identity**: Requires `POST /v1/sessions/link` and session rotation service
- **Security surface**: JWT secret management, Google client secret, OAuth state tokens, JWKS caching
