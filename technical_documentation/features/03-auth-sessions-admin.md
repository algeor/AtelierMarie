# Auth, Sessions, Account, And Admin

Use this when touching login, logout, session cookies, admin checks, account pages, or admin pages.

## Mental Model

The app is anonymous-first.

A visitor gets a session cookie before login. They can browse, cart, and checkout anonymously. Login links a user to the existing session; it should not throw away the cart.

## Main Backend Files

- `app/middleware/session.py`: session cookie creation/validation/expiry behavior.
- `app/dependencies/session.py`: `require_session`.
- `app/dependencies/auth.py`: current user and admin dependencies.
- `app/services/auth_service.py`: Google OAuth, JWT, user upsert.
- `app/routes/auth.py`: login, callback, me, logout.
- `app/routes/admin.py`: admin endpoints.
- `app/config.py`: cookie/JWT/OAuth/admin settings.

## Main Frontend Files

- `frontend/contexts/AuthContext.tsx`
- `frontend/contexts/AdminContext.tsx`
- `frontend/components/auth/*`
- `frontend/components/admin/AdminGuard.tsx`
- `frontend/components/admin/AdminSidebar.tsx`
- `frontend/app/[locale]/auth/callback/*`
- `frontend/app/[locale]/account/page.tsx`
- `frontend/app/[locale]/orders/*`
- `frontend/app/[locale]/admin/*`

## Session Rules

- Session cookie is the base identity for anonymous users.
- Session IDs must be format-validated before DB lookup.
- Returning sessions are validated against DB rows.
- Expiry slides on activity with a threshold.
- Absolute lifetime still caps the session.
- Session middleware skips non-app paths like health/docs/static/webhooks.
- Login rotates/links session to reduce fixation risk.
- Logout clears auth and rotates anonymous session.

## Google OAuth Rules

- Login redirects to Google using configured redirect URI.
- Callback exchanges code server-side.
- Email must be verified.
- JWKS cache must be safe and observable.
- First user can bootstrap admin status.
- OAuth failures should fail gracefully, not crash the app.

## JWT Rules

- JWT is stored in a secure cookie.
- Protected routes validate JWT and current DB user.
- Admin privilege is checked from DB/admin dependency, not trusted forever from old state.
- Logout clears JWT.

## Admin Auth Rules

Admin access can come from:

- logged-in admin JWT
- admin API key where supported

Rules:

- API key compare must be constant-time.
- Empty API key disables API-key auth.
- Production requires a strong admin API key.
- Admin pages should use `AdminGuard` and shared admin context.

## Account And Orders

- Anonymous users see login prompts where account-only data is needed.
- Logged-in users can view profile and order history.
- Order history includes orders from the current session and linked user where applicable.
- Status badges should use shared mappings.

## Safe Change Checklist

- Anonymous checkout still works.
- Login does not erase cart.
- Logout rotates session and clears auth state.
- Admin checks happen on backend, not only in frontend.
- OAuth config is read from settings.
- Tests cover anonymous, logged-in, admin, and denied cases.

