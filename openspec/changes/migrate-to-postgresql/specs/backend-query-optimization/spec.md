## MODIFIED Requirements

### Requirement: FTS5 search with SQL-level filtering
The product search endpoint SHALL push category and stock filters into the SQL query alongside the tsvector MATCH clause, applying LIMIT/OFFSET at the database level.

#### Scenario: Search with category filter
- **WHEN** a client requests `GET /v1/products?q=lavender&category=floral`
- **THEN** the SQL query SHALL include both `search_en @@ plainto_tsquery('english', $1)` and a `category = $2` WHERE clause, and only matching rows are returned from the database

#### Scenario: Search with in-stock filter
- **WHEN** a client requests `GET /v1/products?q=lavender&in_stock=true`
- **THEN** the SQL query SHALL include `stock > 0` in the WHERE clause

#### Scenario: Pagination applied at SQL level
- **WHEN** the tsvector match would return 500 products but page=1&limit=20 is requested
- **THEN** only 20 rows SHALL be fetched from the database (not 500 loaded into Python memory)

## ADDED Requirements

### Requirement: Postgres query plans use appropriate indexes
The critical Layer 1 queries SHALL be supported by indexes so that `EXPLAIN` shows index scans (never sequential scans) on production-sized tables. Required indexes: `idx_products_category`, `idx_products_is_active`, `idx_products_search_en` (GIN), `idx_products_search_bg` (GIN), `idx_orders_session_id`, `idx_orders_user_id`, `idx_orders_status`, `idx_sessions_expires_at`, `idx_cart_items_session_id`, `idx_reactions_product_type`, `idx_reactions_session_created`, `idx_reaction_toggle_log_session_time`, `idx_comments_product_created`, `idx_comments_session_created`.

#### Scenario: Product listing uses index
- **WHEN** `EXPLAIN GET /v1/products?category=floral&in_stock=true` is executed
- **THEN** the plan uses `idx_products_category` and does not sequentially scan `products`

#### Scenario: Search uses GIN index
- **WHEN** `EXPLAIN` is run on a search query against `search_en`
- **THEN** the plan shows a bitmap index scan against `idx_products_search_en`

#### Scenario: Session cleanup uses index
- **WHEN** `EXPLAIN DELETE FROM sessions WHERE expires_at < NOW()` is executed
- **THEN** the plan uses an index scan on `idx_sessions_expires_at`

### Requirement: Partial indexes for hot boolean filters
Where a column's value is heavily skewed and the "true" or "active" subset is the common query filter, the schema SHALL define a partial index rather than a full index. Specifically, `idx_products_is_active` SHALL be defined as `WHERE is_active = TRUE` and `idx_orders_status_open` (new) SHALL cover status IN ('pending','confirmed','shipped') to speed admin queue queries.

#### Scenario: Public listing uses partial active index
- **WHEN** `GET /v1/products` runs its listing query filtered by `is_active = TRUE`
- **THEN** the plan uses the partial index (which is smaller than a full index on `is_active`) and is faster than a sequential scan

#### Scenario: Admin queue uses partial status index
- **WHEN** the admin fetches orders in states `pending`, `confirmed`, or `shipped`
- **THEN** the query plan uses `idx_orders_status_open` and skips fully-delivered / cancelled rows without touching them
