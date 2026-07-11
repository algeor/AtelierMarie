## ADDED Requirements

### Requirement: Batch order-item fetching
The `list_orders` and `list_orders_admin` functions SHALL fetch all order items in a single query using `WHERE order_id IN (...)` instead of issuing one query per order.

#### Scenario: List orders page with 20 orders
- **WHEN** a client requests `GET /v1/orders?page=1&limit=20` and there are 20+ orders
- **THEN** the system SHALL execute at most 3 SQL queries (count + orders + items) instead of 41

#### Scenario: Empty result set
- **WHEN** a client requests orders and the page has 0 results
- **THEN** the system SHALL execute at most 2 queries (count + orders) and skip the items query

### Requirement: FTS5 search with SQL-level filtering
The product search endpoint SHALL push category and stock filters into the SQL query alongside the FTS5 MATCH clause, applying LIMIT/OFFSET at the database level.

#### Scenario: Search with category filter
- **WHEN** a client requests `GET /v1/products?q=lavender&category=floral`
- **THEN** the SQL query SHALL include both the FTS5 MATCH and a `category = ?` WHERE clause, and only matching rows are returned from the database

#### Scenario: Search with in-stock filter
- **WHEN** a client requests `GET /v1/products?q=lavender&in_stock=true`
- **THEN** the SQL query SHALL include `stock > 0` in the WHERE clause

#### Scenario: Pagination applied at SQL level
- **WHEN** FTS5 matches 500 products but page=1&limit=20 is requested
- **THEN** only 20 rows SHALL be fetched from the database (not 500 loaded into Python memory)

### Requirement: Batch CSV import existence check
The admin CSV import endpoint SHALL determine whether each product ID already exists by pre-fetching all existing IDs in a single query, not by probing per-row.

#### Scenario: Import 500-row CSV
- **WHEN** an admin uploads a 500-row CSV file
- **THEN** the system SHALL execute one `SELECT id FROM products WHERE id IN (...)` query (or equivalent batch) instead of 500 individual SELECT queries
