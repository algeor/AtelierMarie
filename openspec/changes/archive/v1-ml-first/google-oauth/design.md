## Context

AtelierMarie has a working event pipeline (JSONL → DuckDB), product catalog (SQLite), and session & identity layer (in-memory cache + DuckDB session_identity). Sessions are anonymous-first: clients generate UUID v4 session_ids, the middleware tracks lifecycle, and events reference sessions. The session-identity system provides `POST /v1/sessions/link` to bind a session to a user_id and rotation on logout.

**Current state:**
- No user accounts or authentication
- Admin routes use a single API key (`ATELIER_ADMIN_API_KEY`)
- Sessions exist but have no identity beyond an opaque UUID
- `app/dependencies/auth.py` has `verify_admin_key()` for admin routes
- SQLite at `app/data/atelier.db` with `products` table (WAL mode)

**Constraints:**
- Zero budget — no Auth0, no Firebase Auth, no paid identity providers
- No third-party OAuth libraries (authlib, python-social-auth) — direct HTTP calls
- Must work on free-tier VPS (limited memory, single process)
- Must integrate cleanly with existing session middleware (path-based enforcement)
- Google OAuth callback is a plain browser GET (no custom headers possible)
- Auth is optional — most endpoints work without login

## Goals / Non-Goals

**Goals:**
- Add Google OAuth 2.0 login as the sole authentication mechanism
- Issue JWT tokens for authenticated sessions with session-validated integrity
- Integrate with session-identity system (link on login, rotate on logout)
- Support optional auth on most endpoints, required auth only for profile/account features
- Verify Google ID tokens securely (RS256 JWKS, not just tokeninfo endpoint)
- Handle returning users (upsert profile on each login)

**Non-Goals:**
- Email/password authentication (avoids password storage liability)
- Multiple OAuth providers (Google only for MVP; architecture permits adding later)
- Token refresh flow (7-day JWT; re-login is fast with Google)
- Admin role elevation via OAuth (admin remains API-key-based)
- User management admin panel
- Account deletion or GDPR data export (future maintenance-tooling concern)
- Rate limiting on auth endpoints

## Decisions

### 1. Google OAuth 2.0 only — no email/password

**Decision:** Authentication is exclusively via Google OAuth. No email/password registration, no magic links, no other social providers.

**Alternatives considered:**
- *Email/password*: Requires password hashing, reset flows, email verification. Massive security surface for zero benefit on a solo-run platform. Rejected.
- *Multiple OAuth providers*: Adds complexity (account linking, provider-specific quirks). Google covers 90%+ of target users. Add Apple/GitHub later if needed. Rejected for MVP.
- *Magic links (passwordless email)*: Requires email sending infrastructure (cost, deliverability). Rejected for zero-budget constraint.

**Rationale:** Google OAuth is free, ubiquitous, and eliminates password storage liability entirely. Single provider keeps the implementation surface minimal.

### 2. Direct HTTP calls to Google (no OAuth library)

**Decision:** Use `httpx` to call Google's OAuth endpoints directly. No authlib, no python-social-auth, no oauthlib.

**Alternatives considered:**
- *authlib*: Full-featured but opaque. Adds complexity (session backends, token stores) that conflicts with our custom session system. Rejected.
- *python-social-auth*: Django-oriented, heavy, opinionated about user models. Rejected.

**Rationale:** The OAuth 2.0 authorization code flow is 3 HTTP calls: (1) build auth URL, (2) POST token exchange, (3) fetch JWKS for verification. Direct calls keep the system transparent, debuggable, and dependency-light.

### 3. JWT with session_id cross-validation (not purely stateless)

**Decision:** JWT payload contains `{user_id, session_id, exp}`. On validation, the server checks that `session_id` is still active in the session cache. This is a "session-validated JWT" — not purely stateless.

**Alternatives considered:**
- *Purely stateless JWT (no session check)*: Cannot revoke on logout — JWT remains valid until expiry. Rejected because logout must immediately invalidate.
- *Server-side session store (no JWT)*: Requires DB lookup on every request. Rejected — adds latency and complexity when the session cache already provides fast in-memory lookups.
- *JWT + denylist on logout*: Stateless with small denylist for revoked tokens. Same multi-worker problem as state tokens. Rejected — session_id check is simpler and already integrated.

**Rationale:** The session cache already exists (session-identity system). Checking `is_active(session_id)` is an in-memory dict lookup (<0.01ms). On logout, session rotation makes the old session_id invalid, which automatically invalidates any JWT referencing it. Zero additional infrastructure.

### 4. State token stores session_id for callback recovery

**Decision:** The in-memory state token store maps `state_token → {expires_at, session_id}`. The session_id is stashed at login time and recovered at callback time.

**Alternatives considered:**
- *Encode session_id in the state parameter itself*: Would expose session_id in URL (browser history, server logs). Security concern. Rejected.
- *Rely on X-Session-ID header on callback*: Impossible — callback is a browser redirect from Google. No custom headers. Rejected.
- *Cookie-based session*: Platform explicitly avoids cookies (header-based sessions for SPA/mobile). Rejected.

**Rationale:** The Google OAuth callback arrives as a plain `GET ?code=X&state=Y` — no custom headers, no body. The only way to know which session initiated the flow is to stash it server-side keyed by the state token. This is standard practice for server-side OAuth flows.

### 5. Google ID token verification via JWKS (RS256)

**Decision:** Verify Google's ID token by fetching Google's JWKS (`https://www.googleapis.com/oauth2/v3/certs`), caching the keys in memory for 6 hours, and validating the RS256 signature + claims (iss, aud, exp) using PyJWT.

**Alternatives considered:**
- *Google tokeninfo endpoint*: `GET https://oauth2.googleapis.com/tokeninfo?id_token=X` — simpler but adds a network call on every login. Acceptable for low-frequency logins, but JWKS is the recommended approach. Rejected as primary (could be fallback).
- *Skip verification, trust the token exchange response*: If the token came directly from Google's token endpoint over HTTPS, it's authentic. However, this skips claim validation (aud, exp) and is not recommended by Google. Rejected.

**Rationale:** `PyJWT[crypto]` handles RS256 natively. JWKS cache means zero network calls on most logins (keys rotate every ~6 hours). This is Google's recommended verification path for server-side apps.

### 6. Users table in SQLite (not DuckDB)

**Decision:** User records live in SQLite alongside products and (future) orders. Not in DuckDB.

**Alternatives considered:**
- *DuckDB*: OLAP-optimized, single-writer model, not suitable for OLTP user upserts. Rejected.
- *Separate SQLite DB*: Unnecessary isolation — users are a transactional concern like products. Rejected.

**Rationale:** SQLite is already the transactional system of record. Users are low-volume, high-read entities (same pattern as products). WAL mode handles concurrent reads. One DB file, one connection pattern.

### 7. Login endpoint returns JSON (not HTTP redirect)

**Decision:** `GET /v1/auth/google/login` returns `{"redirect_url": "..."}` as JSON. The client (SPA/mobile) is responsible for navigating to the URL.

**Alternatives considered:**
- *302 redirect from login endpoint*: Server-side redirect works for traditional web apps but breaks SPA/mobile clients that need to handle the redirect themselves. Rejected for API-first platform.

**Rationale:** API-first design. SPA clients can open the URL in a popup or redirect; mobile clients can use an in-app browser. Returning JSON gives the client full control.

### 8. Callback returns JSON (API-first, not browser-rendered)

**Decision:** `GET /v1/auth/google/callback` returns JSON `{"token": "...", "user": {...}}`. For MVP, this means the browser displays raw JSON after Google redirects.

**Future enhancement:** Add optional `ATELIER_AUTH_SUCCESS_REDIRECT` env var. If set, callback redirects to `{REDIRECT_URL}?token=X` instead of returning JSON. This enables popup/redirect flows when a frontend exists.

**Rationale:** No frontend exists yet. API-first means the callback works for Postman/testing immediately. When a frontend is added, the redirect env var enables the full browser flow without changing the backend contract.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| **In-memory state tokens lost on restart** → pending logins fail | 10-minute TTL means max 10 min of affected logins. User retries. Acceptable for low-frequency login events. |
| **State tokens not shared across workers** → multi-worker login breaks | Free-tier runs single worker. Document as known limitation. Mitigation: move to SQLite `oauth_states` table if multi-worker needed. |
| **JWKS cache stale** → token verification fails with new Google keys | 6-hour cache with fallback: on verification failure, refetch JWKS once before returning 401. Handles key rotation gracefully. |
| **JWT cannot be instantly revoked** → theoretical window after logout | Session_id cross-validation makes this a non-issue. Logout rotates session → old JWT's session_id is invalid → effectively revoked. |
| **Google account disabled/deleted** → user's JWT still works until expiry | Acceptable for 7-day window. Google disabling an account is rare. Future: periodic re-verification on sensitive operations. |
| **No PKCE** → authorization code interception on mobile | MVP targets web SPA. PKCE can be added later for mobile clients without breaking changes. |
| **`httpx` dependency** → new dep not used elsewhere yet | httpx is the standard async HTTP client for FastAPI projects. Will be used by future features (webhooks, external APIs). Justified. |

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│  FastAPI Application                                                      │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  Auth Endpoints (app/api/v1/auth.py)                               │  │
│  │                                                                    │  │
│  │  GET /v1/auth/google/login                                         │  │
│  │  → generate state token (stash session_id)                         │  │
│  │  → return Google OAuth URL                                         │  │
│  │                                                                    │  │
│  │  GET /v1/auth/google/callback?code=X&state=Y                       │  │
│  │  → validate state, recover session_id                              │  │
│  │  → exchange code for tokens (httpx → Google)                       │  │
│  │  → verify ID token (RS256 via cached JWKS)                         │  │
│  │  → upsert user in SQLite                                           │  │
│  │  → POST /v1/sessions/link (bind session → user)                    │  │
│  │  → issue JWT {user_id, session_id, exp}                            │  │
│  │                                                                    │  │
│  │  POST /v1/auth/logout                                              │  │
│  │  → rotate session (session_service)                                │  │
│  │  → return X-Session-Rotated header                                 │  │
│  │                                                                    │  │
│  │  GET /v1/auth/me                                                   │  │
│  │  → decode JWT, verify session active                               │  │
│  │  → return user profile                                             │  │
│  └──────────────────┬─────────────────────────────────────────────────┘  │
│                     │                                                     │
│  ┌──────────────────▼─────────────────────────────────────────────────┐  │
│  │  Services                                                          │  │
│  │                                                                    │  │
│  │  ┌─────────────────────┐     ┌──────────────────────────────────┐ │  │
│  │  │  auth_service.py    │     │  user_service.py                 │ │  │
│  │  │  • build_auth_url() │     │  • create_or_update(google_id,..)│ │  │
│  │  │  • exchange_code()  │     │  • get_by_id(user_id)            │ │  │
│  │  │  • verify_id_token()│     │  • get_by_google_id(google_id)   │ │  │
│  │  │  • create_jwt()     │     └──────────────────────────────────┘ │  │
│  │  │  • decode_jwt()     │                                          │  │
│  │  │  • refresh_jwks()   │                                          │  │
│  │  └─────────────────────┘                                          │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                     │                                                     │
│  ┌──────────────────▼─────────────────────────────────────────────────┐  │
│  │  Dependencies (app/dependencies/auth.py)                           │  │
│  │                                                                    │  │
│  │  verify_admin_key()           ← existing (API key for admin)       │  │
│  │  get_current_user()           ← NEW (required auth, 401 if none)   │  │
│  │  get_current_user_optional()  ← NEW (optional, None if no token)   │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                     │                                                     │
│  ┌──────────────────▼──────────┐     ┌─────────────────────────────┐    │
│  │  SQLite (atelier.db)        │     │  In-Memory Stores           │    │
│  │  ┌───────────────────────┐  │     │  ┌───────────────────────┐  │    │
│  │  │  users                │  │     │  │  state_store           │  │    │
│  │  │  - id (PK, autoincr) │  │     │  │  {token: {expires,     │  │    │
│  │  │  - google_id (unique) │  │     │  │   session_id}}         │  │    │
│  │  │  - email (unique)     │  │     │  │  TTL: 10 minutes       │  │    │
│  │  │  - name               │  │     │  └───────────────────────┘  │    │
│  │  │  - avatar_url         │  │     │  ┌───────────────────────┐  │    │
│  │  │  - created_at         │  │     │  │  jwks_cache            │  │    │
│  │  │  - last_login_at      │  │     │  │  {keys: [...],         │  │    │
│  │  └───────────────────────┘  │     │  │   fetched_at: ...}     │  │    │
│  └─────────────────────────────┘     │  │  TTL: 6 hours          │  │    │
│                                      │  └───────────────────────┘  │    │
│  ┌──────────────────────────────┐    └─────────────────────────────┘    │
│  │  Session-Identity System     │                                        │
│  │  (existing)                  │                                        │
│  │  • POST /v1/sessions/link    │ ◀── called by callback on login        │
│  │  • session rotation          │ ◀── called by logout                   │
│  │  • session cache (is_active) │ ◀── checked by JWT validation          │
│  └──────────────────────────────┘                                        │
│                                                                          │
│                 ┌──────────────────────────────────┐                      │
│                 │  External: Google OAuth Servers   │                      │
│                 │  • accounts.google.com/o/oauth2   │                      │
│                 │  • oauth2.googleapis.com/token    │                      │
│                 │  • googleapis.com/oauth2/v3/certs │                      │
│                 └──────────────────────────────────┘                      │
└──────────────────────────────────────────────────────────────────────────┘
```

## Open Questions

- **PKCE for public clients**: Should the OAuth flow include PKCE (Proof Key for Code Exchange) from the start? It's recommended for SPAs but adds complexity. Leaning: skip for MVP, add when mobile client exists.
- **Account linking edge case**: What happens if a user changes their Google email? google_id remains stable, but email field updates on next login via upsert. Should we emit an event for email changes? Leaning: just upsert, no event.
