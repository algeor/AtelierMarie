## Context

AtelierMarie is a luxury candle e-commerce platform running on FastAPI + SQLite (Layer 1). Orders follow a state machine: pending → confirmed → shipped → delivered (with cancellation from pending/confirmed). The admin updates order status via `PATCH /v1/admin/orders/{order_id}/status`. Customer email is collected at checkout. Sessions track a `preferred_locale` (en/bg).

Currently there is no email infrastructure — no transactional emails, no admin alerts, no shipping notifications. The order service is purely synchronous with no background task usage.

## Goals / Non-Goals

**Goals:**
- Send transactional emails on every order state transition (placed, confirmed, shipped, delivered, cancelled)
- Notify the shop owner when a new order arrives
- Support bilingual templates (EN/BG) based on customer locale
- Add tracking information (number, carrier, URL) to the shipped transition
- Never degrade the order flow — email failures are silent
- Keep the email system testable without network access (console provider)

**Non-Goals:**
- HTML rich email templates (deferred — plain text first)
- Retry queues or dead-letter mechanisms
- Email preference management / unsubscribe flows
- Marketing emails (abandoned cart, promotions)
- Multiple admin notification recipients
- Webhook-based delivery tracking from ZeptoMail (only bounce/complaint consumed, in the follow-up)
- Domain registration (separate prerequisite, does not block code)

## Decisions

### 1. Zoho ZeptoMail (EU) as Email Provider (over Zoho Mail SMTP / Gmail SMTP / Resend)

**Choice:** Zoho **ZeptoMail** in the **EU data center**, via its HTTP API (see Decision 24 for API-vs-SMTP)

**Rationale:**
- Purpose-built transactional service — not a repurposed mailbox. The shop's `contacts@theateliermarie.com` inbox is on Zoho Mail, but a mailbox is not a sender.
- **EU data residency:** ZeptoMail EU keeps sending/processing data in-region, matching the `zoho.eu` mailbox. (Resend sends from the EU but stores account data in the US — a GDPR wrinkle this avoids.)
- Pay-as-you-go with no daily cap: free 10k-email credit, then ~€2.50 / 10k (credits valid 6 months). Simpler and cheaper at this volume than Resend's 100/day free + $20/mo Pro.
- Bounce / spam-complaint **webhooks** (hard/soft bounce, feedback-loop) feed the suppression store.
- One vendor for both the human mailbox and transactional sending.

**Alternatives rejected:**
- **Zoho Mail SMTP** (`smtppro.zoho.com`): needs a paid Mail plan for SMTP access, is rate-limited for human sending, and couples the store's sending reputation to the `contacts@` inbox — the exact reputation risk this change avoids.
- **Gmail SMTP:** unreliable, unprofessional from-address, no feedback loops, revocable.
- **Resend:** viable and originally chosen, but US account-data residency and a two-vendor split; superseded once the Zoho mailbox made ZeptoMail the natural fit.

### 2. Jinja2 for Template Rendering (over string.Template / f-strings)

**Choice:** Jinja2 as an explicit dependency in `pyproject.toml`

**Rationale:**
- Need loops (item lists), conditionals (tracking only when shipped), filters
- Templates as separate `.txt` files — editable without touching Python code
- Industry standard, well-documented, tiny footprint
- NOT a transitive dep of FastAPI (verified: `import jinja2` fails in current venv)

**Alternatives rejected:**
- `string.Template`: no loops, can't iterate order items
- f-strings inline: unmaintainable with 10+ templates × 2 locales

### 3. FastAPI BackgroundTasks for Async Dispatch (over task queue / inline)

**Choice:** `BackgroundTasks.add_task()` — fire-and-forget after response

**Rationale:**
- Zero new infrastructure (no Redis, no Celery, no worker process)
- HTTP response returns immediately; email sends in background
- Sufficient for low volume (5-50 orders/day)
- Matches the project philosophy: simple, single-VPS deployment

**Alternatives rejected:**
- Inline (blocking): adds 200-500ms to every status change API call
- Celery/RQ: massive infrastructure overhead for ~20 emails/day
- asyncio task: harder to test, risk of lost tasks on shutdown

**Connection lifetime caveat:** The background task runs *after* the HTTP response, by which point the request's `with get_db()` context manager has already committed and closed its connection (routes use an inline `with get_db() as conn:`, e.g. `orders.py:57`, `admin.py:413`, not `Depends`). The task therefore MUST open its own connection (`with get_db() as conn:`) inside the background function to do its fresh read — it cannot capture and reuse the request-scoped connection. The task receives only plain values (order_id, event, locale) as arguments, never a live connection or ORM object. `get_db()` opens a fresh `sqlite3.connect` per call (`database.py:411`), so a background-thread read is safe.

_Note (corrected): a captured-connection bug does **not** pass-in-tests-but-fail-in-prod. The async test client (httpx `ASGITransport`) drives the full ASGI cycle including background tasks, and the route's `with` block closes the connection before the task runs in tests too — so the bug fails in tests as well. Open a fresh connection because it is correct, not because tests would otherwise miss it._

### 4. Provider Abstraction via Protocol Class

**Choice:** `EmailProvider` Protocol with `send()` method; implementations: `ZeptoMailProvider`, `ConsoleProvider`

**Rationale:**
- Console provider enables testing without network
- Swapping providers requires one new file + config change
- Protocol (not ABC) — structural typing, no inheritance required

### 5. Template File Format: Subject-in-First-Line

**Choice:** Each `.txt` template has subject on line 1, blank line separator, then body

**Rationale:**
- Subject and body co-located (one file per email type per locale)
- No separate subject mapping file to maintain
- Simple to parse: `rendered.split("\n", 1)`
- Easy for non-developers to edit

### 6. Tracking Data on Orders Table (over separate table)

**Choice:** Add `tracking_number`, `tracking_carrier`, `tracking_url` columns directly to `orders`

**Rationale:**
- One-to-one relationship (one shipment per order at this scale)
- Avoids join complexity for a simple read
- Required when `status = "shipped"`, NULL otherwise
- Carriers: Speedy, Econt, DHL, FedEx, plus freeform "other"

**Alternatives rejected:**
- Separate `shipments` table: over-engineering for single-shipment orders
- JSON blob column: loses queryability

### 7. Locale Fallback Strategy

**Choice:** If locale template missing → fall back to English → if still missing → log error, skip email

**Rationale:**
- English templates always exist (primary development language)
- Bulgarian templates can be added incrementally
- Silent fallback better than crashing on missing translation

### 8. Customer Locale Snapshotted onto the Order

**Choice:** Add a `locale` column to the `orders` table, captured at checkout. All emails read locale **from the order row**, never from a session.

**Rationale:**
- `preferred_locale` lives on the `sessions` table, not `orders` (verified: `database.py:44`). Customer-facing emails for `shipped`/`delivered`/`cancelled` are triggered by an **admin** action — so `request.state.preferred_locale` in the admin route is the *admin's* locale, not the customer's. Reading it there would send a Bulgarian customer an English "shipped" email.
- Sessions expire at 30 days; an order shipped weeks later may have no surviving session to look up.
- The value is already available at checkout (`orders.py:59-63` reads it). Snapshotting it onto the order is consistent with the project's existing **order-snapshot** decision (name/price frozen on `order_items`). Locale is the same class of fact: true-at-purchase-time.

**Consequence:** tasks.md 8.5 ("read preferred_locale in admin route") is wrong and flips to "read `locale` from the order row." A schema migration adds `orders.locale TEXT NOT NULL DEFAULT 'en'`.

### 9. Which Transitions Email the Customer

**Choice:** Send customer email on **placed** (checkout → pending), **shipped**, **delivered**, and **cancelled**. Do **NOT** send a separate "confirmed" email.

**Rationale:**
- pending→confirmed is an internal admin step. A second near-identical email moments after "order placed" reads as noise and burns quota (see Risks: free tier).
- The meaningful customer touchpoints are: we got your order → it's on its way → it arrived → (if applicable) it's cancelled.

**Consequence:** `order_confirmed.txt` (EN + BG) templates and the "confirmed" scenario are dropped from scope. The `confirmed` transition still happens in the state machine and still fires an admin-side event if needed, but sends no customer email.

### 10. Cancellation is Admin-Only; Refund is Out-of-Band

**Choice:** No customer-facing cancel endpoint. Cancellation only via `PATCH /v1/admin/orders/{id}/status` (verified: `admin.py:401`, transition map `order_service.py:24-28`). A customer who wants to cancel contacts the shop (email/phone); the admin cancels, stock is restored, and a refund is issued manually (no payment integration in scope).

**Rationale:**
- Matches how a small family business actually operates — a human confirms and refunds.
- The "order cancelled" email SHALL tell the customer a refund is being processed, so the manual refund is not a silent surprise.

### 11. Order-Email Log Table (Idempotency + Audit + Re-send Foundation)

**Choice:** Add an append-only `order_emails` table recording every send attempt.

```sql
CREATE TABLE IF NOT EXISTS order_emails (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id   TEXT NOT NULL REFERENCES orders(id),
    event      TEXT NOT NULL,      -- placed | shipped | delivered | cancelled | admin_new_order
    recipient  TEXT NOT NULL,
    status     TEXT NOT NULL,      -- sent | failed | skipped_duplicate | skipped_suppressed
    reason     TEXT,               -- provider error (failed) or skip detail
    sent_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_order_emails_order_id ON order_emails(order_id);
-- DB-level idempotency arbiter: at most one successful send per (order_id, event).
CREATE UNIQUE INDEX IF NOT EXISTS idx_order_emails_sent_unique
    ON order_emails(order_id, event) WHERE status = 'sent';
```

**Rationale:**
- **Idempotency (defense in depth, not toggle-driven):** NOTE — the earlier "shipped→confirmed→shipped toggle" justification was wrong: the state machine is strictly forward (`order_service.py:24-28`; `shipped:{delivered}`, no back-edges) and same-state re-entry returns 422, so no customer event can fire twice through the API. The real duplicate risk is **concurrent/retried sends** (admin double-click, client retry, or multiple uvicorn workers) racing the check-then-send. The **partial UNIQUE index** makes the DB the arbiter (insert-first, then send; a duplicate insert fails and the send is skipped), closing the check-then-insert TOCTOU. **This is now the *sole* idempotency guard:** ZeptoMail does not document a send-level idempotency key (unlike Resend's `Idempotency-Key`), so there is no provider-level dedup to lean on — the DB index carries it entirely (see Decision 14).
- **Audit:** when a customer says "I never got it," there's a queryable record, not just scattered structlog lines. Distinct skip reasons (`skipped_duplicate` vs `skipped_suppressed`) keep the trail legible.
- **Re-send foundation:** the deferred admin re-send button has a table to read from and write to.
- **In-flight loss:** a deploy/crash between response and task means the task never runs and no row is written — the audit table then can't distinguish "never attempted" from "sent but unlogged." Accepted risk at this scale; a `queued` row written before dispatch is a future option (recorded in Risks).

Still fire-and-forget: writing the log row happens inside the background task alongside the send; a logging failure is caught and never propagates.

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|------|--------|------------|
| ZeptoMail credit/quota exhausted | Some emails not sent | Log the error response, alert admin. ~4 emails/order (placed+shipped+delivered/cancelled+admin); free 10k credit then pay-as-you-go (~€2.50/10k, no daily cap) covers this scale comfortably. |
| ZeptoMail service outage | Emails delayed/lost | Fire-and-forget logging. Manual re-send from admin. No customer-facing error. |
| Template rendering bug | One email type broken | Per-template try/catch. Other email types unaffected. Structured log with full context. |
| Domain not registered | Cannot send from branded address | Console provider works for dev/test. Production blocked until domain ready — but code is ready. |
| Tracking URL patterns change | Broken links in shipped emails | Admin can override with custom URL. Patterns are static code in `app/constants.py` (NOT pydantic Settings), editable in one place. |
| Email contains stale order data | Customer confusion | Email context built from a fresh DB read at send time, on the task's own connection (see Decision 3), not from the request. |
| Task lost on shutdown/crash | Email never sent, no log row | Accepted at this scale (no retry). Optional future: write a `queued` row before dispatch so the audit table distinguishes "never attempted" from "unlogged." |
| No retry = lost emails | Customer never gets notification | Acceptable at this scale. Admin can manually trigger re-send. Future: add simple retry (1 attempt after 60s). |

## Migration Plan

**Database schema changes:**
```sql
-- New columns on orders (added via the migrate path, see below)
tracking_number  TEXT
tracking_carrier TEXT
tracking_url     TEXT
locale           TEXT NOT NULL DEFAULT 'en'
-- New table (created via _SCHEMA_SQL)
order_emails (...)   -- see Decision 11
```

SQLite has **no** `ADD COLUMN IF NOT EXISTS`. Reuse the repo's existing idempotent helper `_add_column_if_missing()` (`database.py:310-319`, PRAGMA-driven — same pattern as the `preferred_locale` migration at `database.py:329-337`) inside `_migrate_existing_schema`, so **existing databases** get the new columns. Also add the columns to the `CREATE TABLE orders` block in `_SCHEMA_SQL` for **fresh** DBs (that block is `CREATE TABLE IF NOT EXISTS`, so on its own it never alters an existing table). `order_emails` is created via `CREATE TABLE IF NOT EXISTS` in `_SCHEMA_SQL`. `orders.locale` is safe to add because it carries a `DEFAULT`.

**Deployment steps:**
1. Deploy code with `email_provider = "console"` (no emails sent, just logged)
2. Verify tracking fields work in admin UI
3. Register domain + configure DNS + verify in ZeptoMail (EU)
4. Set `EMAIL_PROVIDER=zeptomail`, `EMAIL_API_KEY=<ZeptoMail Send Mail token>`, `ZEPTOMAIL_WEBHOOK_AUTH_KEY=<key>` (follow-up), `ADMIN_NOTIFICATION_EMAIL=contacts@theateliermarie.com`
5. Trigger a real test order (or use `GET /v1/admin/orders/{id}/emails` to inspect the audit log) — there is no dedicated "send test email" endpoint in this change
6. Switch to production

**Rollback:**
- Set `EMAIL_PROVIDER=console` → all emails become log-only
- Tracking columns are additive (no data loss on rollback)
- No breaking changes to existing API contracts (tracking fields are optional additions)

## Deliverability (Research-Driven)

Findings from a 2025-2026 research pass. Split into account/DNS setup (one-time, out of code) and code-level design.

### Setup / account (one-time, no code)

- **Root domain + aliases, not a subdomain (decision reversed).** Send from the **root** `theateliermarie.com` using aliases (`orders@`, `noreply@`); `EMAIL_FROM_ADDRESS = orders@theateliermarie.com`, `Reply-To = contacts@theateliermarie.com`. This is a deliberate simplification for a transactional-only, low-volume sender. Tradeoff accepted: order-mail reputation is **not** isolated from the human `contacts@` inbox (a `send.` subdomain would isolate it — chosen against for operational simplicity). Any future *marketing* stream MUST use a dedicated subdomain, never the root.
- **DNS auth via DKIM + bounce CNAME (no SPF merge).** As verified for this account, ZeptoMail authenticates with a **DKIM TXT** (selector `19154433`, Default, 1024-bit; an optional 2048-bit `1916479283` selector is also offered) plus a **bounce CNAME** (`bounce-zem → cluster89.zeptomail.eu`) that carries return-path + SPF alignment. The existing Zoho `v=spf1` record is **left untouched**. General caution (didn't apply here): a domain may have only one `v=spf1` record — if a provider ever hands you an SPF `include:`, merge it into that one record rather than adding a second (a second = `permerror`).
- **Full auth stack.** Publish the ZeptoMail DKIM TXT + bounce CNAME, plus a DMARC record. DKIM is aligned on the root domain, so DMARC passes on DKIM even before SPF. Verify the domain in the ZeptoMail console before enabling sends.
- **DMARC progression.** Start `_dmarc` at `p=none` with a readable `rua` (`contacts@theateliermarie.com`); after 2-4 weeks of clean reports move to `quarantine`, then `reject`. `pct`/`ruf` tags are widely ignored — don't rely on them.
- **EU data center.** Create the ZeptoMail Mail Agent in the **EU DC** (`smtp.zeptomail.eu` / EU API host). Unlike Resend, this keeps account/sending data in the EU — sign ZeptoMail's **DPA** and document Zoho (EU) as a GDPR processor.
- **Monitoring.** Verify the domain in **Google Postmaster Tools** (only source of Gmail spam-rate; will show "insufficient data" at low volume but accrues). **abv.bg / mail.bg expose no postmaster tooling or feedback loops** (confirmed absence) — rely on clean auth + test against real abv.bg/mail.bg inboxes before launch.
- **Skip at this scale:** dedicated IP (ZeptoMail offers it as an annual add-on; a cold dedicated IP hurts deliverability below high volume), BIMI/VMC (requires `p=reject` + registered trademark + ~$1,400/yr).

### Cost model (supersedes "Cost €0" in proposal)

ZeptoMail is **pay-as-you-go with no daily cap**: a free **10,000-email credit** to start, then credits at ~€2.50 / 10,000 emails (valid 6 months). After Decision 9 (no "confirmed" email) each order generates ~4 emails (placed + shipped + delivered-or-cancelled + admin alert), so ~25 orders/day ≈ 100 emails/day ≈ 3,000/month — the initial free credit alone covers roughly three months, and thereafter the cost is trivial. There is no 100/day cliff to design around (that was a Resend constraint); still log any quota/credit error responses and degrade gracefully.

### Code-level decisions

### 13. Disable open/click tracking

ZeptoMail supports open/click tracking (its webhook exposes `open`/`click` events), and tracking pixels + rewritten click links are phisher-like signals that "have been seen to negatively impact inbox placement." Transactional mail doesn't need open metrics. Send with tracking **off** on every send.

### 14. No provider-level idempotency key (DB index is the sole guard)

**Superseded by the ZeptoMail switch.** Resend offered an `Idempotency-Key` header; ZeptoMail does **not** document a send-level idempotency key. There is therefore no provider-level dedup, and the derived `order-{event}/{order_id}` key form is dropped. Duplicate suppression relies entirely on the `order_emails` partial UNIQUE index (Decision 11): insert the `sent` row first, and a uniqueness violation means "already sent → skip." A concurrency test (two sends for the same `(order_id, event)` → exactly one email) is the safety net, since there is no second layer behind it.

### 15. Consume bounce/complaint/suppression webhooks

Add a webhook endpoint (`POST /v1/webhooks/zeptomail`) handling ZeptoMail's `hard_bounce`, `soft_bounce`, and `fbl_complaint` (feedback-loop / spam-complaint) events. On a hard bounce or complaint, mark the customer's email undeliverable (a small `suppressed_emails` table) so the store stops generating mail to a known-bad address. Note: Gmail does **not** fire complaint events to third parties (visible only in Postmaster Tools).

**Signature verification (ZeptoMail scheme — NOT Svix):** ZeptoMail signs each webhook with a `producer-signature` header carrying three parts — `ts` (timestamp), `s` (the HMAC), and `s-algorithm` (`HMAC-SHA256`) — computed over the payload using a **configurable Authentication Key** set on the Mail Agent. Verify as follows:
- Config: add `zeptomail_webhook_auth_key: SecretStr` to `app/config.py` and `.env.example`. Without it the endpoint cannot be built. (This replaces the earlier Resend/Svix `resend_webhook_secret` / `whsec_` design.)
- Read the **raw body** (`await request.body()`) *before* JSON parsing — the HMAC is computed over the raw bytes; any re-serialization breaks it.
- Enforce **timestamp tolerance** (±5 min) using the `ts` component to reject replays — a captured valid webhook could otherwise be replayed to suppress an arbitrary customer address (denial-of-email).
- Constant-time compare via `hmac.compare_digest` (as `auth.py:115` already does).
- Add `/v1/webhooks/zeptomail` to `session_skip_paths` (`config.py:61-70`) so the session middleware doesn't set a cookie on a machine-to-machine call; mount it outside the admin router (public, authenticated by signature only). Apply a body-size limit.

### 16. Validate email address at checkout

Hard bounces to invalid addresses are the single biggest reputation risk for a new domain. **Already satisfied:** `CreateOrderRequest.customer_email` is `EmailStr` (`models/orders.py:46`) with `email-validator` in deps — so format validation exists. Remaining optional work: typo/MX checks on common-domain typos (e.g. `gmial.com`). Guardrail targets: bounce < 4% (aim ~0), complaint < 0.1% (aim 0).

### 17. Plain-text-first is a recorded trade-off

Filters treat plain-text-*only* as slightly unusual for a commercial sender, and HTML-only worse; best practice is `multipart/alternative` with matched text+HTML parts. We ship plain-text-only at launch for speed and accept the minor trade-off; the "HTML templates later" work (out of scope) SHOULD produce multipart, not HTML-only.

### 18. Cyrillic subject headers must be MIME-encoded

Bulgarian subjects/display names require RFC 2047 encoded-words (`=?utf-8?B?…?=`); bodies are UTF-8. When sending via the ZeptoMail API (JSON) or SMTP, confirm the emitted `Subject` header is encoded-word form, not raw UTF-8 bytes — add a test asserting a Cyrillic subject round-trips correctly. No `List-Unsubscribe` header on transactional mail (only add it if a marketing stream is introduced later, on a separate subdomain).

### 19. Canonical `EmailEvent` vocabulary (single source of truth)

The "event" token is the spine of the feature — it appears in the `order_emails.event` column, template filenames, idempotency keys, and route logic — and must have exactly one canonical form. Define in `app/constants.py` (CLAUDE.md: cross-module strings live here):

```python
EmailEvent = Literal["placed", "shipped", "delivered", "cancelled", "admin_new_order"]

# OrderStatus → EmailEvent (None = no customer email)
STATUS_TO_EMAIL_EVENT: dict[str, str | None] = {
    "pending": "placed",       # NOTE: status is "pending", event is "placed"
    "confirmed": None,         # no email (Decision 9)
    "shipped": "shipped",
    "delivered": "delivered",
    "cancelled": "cancelled",
}
```

Derived forms are computed from the event, never re-spelled: template file = `order_{event}.txt`. (There is no idempotency-key form — ZeptoMail has no send-level idempotency key; see Decision 14.) This kills the `pending`/`placed`/`order_placed` inconsistency. **Route wiring must map status→event** (so `send_order_email(event="pending")` becomes `event=STATUS_TO_EMAIL_EVENT[status]`, skipping when `None`).

### 20. Jinja2 autoescape OFF for `.txt`; template inputs constrained

The renderer `Environment` MUST set `autoescape=False` — for plain-text `.txt`, HTML-escaping is a bug (`Ben & Co` → `Ben &amp; Co`). Consequence to record now: when HTML/multipart templates are added later (Decision 17), autoescape must be turned **on** for `.html`, because `customer_name`/`shipping_address` are stored raw (unlike comments, which use `sanitize_text` at `comment_service.py:120`) and would otherwise be an email-client XSS/spoofing vector. User-supplied values (`customer_name`, `tracking_url`) MUST NOT flow into `Subject`/`From`/`Reply-To` (header injection); `tracking_url` should be constrained to `http(s)://` before the HTML phase.

### 21. `TRACKING_REQUIRED` is a service-layer error, not a Pydantic validator

The 422 with `code: "TRACKING_REQUIRED"` (order-tracking spec) cannot come from a Pydantic `model_validator` — that raises `RequestValidationError` → the framework envelope, not our `{"error":{"code":...}}` form. The conditional check (required only when `status=="shipped"`) lives in the service and raises a custom exception translated inline like `InvalidStateTransitionError` (`admin.py:420-434`). Also: `update_status(conn, order_id, new_status)` (`order_service.py:446`) has no tracking params and its `UPDATE` writes only `status` — signature + UPDATE must be extended to persist tracking.

### 22. Email logs correlate by order_id + event (request_id is unavailable)

`RequestIdMiddleware` resets `request_id_var` in a `finally` before background tasks run (`request_id.py:43-49`), so email logs would carry no `request_id`. Email logs and `order_emails` rows MUST explicitly bind `order_id` + `event` (the task already receives both) as the correlation keys. Optionally pass `request_id` into the task as an argument if request-level tracing is wanted.

### 23. GDPR coverage for new PII stores

`order_emails.recipient` and `suppressed_emails` hold email addresses. Existing erasure anonymizes by `user_id`, but anonymous checkouts have no `user_id`, so these would be un-erasable by construction. Decision: the erasure job MUST also scrub/anonymize `order_emails.recipient` (e.g. by `order_id` join to erased orders) and age out `suppressed_emails`. Console-provider and structlog output MUST NOT log full bodies in production and SHOULD log a hashed/truncated recipient — there is no log-redaction processor today (`logging_config.py`), so this is new work, not an existing guarantee.

### 24. ZeptoMail HTTP API over SMTP

**Choice:** Send via the ZeptoMail **HTTP API** (EU host), not SMTP.

**Rationale:**
- **Async fit:** a single stateless HTTPS POST via `httpx` (already a dependency) — no threadpool hop, no SMTP connection/TLS/handshake state. `smtplib` is blocking and would run in a worker thread under BackgroundTasks.
- **Structured errors:** the API returns an HTTP status + JSON error body, which maps cleanly onto the `order_emails.reason` audit column. SMTP reply codes are clumsier to parse.
- **Egress:** outbound 443 is always open; SMTP submission ports (587/465) are usually fine but not guaranteed on every host (Oracle Cloud hard-blocks port 25; confirm 587 egress if SMTP is ever used).
- **Least churn:** mirrors the original HTTP-based provider shape, so the provider abstraction/tasks/tests are unchanged by the vendor swap.
- **Encoding:** the API/SDK handles RFC 2047 subject encoding (Decision 18); hand-rolled `EmailMessage` puts that on us.

**Alternative kept as fallback:** SMTP via stdlib `smtplib` (`smtp.zeptomail.eu`, 587 STARTTLS, username `emailapikey`, password = Send Mail token) — validated by a manual spike. Viable if API egress ever surprises us, at the cost of the points above. Either transport lives behind the same `EmailProvider` Protocol.

## Resolved / Open Questions

1. **Currency display in emails** — RESOLVED: "€" for EN, "лв" for BG (per email-templates spec).
2. **Which transitions email the customer** — RESOLVED: placed, shipped, delivered, cancelled. No "confirmed" email (Decision 9).
3. **Customer-initiated cancellation** — RESOLVED: admin-only; manual refund out of band; cancelled email mentions the refund (Decision 10).
4. **Customer locale for admin-triggered emails** — RESOLVED: snapshot `orders.locale` at checkout (Decision 8).
5. **Admin re-send** — deferred, but built on the `order_emails` log table (Decision 11).
