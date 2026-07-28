# Payment Integration - Proposal

## Motivation

AtelierMarie can currently accept checkout details and create orders, but it has
no real payment confirmation path. The shop needs secure card payments and a
controlled pay-on-delivery option without handling card data directly or trusting
frontend success pages.

The safest MVP is Stripe Checkout for cards, plus admin-controlled pay on
delivery for low-value local orders. Payment state must be separate from the
existing fulfillment order status so the owner can still review, confirm, ship,
and deliver orders manually.

## Scope

### Capabilities

1. **Stripe Checkout payments** - backend-created one-time Checkout Sessions,
   webhook-confirmed payment, 15-minute local stock reservation, secure retry.
2. **Pay on delivery** - admin-enabled COD-style payment method, capped at EUR 50,
   with manual admin collection marking.
3. **Payment settings** - `/admin/settings/payments` page backed by DB settings
   and append-only settings audit.
4. **Payment state and audit** - separate payment status, provider records, and
   append-only payment event timeline.
5. **Order numbers** - random-looking public order numbers plus internal sequence
   for sorting/accounting.
6. **Admin payment operations** - payment filters, payment timeline, manual
   overrides with required admin notes, review-required alerting.
7. **Customer payment UX** - explicit payment method selection, Stripe redirect
   status handling, clear pending/cancelled/paid labels.

## Non-Goals

- Storing card numbers, CVV, or raw card data.
- Saved cards, subscriptions, invoices, or Stripe Billing.
- Automated Stripe refunds. Deferred to `openspec/changes/deferred/stripe-refunds/`.
- Email OTP for pay on delivery. Deferred to
  `openspec/changes/deferred/pay-on-delivery-email-otp/`.
- Courier API COD shipment creation or courier payout reconciliation.
- Waiting for `shipping-pricing`. This change uses the existing server-side
  `total_cents` snapshot; shipping pricing can later change how that total is
  built.

## Technical Approach

- Keep SQLite as the Layer 1 system of record.
- Add payment summary fields to `orders`, a provider-level `payments` table, and
  append-only `payment_events`.
- Add `site_settings` and `site_setting_events` for payment method controls.
- Add env-only Stripe configuration: secret key, webhook secret, and mode/config
  health display. Secrets are never editable in admin.
- Create Checkout Sessions server-side only from the order snapshot.
- Verify Stripe webhooks using the raw body and Stripe signature, then process
  idempotently by unique event id.
- Run an expiry cleanup every 1 minute to cancel unpaid expired card reservations,
  restore stock, and attempt to expire active Stripe sessions.

## Impact

- Checkout API and UI become payment-aware.
- Admin order views and dashboard revenue must use payment status, not just order
  status.
- Existing email outbox timing changes: card order emails wait for paid webhook;
  pay-on-delivery emails send immediately after order creation.
- Production card payments remain disabled until live Stripe keys and live webhook
  endpoint are configured and verified.

## Open Implementation Verifications

- Confirm Stripe Checkout Session expiration constraints. If Stripe does not allow
  a 15-minute session expiry, keep local 15-minute expiry and call Stripe expire
  during cleanup.
- Choose the exact Stripe SDK/API version during implementation.
- Align webhook body-size cap between app and deployment config; initial target is
  about 64 KB.
