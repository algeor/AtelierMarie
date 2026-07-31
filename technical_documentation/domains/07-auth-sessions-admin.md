# Auth, Sessions, And Admin

The app is anonymous-first. Login is optional for customers, required for owner/admin workflows.

## Main Backend Files

- `app/middleware/session.py`
- `app/dependencies/session.py`
- `app/dependencies/auth.py`
- `app/services/auth_service.py`
- `app/routes/auth.py`
- `app/routes/admin.py`
- `app/config.py`

## Main Frontend Files

- `frontend/contexts/AuthContext.tsx`
- `frontend/contexts/AdminContext.tsx`
- `frontend/components/auth/*`
- `frontend/components/admin/AdminGuard.tsx`
- `frontend/components/admin/AdminSidebar.tsx`
- `frontend/app/[locale]/auth/callback/*`
- `frontend/app/[locale]/account/page.tsx`
- `frontend/app/[locale]/admin/*`

## Session Model

Every visitor gets a session row/cookie.

Session row contains:

- `id`
- `user_id` when logged in
- `preferred_locale`
- `created_at`
- `expires_at`

Cart is keyed by session, so login/logout behavior must be careful.

## Session Lifecycle

```text
first request
  -> SessionMiddleware creates/validates session
  -> request.state.session_id is set
  -> route uses require_session
```

Rules:

- Session IDs are validated before DB lookup.
- Activity can slide expiry.
- Absolute lifetime caps the session.
- Non-app paths and webhooks are skipped.
- Session rotation emits `X-Session-Rotated` so frontend refreshes auth/cart.

## Google OAuth Flow

```text
frontend login button
  -> /v1/auth/login?redirect_to=...
  -> auth_service builds Google URL with PKCE and signed state
  -> Google callback
  -> state validates current session
  -> code exchanged for tokens
  -> Google ID token verified with JWKS cache
  -> email_verified required
  -> user upserted
  -> session linked/rotated
  -> JWT cookie set
  -> frontend callback completes UI state
```

## OAuth Safety Features

- PKCE protects code exchange.
- State JWT is signed and bound to session.
- State expires after a short window.
- JWKS cache is thread-safe.
- Google network failures go through circuit breaker behavior.
- Redirect paths are validated.

## JWT Rules

- JWT cookie stores authenticated user session.
- Protected routes validate JWT.
- Admin privilege is checked against DB/admin dependency.
- Logout clears auth cookie and rotates session.

## Admin Access

Admin routes require either supported admin auth path:

- admin JWT/user check
- admin API key where the dependency supports it

Rules:

- API key compare must be constant-time.
- Empty admin API key disables API-key auth.
- Production requires a strong admin key.
- Frontend admin guard is UX only.

## Safe Change Checklist

- Anonymous checkout still works.
- Login does not erase cart.
- Logout clears auth but leaves usable anonymous session.
- `session-rotated` refreshes auth/cart.
- Admin UI cannot bypass backend auth.
- OAuth redirect cannot send users to unsafe paths.

