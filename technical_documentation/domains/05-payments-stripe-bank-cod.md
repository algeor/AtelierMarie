# Payments: COD, Card, And Bank Transfer

Payment status is separate from fulfillment status.

## Main Backend Files

- `app/models/orders.py`: payment method/status literals.
- `app/routes/orders.py`: checkout and card retry endpoint.
- `app/routes/admin.py`: admin payment mark-paid endpoint.
- `app/routes/webhooks.py`: Stripe webhook endpoint.
- `app/services/order_service.py`: payment fields on order creation and COD delivery behavior.
- `app/services/payment_service.py`: Stripe session and webhook state updates.
- `app/services/email_service.py`: payment-aware email queue/rendering.
- `app/config.py`: Stripe and bank transfer settings.

## Current Names

Payment methods:

- `cod`
- `card`
- `bank_transfer`

Payment statuses:

- `cod_pending`
- `pending`
- `paid`
- `failed`
- `refunded`

Some old specs used `stripe` or `pay_on_delivery`. Current code uses the names above.

## COD Flow

```text
checkout payment_method=cod
  -> order payment_status=cod_pending
  -> stock decremented
  -> cart cleared
  -> placed email queued
  -> admin later moves fulfillment status
  -> when delivered, payment_status becomes paid
```

COD is the default.

## Card Flow

```text
checkout payment_method=card
  -> reject if Stripe secret missing
  -> order payment_status=pending
  -> payment_pending email queued
  -> Stripe Checkout Session created from order total
  -> frontend redirects to Stripe URL
  -> Stripe webhook verifies raw signature
  -> checkout.session.completed marks paid
  -> placed email queued
```

Important rules:

- Frontend never controls payable amount.
- Redirect success URL is not proof of payment.
- Customer page must fetch backend status.
- Webhook event IDs are deduped.
- Session expired event only affects matching current Stripe session.

## Card Retry Flow

Endpoint:

```text
POST /v1/orders/{order_id}/stripe-session
```

Rules:

- Caller must own the order through session/user visibility.
- Order must be card payment.
- Already-paid order returns conflict.
- Only `pending` or `failed` payment states are retryable.
- New Stripe session overwrites stored session id.

## Bank Transfer Flow

```text
checkout payment_method=bank_transfer
  -> allowed only when BANK_IBAN configured
  -> order payment_status=pending
  -> payment_pending email includes bank instructions
  -> admin marks payment paid
  -> placed email queued
```

Bank instruction settings:

- `BANK_IBAN`
- `BANK_BIC`
- `BANK_NAME`

## Admin Payment Mark Paid

Current explicit admin mark-paid operation is for bank transfer orders.

Rules:

- Only admin can call it.
- Only bank transfer order is accepted.
- Already paid returns conflict.
- Success queues `placed` email.

## Abandoned Card Cleanup

Background cleanup cancels old abandoned card orders:

- payment method `card`
- payment status `pending` or `failed`
- older than 24 hours
- status not cancelled/delivered
- restores stock

It does not touch COD or bank transfer orders.

## Safe Change Checklist

- Payment status and fulfillment status stay separate.
- Card email is not misleading before payment is paid.
- Webhook verifies raw body signature.
- Duplicate webhooks do not duplicate email/state changes.
- COD delivery still marks payment paid.
- Bank transfer is hidden/rejected when IBAN is missing.

