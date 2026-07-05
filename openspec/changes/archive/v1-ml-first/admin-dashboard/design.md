# Admin Dashboard — Design

## Context

AtelierMarie is a luxury candle e-commerce platform with:
- **Event pipeline** (DuckDB): page_view, product_click, add_to_cart, remove_from_cart, purchase, search events with session tracking
- **Product catalog** (SQLite): products with name, price, stock, category, active status
- **Orders** (SQLite): orders with items, status, totals, user/session references
- **Sessions** (DuckDB): session records with anonymous/authenticated state, event counts

The admin dashboard aggregates data across all stores to provide a unified business performance view.

## Goals

- Real-time-ish metrics with 5-minute cache (avoid stale data without hammering DuckDB on every request)
- Actionable insights: top products, failing searches (zero results), conversion funnel stages
- Simple single-page dashboard that loads fast and surfaces the most important numbers immediately
- Dual auth model supporting both browser-based admin access and programmatic/CLI tooling

## Non-Goals

- Real-time streaming or WebSocket push updates
- Exportable reports (CSV, PDF)
- Multi-user RBAC (roles beyond admin/non-admin)
- Audit logging of admin actions
- Custom date range charts (MVP uses fixed windows: today, 7d, 30d)
- Alerting or threshold notifications

## Decisions

### 1. DuckDB for aggregates, SQLite for entity data

All aggregate metrics (event counts, session breakdowns, search term frequencies, recommendation CTR) are read from pre-materialized `analytics_*` tables computed by the shared analytics layer. DuckDB aggregate queries are no longer run per-request. Direct DuckDB queries are only used for: (a) the paginated event log, and (b) custom date-range requests that don't match the default 30-day window. Product and order entity lookups use SQLite. Cross-DB joins (e.g., product names for top-viewed products) are performed in the Python service layer — fetch IDs from analytics tables, then batch-lookup details from SQLite.

**Rationale**: DuckDB excels at analytical aggregation over columnar event data, but running these queries per-request is unnecessary now that the analytics layer materializes results every 5 minutes. SQLite holds normalized relational data. Reading from pre-materialized tables is simpler and faster than running aggregate queries on each dashboard load.

### 2. Analytics tables replace per-request caching

Since the analytics layer materializes tables every 5 minutes, the dashboard no longer needs its own caching layer for aggregate metrics. The pre-materialized `analytics_*` tables serve as the primary "cache." A lightweight 30-second in-memory cache may be used to deduplicate rapid-fire requests from a single page load (e.g., multiple metric cards fetching simultaneously), but this is purely for request deduplication, not for freshness management.

**Rationale**: Eliminates duplicate caching logic (analytics layer already refreshes on a 5-minute schedule). Guarantees consistency between what ML services and the admin dashboard see — both read the same materialized tables. Removes a source of cache invalidation bugs that existed when the dashboard maintained its own independent cache.

### 3. Single admin page with metric cards and tables

Frontend is one page with:
- Top row: metric cards (views, sessions, orders, conversion %, add-to-cart %, revenue)
- Second row: top products table (sortable), popular search terms table
- Third row: recent orders table, session breakdown summary, recommendation CTR card

No charting library for MVP — use numbers with optional CSS sparklines or progress bars for visual weight.

**Rationale**: Minimizes frontend complexity. Charts can be added later without architectural changes. Numbers are more actionable than pretty graphs for a solo operator.

### 4. Dual auth: is_admin flag + API key

Browser access: JWT token decoded, user looked up, is_admin checked. Returns 403 if not admin.
Programmatic access: X-Admin-API-Key header compared against ATELIER_ADMIN_API_KEY env var. If match, bypass user lookup.

First-user-as-admin: when a Google sign-in occurs and the users table is empty (count=0), that user gets is_admin=TRUE automatically.

**Rationale**: Simple for single-operator store. API key enables scripts (product import, inventory sync) without browser flow. First-user bootstrap avoids manual DB edits on initial deploy.

### 5. Service-layer metrics computation

All metric computations live in a dedicated service module (e.g., `services/admin_metrics.py`), not in route handlers. Routes call service functions that return typed dataclasses/dicts.

**Rationale**: Testability — service functions can be unit-tested with mock DB connections. Route handlers stay thin. Reusable if we add scheduled reports later.

### 6. Fallback to direct query for custom date ranges

The default dashboard view (last 30 days) reads from analytics tables. When the user specifies custom `from`/`to` query parameters that don't match the materialized window, the dashboard falls through to a direct DuckDB query against the raw events table. This is expected to be rare (admin checking specific historical periods) and acceptable to compute on-demand since it only occurs on explicit user action, not on every page load.

**Rationale**: The analytics layer materializes a fixed 30-day window to serve the common case efficiently. Supporting arbitrary date ranges without pre-computation keeps the analytics layer simple while still giving admins full flexibility when needed.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Analytics layer failure degrades dashboard | Low | High (dashboard shows stale data) | Dashboard shows last available data from analytics tables with a staleness warning in response headers |
| Admin role escalation if first-user logic exploited | Low | Medium | Acceptable for single-operator boutique; add manual override env var |
| Cross-DB consistency (events reference product IDs that don't exist in SQLite) | Low | Low | Graceful handling — show "Unknown Product" for missing IDs |
| Cache serving very stale data if recomputation fails | Low | Medium | Log errors, expose cache age in response headers |
