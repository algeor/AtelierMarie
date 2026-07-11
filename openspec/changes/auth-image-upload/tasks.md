## 1. Dependencies & Config

- [x] 1.1 Add `httpx`, `PyJWT`, `Pillow`, `cryptography` to `pyproject.toml` dependencies
- [x] 1.2 Add `google_redirect_uri`, `jwt_expiry_hours` (default 168), and `frontend_url` (default `http://localhost:3000`) to `app/config.py` Settings
- [x] 1.3 Ensure `static_file_path` directory and `products/` subdirectory are created on app startup (in lifespan)

## 2. Auth Service — Google OAuth

- [x] 2.1 Create `app/services/auth_service.py` with Google OAuth helper functions
- [x] 2.2 Implement `build_google_auth_url(session_id, return_to=None)` — generate code_verifier (43-128 chars, URL-safe random), compute code_challenge=base64url(SHA256(code_verifier)), generate state token (JWT with `type="oauth_state"`, session_id, nonce, code_verifier, optional return_to path, iat, 10min exp), include code_challenge and code_challenge_method=S256 in auth URL, and return Google authorize URL
- [x] 2.3 Implement `exchange_code_for_tokens(code, redirect_uri, code_verifier)` — calls Google token endpoint via httpx (10s timeout) with code_verifier in request body (PKCE), returns ID token
- [x] 2.4 Implement JWKS cache: `_jwks_cache` dict with `{kid: (key_object, fetched_at)}`, 6-hour TTL, fetch from `googleapis.com/oauth2/v3/certs`. On fetch failure: use stale cache if available, raise 503 if empty cache.
- [x] 2.5 Implement `verify_google_id_token(id_token)` — decode RS256 JWT using cached JWKS, validate aud/iss/exp, reject `email_verified=false`, return claims (sub, email, name, picture)
- [x] 2.6 Implement `upsert_user(conn, google_claims)` — INSERT or UPDATE user row, handle first-user-is-admin logic (atomic: explicit `BEGIN IMMEDIATE` for exclusive write lock — count check + insert in same transaction; required because database.py uses default deferred mode)

## 3. Auth Service — JWT & Dependencies

- [x] 3.1 Implement `create_jwt(user_id, email, is_admin, session_id)` — sign HS256 JWT with iss="atelier-marie", aud="atelier-marie-web", exp=now + `settings.jwt_expiry_hours` (default 168h)
- [x] 3.2 Implement `verify_jwt(token)` — decode with `algorithms=["HS256"]`, validate signature + exp + iss + aud, return claims dict or None
- [x] 3.3 Create `get_current_user` FastAPI dependency — extract `atelier_auth` cookie, verify JWT, check session exists in DB AND session.user_id matches JWT's user_id, return `UserResponse` or None
- [x] 3.4 Create `require_auth` dependency — wraps `get_current_user`, raises 401 if None
- [x] 3.5 Create `require_admin` dependency — explicit precedence: (1) JWT valid + DB admin → grant, (2) JWT valid + not admin → 403 (key cannot escalate), (3) no JWT + valid API key → grant, (4) no JWT + no key → 401. Uses hmac.compare_digest for key comparison
- [x] 3.6 Handle edge case: empty `admin_api_key` disables API key auth entirely

## 4. Auth Routes

- [x] 4.1 Replace `app/routes/auth.py` stub with full implementation
- [x] 4.2 Implement `GET /v1/auth/login` — build Google auth URL, return 302 redirect
- [x] 4.3 Implement `GET /v1/auth/callback` — validate state (signature with `algorithms=["HS256"]` → expiry → `type="oauth_state"` → session_id matches request), exchange code (include code_verifier from state for PKCE), verify ID token, upsert user, link session (`UPDATE orders SET user_id = ? WHERE session_id = ? AND user_id IS NULL`), set JWT cookie, redirect to `settings.frontend_url` + return_to path (validated: starts with `/`, does NOT start with `//`)
- [x] 4.4 Implement `GET /v1/auth/me` — return current user profile (200) or 401
- [x] 4.5 Implement `POST /v1/auth/logout` — clear JWT cookie, rotate session (new UUID, set in DB, update session cookie, return X-Session-Rotated header)

## 5. Session Rotation

- [x] 5.1 Implement session rotation logic in auth_service: clear old session's user_id, create new session row, return new session_id
- [x] 5.2 Wire logout route to call session rotation and update the session cookie in the response
- [x] 5.3 Ensure unauthenticated logout still rotates session gracefully (no error) — but only if a valid session cookie exists (prevents session exhaustion DoS)
- [x] 5.4 Add `request.state.session_is_new` flag in session middleware — set True when middleware creates a new session, False when using existing cookie session. Logout route checks this flag to skip rotation for middleware-created sessions.

## 6. Image Service

- [x] 6.1 Create `app/services/image_service.py`
- [x] 6.2 Implement `validate_image_file(file_bytes)` — check size ≤5MB, check magic bytes (FF D8 FF for JPEG, 89 50 4E 47 for PNG), validate product_id matches slug format (`^[a-z0-9][a-z0-9-]*[a-z0-9]$`), raise custom errors
- [x] 6.3 Implement `process_image(file_bytes, product_id, static_path)` — MAX_IMAGE_PIXELS=25M set at MODULE LEVEL (not inside function), open with Pillow, verify real image, strip EXIF, resize (thumbnail mode: 1200×1500 main, 400×500 thumb), save as WebP (quality 85/80)
- [x] 6.4 Ensure target directory `{static_path}/products/` is created if missing
- [x] 6.5 Implement overwrite behavior: new upload replaces existing files
- [x] 6.6 Validate resolved output path is under `{static_path}/products/` (path traversal prevention via pathlib.resolve())

## 7. Image Upload Route

- [x] 7.1 Add `POST /v1/admin/products/{product_id}/image` to `app/routes/admin.py`
- [x] 7.2 Wire `require_admin` dependency on the endpoint
- [x] 7.3 Accept `UploadFile` (multipart), read bytes, call image_service validate + process
- [x] 7.4 Verify product exists in DB (404 if not), update `products.image_url` after processing
- [x] 7.5 Return 200 with `{image_url, thumbnail_url}` on success

## 8. Custom Exceptions

- [x] 8.1 Create auth exceptions: `OAuthError`, `InvalidTokenError`, `UserNotFoundError`
- [x] 8.2 Create image exceptions: `InvalidImageTypeError`, `FileTooLargeError`, `ImageProcessingError`
- [x] 8.3 Wire exception-to-HTTP-status mapping in routes (400, 401, 403, 404, 422)

## 9. Tests — Auth

- [x] 9.1 Test `build_google_auth_url` generates valid state token (with `type="oauth_state"` claim) and correct URL — verify client_id, redirect_uri (from settings), response_type=code, scope=openid email profile are all present as query params
- [x] 9.2 Test `verify_google_id_token` with mocked JWKS (happy path + expired + bad signature + email_verified=false + wrong aud + wrong iss)
- [x] 9.3 Test `upsert_user` — new user created, existing user updated, first-user-is-admin (test concurrent scenario: two threads call upsert_user simultaneously on empty table, verify exactly one gets is_admin=1)
- [x] 9.4 Test `create_jwt` / `verify_jwt` round-trip (valid, expired, tampered, wrong algorithm, bad iss/aud)
- [x] 9.5 Test `get_current_user` dependency — valid JWT, expired JWT, no cookie, session not in DB, session exists but user_id NULLed (post-logout — must fail)
- [x] 9.6 Test `require_admin` — admin JWT, non-admin JWT, valid API key, invalid API key, empty API key config, no credentials, admin revoked in DB, non-admin JWT + valid API key → 403 (JWT is identity, key cannot escalate), admin JWT + invalid API key (should succeed via JWT)
- [x] 9.7 Test OAuth callback route end-to-end (mock httpx calls to Google)
- [x] 9.8 Test `/v1/auth/me` — authenticated and unauthenticated
- [x] 9.9 Test `/v1/auth/logout` — session rotation occurs, cookie cleared, X-Session-Rotated header present, unauthenticated logout with valid session also works, logout without valid session returns 200 without creating new row
- [x] 9.10 Test OAuth callback with invalid state — expired token, tampered signature, mismatched session_id, missing `type` claim each return 400 `invalid_state`
- [x] 9.11 Test OAuth callback with invalid code — mock Google token endpoint error → verify 400 `token_exchange_failed`
- [x] 9.12 Test OAuth callback links session — verify `sessions.user_id` set, session_id cookie unchanged, cart_items preserved, orders.user_id backfilled for anonymous orders
- [x] 9.13 Test logout does not transfer cart — add items, logout, verify new session has empty cart
- [x] 9.14 Test JWKS cache — first call fetches, second within TTL uses cache (no httpx call), after TTL re-fetches, unknown kid triggers refresh even within TTL, fetch failure uses stale cache
- [x] 9.15 Test OAuth callback with email_verified=false — mock Google to return unverified email, verify 400 response with error `"email_not_verified"`
- [x] 9.16 Test JWT signed with old secret rejected after secret rotation
- [x] 9.17 Test return_to path — valid path (starts with `/`) preserved through login flow, invalid path (contains `//` or doesn't start with `/`) falls back to `/`

## 10. Tests — Image Upload

- [x] 10.1 Test `validate_image_file` — valid JPEG, valid PNG, exactly 5MB file (accepted), 5MB+1 byte file (rejected), wrong magic bytes (GIF, SVG, text)
- [x] 10.2 Test `process_image` — verify output dimensions (landscape, portrait, small no-upscale), verify WebP format, verify BOTH main + thumb files created, verify save() called with quality=85 for main and quality=80 for thumb
- [x] 10.3 Test upload route — happy path (admin + valid image), non-admin rejected, product not found, invalid file type, file too large, verify DB `image_url` updated
- [x] 10.4 Test overwrite: upload twice for same product, second replaces first
- [x] 10.5 Test directory auto-creation on first upload
- [x] 10.6 Test corrupted image — valid JPEG magic bytes but truncated body → graceful 422 error, not 500
- [x] 10.7 Test pixel flood protection — image with exactly 25M pixels (5000×5000) accepted; image with >25M pixels (5001×5000) rejected with `image_dimensions_too_large`
- [x] 10.8 Test path traversal prevention — product_id with `../` does not escape static directory; also test null byte (`\x00`), backslash (`\`), and URL-encoded variants (`%2e%2e%2f`)
- [x] 10.9 Test EXIF stripping — upload JPEG with GPS/camera EXIF data, verify output WebP has no EXIF or XMP metadata (use Pillow's `getexif()` on saved file)
- [x] 10.10 Test product_id slug validation — non-slug product_id (contains spaces, uppercase, special chars) rejected before file path construction

## 11. Integration & Wiring

- [x] 11.1 Register auth router in `app/main.py` (replace stub registration if needed)
- [x] 11.2 Ensure admin routes use `require_admin` dependency
- [x] 11.3 REMOVE `GoogleAuthRequest` (redirect_uri field contradicts config-only design) and `AuthTokenResponse` (JWT is in cookie, not response body) from `app/models/auth.py`. Add any new models needed (e.g., error response models for callback).
- [x] 11.4 Configure CORS middleware with `allow_credentials=True` and explicit origins from `settings.cors_origins` (never wildcard with credentials). Verify cookies work cross-origin.
- [x] 11.5 Smoke test: mock Google OAuth → callback → me (200) → logout → verify session cookie changed → me (401) — uses mocked httpx for Google calls, exercises full route chain with TestClient
- [x] 11.6 Test JWT cookie attributes — verify `atelier_auth` cookie has HttpOnly=True, Secure=(True in production, False in dev), SameSite=Lax, Path=/, max-age=604800 after login
- [x] 11.7 Test CORS config — verify response includes `Access-Control-Allow-Credentials: true` for configured frontend origin
