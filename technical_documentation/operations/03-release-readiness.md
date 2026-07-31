# Release Readiness

Use this before shipping risky changes.

## Always Check

- App starts.
- Backend tests for changed domain pass.
- Frontend tests for changed page/component pass.
- Lint passes or known unrelated failures are documented.
- Env examples updated if new settings were added.
- Docs updated if workflow/rule changed.

## High-Risk Area Checks

### Checkout/orders/payments

Verify:

- empty cart rejected
- stock decremented once
- cart clears after success
- order item price snapshot correct
- COD order email behavior
- card payment pending/paid behavior
- bank transfer instructions if enabled
- cancellation stock restoration
- admin order transitions

### Shipping

Verify:

- office delivery works
- door delivery works
- disabled courier/method rejected
- live quote fallback works
- free shipping threshold works
- shipped transition requires tracking or creates Speedy waybill

### Product/admin/media

Verify:

- create product
- edit product
- deactivate/reactivate product
- upload image
- set primary image
- upload video or failure path
- public listing/detail still render

### Auth/admin

Verify:

- anonymous browsing/cart/checkout
- login callback
- logout
- cart refresh after session rotation
- admin guard plus backend admin denial

### Legal/analytics

Verify:

- privacy/cookies text matches behavior
- analytics denied path
- analytics accepted path
- production guard for analytics legal approval

## Commands

Focused backend example:

```bash
.venv/bin/pytest tests/test_order_service.py tests/test_payment_integration.py -v --tb=short
```

Focused frontend example:

```bash
cd frontend && npx vitest run __tests__/app/checkout.test.tsx
```

All backend:

```bash
make test-backend
```

All frontend:

```bash
make test-frontend
```

Lint:

```bash
make lint
```

## Do Not Ship If

- checkout depends on analytics
- frontend controls charged amount
- Stripe redirect is treated as payment proof
- admin-only behavior has only frontend protection
- webhooks parse before signature verification
- email provider failure can undo order state
- product safety/legal copy is missing from product/checkout surfaces

