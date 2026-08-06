## REMOVED Requirements

### Requirement: FTS5 search with SQL-level filtering
**Reason**: FTS5 is SQLite-specific and is removed with the SQLite backend.
**Migration**: Use Postgres full-text search with SQL-level filters and pagination.

## ADDED Requirements

### Requirement: Postgres full-text search with SQL-level filtering
The product search endpoint SHALL use Postgres full-text search and SHALL push category, taxonomy, stock, active-state, sort, and pagination filters into SQL.

#### Scenario: Search with category filter
- **WHEN** a client requests `GET /v1/products?q=lavender&category=floral`
- **THEN** the SQL query includes both full-text search and a category or taxonomy filter
- **AND** only matching rows are returned from the database

#### Scenario: Search with in-stock filter
- **WHEN** a client requests `GET /v1/products?q=lavender&in_stock=true`
- **THEN** the SQL query includes a stock predicate equivalent to `stock > 0`

#### Scenario: Pagination applied at SQL level
- **WHEN** full-text search matches 500 products but page=1&limit=20 is requested
- **THEN** only the requested page of rows is fetched from the database

#### Scenario: Locale-specific search fields are used
- **WHEN** a client searches with locale `bg`
- **THEN** search uses Bulgarian product name and description fields for matching
- **AND** English fields remain available for English locale searches
