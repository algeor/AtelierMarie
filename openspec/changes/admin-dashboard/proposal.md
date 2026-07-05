# Admin Dashboard — Proposal

## Why

The AtelierMarie platform captures rich event data (page views, product clicks, cart actions, purchases, search queries) and maintains products and orders in SQLite, but there is no visibility into business performance. An admin dashboard surfaces conversion metrics, popular products, search analytics, and recommendation effectiveness — essential for a data-driven boutique candle business.

Without this, the store operator must query databases manually or rely on intuition. The dashboard closes the feedback loop between marketing/merchandising decisions and measurable outcomes.

## What Changes

### New API Endpoints

- **GET /v1/admin/dashboard** — Aggregate metrics including total views, unique sessions, total orders, conversion rate, add-to-cart rate, total revenue, top products, popular search terms, session breakdown, and recommendation CTR.
- **GET /v1/admin/events** — Paginated event log with filtering by event_type and date range.
- **GET /v1/admin/products** — All products with computed view_count, cart_count, and order_count from event data.
- **GET /v1/admin/orders** — Paginated order list with status, totals, item counts, and user/session info.

### Admin Access Control

- First-user-as-admin: the first Google sign-in auto-promotes the user to admin (is_admin=TRUE on users table).
- API key for programmatic access: X-Admin-API-Key header checked against ATELIER_ADMIN_API_KEY env var.
- All /v1/admin/* endpoints gated behind admin auth dependency.

### Frontend Admin Page

- New /(admin)/dashboard route with metrics cards, sortable tables, and session/recommendation summaries.
- Admin auth gate redirects non-admin users.

## Capabilities (New)

| Capability | Description |
|---|---|
| `dashboard-metrics` | Aggregate business metrics computed from DuckDB events + SQLite orders |
| `admin-events-log` | Paginated event browser with type and date filtering |
| `admin-products` | Product performance view (views, carts, orders per product) |
| `admin-orders` | Order management list with status and pagination |
| `admin-access-control` | Dual auth model — Google user with is_admin flag + API key bearer token |

## Impact

- **New routes**: /v1/admin/dashboard, /v1/admin/events, /v1/admin/products, /v1/admin/orders
- **New frontend**: /(admin) route group with dashboard page
- **DuckDB**: Aggregate queries over events and sessions tables
- **Dependencies**:
  - `google-oauth` — user model with is_admin flag
  - `event-ingestion-pipeline` — events data in DuckDB
  - `orders-checkout` — order data in SQLite
