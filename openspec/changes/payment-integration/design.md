# Payment Integration - Design

## Goals / Non-Goals

**Goals:**
- Accept EUR card payments through Stripe Checkout without handling card details.
- Accept admin-controlled pay on delivery for orders up to EUR 50.
- Reserve stock for card payment attempts for 15 minutes, then restore it on
  expiry.
- Keep payment state separate from fulfillment state.
- Make webhooks idempotent, signed, auditable, and safe to retry.
- Give admins payment settings, status filters, payment timeline, and review tools.

**Non-Goals:**
- Automated refunds, email OTP, saved cards, subscriptions, courier COD API
  reconciliation, or multi-currency.

## Decisions

### 1. Payment state is separate from fulfillment state

`orders.status` remains the fulfillment/admin lifecycle. Payment state is tracked
with `orders.payment_status` and provider rows in `payments`.

Card payment success sets `payment_status = paid` while keeping
`orders.status = pending`, preserving owner review before confirmation/shipping.

Payment states:
- `unpaid`
- `pending`
- `paid`
- `failed`
- `cancelled`
- `pending_collection`
- `collected`
- `refunded`
- `payment_review_required`

Stripe flow: `pending -> paid | failed | cancelled | payment_review_required`.
Pay-on-delivery flow: `pending_collection -> collected | cancelled`.

### 2. Data model uses orders + payments + payment_events

`orders` stores fast summary fields needed for admin/customer reads:
- internal numeric sequence for sorting/accounting
- random-looking public `order_number`
- `payment_method`
- `payment_status`
- `reserved_until`
- `paid_at` and `collected_at`

`payments` stores provider-specific records:
- provider (`stripe`, `pay_on_delivery`)
- amount/currency snapshot
- Stripe Checkout Session ID
- Stripe PaymentIntent ID
- provider status/details needed for reconciliation

`payment_events` is append-only audit for webhooks, manual overrides, collection,
expiry cleanup, and review-required transitions.

### 3. Public order numbers do not expose order volume

Generate public order numbers as `AM-` plus 6 Crockford Base32-style random
characters, avoiding ambiguous characters such as `O`, `I`, and `L`.

If a collision occurs, retry generation up to 10 times, then fail loudly. Keep an
internal numeric sequence for sorting/accounting.

### 4. Payment settings live in DB, Stripe secrets live in env

Payment settings are edited at `/admin/settings/payments` and stored in
`site_settings`:
- `card_payments_enabled`
- `pay_on_delivery_enabled`
- `pay_on_delivery_max_cents` (default 5000)

Settings changes are appended to `site_setting_events` with admin id/email,
setting key, old value, new value, timestamp, and request id. Settings changes do
not send email in MVP.

Stripe secret key and webhook secret are environment-only. Admin sees read-only
configuration health and Stripe mode (`test`/`live`). Production card payments can
only be enabled with live keys and a verified live webhook endpoint.

### 5. Card checkout reserves stock locally for 15 minutes

Creating a Stripe payment order atomically validates stock, creates the order and
payment row, decrements stock, clears the cart, and sets `reserved_until = now +
15 minutes`.

An expiry cleanup runs every 1 minute. For expired unpaid card orders it cancels
the payment/order attempt, restores stock, records a `payment_events` row, and
attempts to expire the Stripe Checkout Session. The cart is not restored in MVP.

If Stripe later reports success after local expiry and stock restoration, mark the
payment as `payment_review_required` and alert admin; do not silently mark paid.

### 6. Stripe Checkout is created and confirmed server-side

The backend creates one-time Stripe Checkout Sessions using only server-side order
snapshots. The frontend never sends payable totals as proof.

Stripe metadata is non-sensitive only: order id/order number, environment, and safe
references. Do not send delivery address, phone, notes, or internal admin data.

Local validated checkout email remains source of truth and must not be overwritten
by Stripe-collected email.

### 7. Retry reuses active sessions only

The customer may retry payment within the 15-minute reservation window. Retry must
require the same session/user and a valid `payment_return_token`.

Reuse an active unexpired Checkout Session for the same unpaid reserved order.
Never reuse a session after payment, cancellation, or expiry.

Stripe cancel return does not cancel the local order immediately. It shows payment
not completed and allows retry while reservation remains valid.

If admin disables card payments while a customer has an active Checkout URL, block
new sessions and retry attempts. Do not bulk-expire active Stripe URLs solely due
to the settings toggle. Already-paid webhooks must still be processed.

### 8. Webhooks are signed, idempotent, minimal, and allowlisted

Webhook endpoint: `POST /v1/webhooks/stripe`, skipped by session middleware. It
must use raw body verification and reject missing/invalid signatures.

MVP event allowlist:
- `checkout.session.completed`
- `checkout.session.expired`
- `payment_intent.payment_failed`
- `charge.refunded` as audit-only

Store Stripe event ids with a unique constraint. Store minimal event audit only:
event id, type, created timestamp, livemode, order id, processing status, and
error. Do not store full raw payload by default.

For `payment_intent.payment_failed`, record the failed attempt but keep the stock
reservation until Checkout Session/local timeout if the session is still active.

### 9. Pay on delivery is real order creation, not temporary reservation

Pay on delivery is disabled by default and capped at EUR 50. It is allowed for both
office pickup and door delivery. It validates stock at submit time, decrements
stock immediately, clears the cart, creates the order with
`payment_status = pending_collection`, and sends the normal order email
immediately.

Admin later marks payment collected. Manual collection/override actions require an
admin-only note and write `payment_events`.

Once shipping pricing exists, the COD collection amount is locked at order
creation and includes the server-side shipping snapshot.

### 10. Customer UI never treats redirects as proof

After Stripe redirects back, frontend fetches order/payment status and shows:
- card paid: `Payment received`
- card pending: `Payment processing`
- pay on delivery: `Order received. Payment will be collected on delivery.`

Customer payment labels:
- `pending`: `Payment pending`
- `paid`: `Paid`
- `failed`: `Payment failed`
- `cancelled`: `Payment cancelled`
- `pending_collection`: `Pay on delivery`
- `collected`: `Payment collected`
- `payment_review_required`: `Payment under review`

Customer order history includes pending and cancelled card attempts, clearly marked
and not presented as active/revenue orders.

### 11. Admin UI is payment-aware

Admin order views show payment status filters/sections for pending, failed,
cancelled, and review-required payments. Revenue counts only paid/collected
orders.

Admin payment labels are operational:
- `pending`: `Stripe pending`
- `pending_collection`: `COD pending collection`
- `payment_review_required`: `Review required`

Order detail includes an admin-only payment timeline from `payment_events`.

`payment_review_required` triggers immediate in-app alert and admin email. Email
contains order number, reason, Stripe Checkout Session ID, Stripe PaymentIntent ID
when known, and admin link, but no customer PII.

### 12. Rate limits are conservative MVP constants

- checkout/order creation: max 5 attempts per 15 minutes per session, and max 20
  per hour per IP
- Stripe Checkout Session creation/retry: max 3 session creations per order and max
  10 per hour per session
- pay on delivery: max 2 orders per hour per session and max 5 per day per IP
- public payment-status polling after Stripe return: max 60 requests per 5 minutes
  per session/IP
- webhooks: cap body size and verify signatures; no ordinary IP rate limit for
  signed Stripe webhooks

These values should be constants so production logs can guide later tuning.

## Launch Requirements

- Local Stripe webhook testing with Stripe CLI or equivalent before implementation
  is marked complete.
- Production card payments disabled until live Stripe keys and live webhook endpoint
  are configured and verified.
- App and deployment body-size limits aligned for Stripe webhook payloads.
