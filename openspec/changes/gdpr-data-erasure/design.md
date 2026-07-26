## Context

AtelierMarie is anonymous-first: identity is a session cookie, and checkout works without login.
PII therefore spreads across records keyed three different ways — `session_id` (anonymous),
`user_id` (logged in), and raw `customer_email` (order snapshots). A single data subject may appear
under all three. The existing `app/services/gdpr_service.py` only scrubs `order_emails.recipient`
and is never called.

Two legal duties collide:
- **Art. 17 (erasure):** on request, remove the subject's personal data without undue delay.
- **Art. 6(1)(c) + Art. 5(1)(e) (legal obligation / storage limitation):** invoice and order data
  must be retained for the statutory tax/accounting window, then must not be kept longer.

Constraints (from CLAUDE.md): Layer 1 only, SQLite only, no Layer 2 imports. `order_items` rows are
**immutable snapshots** (product name + price at purchase) and are intentionally not FK-joined to
products. `idx_order_emails_sent_unique` is a partial unique index on `(order_id, event)` where
`status='sent'`.

## Goals / Non-Goals

**Goals:**
- One `erase_data_subject(...)` service operation that resolves a subject across `session_id`,
  `user_id`, and `email`, then removes PII everywhere it lives in Layer 1.
- NULL-ification/placeholder during the retention window; hard-delete of orders only after it.
- Admin-triggered endpoint + a scheduled retention sweep, both thin wrappers over the service.
- Deterministic, idempotent, transactional erasure that leaves order structure + financials intact.

**Non-Goals:**
- Subject access/portability export (Art. 15/20) — separate change.
- Public self-service erasure UI — separate change.
- Any Layer 2 / analytics erasure (no Layer 2 code exists yet).
- Schema migrations — PII is overwritten in place; no new columns required.

## Decisions

### Decision 1 — Erasure = NULL-ification, hard-delete only after retention window
On an erasure request, order PII (`customer_email`, `customer_name`, `delivery_details`, `notes`) is
overwritten with an `[erased]` placeholder / NULL on **all** of the subject's matched orders,
**regardless of age** — scrubbing PII is always safe. `total_cents`, `status`, and `order_items` are
preserved. The retention **window governs hard-delete only**: a separate sweep hard-deletes orders
once `created_at` is older than `data_retention_years`.

Hard-delete must remove **all three** FK children of `orders(id)` before the order row, because
`PRAGMA foreign_keys=ON` (`database.py:395`) enforces the constraint:
`order_emails`, `order_email_send_claims`, and `order_items` — children first, order row last.

*Why:* satisfies Art. 17 immediately (PII gone) without breaching Art. 6(1)(c) (financial record
kept for tax law). Matches CLAUDE.md's stated GDPR approach ("NULL-ification of PII fields, not
cascade delete"). *Alternative rejected:* immediate hard-delete on request — breaches the retention
obligation and destroys financial audit trail.

### Decision 2 — Subject resolution by (email, user_id, session_id), any subset
The service accepts any combination of identifiers and unions the matched records: `orders` by
`customer_email` OR `user_id` OR `session_id`; `comments` by `user_id` OR `session_id`;
`contact_messages` by `email`; `users` by `id` OR `email`; `order_emails` by resolved order.

*Why:* anonymous-first means one person's data is keyed inconsistently; erasure must catch all of it,
including contact-form submissions keyed only by raw email. *Alternative rejected:* email-only —
misses anonymous orders/comments placed before any email was captured, and misses the reverse
(session with no order email).

### Decision 2b — `users` PII uses per-subject unique placeholders, not NULL or a constant
`users.email` and `users.google_id` are `UNIQUE NOT NULL` (`database.py:48-49`). They can be neither
NULLed (violates NOT NULL) nor set to a shared `[erased]` constant (the UNIQUE index collides on the
second erased user). Erasure therefore writes **per-subject unique** values derived from the row id:
`email = 'erased-' || id || '@invalid'`, `google_id = 'erased-' || id`. `name` and `avatar_url` are
nullable → set NULL. Idempotent re-runs match the `users` row by **`id`** (the email is already
scrubbed), not by email.

### Decision 2c — Erasure does NOT delete the suppression record
`suppressed_emails` is the do-not-contact list for hard bounces / complaints; deleting a subject's
entry on an erasure request risks **re-contacting** them and destroys the record that lets us honor
their objection (GDPR Recital 65; Art. 21 permits retaining minimal data to enforce a suppression).
Erasure therefore **leaves `suppressed_emails` in place** (the address may optionally be stored
hashed). Bounded retention is handled by the sweep's `age_out_suppressed_emails`, not by erasure.

### Decision 3 — `comments` are hard-deleted, not anonymized
Comment `body` is free text that may itself contain PII; there is no retention obligation on it.
Delete the rows outright. *Alternative rejected:* NULL the `display_name`/`body` — leaves orphaned
empty threads and still risks PII residue in `body`.

### Decision 3b — Session-keyed pseudonymous data is deliberately out of scope
`reactions`, `reaction_toggle_log`, and `cart_items` are keyed only by `session_id` and hold no
free text or contact detail (low re-identification risk, Recital 30). `cart_items` and expired
sessions are already cleared by existing cleanup. Erasure does not touch them; this is an explicit
scope decision, not an omission. If a future request requires it, clearing by `session_id` is trivial
to add.

### Decision 4 — Single transaction per erasure, idempotent
All writes for one erasure run inside one `BEGIN`/`COMMIT`. Placeholder writes are guarded with
`WHERE <field> != '[erased]'` so re-running is a no-op. The sweep is a separate transaction.

*Why:* partial erasure is worse than none (leaves PII while reporting success). Idempotency lets an
admin safely retry.

### Decision 5 — Sweep wired into the existing cleanup loop
Extend `cleanup_runtime_records()` in `app/main.py` to also call the retention sweep, reusing the
hourly `session_cleanup_loop`. No new scheduler.

*Why:* one background task already exists and is battle-tested; adding a second loop is needless.

## Risks / Trade-offs

- **Over-erasure of a shared session** → session_id is per-browser, so a shared device could link
  two people. Mitigation: require **email or user_id** as the primary identifier for admin-triggered
  erasure; session_id is only unioned in when tied to a resolved subject.
- **Hard-delete cascade ordering** → `PRAGMA foreign_keys=ON`, and `orders(id)` has **three** FK
  children (`order_emails`, `order_email_send_claims`, `order_items`). Deleting the order first
  violates the constraint. Mitigation: delete all three children first, order row last, in one
  transaction.
- **`users` UNIQUE NOT NULL** → email/google_id cannot be NULLed or set to a shared constant.
  Mitigation: per-subject unique placeholders (Decision 2b); re-run matches by `id`.
- **`idx_order_emails_sent_unique` conflict** → erasure only rewrites `recipient`, never `status`,
  so the partial unique index is untouched. Hard-delete removes the row entirely — also safe.
- **Retention window too short/long** → configurable `data_retention_years`; document the chosen
  value with the DPO. Default conservative (e.g. keep for statutory period).
- **Not legal advice** → the retention period is a legal determination; the code makes it a config
  knob, it does not decide the number.

## Migration Plan

No schema migration. Deploy is additive: new service functions, one new admin route, one config
field, and the sweep call in the cleanup loop. Rollback = revert the code; no data shape changed.
On first deploy the sweep will act on any already-past-window orders — confirm the retention value
before enabling.

## Open Questions

- Exact `data_retention_years` value (legal input needed — likely the Bulgarian statutory
  accounting-record period).
- Should admin erasure also revoke/rotate the subject's active sessions immediately? (Leaning yes —
  delete `sessions` rows for the resolved `user_id`.)
