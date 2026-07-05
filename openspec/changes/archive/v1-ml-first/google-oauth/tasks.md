## 1. Dependencies & Configuration

- [ ] 1.1 Add `httpx` and `PyJWT[crypto]` to project dependencies
- [ ] 1.2 Add OAuth/JWT settings to pydantic-settings config: `ATELIER_GOOGLE_CLIENT_ID`, `ATELIER_GOOGLE_CLIENT_SECRET`, `ATELIER_GOOGLE_REDIRECT_URI`, `ATELIER_JWT_SECRET`
- [ ] 1.3 Add startup validation that fails fast if `ATELIER_JWT_SECRET` is not configured

## 2. Database Schema

- [ ] 2.1 Add `users` table schema to `app/db/sqlite.py` (id, google_id UNIQUE, email UNIQUE, name, avatar_url, created_at, last_login_at)
- [ ] 2.2 Add `CREATE TABLE IF NOT EXISTS users` to SQLite initialization (alongside products table)

## 3. User Service

- [ ] 3.1 Create `app/models/users.py` with Pydantic models: `UserCreate`, `UserResponse`, `TokenResponse`
- [ ] 3.2 Create `app/services/user_service.py` with `create_or_update(google_id, email, name, avatar_url) -> User`
- [ ] 3.3 Implement upsert logic: INSERT on new google_id, UPDATE name/avatar_url/last_login_at on existing
- [ ] 3.4 Implement `get_by_id(user_id: int) -> Optional[User]`
- [ ] 3.5 Implement `get_by_google_id(google_id: str) -> Optional[User]`

## 4. Auth Service (Google OAuth + JWT)

- [ ] 4.1 Create `app/services/auth_service.py` with in-memory state store (`dict[str, {expires_at, session_id}]`)
- [ ] 4.2 Implement `generate_state_token(session_id) -> str` (32 bytes random, URL-safe base64, stash session_id)
- [ ] 4.3 Implement `validate_state_token(state) -> {session_id}` (pop from store, check expiry, return session_id)
- [ ] 4.4 Implement `build_auth_url(state_token) -> str` (Google OAuth URL with client_id, redirect_uri, scopes, state)
- [ ] 4.5 Implement `exchange_code(code) -> dict` (httpx POST to Google token endpoint, return token response)
- [ ] 4.6 Implement JWKS cache: fetch from `googleapis.com/oauth2/v3/certs`, cache in-memory, 6-hour TTL
- [ ] 4.7 Implement `verify_id_token(id_token) -> dict` (RS256 verification via cached JWKS, validate iss/aud/exp, fallback refetch on failure)
- [ ] 4.8 Implement `create_jwt(user_id, session_id) -> str` (HS256, 7-day expiry)
- [ ] 4.9 Implement `decode_jwt(token) -> dict` (verify signature + expiry, return payload)
- [ ] 4.10 Implement state store cleanup (remove expired entries on each access or periodic sweep)

## 5. Auth Dependencies

- [ ] 5.1 Add `get_current_user(request) -> User` to `app/dependencies/auth.py` (extract Bearer token, decode JWT, verify session active, fetch user from DB, return 401 on failure)
- [ ] 5.2 Add `get_current_user_optional(request) -> Optional[User]` (same as above but returns None instead of 401 when token missing or invalid)

## 6. Auth Endpoints

- [ ] 6.1 Create `app/api/v1/auth.py` router
- [ ] 6.2 Implement `GET /v1/auth/google/login` (require X-Session-ID, generate state, return redirect_url)
- [ ] 6.3 Implement `GET /v1/auth/google/callback` (validate state, exchange code, verify ID token, upsert user, link session, issue JWT)
- [ ] 6.4 Implement `POST /v1/auth/logout` (require auth, rotate session, return X-Session-Rotated header)
- [ ] 6.5 Implement `GET /v1/auth/me` (require auth, return user profile)
- [ ] 6.6 Register auth router in the FastAPI app

## 7. Session Integration

- [ ] 7.1 In callback: call `POST /v1/sessions/link` internally with recovered session_id and user_id
- [ ] 7.2 In logout: call session rotation service (mark session expired, get new session_id)
- [ ] 7.3 In JWT validation (`get_current_user`): check session_id is active via session cache `is_active()` check

## 8. Tests

- [ ] 8.1 Unit tests for auth_service: state token generation, validation, expiry, cleanup
- [ ] 8.2 Unit tests for auth_service: JWT creation and decoding (valid, expired, tampered)
- [ ] 8.3 Unit tests for auth_service: ID token verification (mock JWKS, valid/invalid tokens)
- [ ] 8.4 Unit tests for user_service: create new user, update returning user, get by id/google_id
- [ ] 8.5 Unit tests for auth dependencies: get_current_user (valid, no token, invalid token, expired session)
- [ ] 8.6 Unit tests for auth dependencies: get_current_user_optional (valid, no token → None, invalid → None)
- [ ] 8.7 Integration test: full login flow (login → redirect → callback → JWT issued → /me works)
- [ ] 8.8 Integration test: logout flow (logout → session rotated → old JWT rejected)
- [ ] 8.9 Integration test: returning user (second login updates profile, same user_id)
- [ ] 8.10 Integration test: CSRF protection (callback with invalid/expired state → 400)
