## Payment Integration Discussion Capture

Status: discussion notes, not a finalized proposal.

These notes capture the payment architecture decisions discussed before writing an
`opsx:propose`-style change. The intended future proposal is likely a Stripe
Checkout payment integration plus a lightweight admin site-settings foundation.

## Current Project Context

- AtelierMarie currently uses SQLite as the Layer 1 system of record, not PostgreSQL.
- Existing checkout creates an order with `status = pending`, snapshots prices,
  decrements stock, clears the cart, and queues emails.
- Existing order status represents fulfillment/admin workflow. Payment state should
  be separate from fulfillment state.
- Shipping picker exists as structured delivery data. Real-time shipping pricing is
  planned separately in `shipping-pricing`.

## Core Payment Direction

- Launch currency: EUR only.
- Card payments: Stripe Checkout, one-time payments only.
- No saved cards, subscriptions, or card detail handling in this app.
- Stripe secrets and webhook secrets stay env-only and are never editable in admin.
- Payment amount must be computed only from the server-side order snapshot.
- Payment implementation should proceed before `shipping-pricing`. The payment
  layer uses the server-side `total_cents` snapshot; `shipping-pricing` can later
  change how `total_cents` is built without changing payment trust boundaries.
- Frontend success/cancel pages must never be trusted as payment proof.
- Stripe webhook confirmation is the authoritative source for card payment success.

## Payment Methods

### Stripe Card Payment

- Admin can enable/disable card payments.
- Admin can only enable card payments when Stripe config is complete.
- Admin settings should show Stripe configuration health and mode (`test`/`live`) as
  read-only status.
- Stripe metadata should contain only non-sensitive data such as `order_id`,
  environment, and safe references.
- Stripe metadata must not include delivery address, phone, notes, or internal admin
  data.
- Local validated checkout email remains the source of truth. Stripe email must not
  overwrite `orders.customer_email`.

### Pay On Delivery

- Pay on delivery should be a first-class payment method.
- Admin can enable/disable pay on delivery globally.
- Pay on delivery is disabled by default.
- Maximum pay-on-delivery amount: EUR 50.
- Pay on delivery is allowed for both office pickup and door delivery.
- For MVP, no courier API integration is required to support pay on delivery.
- Future courier integration may create COD shipments and fetch courier payment or
  payout status from Speedy/Econt if their APIs expose it.
- Admin must explicitly mark pay-on-delivery payment as collected.
- Pay-on-delivery orders reserve/decrement stock immediately because the customer
  has placed a real order.

## Admin Site Settings

- Add a general admin settings area now, scoped initially to payment settings.
- Payment settings should live at `/admin/settings/payments` from day one, rather
  than a single catch-all `/admin/settings` page.
- Payment settings should include:
  - card payments enabled/disabled
  - pay on delivery enabled/disabled
  - pay-on-delivery max amount, default EUR 50
- Fresh DB defaults:
  - card payments disabled unless Stripe is configured and admin enables it
  - pay on delivery disabled
  - pay-on-delivery max EUR 50
- Saving settings must reject a state where both payment methods are disabled.
- Public checkout receives only safe settings such as enabled payment methods and
  max pay-on-delivery amount.
- Payment settings are read from the DB on each checkout request for immediate
  admin toggle effect.
- Admin settings changes need a lean audit log:
  - admin user id/email
  - setting key
  - old value
  - new value
  - timestamp
  - request id
- Payment settings changes do not send admin email in MVP. The audit log is the
  source of truth for settings-change history.

## Recommended Admin Settings Data Shape

- Use a `site_settings` table for current settings values, initially scoped to
  payment settings:
  - `card_payments_enabled`
  - `pay_on_delivery_enabled`
  - `pay_on_delivery_max_cents`
- Use a separate append-only `site_setting_events` table for admin settings audit.
- Keep Stripe secret key and webhook secret out of `site_settings`; they remain
  environment-only.
- Public checkout should read a safe projection of settings, never the raw admin
  settings/audit rows.

## Order And Payment State

- Keep fulfillment state and payment state separate.
- Existing `orders.status` remains the admin/fulfillment lifecycle.
- Card payment success sets `payment_status = paid` while keeping
  `orders.status = pending` for owner review.
- Payment states discussed:
  - `unpaid`
  - `pending`
  - `paid`
  - `failed`
  - `cancelled`
  - `pending_collection`
  - `collected`
  - `refunded`
  - `payment_review_required`
- Stripe state flow:
  - `pending -> paid | failed | cancelled | payment_review_required`
- Pay-on-delivery state flow:
  - `pending_collection -> collected | cancelled`
- Manual admin payment overrides require a note.
- Any current admin can perform manual payment actions for MVP; actions are audit
  logged. A stricter owner-admin role can come later.

## Stock Reservation And Expiry

- Stripe card payment reserves/decrements stock for 15 minutes.
- Local reservation fields should include a `reserved_until` timestamp.
- If payment is not completed within 15 minutes, the order is automatically
  cancelled and stock is restored.
- Expired card-payment orders remain visible as cancelled in order history.
- Abandoned/expired card orders do not restore the cart for MVP.
- Cleanup should run every 1 minute. A reservation may therefore live for roughly
  15-16 minutes in practice, which is acceptable.
- On local reservation expiry, cleanup should attempt to expire the Stripe Checkout
  Session.
- If Stripe later reports success after local reservation expiry and stock release,
  mark the payment/order as `payment_review_required`, do not silently treat it as
  normal paid flow.

## Stripe Checkout Session Reuse And Retry

- Reuse an active unexpired Stripe Checkout Session for the same unpaid reserved
  order.
- Never reuse a session after payment, cancellation, or expiry.
- Customer can retry payment for the same reserved order within the reservation
  window.
- Retry should require the same session/user that created the order plus a valid
  `payment_return_token`.
- Stripe cancel return must not immediately cancel the order; show payment not
  completed and keep reservation until expiry, with retry if still valid.
- If admin disables card payments mid-checkout, no new Stripe sessions should be
  created. Already-paid webhooks must still be processed.

## Payment Return Token

- Add a random `payment_return_token` for Stripe return URLs.
- Return URLs should not rely only on the order UUID.
- The token is for payment return/retry flows, not a replacement for normal
  session/user order ownership checks.
- Invalidate or rotate the token after payment succeeds, the order is cancelled,
  or the payment reservation expires.

## Stripe Webhook Handling

- Webhook endpoint: `POST /v1/webhooks/stripe`.
- Endpoint must be skipped by session middleware.
- Use the raw request body for Stripe signature verification.
- Reject missing or invalid Stripe signatures.
- Store Stripe event IDs with a unique constraint for idempotency.
- Process only expected event types.
- MVP webhook allowlist:
  - `checkout.session.completed`
  - `checkout.session.expired`
  - `payment_intent.payment_failed`
  - `charge.refunded` as audit-only
- Let Stripe retry if webhook processing fails after verification.
- Store minimal webhook/payment audit in DB, not full raw payload by default.
- Minimal stored event fields should include event id, event type, created timestamp,
  livemode, order id, processing status, and error if any.
- Handle `charge.refunded` as audit-only in MVP; do not mutate order state yet.
- For `payment_intent.payment_failed`, record the failed attempt but keep the stock
  reservation until session/local timeout if the Checkout Session is still active.

## Payment Events And Audit

- Add a `payment_events` table for:
  - Stripe webhook events
  - manual admin overrides
  - pay-on-delivery collection
  - expiry cleanup
  - review-required transitions
- Store Stripe Checkout Session ID and PaymentIntent ID for reconciliation in the
  Stripe Dashboard.
- Payment logs should avoid customer PII by default.
- Logs may include order id/order number, payment status, Stripe IDs, event IDs, and
  request ID.
- Logs should avoid email, phone, delivery address, and notes.

## Recommended Database Shape

- Use `orders` for customer/order lifecycle summary fields that need fast filtering:
  - internal sequence id for sorting/accounting
  - `order_number`
  - `payment_method`
  - `payment_status`
  - `reserved_until`
  - `paid_at` / `collected_at` when relevant
- Use `payments` for the provider-specific payment record:
  - provider (`stripe`, `pay_on_delivery`)
  - amount and currency snapshot
  - Stripe Checkout Session ID
  - Stripe PaymentIntent ID
  - provider status/details needed for reconciliation
- Use `payment_events` as append-only audit for webhooks, manual overrides,
  expiry cleanup, pay-on-delivery collection, and review-required transitions.
- Rationale: `orders` remains easy to query for admin/customer pages, while payment
  provider details and audit history are isolated from fulfillment state.
- This `orders` + `payments` + `payment_events` split is accepted as the proposal
  baseline.

## Emails And Customer-Facing Status

- Stripe card orders send customer order email only after `payment_status = paid`.
- Pay-on-delivery orders send customer order email immediately after order creation.
- Expired/cancelled Stripe attempts do not send customer email for MVP.
- After Stripe redirects back, the frontend fetches the order/payment status:
  - show paid only if webhook has confirmed payment
  - show processing if webhook has not arrived yet
  - show failed/cancelled/review states when relevant
- Customers may see unpaid/reserved card orders, but they must be clearly labeled.
- Customer order history should include cancelled card-payment attempts so the
  customer can understand what they did. These entries must be clearly marked as
  cancelled/unpaid and not presented as active orders.
- Pending card-payment attempts should appear in customer order history during the
  15-minute reservation window, clearly labeled "Payment pending", so customers can
  retry payment.
- Customer payment status labels:
  - `pending`: "Payment pending"
  - `paid`: "Paid"
  - `failed`: "Payment failed"
  - `cancelled`: "Payment cancelled"
  - `pending_collection`: "Pay on delivery"
  - `collected`: "Payment collected"
  - `payment_review_required`: "Payment under review"
- Order confirmation/status page should vary by method/status:
  - card paid: "Payment received"
  - card pending: "Payment processing"
  - pay on delivery: "Order received. Payment will be collected on delivery."
- Admin can see unpaid/reserved card orders, clearly labeled and filterable.
- Checkout card-payment copy should state: "Your items are reserved for 15 minutes
  while you complete card payment."
- Checkout pay-on-delivery copy should state: "Payment is collected when your order
  is delivered. Available up to EUR 50."
- Customer-facing payment method labels should be plain: "Card payment" and "Pay on
  delivery".

## Admin Payment Review

- `payment_review_required` should be visible in admin.
- MVP should alert both in-app and by admin email.
- Admin email alerts for `payment_review_required` should send immediately for each
  event, not as a digest.
- Admin email should include order number, review reason, Stripe Checkout Session
  ID, Stripe PaymentIntent ID when known, and admin order link, but no customer PII.
- Admin can:
  - view reason
  - mark paid manually
  - cancel/refund manually
  - add a note
- Manual override actions require a note.
- Manual override notes are admin-only and must never be shown to customers.
- Admin order detail should include an admin-only payment timeline sourced from
  `payment_events`.

## Dashboard And Reporting

- Revenue metrics should count only paid or collected orders.
- Existing dashboard revenue must stop summing all orders once payment states exist.
- Dashboard/admin order views should add separate sections or filters for:
  - pending payments
  - failed payments
  - cancelled payments
- Admin payment status labels should be operational:
  - `pending`: "Stripe pending"
  - `pending_collection`: "COD pending collection"
  - `payment_review_required`: "Review required"

## Human-Friendly Order Numbers

- Human-friendly order numbers are required now.
- UUID remains useful for internal/public route identity.
- Sequence should be global forever, not reset yearly.
- Format should be autogenerated and should not make early customers feel they are
  order 1, 2, or 10.
- Use a random-looking public order number so order volume is not inferable, for
  example an `AM-7K2Q9F`-style code.
- Use `AM-` plus 6 Crockford Base32-style random characters, avoiding ambiguous
  characters such as `O`, `I`, and `L`.
- If a generated public order number collides, retry generation up to 10 times,
  then fail loudly rather than silently falling back to a weak format.
- Keep an internal numeric sequence for sorting, accounting, and admin operations.

## Security Controls For Further Review

- Rate limits are required. Proposed MVP thresholds:
  - checkout/order creation: max 5 attempts per 15 minutes per session, and max 20
    attempts per hour per IP
  - Stripe Checkout Session creation/retry: max 3 session creations per order and
    max 10 per hour per session
  - pay on delivery: max 2 orders per hour per session and max 5 per day per IP
  - public payment-status polling after Stripe return: max 60 requests per 5
    minutes per session/IP
  - webhooks: cap body size and verify signatures; do not apply ordinary IP rate
    limits to signed Stripe webhooks
- These numbers are conservative starting points for a low-volume shop and should
  be adjustable by constants after observing production logs.
- These thresholds are accepted as MVP constants.
- Pay-on-delivery extra security needs further discussion.
- Email OTP for pay on delivery is deferred to `openspec/changes/deferred/pay-on-delivery-email-otp/`.
- Automated Stripe refunds are deferred to `openspec/changes/deferred/stripe-refunds/`.
- MVP recommendation: admin handles refunds in Stripe Dashboard; app records refund
  events audit-only unless later expanded.
- Pay-on-delivery order creation must validate stock at submit time, the same as
  card checkout.
- In production, card payments can only be enabled with live Stripe keys. Test-mode
  Stripe keys may be shown as configured but must not allow production card payments.

## Payment Method Changes During Checkout

- If admin disables card payments while a customer has an active Stripe Checkout
  URL, block new Stripe sessions and retry attempts.
- Do not bulk-expire existing active Stripe Checkout URLs solely because the admin
  toggled card payments off.
- Already-paid webhooks must still be processed so completed payments are not lost.

## Proposal Boundary And Launch Prerequisites

- Write one combined proposal for payment integration and admin payment settings.
  Checkout behavior depends on settings, so splitting them would create an awkward
  intermediate state.
- Implementation completion should require local Stripe webhook verification with
  Stripe CLI or equivalent local webhook testing.
- Production card payments must remain disabled until the live Stripe webhook
  endpoint is configured and verified.

## Pay-On-Delivery Amount Locking

- Pay-on-delivery collection amount is locked at order creation.
- Once shipping pricing exists, the locked COD amount must include the server-side
  shipping amount snapshot.

## Open Questions To Continue

1. Review whether any decisions above should be changed before writing the proposal.
2. Decide whether to name the change `payment-integration` or something more
   specific like `stripe-cod-payments`.
