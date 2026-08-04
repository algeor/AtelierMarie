# Request And Data Flow

This explains the main flows developers modify most often.

## Product Listing Flow

```text
Browser page
  -> frontend lib/api.ts
  -> real api-client or mock-api
  -> GET /v1/products
  -> app/routes/products.py
  -> app/services/product_service.py
  -> Postgres products + taxonomy + media/video attachers
  -> ProductListResponse
  -> ProductGrid/ProductCard
```

Important details:

- Locale affects resolved product names/descriptions.
- Taxonomy filters are slugs, not display labels.
- Images/videos are attached in batches to avoid N+1 work.
- Public results show active products.

## Add To Cart Flow

```text
AddToCartButton
  -> CartContext
  -> POST /v1/cart
  -> cart route
  -> cart_service.add_item
  -> validate product active + stock + quantity bounds
  -> cart response
  -> cart drawer/badge updates
```

Important details:

- Cart is session-keyed.
- Quantity limits are backend-enforced.
- Optimistic frontend updates must reconcile with backend response.

## Checkout Flow

```text
checkout page
  -> delivery details + payment method + shipping quote
  -> POST /v1/orders
  -> orders route resolves session/user/locale/email
  -> order_service.checkout opens BEGIN IMMEDIATE
  -> stock/product/price/shipping validation
  -> insert order + order_items
  -> decrement stock
  -> clear cart
  -> queue email rows
  -> commit
  -> optional Stripe session creation for card
  -> optional analytics event
  -> response to frontend
```

Important details:

- Server computes item totals.
- Order items are immutable snapshots.
- Card redirect URL is not proof of payment.
- Analytics is not a checkout dependency.

## Card Payment Flow

```text
checkout creates card order
  -> payment_status = pending
  -> payment_service creates Stripe Checkout Session
  -> frontend redirects customer to Stripe
  -> Stripe redirects customer back
  -> frontend fetches backend order/payment state
  -> Stripe sends webhook
  -> raw body signature verified
  -> payment_service marks order paid
  -> placed email queued
```

Important details:

- The backend Stripe session amount comes from the stored order total.
- Duplicate webhooks are deduped through `stripe_events`.
- Session expiry sets payment failed only for the matching current session.

## Ship Order Flow

```text
admin order detail
  -> status change to shipped
  -> admin route
  -> order_service.update_status
  -> if Speedy and no tracking supplied, create waybill first
  -> tracking fields required/generated
  -> order status becomes shipped
  -> shipped email queued
```

Important details:

- Speedy waybill failure keeps order `confirmed`.
- Tracking display does not drive the order state machine.

## Email Flow

```text
business event
  -> insert order_emails/contact_messages queued row
  -> email_outbox_loop wakes every ~15s
  -> claim eligible row
  -> render template by locale/event
  -> provider sends
  -> row becomes sent/failed/skipped
```

Important details:

- Business event should not fail because provider is slow.
- The DB guards duplicate successful sends for the same order/event.
- Suppressed recipients are skipped.

## Analytics Flow

```text
cookie consent accepted
  -> frontend tracking emits events
  -> POST /v1/analytics/events
  -> validate + dedupe
  -> JSONL and/or DuckDB storage
  -> admin reports read DuckDB and Postgres order totals
```

Important details:

- No consent means no frontend event emission.
- Backend purchase coverage can still record a consent-aware purchase event.
- Analytics failures are isolated.

