# Routes, Services, And Models

This explains how backend code is supposed to be shaped.

## The Pattern

```text
HTTP request
  -> route validates HTTP concerns
  -> Pydantic parses request body/query/path
  -> route resolves dependencies like session/admin
  -> route calls service with plain values
  -> service does business work and SQL
  -> service returns dict/model-shaped data or raises custom error
  -> route maps result/error to response model/status
```

## Routes

Routes live in `app/routes`.

Routes should handle:

- path/query/body shape
- `Depends(...)`
- auth/session/admin dependencies
- response models
- HTTP status codes
- translating service exceptions
- small content-type checks where needed

Routes should not handle:

- multi-statement DB transactions
- price calculations
- stock rules
- provider payload construction
- repeated SQL blocks

## Services

Services live in `app/services`.

Services should handle:

- domain rules
- SQL reads/writes
- transaction boundaries
- external client orchestration
- custom exceptions
- return data that can be validated into response models

Service functions usually take an explicit `sqlite3.Connection` when they are part of a larger transaction or need testable DB control.

## Models

Models live in `app/models`.

Models should handle:

- request schema
- response schema
- field constraints
- simple validators
- literal status values

Models should not query the DB.

## Example: Checkout

Route file: `app/routes/orders.py`.

Service file: `app/services/order_service.py`.

Model file: `app/models/orders.py`.

Flow:

1. Route receives `CreateOrderRequest`.
2. Route checks JSON content type.
3. Route resolves session/user/locale/email.
4. Route calls `checkout(...)` service.
5. Service owns transaction, stock, totals, order rows, cart clearing, email queue.
6. Route optionally creates Stripe session for card payments.
7. Route returns `OrderResponse`.

## Example: Product Listing

Route file: `app/routes/products.py`.

Service file: `app/services/product_service.py`.

Model file: `app/models/products.py`.

Flow:

1. Route parses query params like search/page/filter/locale.
2. Service clamps pagination and builds safe SQL.
3. Service resolves locale fields.
4. Service attaches taxonomy/media/video fields.
5. Route returns response model.

## Adding A New Endpoint

Use this order:

1. Add or update Pydantic models.
2. Add service function and custom exceptions.
3. Add route function.
4. Map exceptions to standard error responses.
5. Add backend tests.
6. Update frontend type/api/mock if public/admin UI uses it.
7. Add or update docs if the workflow changed.

## Common Mistakes

- Returning raw SQLite rows from routes.
- Letting a provider exception bubble to FastAPI.
- Duplicating service SQL in admin and public routes.
- Adding a backend field and forgetting `frontend/lib/types.ts`.
- Trusting browser-computed prices.

