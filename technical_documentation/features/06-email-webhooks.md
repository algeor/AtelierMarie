# Email And Webhooks

Use this when touching transactional email, templates, provider code, bounce/complaint handling, or Stripe webhooks.

## Main Backend Files

- `app/services/email_service.py`: outbox, send attempts, sweeper, immediate send helpers.
- `app/email/renderer.py`: Jinja2 text template rendering.
- `app/email/providers/*`: console and ZeptoMail providers.
- `app/email/templates/en/*`, `app/email/templates/bg/*`: plain-text templates.
- `app/email/redaction.py`: safe recipient logging helpers.
- `app/services/webhook_service.py`: ZeptoMail webhook verification/handling.
- `app/routes/webhooks.py`: ZeptoMail and Stripe webhook endpoints.
- `app/services/payment_service.py`: Stripe webhook state updates.
- `app/models/orders.py`: email audit response model.

## Email Model

Email is durable outbox first.

That means app code inserts an `order_emails` row with status `queued`. Sending can happen through a sweeper or immediate attempt, but order operations should not depend on provider speed.

## Template Rules

- Templates are plain text.
- Templates are bilingual.
- Subject is stored in the template format expected by the renderer.
- Locale follows the order's snapshotted locale.
- Prices are formatted before rendering.
- Bank transfer templates need IBAN/BIC/bank/reference when method is `bank_transfer`.
- Do not add provider tracking pixels/click tracking to transactional mail.

## Which Email Sends When

- COD checkout: queue `placed` immediately.
- Card checkout: queue `payment_pending`; queue `placed` only after verified Stripe success.
- Bank transfer checkout: queue `payment_pending` with payment instructions; queue `placed` after admin marks paid.
- `confirmed`: no customer email.
- `shipped`: customer email with tracking.
- `delivered`: customer email.
- `cancelled`: customer email. Refund copy depends on payment state/method.
- Admin new order: queued as admin notification when configured.

## Deliverability Rules

- Send from authenticated root domain config.
- Open/click tracking stays off for transactional email.
- Bounce/complaint webhooks suppress bad recipients.
- Suppression exists to avoid re-contact. Do not casually delete it.
- Cyrillic subjects must render correctly.
- Log redacted recipient info, not raw PII.

## ZeptoMail Webhook Rules

- Endpoint: `POST /v1/webhooks/zeptomail`.
- It is skipped by session middleware.
- Verify HMAC/signature over raw body.
- Reject oversized/malformed/unsigned payloads.
- Bounce/complaint events update suppression state.

## Stripe Webhook Rules

- Endpoint: `POST /v1/webhooks/stripe`.
- It is skipped by session middleware.
- Verify `Stripe-Signature` using the raw body.
- Handle `checkout.session.completed` by marking card payment paid and queuing `placed` email.
- Handle `checkout.session.expired` by marking pending matching session failed.
- Unknown valid event types return success and log.
- Duplicate events must be idempotent.
- Do not store or log full raw payloads unless there is a deliberate, reviewed reason.

## Safe Change Checklist

- Email row is queued in the same transaction as the business event when needed.
- Provider failure does not undo order/payment/admin action.
- Template exists in English and Bulgarian.
- No misleading customer email before payment is actually paid.
- Webhook verifies raw body before trusting payload.
- Webhook path is in `session_skip_paths`.
- Tests cover duplicate webhook delivery.

