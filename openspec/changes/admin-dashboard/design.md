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

All aggregate queries (event counts, session breakdowns, search term frequencies, recommendation CTR) run against DuckDB. Product and order entity lookups use SQLite. Cross-DB joins (e.g., product names for top-viewed products) are performed in the Python service layer — fetch IDs from DuckDB, then batch-lookup details from SQLite.

**Rationale**: DuckDB excels at analytical aggregation over columnar event data. SQLite holds normalized relational data. Mixing in application code is simpler than maintaining a denormalized view.

### 2. In-memory cache with 5-minute TTL

Dashboard metrics are cached in a module-level dict with timestamp. On request: if cache age < 5 min, serve cached. Otherwise, recompute asynchronously and serve stale until ready.

**Rationale**: Dashboard queries scan potentially millions of events. A 5-minute window is acceptable for a single-operator boutique. Avoids need for Redis or external cache.

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

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| DuckDB aggregate queries slow with >1M events | Medium | High (dashboard timeout) | 5-min cache + time-bounded queries (default 30d window) |
| Admin role escalation if first-user logic exploited | Low | Medium | Acceptable for single-operator boutique; add manual override env var |
| Cross-DB consistency (events reference product IDs that don't exist in SQLite) | Low | Low | Graceful handling — show "Unknown Product" for missing IDs |
| Cache serving very stale data if recomputation fails | Low | Medium | Log errors, expose cache age in response headers |
