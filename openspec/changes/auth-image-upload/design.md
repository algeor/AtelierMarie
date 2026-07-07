## Context

The app skeleton already has:
- `users` table schema in `database.py` (google_id, email, name, avatar_url, is_admin, last_login_at)
- `sessions` table with `user_id` FK to users
- Pydantic models: `UserResponse`, `AuthTokenResponse`, `GoogleAuthRequest` in `app/models/`
- Auth route stub in `app/routes/auth.py` returning 501
- Config with `google_client_id`, `google_client_secret`, `jwt_secret`, `jwt_algorithm`, `admin_api_key`, `static_file_path`
- Session middleware that eagerly creates session rows and sets `request.state.session_id`

No external auth library is used — OAuth is implemented directly via `httpx` to minimize dependencies and control the flow.

## Goals / Non-Goals

**Goals:**
- Implement Google OAuth 2.0 login with direct HTTP calls (no authlib)
- Issue JWT cookies for authenticated users; validate on protected routes
- First-user-is-admin bootstrap (no manual DB edits)
- Dual admin auth: JWT `is_admin` OR `Authorization: Bearer <API_KEY>`
- Session rotation on logout (prevent session fixation)
- Product image upload with validation, resize, and WebP conversion
- All auth/image code fully tested with mocked external services

**Non-Goals:**
- No email/password auth — Google OAuth only (family business, few admins)
- No refresh tokens — JWT has 7-day expiry; user re-logs after that
- No CDN or cloud storage — images served from local disk via Nginx
- No image cropping UI — server picks resize strategy (fit within bounds)
- No multi-provider OAuth — Google only for MVP
- No RBAC beyond admin/non-admin binary flag

## Decisions

### 1. Direct httpx for OAuth (no authlib/oauthlib)

**Choice:** Use `httpx` to call Google's token and userinfo endpoints directly.

**Rationale:** The OAuth flow is just 3 HTTP calls (authorize URL → token exchange → verify ID token). Adding authlib would bring 15+ transitive dependencies for 50 lines of code. `httpx` is already needed for async HTTP in the project.

**Alternative considered:** `authlib` — rejected for over-engineering at this scale.

### 2. JWT as HttpOnly cookie (not Authorization header)

**Choice:** Set JWT in an HttpOnly, Secure, SameSite=Lax cookie named `atelier_auth`.

**Rationale:** The frontend is same-origin (Nginx proxies both). Cookies are sent automatically — no token management in JS, no XSS-accessible localStorage. HttpOnly prevents JS access; SameSite=Lax prevents CSRF on state-changing requests.

**Alternative considered:** `Authorization: Bearer` header with localStorage — rejected because it's less secure for browser-based SPA and requires manual header management.

### 3. JWKS cached in-memory with TTL

**Choice:** Cache Google's JWKS (public keys for ID token verification) in a module-level dict with 6-hour TTL. Re-fetch on cache miss or expiry.

**Rationale:** Google rotates keys infrequently (~weekly). Caching avoids a network call per login. 6-hour TTL balances freshness vs. performance.

**Implementation:** Simple dict `{kid: (key, fetched_at)}`. On verify: check TTL → if stale, fetch → find matching `kid` → verify RS256. On fetch failure: use stale cache if available; fail with 503 if no cache exists.

### 4. Pillow for image processing

**Choice:** Use Pillow (PIL fork) for resize + WebP conversion.

**Rationale:** Pillow is the de-facto Python image library. It handles JPEG/PNG input and WebP output natively. No external binaries needed (unlike ImageMagick).

**Processing pipeline:**
1. Validate content-type and file size (≤5MB, JPEG/PNG only)
2. Open with Pillow, verify it's a real image (not a renamed file)
3. Resize: `Image.thumbnail((1200, 1500))` preserving aspect ratio (main); `Image.thumbnail((400, 500))` for thumb
4. Save as WebP (quality=85 for main, quality=80 for thumb)
5. Update `products.image_url` in DB

### 5. State token for CSRF protection in OAuth

**Choice:** Encode `{session_id, nonce, timestamp}` as a signed JWT (short-lived, 10 minutes) and pass as OAuth `state` parameter.

**Rationale:** Prevents CSRF on the callback endpoint. The session_id binding ensures the callback is processed by the same browser session that initiated login. Timestamp prevents replay of old state tokens.

### 6. Admin API key comparison with hmac.compare_digest

**Choice:** Use `hmac.compare_digest()` for API key comparison.

**Rationale:** Prevents timing attacks that could leak the key character-by-character. Standard practice for secret comparison.

## Risks / Trade-offs

**[Risk] Google OAuth outage blocks all login** → Mitigation: Admin API key still works for admin operations. Store functions for anonymous users regardless. Login is not required for purchasing.

**[Risk] JWT secret compromise** → Mitigation: Production validator rejects the dev default secret. Rotation requires restarting the app (all existing JWTs invalidated — acceptable for few-user system).

**[Risk] Image processing OOM on large files** → Mitigation: Reject files >5MB before processing. Set `PIL.Image.MAX_IMAGE_PIXELS = 25_000_000` at module level in `image_service.py` (import-time, not inside a function) to prevent pixel flood attacks. Even within 5MB file size, adversarial inputs can have enormous pixel counts.

**[Risk] Disk space from product images** → Mitigation: ~50 products × 2 images × ~200KB = ~20MB total. Negligible on any VPS. No cleanup on product deactivation — revisit if catalog grows past 500 products.

**[Trade-off] No refresh tokens** → Users must re-login after 7 days. Acceptable for a store with few repeat admin sessions. Reduces complexity significantly.

**[Trade-off] Synchronous image processing** → Upload blocks until resize completes (~200-500ms for a 5MB image). Acceptable for admin-only operation with few concurrent uploads. Background processing adds complexity for no user benefit at this scale.

**[Trade-off] No JPEG fallback for images** → The core-ecommerce design mentioned "WebP with JPEG fallback." Dropped because WebP support is universal in 2026 browsers. Generating JPEG fallback doubles storage and code complexity for zero benefit. All images are WebP-only.

**[Trade-off] Admin `is_admin` verified from DB on admin requests** → Adds one SELECT per admin request but ensures admin revocation takes effect immediately (not after 7-day JWT expiry). Acceptable overhead — admin requests are infrequent.

**[Trade-off] Logout CSRF mitigation via SameSite=Lax only** → The `POST /v1/auth/logout` endpoint is protected from cross-site POSTs by `SameSite=Lax` on the cookie. For a single-origin deployment without untrusted subdomains, this is sufficient. If subdomain isolation changes, add a CSRF token.

**[Trade-off] CORS credentials mode requires exact origin** → When `allow_credentials=True`, browsers reject `Access-Control-Allow-Origin: *`. The CORS config MUST specify exact frontend origins. Production config already validates no wildcards; CORS also needs `allow_credentials=True` for cross-origin cookies to work between Next.js and the API.

**[Trade-off] Order backfill relies on UUID4 unguessability** → The `UPDATE orders SET user_id` backfill on login uses the current session_id as authorization boundary. An attacker would need to guess a 128-bit UUID4 to claim another user's orders. Accepted risk for the threat model (small family business, ~50 orders/month).
