# Backend Testing Fixtures

The backend tests are optimized for speed without ignoring real middleware entirely.

## Test Layout

```text
tests/
  test_*.py          Unit/service/route tests
  realapp/           Integration tests with real middleware behavior
conftest.py          Shared fixtures and helpers
```

## Main Fixture Strategy

Most tests use module-scoped app/client/db fixtures.

Why:

- `init_db()` and `create_app()` are expensive.
- Rebuilding them per test made the suite slow.
- Per-test cleanup deletes data rows instead.

## Fake Session Middleware

Route tests usually replace real session middleware with `FakeSessionMiddleware`.

It stamps a fixed `session_id` on the request without DB cookie work.

Use it for:

- product route tests
- cart route tests
- order route tests where session mechanics are not the point

Do not use it for:

- session cookie tests
- expiry/sliding lifetime tests
- login/logout rotation behavior

Those belong in `tests/realapp/` or session-specific tests.

## Important Helpers

- `make_session(conn)`: inserts a session row.
- `seed_products(conn)`: inserts default product rows.
- `admin_client`: async client with admin Bearer header.
- `service_db`: raw SQLite connection for service tests without app setup.

## Cleanup

Autouse cleanup deletes rows after each test in FK-safe order.

It preserves the fake session row used by route tests.

## Choosing A Test Type

| Change | Test target |
|---|---|
| Pure service logic | service test with `service_db`. |
| HTTP status/response/errors | route test with `client` or `admin_client`. |
| Middleware/session behavior | `tests/realapp/` or session-specific tests. |
| Schema change | database test plus affected service/route tests. |
| Checkout/payment/shipping | service and route tests, plus edge cases. |
| Email template | renderer/service tests. |
| Webhook | signature, duplicate event, and state mutation tests. |

## Test Smells

- Copy-pasted product/session insert blocks instead of helpers.
- Route test asserting deep business internals better suited to service test.
- Service test going through HTTP for no reason.
- Test passes only because frontend mock data differs from backend reality.
- New status added without badge/label tests.

