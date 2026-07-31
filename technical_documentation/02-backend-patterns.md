# Backend Patterns

Use this when touching `app/`.

## The Shape

```text
routes/      HTTP only: Depends, status codes, response models, error mapping
services/    Business rules: transactions, external calls, data decisions
models/      Pydantic contracts: request/response shapes and field validation
database.py  Schema, migrations, WAL setup, connection helpers
config.py    Env-driven settings via Pydantic Settings
```

If you put business logic in a route, you are probably making future tests harder.

## Route Rules

- Keep routes thin.
- Use Pydantic models for input/output.
- Translate service exceptions into the standard error envelope.
- Use dependencies for auth/session, not repeated cookie parsing.
- Do not let provider-specific exceptions escape routes.

Standard error shape:

```json
{
  "error": {
    "code": "SOME_CODE",
    "message": "Human-readable message",
    "details": null
  }
}
```

## Service Rules

- Services take explicit parameters.
- Services return plain data or raise custom exceptions.
- Services own transactions when multiple writes must succeed together.
- Use `BEGIN IMMEDIATE` for checkout-like stock mutations.
- Use parameterized SQL with `?` placeholders.
- Chain exceptions with `raise X(...) from exc` when wrapping.

High-risk services:

- `app/services/order_service.py`: stock, checkout, order state, shipping snapshots.
- `app/services/payment_service.py`: Stripe sessions and webhooks.
- `app/services/product_service.py`: product CRUD, search, discounts, taxonomy.
- `app/services/shipping_service.py`: courier price orchestration and fallback.
- `app/services/email_service.py`: durable outbox and email dispatch.
- `app/services/analytics_service.py`: optional event storage/reporting.

## Model Rules

- Backend contracts live in `app/models/*`.
- Frontend mirrors them in `frontend/lib/types.ts`.
- Money is always integer cents.
- Product IDs are text slugs/SKUs, not auto-increment IDs.
- Use `Literal[...]` for constrained status strings.
- For Pydantic v2 use `model_validate()`, `model_dump()`, and `field_validator`.

## Database Rules

- SQLite is the source of truth.
- WAL mode is enabled by startup.
- Foreign keys are enabled.
- Fresh schema may be stricter than an old local DB. Test fresh DB paths.
- Order items are snapshots. Do not join them back to current product data for historical order display.
- Product search uses FTS5 and sanitized query input.
- Analytics DuckDB is separate. Do not share connections with the main SQLite app.

## Config Rules

- Use `get_settings()` from `app/config.py`.
- Do not call `os.getenv()` in app code.
- Production refuses unsafe defaults for admin/JWT/CORS/analytics approval.
- Courier credentials are lazy-validated so the app can still start and fallback.

## Logging Rules

- Use `structlog.get_logger(__name__)`.
- Include request/order/product IDs where useful.
- Do not log PII: email, phone, address, notes, raw webhook payloads.
- Request IDs come from middleware. Keep them useful.

## External Services

- Google OAuth: cache JWKS safely, use circuit breaker behavior.
- Stripe: imported only inside payment/webhook code paths.
- Email: queue first, send through sweeper or immediate attempt. HTTP should not fail just because email is slow.
- Couriers: pricing can fallback. Shipping a Speedy order must not mark `shipped` if waybill creation fails.

## Test Rules

- Service tests should use service functions directly where possible.
- Route tests check HTTP shape, dependencies, and error mapping.
- Real middleware tests live under `tests/realapp/`.
- If a new column is added, test fresh DB creation and migration/backfill behavior.
- For checkout/order changes, test stock decrement, cart clear, immutable item snapshot, and rollback on failure.

