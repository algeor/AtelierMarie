## 1. Dependencies & Configuration

- [x] 1.1 Add `jinja2` (core) to `pyproject.toml`; for ZeptoMail either add the `zeptomail` SDK **or** use a thin `httpx` POST (httpx already present — no new dep). Console provider never imports the sender lib.
- [x] 1.2 Email settings in `app/config.py` already exist; reconcile `email_from_address` default (`orders@example.invalid` → `orders@theateliermarie.com`, root-domain alias), `email_provider` Literal to `["console", "zeptomail"]`, `email_reply_to` default `contacts@theateliermarie.com`, and use `EmailStr` for addresses + `SecretStr` for `email_api_key`
- [x] 1.3 Add production validation for email settings (warn if zeptomail provider but no API key)
- [x] 1.4 Add `zeptomail_webhook_auth_key: SecretStr` to `app/config.py` + `.env.example` (required for the webhook endpoint — follow-up)
- [x] 1.5 Define `EmailEvent` Literal + `STATUS_TO_EMAIL_EVENT` map in `app/constants.py` (single source; `pending→placed`, `confirmed→None`)
- [x] 1.6 Move carrier URL patterns into `app/constants.py` (used by service + validation + frontend dropdown — NOT pydantic Settings)

## 2. Database Schema — Tracking Fields, Locale, Email Log

- [x] 2.1 Add `tracking_number`, `tracking_carrier`, `tracking_url` columns to orders — via `_add_column_if_missing()` in `_migrate_existing_schema` **and** in the `CREATE TABLE orders` block of `_SCHEMA_SQL` (SQLite has no `ADD COLUMN IF NOT EXISTS`; see `preferred_locale` precedent at `database.py:329`)
- [x] 2.2 Add carrier URL pattern mapping (speedy, econt, dhl, fedex) in `app/constants.py` (per task 1.6)
- [x] 2.3 Write tests for tracking URL auto-generation from carrier + number
- [x] 2.4 Add `locale TEXT NOT NULL DEFAULT 'en'` column to orders (same migrate-path + `_SCHEMA_SQL` approach); snapshot session `preferred_locale` onto the order in the checkout service (value already read at `orders.py:59-63`; add `locale` to the INSERT + `OrderData`)
- [x] 2.5 Create `order_emails` table (order_id, event, recipient, status, reason, sent_at) in `_SCHEMA_SQL`, with index on order_id **and a partial UNIQUE index `(order_id, event) WHERE status='sent'`**; create `order_email_send_claims` keyed by `(order_id, event)` for in-flight coordination
- [x] 2.5a Add outbox columns to `order_emails` for durable retry (design Decision 25): `attempts INTEGER NOT NULL DEFAULT 0`, `next_attempt_at TEXT`; extend the `status` set with `queued` (intent written, not yet sent) and `failed_permanent` (terminal — poison message / MAX attempts, minimal dead-letter)
- [x] 2.6 Write test: order created with locale "bg" persists `orders.locale = "bg"`

## 3. Order Status API — Tracking Support

- [x] 3.1 Update `UpdateOrderStatusRequest` model to include optional `tracking_number`, `tracking_carrier`, `tracking_url` fields
- [x] 3.2 Add validation in the **service layer** (not a Pydantic validator): tracking_number and tracking_carrier required when status="shipped" → raise a custom exception translated to 422 `TRACKING_REQUIRED` inline (like `InvalidStateTransitionError` at `admin.py:420`)
- [x] 3.3 Extend `update_status()` signature + `UPDATE` (currently `order_service.py:446`, writes only status) to persist tracking fields and auto-generate tracking_url from known carriers
- [x] 3.4 Update `OrderResponse` model to include tracking_number, tracking_carrier, tracking_url (nullable)
- [x] 3.5 Update `_fetch_order_with_items()` to include tracking fields in returned OrderData
- [x] 3.6 Write tests for shipped-with-tracking, shipped-without-tracking (rejected), and tracking URL auto-generation

## 4. Email Provider Abstraction

- [x] 4.1 Create `app/email/__init__.py`
- [x] 4.2 Create `app/email/providers/__init__.py` with `EmailProvider` Protocol (method: `send(to, subject, body, reply_to, tags)`)
- [x] 4.3 Implement `app/email/providers/console_provider.py` — logs email to structlog, no network
- [x] 4.4 Implement `app/email/providers/zeptomail_provider.py` — sends via the ZeptoMail HTTP API (EU host) as an `httpx` POST (or the `zeptomail` SDK); tracking disabled; no idempotency key (ZeptoMail has none — DB index is the guard)
- [x] 4.5 Create provider factory function: returns provider based on `settings.email_provider`
- [x] 4.6 Write tests for console provider (verify log output) and ZeptoMail provider (mock the HTTP call / SDK)

## 5. Template Renderer

- [x] 5.1 Create `app/email/renderer.py` with Jinja2 Environment (**`autoescape=False`** for `.txt`) + FileSystemLoader pointing to templates dir
- [x] 5.2 Implement `render_template(event, locale, context)` → `(subject, body)` with first-line-is-subject parsing
- [x] 5.3 Implement locale fallback (missing BG → try EN → log error if both missing)
- [x] 5.4 Write tests for template rendering: variable interpolation, loops, conditionals, locale fallback, **both-templates-missing → skip + error log**, and `autoescape=False` (e.g. `Ben & Co` stays literal)

## 6. Email Templates (Plain Text)

- [x] 6.1 Create `app/email/templates/en/order_placed.txt` — greeting, item list, total, "we'll notify you when it ships"
- [x] 6.3 Create `app/email/templates/en/order_shipped.txt` — tracking carrier, number, URL
- [x] 6.4 Create `app/email/templates/en/order_delivered.txt` — "your order has arrived, enjoy!"
- [x] 6.5 Create `app/email/templates/en/order_cancelled.txt` — cancellation notice + refund being processed
- [x] 6.6 Create `app/email/templates/en/admin_new_order.txt` — order summary, customer info, admin link
- [x] 6.7 Create `app/email/templates/bg/order_placed.txt`
- [x] 6.9 Create `app/email/templates/bg/order_shipped.txt`
- [x] 6.10 Create `app/email/templates/bg/order_delivered.txt`
- [x] 6.11 Create `app/email/templates/bg/order_cancelled.txt` — includes refund-being-processed line

_(No order_confirmed templates — confirmed transition sends no customer email, per design Decision 9.)_

## 7. Email Service (Orchestration)

- [x] 7.1 Create `app/services/email_service.py` with `send_order_email(to, order_id, event, locale, context)` function
- [x] 7.2 Implement context builder: `_build_email_context(order_data, locale)` — converts cents to display prices, formats items
- [x] 7.3 Implement `send_admin_alert(order_data)` for new-order notification to owner
- [x] 7.4 Add comprehensive error handling: catch all provider/render exceptions, log, never raise
- [x] 7.5 Write tests for email service using an in-memory `RecordingProvider` double (assert subject/body/absence of List-Unsubscribe); verify template/locale selection and context building
- [x] 7.6 Select template locale from `orders.locale` (fresh DB read in the sweeper's send path), never from the acting session
- [x] 7.7 Idempotency via DB send claims plus the partial UNIQUE index: acquire an `in_flight` claim before sending; skip/log `skipped_in_flight` if another worker's sweeper owns an unexpired claim; skip/log `skipped_duplicate` if a successful send is already recorded; insert the `sent` row only after provider success
- [x] 7.8 Update the `order_emails` row to its terminal/attempt state (sent/failed/failed_permanent/skipped_duplicate/skipped_in_flight/skipped_suppressed, with `reason`) inside the send path; bind `order_id`+`event` on all logs (request_id is unavailable outside the request — Decision 22); catch logging failures so they never propagate
- [x] 7.9 Ensure the send path opens its own `with get_db()` connection (it runs in the sweeper loop, not a request)
- [x] 7.10 Write tests: concurrent duplicate-event (two sweepers / two workers) → one email, locale-from-order (admin locale differs from customer), transient provider error → `failed` row stays retryable + attempts incremented, permanent error / MAX attempts → `failed_permanent` + admin alert, log rows written

## 8. Route Integration (durable outbox write)

- [x] 8.1 In `create_order` (`app/routes/orders.py`), within the checkout transaction, insert `order_emails` rows with `status='queued'` for the customer `placed` email **and** the `admin_new_order` email — same `BEGIN/COMMIT` as the order, so the intent survives any crash (design Decision 25). No `BackgroundTasks`.
- [x] 8.2 Derive the customer event as `event="placed"` (map `pending`→`placed` via `STATUS_TO_EMAIL_EVENT`; NOT `event="pending"`) when writing the queued row
- [x] 8.3 In `admin_update_order_status` (`app/routes/admin.py`), after a successful transition, insert a `queued` `order_emails` row in the same transaction as the status `UPDATE`
- [x] 8.4 Compute the event via `STATUS_TO_EMAIL_EVENT[new_status]`; write no row when the map returns `None` (confirmed)
- [x] 8.5 Locale is not passed by the route — the sweeper's send path reads `orders.locale` on its own fresh DB read (7.6); the admin route never passes a session locale
- [x] 8.6 Write a `tests/realapp/` integration test (real middleware + real DB, RecordingProvider): checkout and ship write `queued` rows in the order transaction; drive one sweeper tick and assert the email side-effect succeeded and rows reach `sent` — proving the send path read the DB on its own connection

## 8b. Sweeper Loop (delivery guarantee)

- [x] 8b.1 Add `email_outbox_loop()` in `app/main.py` — a clone of `session_cleanup_loop` (`main.py:26`): `while True: await sleep(~15s); drain_email_outbox()`, swallowing/logging all exceptions so the loop never dies
- [x] 8b.2 Register the loop as an `asyncio.create_task` in `lifespan` alongside the session-cleanup task; cancel + await it on shutdown (same pattern as `main.py:59-64`)
- [x] 8b.3 Implement `drain_email_outbox()`: `SELECT` rows `WHERE status IN ('queued','failed') AND (next_attempt_at IS NULL OR next_attempt_at <= now) AND attempts < MAX`; for each, run the send path (7.6–7.9 — acquire claim, render, send)
- [x] 8b.4 On transient failure (5xx/timeout): increment `attempts`, set `next_attempt_at` via exponential backoff, leave status retryable (`failed`)
- [x] 8b.5 On permanent failure (4xx/render error) or `attempts` reaching MAX: set `status='failed_permanent'` and emit an admin alert (structured error log at minimum; queue an `admin_new_order`-style alert if the failure is itself an email is out of scope — log it)
- [x] 8b.6 Write tests (can call `drain_email_outbox()` directly, no real loop): queued row → sent; provider down for N ticks then recovers → eventually sent, no duplicate; MAX attempts → `failed_permanent` + alert; two concurrent drains (simulating 2 workers) → one provider call via the claim

## 9. Frontend — Order Tracking Display

- [x] 9.1 Update `OrderResponse` TypeScript type in `frontend/lib/types.ts` to include tracking fields
- [x] 9.2 Display tracking info (carrier, number, link) on order detail page when status is shipped/delivered
- [x] 9.3 Add tracking section to order status timeline component
- [x] 9.4 Update `frontend/lib/mock-api.ts` (`createOrder`, `mockOrders`, status-update) with tracking fields so the new UI works in mock mode (dual mock/real parity)

## 10. Frontend — Admin Shipping Form

- [x] 10.1 Expand admin order status update form: show tracking fields when "shipped" is selected
- [x] 10.2 Add carrier dropdown (Speedy, Econt, DHL, FedEx, Other)
- [x] 10.3 Auto-generate tracking URL preview when carrier + number entered
- [x] 10.4 Validate tracking_number required before allowing ship submission
- [x] 10.5 Write frontend tests for shipping form behavior

## 11. Deliverability

- [x] 11.1 ZeptoMail provider: disable open/click tracking on every send
- [x] 11.2 (No provider idempotency key — ZeptoMail offers none; duplicate suppression is the `order_emails` UNIQUE index, task 7.7)
- [x] 11.3 Verify Cyrillic subject headers are RFC 2047 encoded-words (add a round-trip test)
- [x] 11.4 (Format validation already satisfied by `EmailStr` at `models/orders.py:46`) — optional: add typo/MX check on common-domain typos
- [x] 11.5 Add `POST /v1/webhooks/zeptomail` (hard_bounce/soft_bounce/fbl_complaint): verify ZeptoMail's `producer-signature` HMAC-SHA256 (`ts`/`s`/`s-algorithm`) over the **raw body** using `zeptomail_webhook_auth_key`, **reject stale timestamps** (replay), `hmac.compare_digest`; add path to `session_skip_paths`; mount outside admin router
- [x] 11.6 Create `suppressed_emails` store; skip + log (`skipped_suppressed`) sends to suppressed addresses
- [x] 11.7 Write tests: invalid-signature 401/403, stale-timestamp replay rejected, raw-body verification, hard-bounce suppression, duplicate-bounce idempotent, suppressed-address send skipped
- [x] 11.8 Ensure no `List-Unsubscribe` header is added to transactional mail
- [x] 11.9 (Ops, no code) Root-domain sending identity: ZeptoMail **DKIM TXT** (selector `19154433`, Default) + **bounce CNAME** (`bounce-zem → cluster89.zeptomail.eu`, carries SPF/return-path — no root-SPF merge) + **DMARC** (`_dmarc` TXT, `p=none`) + EU DC + Postmaster Tools + ZeptoMail DPA — documented in proposal prerequisites & EMAIL_SETUP.md
- [x] 11.10 (Ops, post-launch, no code) **DMARC progression:** keep `_dmarc` at `p=none` and watch the aggregate reports (rua → `contacts@`) for 2–4 weeks; confirm the only sending sources are Zoho (replies) + ZeptoMail (order mail); then tighten `p=none` → `p=quarantine` → `p=reject`. (This is what clears the MXToolbox "Quarantine/Reject not enabled" flag — intentionally not done at launch.)
- [x] 11.11 (Ops, no code) Confirm the **Zoho DKIM** selector (`dkim._domainkey`) shows **verified** in the Zoho console so replies sent from the `contacts@` inbox are DKIM-signed.
- [x] 11.12 (Ops, optional/cosmetic, no code) Delete the duplicate `zoho-verification` TXT record at the root. **BIMI is intentionally deferred** (requires DMARC `p=reject` + a VMC certificate ~$1k/yr) — revisit only if a brand logo in the inbox is wanted. The MXToolbox `http` "not resolved" flag is expected until a website is pointed at the domain — unrelated to email.

## 12. Auditability & GDPR

- [x] 12.1 Add `GET /v1/admin/orders/{id}/emails` (admin-gated) to read the `order_emails` audit trail for an order
- [x] 12.2 Extend the GDPR erasure job to scrub/anonymize `order_emails.recipient` (join by `order_id` to erased orders) and age out `suppressed_emails`
- [x] 12.3 Add a log-redaction decision for the console/structlog output: never log full bodies in production; log a hashed/truncated recipient
- [x] 12.4 Update CLAUDE.md app structure docs to include the new `app/email/` package and note `.txt` templates rely on a source checkout (or add `package-data`)
