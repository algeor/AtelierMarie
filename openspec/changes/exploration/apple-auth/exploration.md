# Apple Auth Exploration

## Current Auth Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                         Current Flow (Google Only)                  │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Frontend                 Backend                   Google          │
│  ────────                 ───────                   ──────          │
│                                                                    │
│  LoginButton              GET /v1/auth/login                       │
│  ─────────── click ──────▶ build state JWT ───────▶ OAuth consent  │
│                           (PKCE + session bind)                    │
│                                                                    │
│                           GET /v1/auth/callback ◀── code + state   │
│                            ├── validate state                      │
│                            ├── exchange code (httpx)               │
│                            ├── verify ID token (JWKS RS256)        │
│                            ├── upsert_user(google_id, ...)         │
│                            ├── link session                        │
│                            └── set JWT cookie                      │
│                                                                    │
│  /auth/callback ◀────────── 302 redirect                          │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

## Google-Specific Coupling Points

| Layer | Coupling | Details |
|-------|----------|---------|
| **DB schema** | `google_id TEXT UNIQUE NOT NULL` | User identity column is Google-specific |
| **Config** | `google_client_id`, `google_client_secret`, `google_redirect_uri` | No provider abstraction |
| **auth_service.py** | Hardcoded Google URLs, JWKS cache, token exchange | ~520 lines, all Google |
| **routes/auth.py** | Single `/login` endpoint → Google | No provider routing |
| **Frontend** | Single `login()` → `/v1/auth/login` | No provider choice UI |
| **Design decision** | "No multi-provider OAuth — Google only for MVP" | Explicitly scoped out in original design |

## Apple vs. Google OAuth — Key Differences

| Aspect | Google | Apple |
|--------|--------|-------|
| **ID Token delivery** | Returned in token exchange response | Also returned in the **POST form body** on first login |
| **User info** | Always in ID token claims | Name only provided on **first authorization** (must persist immediately) |
| **Token exchange** | Standard OAuth2 | Requires **client_secret as a signed JWT** (ES256, rotated every 6 months) |
| **JWKS endpoint** | `googleapis.com/oauth2/v3/certs` | `appleid.apple.com/auth/keys` |
| **Redirect method** | GET with query params | **POST with form data** (by default) |
| **Scopes** | `openid email profile` | `name email` (no `openid` keyword, but returns an OIDC ID token) |
| **Email relay** | Always real email | Can be a **private relay address** (`xyz@privaterelay.appleid.com`) |
| **Account deletion** | Not required | **Apple requires** you support "notify me on delete" webhook |

## Architectural Questions

### 1. DB Schema — `google_id` → multi-provider identity?

```sql
-- Option A: Add apple_id column alongside google_id
ALTER TABLE users ADD COLUMN apple_id TEXT UNIQUE;
-- Make google_id nullable (existing constraint is NOT NULL)

-- Option B: Replace with provider/provider_id (provider-agnostic)
-- Requires migration of existing google_id values
CREATE TABLE users (
    id          TEXT PRIMARY KEY,
    provider    TEXT NOT NULL,  -- 'google' | 'apple'
    provider_id TEXT NOT NULL,  -- sub claim from either provider
    email       TEXT UNIQUE NOT NULL,
    ...
    UNIQUE(provider, provider_id)
);

-- Option C: Separate user_identities table (one user, multiple providers)
CREATE TABLE user_identities (
    user_id     TEXT NOT NULL REFERENCES users(id),
    provider    TEXT NOT NULL,  -- 'google' | 'apple'
    provider_id TEXT NOT NULL,  -- sub claim
    PRIMARY KEY (provider, provider_id)
);
-- users table loses google_id entirely
```

**Trade-offs:**
- **Option A** is simplest migration (just add a column, relax NOT NULL on google_id), but doesn't scale to a third provider.
- **Option B** is clean but breaks the "same user, two providers" linking case.
- **Option C** is the most flexible (one user can have both Google and Apple linked) but adds a JOIN to every auth lookup.

### 2. Account Linking — Same email, different providers?

If someone signs up with Google (gmail), then later uses "Sign in with Apple" with the same email — same user or different?

- Apple's private relay emails make matching by email unreliable (user may hide their real email).
- Options:
  - **Match by email**: If Apple provides the same email → link to existing user. If relay email → create new user.
  - **Never auto-link**: Each provider creates a separate account. User must explicitly link in settings.
  - **Prompt on collision**: "An account with this email exists via Google. Link it?"

### 3. Frontend UX — Provider Choice

```
┌──────────────────────────────┐
│         Sign In              │
│                              │
│  ┌────────────────────────┐  │
│  │  Continue with Google  │  │
│  └────────────────────────┘  │
│                              │
│  ┌────────────────────────┐  │
│  │  Continue with Apple   │  │
│  └────────────────────────┘  │
│                              │
└──────────────────────────────┘
```

Current `LoginButton` is a simple text link → `window.location.href = /v1/auth/login`. Would need to become a chooser (modal, page, or inline buttons).

Alternatively: keep the current button as "Sign In" and make `/auth/login` a page with both options (server-rendered, no JS needed for the redirect).

### 4. Apple's "Name Only on First Auth" Quirk

Apple only sends the user's name in the **first** authorization callback (via POST form body as a JSON-encoded `user` field). If you miss capturing it, you can never get it again without the user revoking and re-authorizing in their Apple ID settings.

**Implication:** The callback handler MUST parse and persist `request.form["user"]` on the very first login. On subsequent logins, Apple only sends the ID token (no name, no email in the form body — only in the token claims).

### 5. Apple Client Secret — ES256 JWT Generation

Unlike Google's static client secret, Apple requires you to generate a short-lived JWT as your client secret:

```python
# Pseudo-code for Apple client secret generation
import jwt, time

headers = {"kid": APPLE_KEY_ID, "alg": "ES256"}
payload = {
    "iss": APPLE_TEAM_ID,
    "iat": int(time.time()),
    "exp": int(time.time()) + 86400 * 180,  # max 6 months
    "aud": "https://appleid.apple.com",
    "sub": APPLE_CLIENT_ID,  # your Services ID
}
client_secret = jwt.encode(payload, APPLE_PRIVATE_KEY, algorithm="ES256", headers=headers)
```

**Config needed:**
- `apple_client_id` (Services ID, e.g., `com.atelier-marie.auth`)
- `apple_team_id` (10-char Apple Developer Team ID)
- `apple_key_id` (Key ID from Apple Developer portal)
- `apple_private_key` (ES256 `.p8` file contents — SENSITIVE)
- `apple_redirect_uri`

### 6. Apple's POST Callback

Apple sends the callback as a **POST** (not GET like Google). The `code` and `state` come in the form body, not query params. The `/v1/auth/callback` route needs to handle both methods, or Apple needs its own callback endpoint.

```
GET  /v1/auth/callback?code=...&state=...     ← Google
POST /v1/auth/callback  (form: code, state, user)  ← Apple
```

### 7. The Relay Email Problem

If a user picks "Hide my email" with Apple, they get `<random>@privaterelay.appleid.com`. This means:
- You CAN still email them (Apple forwards to their real inbox if you register your sending domain)
- You CANNOT match this to an existing Google account by email
- Order confirmation emails would show the relay address in the `customer_email` field

**Apple email relay forwarding requires:**
1. Register your outbound email domains in Apple Developer portal
2. Set up SPF/DKIM for those domains
3. Apple verifies and enables forwarding

## Risks / Concerns

- **Complexity vs. user pool**: This is a family candle business. How many users actually need Apple auth? If the answer is "the owner has an iPhone and wants convenience," a simpler path might be sufficient.
- **Apple Developer Program**: Requires $99/year enrollment + app/service registration. Already enrolled?
- **Migration**: Changing `google_id NOT NULL` to nullable or a new schema requires a careful migration of existing user rows.
- **Testing surface area**: Apple OAuth is notoriously hard to test locally (no localhost redirect URIs without workarounds, no easy way to get test tokens).
- **Account deletion webhook**: Apple requires apps to support account deletion notifications. If a user deletes their Apple ID or revokes your app, Apple sends a server-to-server notification that you must handle.

## Open Questions

1. **Is this for all users or mainly the admin/owner?** (Family member with Apple device wanting convenience?)
2. **Account linking strategy?** (Same email = same user? Or always separate?)
3. **Apple Developer enrollment status?** (Already have Team ID, Services ID, Key?)
4. **Relay email policy?** (Allow hidden emails? Require real email for order confirmations?)
5. **Endpoint structure?** (Shared `/auth/callback` with method detection, or separate `/auth/google/callback` + `/auth/apple/callback`?)
6. **DB migration approach?** (Add column? Restructure to provider-agnostic?)
