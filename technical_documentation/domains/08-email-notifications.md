# Email Notifications

Email is durable and payment-aware.

## Main Backend Files

- `app/services/email_service.py`
- `app/services/contact_service.py`
- `app/email/renderer.py`
- `app/email/providers/*`
- `app/email/templates/en/*`
- `app/email/templates/bg/*`
- `app/routes/webhooks.py`
- `app/services/webhook_service.py`
- `app/database.py` tables: `order_emails`, `order_email_send_claims`, `suppressed_emails`, `contact_messages`

## Outbox Model

Business code queues email rows. The sweeper sends later.

```text
business event
  -> insert queued row in same transaction
  -> email_outbox_loop wakes
  -> claim row
  -> suppression check
  -> render template
  -> provider.send
  -> mark sent/failed/skipped
```

## Why Queue First

- Provider outage should not undo checkout.
- Admin state changes should not fail because email is slow.
- Retries need durable state.
- Multiple workers need DB-level idempotency.

## Order Email Events

Common events:

- `placed`
- `payment_pending`
- `shipped`
- `delivered`
- `cancelled`
- `admin_new_order`

Payment-aware behavior:

- COD: `placed` at checkout.
- Card: `payment_pending` at checkout, `placed` after Stripe success.
- Bank transfer: `payment_pending` at checkout, `placed` after admin marks paid.
- Confirmed status does not send customer email.

## Template Context

Templates receive precomputed display data:

- short order id
- customer name/email
- item lines
- item/shipping/total displays
- delivery labels and lines
- tracking fields
- legal policy URLs
- trader identity
- payment method/status
- bank transfer details when configured

Templates should not do arithmetic.

## Provider Model

Provider interface supports:

- console provider for dev/test
- ZeptoMail provider for real sending
- transient errors for retry
- permanent errors for terminal failure

## Idempotency

Two DB mechanisms protect sends:

- `order_email_send_claims`: one worker owns a send attempt at a time.
- `idx_order_emails_sent_unique`: one successful send per order/event.

## Suppression

Bounce/complaint handling writes `suppressed_emails`.

Rules:

- suppressed recipients are skipped
- do not delete suppression on normal erasure request without legal/product decision
- logs should redact recipient info

## Contact Emails

Contact form messages use `contact_messages` with similar durable email state.

They are rate-limited by IP and cleaned by retention.

## Safe Change Checklist

- Email intent is queued in same transaction as business event.
- Provider failure does not break checkout/order action.
- English and Bulgarian templates both exist.
- Payment emails are not misleading.
- Duplicate sends are still blocked.
- Recipient PII is redacted in logs.

