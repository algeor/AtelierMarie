## Why

The store currently has no user authentication — every visitor is anonymous with only a session cookie. To enable "My Orders" history, admin access to the management panel, and secure product image uploads, we need Google OAuth login, JWT-based identity, and an image processing pipeline. This is Day 5 of the implementation plan and unblocks admin UI and user-facing account features.

## What Changes

- **Users table schema** already exists in `database.py` — implementation will use it as-is (google_id, email, name, avatar_url, is_admin, last_login_at)
- **Google OAuth flow** via direct `httpx` calls (no authlib) — login redirect, callback token exchange, Google JWKS verification
- **JWT cookie issuance** (HS256, 7-day expiry) with `user_id`, `email`, `is_admin`, `session_id` claims
- **First-user-is-admin bootstrap** — first Google OAuth user auto-promoted, no manual DB edits
- **Dual admin auth dependency** — `require_admin` accepts JWT `is_admin` claim OR `Authorization: Bearer <API_KEY>` (constant-time comparison)
- **Session rotation on logout** — old session cleared, new UUID issued, `X-Session-Rotated` header sent
- **Login linking** — existing session's `user_id` set on OAuth callback; cart items preserved
- **Product image upload** — multipart POST, validate JPEG/PNG ≤5MB, resize (1200×1500 main, 400×500 thumb), convert to WebP via Pillow, save to static dir
- **Auth route stubs replaced** — `app/routes/auth.py` currently returns 501; will be fully implemented

## Capabilities

### New Capabilities
- `google-oauth`: Google OAuth 2.0 login/callback flow, JWKS token verification, user upsert, first-admin bootstrap
- `jwt-auth`: JWT cookie issuance, validation, session cross-check, `get_current_user` dependency
- `admin-auth`: Dual admin authentication (JWT is_admin OR API key), `require_admin` dependency
- `session-auth-lifecycle`: Session rotation on logout, login linking (session ↔ user_id binding)
- `image-upload`: Product image upload, validation, resize, WebP conversion, static file serving

### Modified Capabilities

(none — no existing specs are being modified at the requirement level)

## Impact

- **New files:** `app/services/auth_service.py`, `app/services/image_service.py`
- **Modified files:** `app/routes/auth.py` (replace stub), `app/routes/admin.py` (add image endpoint + wire `require_admin`)
- **Dependencies added:** `httpx` (OAuth HTTP calls), `PyJWT` (token signing/verification), `Pillow` (image processing), `cryptography` (JWKS RS256 verification)
- **Config:** `google_client_id`, `google_client_secret`, `admin_api_key` already in `app/config.py` — may add `google_redirect_uri`, `jwt_expiry_hours`
- **Static files:** Product images written to `settings.static_file_path` — Nginx serves in production
- **Tests:** Mock Google OAuth endpoints, test first-admin flow, test image validation/processing
