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
- Webhook-based delivery tracking from Resend
- Domain registration (separate prerequisite, does not block code)

## Decisions

### 1. Resend as Email Provider (over Gmail SMTP / Brevo)

**Choice:** Resend Python SDK

**Rationale:**
- Purpose-built transactional API vs repurposing a personal mailbox
- Free tier (100/day, 3000/month) covers expected volume
- Modern Python SDK: one HTTP POST, typed params, async support
- Custom from-address via DNS (no mail server needed)
- Delivery tracking, bounce detection included
- Google can kill SMTP access without warning; Resend cannot

**Alternatives rejected:**
- Gmail SMTP: unreliable, unprofessional from-address, no tracking, can be revoked
- Brevo: viable but heavier SDK, more marketing-focused, less developer-friendly

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

### 4. Provider Abstraction via Protocol Class

**Choice:** `EmailProvider` Protocol with `send()` method; implementations: `ResendProvider`, `ConsoleProvider`

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

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|------|--------|------------|
| Resend free tier exceeded (100/day) | Some emails not sent | Log rate-limit, alert admin. Upgrade to paid ($20/mo) if needed. At 5 transitions × 20 orders = 100 emails, this is the ceiling. |
| Resend service outage | Emails delayed/lost | Fire-and-forget logging. Manual re-send from admin. No customer-facing error. |
| Template rendering bug | One email type broken | Per-template try/catch. Other email types unaffected. Structured log with full context. |
| Domain not registered | Cannot send from branded address | Console provider works for dev/test. Production blocked until domain ready — but code is ready. |
| Tracking URL patterns change | Broken links in shipped emails | Admin can override with custom URL. Patterns stored as config, not hardcoded. |
| Email contains stale order data | Customer confusion | Email context built from fresh DB read at send time (inside BackgroundTask), not from the request. |
| No retry = lost emails | Customer never gets notification | Acceptable at this scale. Admin can manually trigger re-send. Future: add simple retry (1 attempt after 60s). |

## Migration Plan

**Database schema changes:**
```sql
ALTER TABLE orders ADD COLUMN tracking_number TEXT;
ALTER TABLE orders ADD COLUMN tracking_carrier TEXT;
ALTER TABLE orders ADD COLUMN tracking_url TEXT;
```

Applied at startup in `database.py` schema initialization (idempotent `ALTER TABLE ... ADD COLUMN` with IF NOT EXISTS pattern or try/except for SQLite).

**Deployment steps:**
1. Deploy code with `email_provider = "console"` (no emails sent, just logged)
2. Verify tracking fields work in admin UI
3. Register domain + configure DNS + verify in Resend
4. Set `EMAIL_PROVIDER=resend`, `EMAIL_API_KEY=re_xxx`, `ADMIN_NOTIFICATION_EMAIL=owner@gmail.com`
5. Send test email via admin dashboard
6. Switch to production

**Rollback:**
- Set `EMAIL_PROVIDER=console` → all emails become log-only
- Tracking columns are additive (no data loss on rollback)
- No breaking changes to existing API contracts (tracking fields are optional additions)

## Open Questions

1. **Currency display in emails** — Bulgarian customers: "лв" or "BGN"? International: "€" or "EUR"? (Currently proposal assumes "лв" for BG, "€" for EN)
2. **Order placed vs confirmed** — should "order placed" email be sent immediately at checkout (pending), or wait until admin confirms? (Current design: send on both transitions)
3. **Admin re-send** — should we add a "Resend notification" button in the admin UI for this change, or defer to a future change?
