## Context

Atelier Marie runs a localized Next.js storefront (`localePrefix: "always"`, routes under `app/[locale]`) backed by FastAPI + SQLite. The current footer has working Home/Shop links, placeholder About/Contact links, and no social links.

The `email-integration` branch already implements the email foundation this change should reuse: ZeptoMail/console providers, Jinja2 plain-text templates, durable SQLite outbox semantics, retry/backoff, and a 15-second sweeper. That implementation is currently order-specific (`order_emails` references `orders` and the send path builds order context), so contact messages need their own durable contact queue path rather than fake order rows.

## Goals / Non-Goals

**Goals:**

- Make Instagram and TikTok reachable from every page footer.
- Add a localized contact page at `/[locale]/contact`; `/contact` continues through the existing locale middleware redirect.
- Collect name, email, and message with accessible client-side validation.
- Persist every valid contact message before any email attempt.
- Notify the owner at `ADMIN_NOTIFICATION_EMAIL` (`contacts@theateliermarie.com`) through the existing email provider/rendering stack.
- Keep contact email delivery durable: restart/provider outage delays delivery but does not lose the queued notification.

**Non-Goals:**

- No CRM, ticket statuses, assignment, or reply-from-dashboard.
- No admin UI for browsing contact messages in this change.
- No customer auto-reply email.
- No social feed embed or third-party widget.
- No CAPTCHA unless spam becomes a real problem after launch.

## Decisions

### 1. Reuse email providers/templates, add a contact-specific durable queue

**Choice:** Contact messages use the existing email provider factory, ZeptoMail/console providers, and Jinja2 renderer, but they do not use `order_emails`.

**Rationale:** The implemented `order_emails` table and `send_order_email` path are intentionally order-shaped: `order_id` is required, idempotency is keyed by `(order_id, event)`, and context comes from `_fetch_order_with_items`. A contact submission is not an order. Forcing it through that table would introduce fake data and weaken the model.

**Implementation direction:** Add `contact_messages` as both the audit record and durable email outbox for the single owner notification. It should include message data plus email-delivery state:

```sql
CREATE TABLE IF NOT EXISTS contact_messages (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    name                  TEXT NOT NULL,
    email                 TEXT NOT NULL,
    message               TEXT NOT NULL,
    locale                TEXT NOT NULL DEFAULT 'en',
    ip_address            TEXT,
    email_status          TEXT NOT NULL DEFAULT 'queued',
    email_attempts        INTEGER NOT NULL DEFAULT 0,
    email_next_attempt_at TEXT,
    email_claimed_until   TEXT,
    email_sent_at         TEXT,
    email_error           TEXT,
    created_at            TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_contact_messages_created_at
    ON contact_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_contact_messages_email_status
    ON contact_messages(email_status, email_next_attempt_at);
```

The contact drain path can share constants/helper patterns with `email_service.drain_email_outbox()` where practical, but the row reader/context builder is contact-specific.

### 2. Queue in the same transaction as persistence

**Choice:** `POST /v1/contact` inserts the contact row with `email_status='queued'` and returns HTTP 201 after the row commits. It does not send inline and does not schedule a FastAPI `BackgroundTasks` job.

**Rationale:** The contact message itself is the durable work item. If the process restarts after commit, the sweeper still finds the queued row. This matches the email-notifications reliability model and avoids in-memory task loss.

### 3. Contact sweeper extends the existing app lifespan work

**Choice:** Add contact-message draining to the existing email outbox loop, either by calling `drain_contact_message_emails()` from the same `email_outbox_loop` tick or by making `drain_email_outbox()` dispatch both order and contact queues.

**Rationale:** One periodic email drain loop is enough. Contact volume is tiny, and a separate worker/process would be unnecessary.

**Concurrency requirement:** Production may run multiple uvicorn workers. The contact drain path must claim a row before sending so two sweepers do not email the same contact message. A simple SQLite `BEGIN IMMEDIATE` update from `queued`/`failed` to `in_flight` with `email_claimed_until` is sufficient; expired claims become retryable.

### 4. Owner notification recipient

**Choice:** Contact notifications are sent to `settings.admin_notification_email`.

**Rationale:** The email setup already uses `contacts@theateliermarie.com` as the owner mailbox and reply destination. A separate `CONTACT_NOTIFICATION_EMAIL` setting adds configuration surface without a current need.

**Behavior when unset:** Persist the message, mark email delivery as skipped/no-recipient or failed-permanent with a clear reason, and log it. The user-facing submission still succeeds because the message is saved.

### 5. Reply-To is the submitter

**Choice:** Contact notification emails should set `reply_to` to the submitter's email address, not the global `EMAIL_REPLY_TO`, when the provider supports it.

**Rationale:** The owner should be able to reply directly from the inbox. The from-address remains the configured transactional sender (`orders@theateliermarie.com` or the existing email sender config), so SPF/DKIM/DMARC alignment stays under the verified domain.

### 6. Localized page, stable backend contract

**Choice:** The frontend page is `app/[locale]/contact/page.tsx`, using existing next-intl routing. The backend endpoint remains locale-neutral at `POST /v1/contact`; the request includes `locale` (`en` or `bg`) for template/context.

**Rationale:** Storefront routing is localized, but the API should not duplicate routes by locale. The existing middleware already redirects `/contact` to `/{detected-locale}/contact`.

### 7. Spam controls stay small but server-side

**Choice:** Use server-side validation, a hidden honeypot field named `website`, and a SQLite-backed per-IP rate limit of 5 accepted submissions per hour.

**Rationale:** In-memory limits are weak with multiple workers and reset on restart. Counting recent persisted valid messages by IP is enough for this scale and avoids adding CAPTCHA friction.

**Honeypot behavior:** If `website` is non-empty, return HTTP 201 with the normal response but do not persist or email.

### 8. Social URLs are configurable with confirmed defaults

**Choice:** Footer social links read from public frontend env vars with these defaults:

- Instagram: `https://www.instagram.com/atelier_marie25?igsh=MWQ1YzA4aHF2a3Q4MA==`
- TikTok: `https://www.tiktok.com/@ateliermarie25?_r=1&_t=ZN-98H9buODbdu`

**Rationale:** The profiles are public content, not secrets. Env vars allow changing the links without touching component code; defaults make local development work immediately.

### 9. Contact page presentation is restrained and storefront-native

**Choice:** The contact page uses the existing luxury storefront design language with a quiet two-column desktop layout: contextual contact copy and direct links on one side, the form on the other. On mobile, the sections stack in a single column. The form may be visually framed, but the page should not become a marketing hero, decorative card grid, or social-media-style panel.

**Rationale:** The page is a utility surface for customers who already intend to reach the shop. Elegance comes from spacing, typography, clean field states, and consistent materials rather than oversized copy, gradients, shadows, or decorative shapes.

**Implementation notes:** Use existing colors, typography, focus rings, and button styles. Keep the heading modest, body copy short, and form labels/errors readable. Include direct contact/social links near the form so visitors who prefer email or social can use them without scrolling.

## Risks / Trade-offs

- **Provider failure:** Message is already persisted; sweeper retries with backoff and logs terminal failure.
- **Duplicate owner notification:** Contact drain must claim rows before provider send. This is the same class of two-worker risk handled by the order email outbox.
- **Spam:** Honeypot + 5/hour/IP handles basic bots. CAPTCHA is intentionally deferred.
- **Admin visibility:** Messages are stored but no admin UI is shipped here. Database/manual inspection remains possible; a dashboard view can be a follow-up.
- **Personal data:** Contact rows contain name, email, message, and IP. Do not log full message bodies in production; structured logs should include only message id/status and redacted recipient/email.
