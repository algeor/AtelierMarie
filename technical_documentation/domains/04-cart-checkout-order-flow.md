# Cart, Checkout, And Order Flow

This is the core sales path.

## Main Backend Files

- `app/models/cart.py`
- `app/models/orders.py`
- `app/routes/cart.py`
- `app/routes/orders.py`
- `app/routes/admin.py`
- `app/services/cart_service.py`
- `app/services/order_service.py`

## Main Frontend Files

- `frontend/contexts/CartContext.tsx`
- `frontend/components/cart/*`
- `frontend/app/[locale]/checkout/page.tsx`
- `frontend/components/checkout/*`
- `frontend/app/[locale]/orders/*`
- `frontend/components/orders/*`

## Cart Read Flow

```text
CartContext hydrates
  -> GET /v1/cart?locale=...
  -> cart_service.get_cart
  -> active items and unavailable items separated
  -> effective prices computed
  -> taxonomy/media attached
  -> CartResponse
```

Unavailable items happen when products are deleted or deactivated after they were added.

## Add/Update/Remove Flow

- Add validates active product, stock, per-item max, and max distinct items.
- Update validates quantity and stock.
- Remove deletes the cart row.
- All return the full updated cart.

## Checkout Flow

Checkout is intentionally one service transaction.

```text
order_service.checkout
  -> BEGIN IMMEDIATE
  -> read cart + product rows
  -> reject empty cart
  -> collect inactive/stock failures
  -> compute effective prices
  -> validate shipping price/provenance
  -> insert order
  -> insert order_items snapshots
  -> decrement stock
  -> delete purchased cart items
  -> queue email rows
  -> COMMIT
```

Why `BEGIN IMMEDIATE` matters:

- It serializes checkout writers.
- It reduces last-item race conditions.
- The DB `CHECK (stock >= 0)` is still the final guard.

## Order Items Are Snapshots

`order_items` stores:

- product id text
- product name at purchase time
- price at purchase time
- quantity

It does not FK to products on purpose. Historical orders must survive product changes/deletion.

## Order State Machine

Fulfillment status transitions:

```text
pending -> confirmed | cancelled
confirmed -> shipped | cancelled
shipped -> delivered
delivered -> no next state
cancelled -> no next state
```

Shipping requires tracking number and carrier unless Speedy waybill creation fills them.

## Cancellation

Cancellation restores stock for order items when allowed by the service.

Do not add new cancellation paths without checking:

- current status
- payment method
- payment status
- email behavior
- stock restoration

## Safe Change Checklist

- Empty cart rejected.
- Product inactive rejected.
- Stock failure returns all failed items when possible.
- Stock cannot go negative.
- Cart clears only after successful order creation.
- Email queue rows match payment method.
- Order list/detail still includes items and payment/shipping fields.

