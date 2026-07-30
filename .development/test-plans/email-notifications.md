# Test Guide — Email Notifications

Feature: transactional order emails (EN/BG) + shipment tracking + durable outbox.
OpenSpec change: `openspec/changes/email-notifications`. Status: **85/85 tasks, all tests green.**

---

## TL;DR (what it does)

Every order state change queues an email **in the same DB transaction as the order**,
then a ~15s background sweeper sends it (retry + backoff, dedupe across 2 workers).
Emails never block or break checkout. Dev/tests use a **console provider** (no network).

- Customer: `placed` → `shipped` (with tracking) → `delivered` / `cancelled`
- Owner: `admin_new_order` alert
- No `confirmed` email (internal step)

---

## How to run the tests

```bash
# Backend — 725 pass, ruff clean
make test-backend                 # or: .venv/bin/pytest
.venv/bin/ruff check .

# Just the email feature (serial: these use the get_db module path)
.venv/bin/pytest tests/test_email_service.py tests/test_email_providers.py \
  tests/test_email_renderer.py tests/test_webhooks.py -o addopts=""

# Tracking + outbox integration (real middleware + real DB)
.venv/bin/pytest tests/test_order_service.py tests/realapp/test_order_routes.py -o addopts=""

# Frontend — 167 pass
cd frontend && npx vitest run
cd frontend && npx vitest run __tests__/components/admin/ShipOrderModal.test.tsx
```

### Test files added/touched
| File | Covers |
|------|--------|
| `tests/test_email_providers.py` | console + ZeptoMail (mocked httpx), Cyrillic subject round-trip, no List-Unsubscribe |
| `tests/test_email_renderer.py` | interpolation, loops, conditionals, locale fallback, both-missing, autoescape OFF |
| `tests/test_email_service.py` | send path, idempotency (2 drains → 1 send), retry/backoff, `failed_permanent`, locale-from-order, suppression |
| `tests/test_webhooks.py` | signature verify, replay reject, raw-body, suppression, idempotent bounce, GDPR helpers |
| `tests/test_order_service.py` | tracking persist/require/autogen, locale snapshot |
| `tests/realapp/test_order_routes.py` | queued rows in order txn, sweeper delivers, ship email, confirmed = no email, audit endpoint |
| `frontend/__tests__/components/admin/ShipOrderModal.test.tsx` | required tracking #, URL preview, custom URL for "other" |

---

## Manual smoke test (console provider, no real email)

```bash
make dev-backend        # EMAIL_PROVIDER defaults to console
```

1. **Place an order** (checkout via UI or `POST /v1/orders`).
   → within ~15s, terminal logs `email_console_send` for the `placed` email.
   → `admin_new_order` is skipped unless `ADMIN_NOTIFICATION_EMAIL` is set.
2. **Ship it** (admin orders page → status → "Shipped" → fill tracking).
   → `shipped` email logged with carrier + tracking URL.
   → try submitting with no tracking number → blocked (and API returns 422 `TRACKING_REQUIRED`).
3. **Inspect the audit trail:** `GET /v1/admin/orders/{id}/emails` (admin auth)
   → shows one row per event with `status` (queued/sent/skipped_*), attempts, reason.
4. **BG locale:** set session locale to `bg` before checkout → emails render in Bulgarian
   (locale is snapshotted on the order, so admin-triggered emails stay in the customer's language).

### Verify durability / retry (optional)
- Kill the server between checkout and the sweep → restart → the `queued` row is still there and gets sent (no loss).
- The retry/`failed_permanent` path is covered by `tests/test_email_service.py::TestRetry`.

---

## Going live (not enabled by default)

Emails are **console-only** until configured:

```bash
EMAIL_PROVIDER=zeptomail
EMAIL_API_KEY=<ZeptoMail Send Mail token>
ADMIN_NOTIFICATION_EMAIL=contacts@theateliermarie.com
ZEPTOMAIL_WEBHOOK_AUTH_KEY=<webhook signing key>
```
Plus DNS (DKIM + bounce CNAME + DMARC) per the proposal / `EMAIL_SETUP.md`.

---

## Known non-issues
- Frontend `tsc --noEmit` shows errors about `items_total_cents` / `shipping_cents` missing in mock
  seed data + a couple in `LanguageToggle`. These are **pre-existing branch WIP** (shipping-pricing),
  not from this change — none reference the email/tracking files. `vitest` (the actual test runner) is green.
