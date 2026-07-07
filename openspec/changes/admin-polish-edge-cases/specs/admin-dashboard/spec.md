## ADDED Requirements

### Requirement: Admin dashboard returns aggregate statistics
The system SHALL provide a `GET /v1/admin/dashboard` endpoint that returns operational statistics computed from SQLite. The endpoint MUST require admin authentication (JWT `is_admin` or API key). The response MUST include `Cache-Control: no-store, no-cache` headers to prevent caching of sensitive business data by proxies or browsers.

Note: The existing stub `GET /v1/admin/stats` is renamed to `GET /v1/admin/dashboard` (the stub returns 501 so this is not a breaking change).

#### Scenario: Successful dashboard retrieval
- **WHEN** an authenticated admin requests `GET /v1/admin/dashboard`
- **THEN** the system returns 200 with a JSON body containing:
  - `total_orders` (integer): count of all non-cancelled orders
  - `total_revenue_cents` (integer): sum of `total_cents` from all non-cancelled orders (uses `COALESCE(SUM(...), 0)` for empty tables)
  - `total_products` (integer): count of active products (`is_active = 1`)
  - `carts_with_items` (integer): count of distinct sessions with cart items (note: includes expired sessions — acceptable at MVP scale)
  - `orders_by_status` (object): keys are status strings, values are counts (e.g., `{"pending": 3, "confirmed": 5, "shipped": 2, "delivered": 10}`). Empty dict if no orders exist.

#### Scenario: Dashboard with no orders
- **WHEN** an authenticated admin requests `GET /v1/admin/dashboard` and no orders exist
- **THEN** the system returns 200 with `total_orders: 0`, `total_revenue_cents: 0`, `orders_by_status: {}`, and accurate counts for products and carts

#### Scenario: Unauthenticated access denied
- **WHEN** a request to `GET /v1/admin/dashboard` has no credentials (no JWT cookie, no API key)
- **THEN** the system returns 401 with `{error: {code: "UNAUTHORIZED", message: "Authentication required"}}`

#### Scenario: Non-admin authenticated access denied
- **WHEN** a request to `GET /v1/admin/dashboard` has a valid JWT but `is_admin` is false
- **THEN** the system returns 403 with `{error: {code: "FORBIDDEN", message: "Admin access required"}}`

#### Scenario: Dashboard response time
- **WHEN** the database contains up to 10,000 orders and 1,000 products
- **THEN** the dashboard endpoint MUST respond within 200ms

#### Scenario: Cache-Control header present
- **WHEN** the dashboard endpoint returns a response (any status code)
- **THEN** the response includes `Cache-Control: no-store, no-cache` header

### Requirement: Dashboard excludes cancelled orders from revenue
The system SHALL NOT include cancelled orders in `total_orders` or `total_revenue_cents` calculations. Cancelled orders MUST still appear in `orders_by_status` with their count.

Note: Revenue includes pending orders because at MVP there is no payment integration — all placed orders are considered committed. When payment processing is added, revenue should exclude unpaid orders (filter to `status IN ('confirmed', 'shipped', 'delivered')`).

#### Scenario: Revenue excludes cancelled orders
- **WHEN** there are 5 orders (3 confirmed at 2000 cents each, 2 cancelled at 1500 cents each)
- **THEN** `total_orders` is 3, `total_revenue_cents` is 6000, and `orders_by_status` includes `{"confirmed": 3, "cancelled": 2}`
