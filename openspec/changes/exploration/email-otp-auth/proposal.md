# Email OTP Authentication

## Summary

Add email + OTP (one-time passcode) as an alternative authentication method so customers who don't have or don't want to use Google can still create accounts and access order history.

## Motivation

- Not all customers have Google accounts (or want to use them for shopping)
- Bulgaria-based customer base may prefer email-based login
- No passwords to store = lower security burden than traditional signup
- Builds email infrastructure that's needed anyway (order confirmations, shipping updates)
- Feels modern/premium — used by Notion, Linear, many luxury DTC brands

## Proposed Flow

```
User enters email → POST /v1/auth/otp/request
       │
       ▼
Backend generates 6-digit numeric code (10–15 min TTL, max 5 attempts)
Sends email via transactional service (Resend recommended)
       │
       ▼
User reads code from inbox, types it → POST /v1/auth/otp/verify
       │
       ▼
Backend validates code → upsert user → issue JWT
(Same downstream as Google OAuth from here — session linked, cart preserved)
```

## Frontend UX

```
┌──────────────────────────────────┐
│          Sign In                 │
│                                  │
│  ┌────────────────────────────┐  │
│  │   Continue with Google     │  │
│  └────────────────────────────┘  │
│                                  │
│  ─────────── or ───────────────  │
│                                  │
│  ┌────────────────────────────┐  │
│  │   Email: [____________]    │  │
│  │   [Send me a code]        │  │
│  └────────────────────────────┘  │
│                                  │
│  (after code sent)               │
│  ┌────────────────────────────┐  │
│  │   Code: [_ _ _ _ _ _]     │  │
│  │   [Verify]                 │  │
│  │                            │  │
│  │   Didn't get it? Resend    │  │
│  └────────────────────────────┘  │
│                                  │
└──────────────────────────────────┘
```

## Prerequisites

### 1. Email Sending Infrastructure (does not exist today)

- **Service choice:** Resend (100/day free tier, simple API, good deliverability)
- **DNS:** SPF + DKIM + DMARC records for sending domain
- **Config:** API key, sender address, sender name
- **Note:** This also unblocks order confirmation emails, shipping notifications, etc.

### 2. DB Schema Migration

Current `users.google_id TEXT UNIQUE NOT NULL` blocks non-Google users entirely. Two options:

**Option A — Minimal (add column, relax constraint):**
```sql
-- google_id becomes nullable
-- add auth_method column
ALTER TABLE users ADD COLUMN auth_method TEXT NOT NULL DEFAULT 'google';
-- Make google_id nullable (requires table rebuild in SQLite)
```

**Option B — Provider-agnostic (recommended if Apple auth also planned):**
```sql
CREATE TABLE user_identities (
    user_id     TEXT NOT NULL REFERENCES users(id),
    provider    TEXT NOT NULL,  -- 'google' | 'email_otp' | 'apple'
    provider_id TEXT NOT NULL,  -- google sub, email address, apple sub
    PRIMARY KEY (provider, provider_id)
);
-- users table loses google_id, keeps email as display/contact field
```

Option B aligns with the Apple auth exploration already in `openspec/changes/apple-auth/`.

## Security Design

| Concern | Mitigation |
|---------|-----------|
| Brute force | Max 5 attempts per code, then invalidate |
| Mailbombing | Max 3 OTP requests per email per 10 minutes |
| Code TTL | 10–15 minutes, then expired |
| One-use | Code marked `used_at` on first successful verify |
| Timing attacks | `hmac.compare_digest` for code comparison |
| Email enumeration | Always respond "code sent" regardless of whether email exists |
| Replay | Code invalidated immediately after use |

## New DB Table

```sql
CREATE TABLE auth_codes (
    id          TEXT PRIMARY KEY,
    email       TEXT NOT NULL,
    code        TEXT NOT NULL,
    expires_at  TEXT NOT NULL,
    attempts    INTEGER DEFAULT 0,
    used_at     TEXT,
    created_at  TEXT NOT NULL
);

CREATE INDEX idx_auth_codes_email_active
    ON auth_codes(email, expires_at)
    WHERE used_at IS NULL;
```

## New Endpoints

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/v1/auth/otp/request` | POST | None | Request OTP code (body: `{email}`) |
| `/v1/auth/otp/verify` | POST | None | Verify OTP code (body: `{email, code}`) |

## What This Unlocks

- Non-Google customers can create accounts
- Order history across devices for anyone with email
- Foundation for order notification emails (shared email infra)
- Provider-agnostic schema sets up Apple auth later
- "Resend code" pattern reusable for email verification flows

## What This Doesn't Solve

- Users who won't give email at all (but anonymous checkout still works)
- Real-time auth (always an email delivery delay, typically <10s)
- SMS OTP (different infra, not proposed here)

## Relationship to Other Changes

- **`apple-auth/`** — shares the DB schema migration (Option B serves both)
- **Order notifications** — shares email sending infrastructure
- **`core-ecommerce/`** — auth endpoints follow same patterns (JWT, session linkage)

## Open Questions

1. **Email service:** Resend vs Postmark vs SendGrid? (Leaning Resend for simplicity)
2. **Schema migration:** Option A (minimal) or Option B (provider-agnostic)? Depends on whether Apple auth is still planned
3. **Account linking:** If someone uses Google with `foo@gmail.com` then later does email OTP with same address — same user? Auto-link? Prompt?
4. **Email template:** Plain text or branded HTML? (Plain is faster to ship, HTML looks more professional)
5. **Priority:** Build email infra first as standalone (also serves order notifications), then layer OTP on top?

## Rough Build Sequence

1. Email service setup (Resend, DNS records, verify sending works)
2. DB migration (schema change — pick Option A or B)
3. `POST /v1/auth/otp/request` + rate limiting
4. `POST /v1/auth/otp/verify` + user upsert + JWT issuance
5. Frontend: provider chooser UI (Google + email)
6. Frontend: email input → code input form
7. Edge case tests (expired, max attempts, resend, account linking)

## Status

**Parked** — captured for future implementation. No immediate timeline.
