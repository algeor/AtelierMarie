# Payment Integration - Tasks

## 1. Schema And Migration

- [x] 1.1 Add order payment summary fields: internal sequence, `order_number`, `payment_method`, `payment_status`, `reserved_until`, `paid_at`, `collected_at`, `payment_return_token`.
- [x] 1.2 Add `payments` table for provider, amount/currency, Stripe Checkout Session ID, Stripe PaymentIntent ID, provider status/details, timestamps.
- [x] 1.3 Add `payment_events` table with unique Stripe event id support and append-only event metadata.
- [x] 1.4 Add `site_settings` and `site_setting_events` tables for payment settings and audit.
- [x] 1.5 Add indexes for admin filters: payment status, payment method, reserved_until, order_number, Stripe IDs.
- [x] 1.6 Backfill existing orders with safe payment defaults and generated public order numbers.

## 2. Configuration And Settings

- [x] 2.1 Add Stripe env config: secret key, webhook secret, publishable key if needed, mode/config health helpers.
- [x] 2.2 Enforce production live-key requirement before card payments can be enabled.
- [x] 2.3 Implement payment settings service with defaults: card disabled, pay on delivery disabled, max 5000 cents.
- [x] 2.4 Implement settings audit writes with admin id/email, key, old/new values, timestamp, request id.
- [x] 2.5 Add public safe settings endpoint for checkout payment-method availability.
- [x] 2.6 Add admin settings endpoints for `/v1/admin/settings/payments`.

## 3. Payment Models And Services

- [x] 3.1 Add Pydantic models for payment method, payment status, payment settings, payment events, checkout responses.
- [x] 3.2 Implement random public order number generation: `AM-` + 6 unambiguous Base32 chars, 10 collision retries.
- [x] 3.3 Implement payment service for card order creation, provider row creation, Stripe session creation, and retry/reuse.
- [x] 3.4 Implement pay-on-delivery order creation with EUR 50 cap, stock validation, immediate stock decrement, and immediate order email.
- [x] 3.5 Implement manual admin payment actions: mark paid, mark collected, mark refunded/review transition, cancel, all with required note.
- [x] 3.6 Ensure card payment order email queues only after `payment_status = paid`.

## 4. Stripe Integration

- [x] 4.1 Add Stripe client wrapper isolated behind service functions.
- [x] 4.2 Create one-time Checkout Sessions from server-side order snapshots only.
- [x] 4.3 Add success/cancel URLs using `payment_return_token`.
- [x] 4.4 Reuse active unexpired sessions for valid retry; block reuse after paid/cancelled/expired.
- [x] 4.5 On local expiry cleanup, attempt to expire active Stripe Checkout Sessions.
- [x] 4.6 Verify Stripe Checkout Session expiry constraints and document final behavior in design if Stripe minimum differs from 15 minutes.

## 5. Webhooks And Expiry

- [x] 5.1 Add `POST /v1/webhooks/stripe` using raw body signature verification and session middleware skip.
- [x] 5.2 Process allowlisted events: `checkout.session.completed`, `checkout.session.expired`, `payment_intent.payment_failed`, `charge.refunded` audit-only.
- [x] 5.3 Store Stripe event ids uniquely and make processing idempotent.
- [x] 5.4 Mark paid on completed sessions only when local reservation/order state is valid.
- [x] 5.5 Mark late successes after local expiry as `failed` with a `requires_review` payment event; admin email/in-app alert surface remains tracked by 7.7.
- [x] 5.6 Add 1-minute cleanup loop for expired unpaid card reservations, stock restoration, event logging, and Stripe session expiry attempts.
- [x] 5.7 Add webhook body-size cap and align deployment notes.

## 6. Rate Limiting And Security

- [x] 6.1 Add checkout/order creation rate limits per session/IP.
- [x] 6.2 Add Stripe session creation/retry rate limits per order/session.
- [x] 6.3 Add stricter pay-on-delivery rate limits per session/IP.
- [x] 6.4 Add payment-status polling rate limits.
- [x] 6.5 Ensure logs avoid email, phone, address, notes, and raw webhook payloads.
- [x] 6.6 Add tests for invalid content type, disabled methods, amount tampering, expired token, wrong session retry, and production test-key rejection.

## 7. Backend API And Admin

- [x] 7.1 Update `POST /v1/orders` or add checkout endpoint to accept selected payment method and return Stripe URL when needed.
- [x] 7.2 Update order response/list models with payment status, method, order number, reservation info, and payment labels as needed.
- [x] 7.3 Add admin filters for payment status/method and include payment summary in admin order lists.
- [x] 7.4 Add admin order detail payment timeline from `payment_events`.
- [x] 7.5 Add admin payment review actions with required note.
- [x] 7.6 Update dashboard revenue queries to count only paid/collected orders and show pending/failed/cancelled payment sections.
- [x] 7.7 Add immediate admin email and in-app alert path for `payment_review_required`.

## 8. Frontend Checkout And Customer Pages

- [x] 8.1 Fetch safe payment settings in checkout and render enabled payment methods.
- [x] 8.2 Add payment method selection with default card when both methods are enabled.
- [x] 8.3 Show accepted checkout copy for card reservation and pay-on-delivery collection.
- [x] 8.4 Redirect to Stripe Checkout for card payments; route to order confirmation/status for pay on delivery.
- [x] 8.5 Add Stripe return/cancel status page behavior: fetch order/payment status, never trust redirect alone.
- [x] 8.6 Update order history to show pending/cancelled card attempts clearly.
- [x] 8.7 Update order detail/confirmation copy by payment method/status.

## 9. Frontend Admin

- [x] 9.1 Add `/admin/settings/payments` page and sidebar navigation.
- [x] 9.2 Show Stripe config health and mode as read-only.
- [x] 9.3 Add card/pay-on-delivery toggles and pay-on-delivery max amount control.
- [x] 9.4 Reject UI save when both payment methods are disabled; surface backend validation errors.
- [x] 9.5 Add admin order payment filters/labels and payment timeline UI.
- [x] 9.6 Add manual payment action modals/forms requiring notes.

## 10. Tests And Verification

- [x] 10.1 Backend unit tests for order number generation, settings service, payment state transitions, expiry cleanup, and manual overrides.
- [x] 10.2 Backend route tests for checkout card/COD flows, disabled methods, COD cap, rate limits, and access control.
- [x] 10.3 Webhook tests for signature rejection, idempotency, allowlisted events, late success review, failed payment, expired session, refund audit-only.
- [x] 10.4 Frontend tests for checkout payment selection, settings page, customer labels, Stripe return status, and admin timeline/actions.
- [x] 10.5 Run local Stripe CLI webhook verification and document commands/results before marking complete.
- [x] 10.6 Update `.env.example`, frontend env examples, deployment docs, and test plans.
