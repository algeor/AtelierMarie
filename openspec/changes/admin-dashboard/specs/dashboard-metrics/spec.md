# Dashboard Metrics — Spec

## ADDED Requirements

### Requirement: Aggregate metrics endpoint returns core business KPIs

The GET /v1/admin/dashboard endpoint must return total_views, unique_sessions, total_orders, conversion_rate (orders divided by sessions), add_to_cart_rate (add_to_cart events divided by sessions), and total_revenue.

For the default 30-day window, these metrics are read from pre-materialized `analytics_funnel` and `analytics_session_metrics` tables computed by the analytics layer. Direct DuckDB queries are only executed when custom date range parameters (`from`/`to`) are provided.

#### Scenario: Dashboard returns all core metrics for default 30-day window

WHEN an admin requests GET /v1/admin/dashboard without date parameters
THEN the response contains total_views as an integer count of all page_view events in the last 30 days
AND unique_sessions as the distinct count of session_ids in the last 30 days
AND total_orders as the count of completed orders in the last 30 days
AND conversion_rate as a decimal (total_orders / unique_sessions)
AND add_to_cart_rate as a decimal (add_to_cart events / unique_sessions)
AND total_revenue as the sum of all completed order totals in the last 30 days

#### Scenario: Dashboard returns zero metrics when no data exists

WHEN an admin requests GET /v1/admin/dashboard
AND there are no events or orders in the system
THEN the response contains total_views=0, unique_sessions=0, total_orders=0, conversion_rate=0.0, add_to_cart_rate=0.0, total_revenue=0.0

#### Scenario: Conversion rate handles division by zero

WHEN an admin requests GET /v1/admin/dashboard
AND there are events but unique_sessions is 0
THEN conversion_rate is returned as 0.0
AND add_to_cart_rate is returned as 0.0

---

### Requirement: Top 10 products by views, add-to-cart, and purchases

The dashboard returns three ranked lists: top 10 products by view count, top 10 by add-to-cart count, and top 10 by purchase count.

For the default 30-day window, product metrics are read from `analytics_product_metrics`. Product names are resolved via batch SQLite lookup.

#### Scenario: Top products by views returns ranked list with product details

WHEN an admin requests GET /v1/admin/dashboard
AND multiple products have page_view events
THEN the response includes top_products_by_views as a list of up to 10 items
AND each item contains product_id, product_name, and view_count
AND the list is ordered by view_count descending

#### Scenario: Top products by add-to-cart reflects cart activity

WHEN an admin requests GET /v1/admin/dashboard
AND products have add_to_cart events
THEN the response includes top_products_by_cart as a list of up to 10 items
AND each item contains product_id, product_name, and cart_count
AND the list is ordered by cart_count descending

#### Scenario: Top products by purchases reflects completed orders

WHEN an admin requests GET /v1/admin/dashboard
AND products appear in completed orders
THEN the response includes top_products_by_purchases as a list of up to 10 items
AND each item contains product_id, product_name, and purchase_count
AND the list is ordered by purchase_count descending

#### Scenario: Fewer than 10 products returns all available

WHEN an admin requests GET /v1/admin/dashboard
AND only 3 products have view events
THEN top_products_by_views contains exactly 3 items

---

### Requirement: Popular search terms aggregation

The dashboard returns the top 20 search queries by frequency, including the average result count per query.

#### Scenario: Popular searches returns ranked terms

WHEN an admin requests GET /v1/admin/dashboard
AND there are search events with query metadata
THEN the response includes popular_searches as a list of up to 20 items
AND each item contains query (the search term), search_count, and avg_result_count
AND the list is ordered by search_count descending

#### Scenario: Search terms are normalized for aggregation

WHEN an admin requests GET /v1/admin/dashboard
AND search events contain queries "Vanilla", "vanilla", and "VANILLA"
THEN these are aggregated as a single term with combined search_count

#### Scenario: Zero-result searches are included

WHEN an admin requests GET /v1/admin/dashboard
AND some search events have result_count=0 in metadata
THEN those searches appear in popular_searches with their avg_result_count reflecting the zero results

---

### Requirement: Session breakdown by authentication state

The dashboard returns counts of anonymous sessions, authenticated sessions, and converted sessions (sessions that completed a purchase), plus average events per session.

#### Scenario: Session breakdown categorizes correctly

WHEN an admin requests GET /v1/admin/dashboard
AND there are sessions with and without user_id associations
THEN the response includes session_breakdown with anonymous_count (sessions never linked to a user)
AND authenticated_count (sessions linked to a user but no purchase)
AND converted_count (sessions that include at least one purchase event)
AND avg_events_per_session as the mean event count across all sessions

#### Scenario: A session that authenticates mid-flow counts as authenticated

WHEN a session starts anonymous and later associates with a user_id
AND the session does not complete a purchase
THEN it is counted in authenticated_count, not anonymous_count

---

### Requirement: Recommendation click-through rate

The dashboard computes CTR for product recommendations: impressions (recommendation shown) vs clicks (recommended product clicked).

CTR metrics are read from `analytics_ctr` table for the default view.

#### Scenario: Recommendation CTR computed from events

WHEN an admin requests GET /v1/admin/dashboard
AND there are recommendation_shown and recommendation_clicked events
THEN the response includes recommendation_ctr as a decimal (clicks / impressions)
AND recommendation_impressions as the total count
AND recommendation_clicks as the total count

#### Scenario: No recommendation data returns zero CTR

WHEN an admin requests GET /v1/admin/dashboard
AND there are no recommendation events
THEN recommendation_ctr is 0.0
AND recommendation_impressions is 0
AND recommendation_clicks is 0

---

### Requirement: Optional date range filtering

The dashboard accepts optional from and to query parameters (YYYY-MM-DD format) to scope all metrics to a specific date range.

#### Scenario: Date range filters all metrics

WHEN an admin requests GET /v1/admin/dashboard?from=2026-06-01&to=2026-06-30
THEN all metrics (views, sessions, orders, revenue, top products, searches, sessions, CTR) are computed using only data from June 1-30, 2026

#### Scenario: Only from parameter provided

WHEN an admin requests GET /v1/admin/dashboard?from=2026-06-15
THEN metrics are computed from June 15, 2026 through the current date

#### Scenario: Only to parameter provided

WHEN an admin requests GET /v1/admin/dashboard?to=2026-06-15
THEN metrics are computed from the earliest available data through June 15, 2026

#### Scenario: Invalid date format returns 422

WHEN an admin requests GET /v1/admin/dashboard?from=06/01/2026
THEN the response status is 422 Unprocessable Entity
AND the error message indicates the expected date format is YYYY-MM-DD

---

### Requirement: Metrics freshness reflects analytics layer schedule

Dashboard metrics for the default view are served from pre-materialized analytics tables (refreshed every 5 minutes by the analytics layer). The response includes freshness metadata.

#### Scenario: Response includes freshness metadata
WHEN an admin requests GET /v1/admin/dashboard
THEN the response includes `analytics_computed_at` (ISO timestamp of last analytics run)
AND the response includes `analytics_age_seconds` indicating staleness

#### Scenario: Default view reads from analytics tables
WHEN an admin requests GET /v1/admin/dashboard without date parameters
THEN metrics are read from analytics_funnel and analytics_session_metrics tables
AND no aggregate DuckDB queries are executed against the raw events table

#### Scenario: Custom date range triggers direct query
WHEN an admin requests GET /v1/admin/dashboard?from=2026-06-01&to=2026-06-15
THEN metrics are computed via direct DuckDB query against the events table (not from analytics tables)
AND the response includes `source: "direct_query"` instead of `source: "analytics_layer"`

---

### Requirement: Direct-query results are cached in-memory per date range

Custom date range queries hit DuckDB directly and are expensive. The system SHALL cache these results in-memory with a 5-minute TTL, keyed by the (from, to) parameter pair. The cache is bounded to prevent unbounded memory growth.

#### Scenario: Repeated date-range query served from cache

WHEN an admin requests GET /v1/admin/dashboard?from=2026-06-01&to=2026-06-30
AND the same date range was queried less than 5 minutes ago
THEN the cached result is returned without querying DuckDB
AND the response includes `source: "direct_query"` and `cached: true`

#### Scenario: Cache miss triggers DuckDB query

WHEN an admin requests GET /v1/admin/dashboard?from=2026-06-01&to=2026-06-30
AND no cache entry exists for that date range or it is older than 5 minutes
THEN fresh metrics are computed from DuckDB
AND the result is stored in cache with a 5-minute TTL

#### Scenario: Date-range cache limited to 10 entries

WHEN more than 10 distinct date-range query results are cached
THEN the least recently used entry is evicted to prevent unbounded memory growth

#### Scenario: Default view (no date range) is not cached in-memory

WHEN an admin requests GET /v1/admin/dashboard without date parameters
THEN the response is served from the pre-materialized analytics tables
AND no in-memory caching layer is involved (the analytics layer IS the cache)
