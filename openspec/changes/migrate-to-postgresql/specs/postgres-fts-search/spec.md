## ADDED Requirements

### Requirement: Product search uses tsvector + GIN index
The `products` table SHALL expose two generated `tsvector` columns — `search_en` (using the `english` text search configuration) and `search_bg` (using the `simple` text search configuration) — each concatenating weighted name, description, and category content. Each SHALL be backed by a `GIN` index.

#### Scenario: Search columns are generated
- **WHEN** the schema is inspected
- **THEN** `products.search_en` and `products.search_bg` exist as `tsvector` columns with `GENERATED ALWAYS AS (...) STORED`
- **AND** they combine `name_*` (weight A), `description_*` (weight B), and `category` (weight C) via `setweight(to_tsvector(config, coalesce(col, '')), weight)`

#### Scenario: GIN indexes exist for both languages
- **WHEN** the schema is inspected
- **THEN** `idx_products_search_en` and `idx_products_search_bg` exist as GIN indexes over `search_en` and `search_bg` respectively

#### Scenario: No FTS triggers exist
- **WHEN** the schema is inspected
- **THEN** no triggers named `products_fts_*` exist and no virtual FTS5 tables are present — the generated columns replace them entirely

### Requirement: Search index updates on write without triggers
Because the `tsvector` columns are `GENERATED ALWAYS AS ... STORED`, updates to `name_en`, `name_bg`, `description_en`, `description_bg`, or `category` SHALL cause Postgres to automatically recompute the search columns as part of the row write. No application code or trigger SHALL be responsible for maintaining the search index.

#### Scenario: Insert populates search columns
- **WHEN** a new product is inserted with `name_en = 'Lavender Dream'` and `description_en = 'Calming floral notes'`
- **THEN** immediately after insert, `search_en` contains the tokenized, weighted lexemes for those values and is queryable

#### Scenario: Update to name_en refreshes search_en
- **WHEN** an existing product's `name_en` is changed from 'Old Name' to 'New Fragrance'
- **THEN** the next query using `search_en @@ plainto_tsquery('english', 'fragrance')` matches this product
- **AND** the same query with `'old'` no longer matches

#### Scenario: Update to unrelated column does not touch search
- **WHEN** an existing product's `stock` is decremented
- **THEN** `search_en` and `search_bg` are unchanged (they depend on name/description/category only, not stock)

### Requirement: Search queries use plainto_tsquery for user input
The product service search function SHALL construct the tsquery from user input via `plainto_tsquery(config, $1)` — never by concatenating raw user input into the SQL. This safely escapes operators (`&`, `|`, `!`, `<->`) and treats input as literal words.

#### Scenario: User input with special operators is safe
- **WHEN** a client sends `q=lavender OR poison`
- **THEN** the service passes the entire string to `plainto_tsquery`, which treats it as literal words "lavender", "or", "poison" — the `OR` is NOT interpreted as a boolean operator
- **AND** no SQL injection is possible via the search parameter

#### Scenario: Empty search returns empty
- **WHEN** the client sends `q=` (empty string) or `q=` with only whitespace
- **THEN** the service SHALL NOT execute the tsvector query and SHALL fall through to the unfiltered listing path (or return empty, per existing behavior)

### Requirement: Search matches locale-appropriate index
The search implementation SHALL use `search_en` when `locale=en` and `search_bg` when `locale=bg`. The corresponding text search configuration (`english` vs. `simple`) SHALL be used in `plainto_tsquery` to match the index's configuration.

#### Scenario: English search uses English index and config
- **WHEN** `search_products("lavender", locale="en")` is called
- **THEN** the query is `WHERE search_en @@ plainto_tsquery('english', $1)` and results include products whose English content stems-matches "lavender"

#### Scenario: Bulgarian search uses Bulgarian index and simple config
- **WHEN** `search_products("лавандула", locale="bg")` is called
- **THEN** the query is `WHERE search_bg @@ plainto_tsquery('simple', $1)` and results include products whose Bulgarian content contains "лавандула" as a lowercased whitespace-split token

### Requirement: Search results ranked by relevance
The product service SHALL order search results by `ts_rank_cd(search_<locale>, plainto_tsquery(...)) DESC` before applying LIMIT/OFFSET, so that better matches appear first.

#### Scenario: Better matches come first
- **WHEN** `search_products("lavender", locale="en")` is called and product A has "lavender" in `name_en` while product B has it only in `description_en`
- **THEN** product A appears before product B in the result list (name has weight A, description has weight B)

#### Scenario: LIMIT/OFFSET applied at SQL level
- **WHEN** the tsvector match would return 500 rows but the request asks for `page=1&limit=20`
- **THEN** only 20 rows are fetched from Postgres — the ORDER BY + LIMIT are in the SQL, not applied in Python

### Requirement: Search combines with category, stock, and active filters
The search SQL SHALL include `WHERE is_active = TRUE` and — when the client supplies them — `category = $N` and `stock > 0` filters in the same WHERE clause as the tsvector match. Filters SHALL NOT be applied post-fetch in Python.

#### Scenario: Search plus category filter
- **WHEN** a client sends `GET /v1/products?q=lavender&category=floral`
- **THEN** the SQL query includes `search_en @@ plainto_tsquery('english', $1) AND category = $2 AND is_active = TRUE`

#### Scenario: Search plus in-stock filter
- **WHEN** a client sends `GET /v1/products?q=lavender&in_stock=true`
- **THEN** the SQL query includes `stock > 0` as an additional WHERE clause

#### Scenario: Inactive products never surface in search
- **WHEN** an inactive product has content that would match the tsquery
- **THEN** the `is_active = TRUE` predicate excludes it and it does NOT appear in the results

### Requirement: FTS5 code paths removed
After migration, no code under `app/` SHALL reference SQLite FTS5 tables (`products_fts`, `products_fts_en`, `products_fts_bg`), the `MATCH` operator against FTS tables, or the rebuild command (`INSERT INTO products_fts_* VALUES ('rebuild')`).

#### Scenario: Grep for FTS5 artifacts returns nothing
- **WHEN** `grep -RE "products_fts|MATCH|fts5" app/` is run
- **THEN** it produces no matches
