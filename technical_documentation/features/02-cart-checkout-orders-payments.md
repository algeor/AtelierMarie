# Cart, Checkout, Orders, And Payments

Use this when touching anything that can affect money, stock, order state, checkout, or payment.

This is the danger zone. Small changes here can break real sales.

## Main Backend Files

- `app/models/cart.py`: cart contracts.
- `app/models/orders.py`: order and payment contracts.
- `app/routes/cart.py`: cart HTTP endpoints.
- `app/routes/orders.py`: customer order/checkout endpoints.
- `app/routes/admin.py`: admin order list/detail/status/payment endpoints.
- `app/routes/webhooks.py`: Stripe webhook endpoint.
- `app/services/cart_service.py`: cart logic.
- `app/services/order_service.py`: checkout transaction and order state machine.
- `app/services/payment_service.py`: Stripe sessions and webhook state updates.
- `app/services/pricing.py`: discount/effective price helper.
- `app/services/analytics_service.py`: optional purchase event recording.

## Main Frontend Files

- `frontend/contexts/CartContext.tsx`
- `frontend/components/cart/*`
- `frontend/app/[locale]/checkout/page.tsx`
- `frontend/components/checkout/*`
- `frontend/app/[locale]/orders/*`
- `frontend/components/orders/*`
- `frontend/lib/api-client.ts`
- `frontend/lib/types.ts`

## Cart Rules

- Cart is keyed by session.
- Login should not destroy the cart.
- Quantity limits are enforced by backend config.
- Add/update/remove returns the updated cart.
- Product stock and active status matter before checkout.

## Checkout Transaction

Checkout does all critical writes inside one transaction:

1. Fetch cart rows with product data.
2. Reject empty cart.
3. Validate product active state and stock.
4. Compute effective item prices.
5. Validate/normalize shipping price data.
6. Insert `orders` row.
7. Insert immutable `order_items` rows.
8. Decrement product stock.
9. Clear purchased cart rows.
10. Queue customer/admin emails.
11. Commit.

Rule: if a later step fails, earlier steps must not half-stick.

## Price Rules

- Item prices come from server-side product data.
- Active discounts are computed server-side.
- `order_items.price_cents` is the purchase snapshot.
- `items_total_cents + shipping_cents = total_cents`.
- Free shipping is enforced server-side when item total reaches the threshold.
- Shipping price echoed from the client is range-validated and provenance-normalized. It is not treated as perfect truth.

## Order Status vs Payment Status

These are separate axes.

Order status is fulfillment:

- `pending`
- `confirmed`
- `shipped`
- `delivered`
- `cancelled`

Payment method is how the customer pays:

- `cod`
- `card`
- `bank_transfer`

Payment status is money state:

- `cod_pending`
- `pending`
- `paid`
- `failed`
- `refunded`

Do not mark an order `shipped` just because payment is paid. The owner still controls fulfillment.

## Payment Rules

### COD

- Default payment method.
- Checkout creates a real order immediately.
- Stock is decremented immediately.
- Customer gets `placed` email immediately.
- On `delivered`, COD payment auto-advances to `paid`.

### Card

- Backend creates local order first.
- Backend creates Stripe Checkout Session using server-calculated `total_cents`.
- Frontend redirects to Stripe only after backend returns a URL.
- Customer gets `payment_pending` email first.
- `placed` email is queued only after verified Stripe success marks payment `paid`.
- Stripe webhook must verify the raw body signature.
- Duplicate webhook events are idempotent.
- Retry session is allowed only for owned card orders in retryable states.

### Bank transfer

- Offered only when `BANK_IBAN` is configured.
- Checkout creates an order with payment `pending`.
- Customer gets payment instructions.
- Admin marks payment paid through the admin payment endpoint.
- Marking paid queues the normal `placed` email.

## Order State Machine

Allowed fulfillment transitions:

```text
pending -> confirmed | cancelled
confirmed -> shipped | cancelled
shipped -> delivered
delivered -> no next state
cancelled -> no next state
```

Shipping requires tracking fields unless Speedy waybill automation creates them.

Cancelling restores stock according to the service rules.

## Analytics Rule

`record_purchase_confirmed` is optional analytics coverage. It must not decide whether checkout succeeds.

## Safe Change Checklist

- Checkout still uses one transaction.
- Stock cannot go negative.
- Cart clears only for successfully ordered items.
- Order item snapshots stay immutable.
- Payment state and fulfillment state stay separate.
- Card success is based on verified webhook/backend status, not redirect URL.
- Email queue behavior matches payment method.
- Customer-facing totals match charged totals.
- Tests cover success, validation failure, stock failure, and retry/failure paths.

