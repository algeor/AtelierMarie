## MODIFIED Requirements

### Requirement: Product service searches products by text
The product service SHALL perform full-text search across product name, description, and category using PostgreSQL `tsvector` columns and GIN indexes. User search input SHALL be passed to `plainto_tsquery(config, $1)` — never interpolated into SQL — which safely treats operator characters (`&`, `|`, `!`, `<->`) as literal words. The service SHALL choose the English or Bulgarian tsvector index based on the requested locale and SHALL return results ranked by `ts_rank_cd(...)` descending. Only active products SHALL appear in results.

#### Scenario: Search matching products
- **WHEN** `search_products("lavender", locale="en")` is called and products with "lavender" in name, description, or category exist and are active
- **THEN** matching products are returned sorted by `ts_rank_cd` descending

#### Scenario: Search with no matches
- **WHEN** `search_products("xyznonexistent", locale="en")` is called
- **THEN** an empty list is returned

#### Scenario: Search excludes inactive products
- **WHEN** `search_products("discontinued", locale="en")` is called and the matching product has `is_active = FALSE`
- **THEN** an empty list is returned

#### Scenario: Search with special characters treated as literal text
- **WHEN** `search_products("lavender & poison", locale="en")` is called
- **THEN** `plainto_tsquery` treats the input as literal words "lavender" and "poison" — the `&` is NOT interpreted as a boolean AND operator, and no SQL injection is possible

#### Scenario: English stemming works
- **WHEN** `search_products("candles", locale="en")` is called and a product has `name_en = 'Aromatic Candle'`
- **THEN** the product matches, because the `english` config stems "candles" and "candle" to the same lexeme

#### Scenario: Bulgarian search uses simple config
- **WHEN** `search_products("лавандула", locale="bg")` is called
- **THEN** the query targets `search_bg` using `plainto_tsquery('simple', $1)` and matches products whose Bulgarian content contains "лавандула" as a lowercased token

### Requirement: Product service lists active products with pagination
The product service SHALL return a paginated list of active products. The service SHALL accept optional filters for category, in-stock-only, and a sort parameter. Default sort SHALL be by `created_at` descending (newest first). The service SHALL return the total count of matching products alongside the page of results. The page number SHALL be clamped to a maximum of 10,000 and limit SHALL be clamped to a maximum of 100. All filters (including search) SHALL be applied at the SQL level with `LIMIT` and `OFFSET`, never post-fetch in Python.

#### Scenario: List products with default parameters
- **WHEN** `list_products()` is called with no filters
- **THEN** the service returns up to 20 active products sorted by created_at descending, with total count

#### Scenario: Excessive page number is clamped
- **WHEN** `list_products(page=9999999)` is called
- **THEN** the service uses page=10000 (the maximum), not page=9999999

#### Scenario: Excessive limit is clamped
- **WHEN** `list_products(limit=5000)` is called
- **THEN** the service uses limit=100 (the maximum)

#### Scenario: Pagination returns correct slice
- **WHEN** `list_products(page=2, limit=5)` is called with 12 matching products
- **THEN** products 6–10 are returned with total=12, page=2, limit=5

## ADDED Requirements

### Requirement: Product service uses row locks for stock decrement
When the product service decrements stock as part of a checkout transaction, it SHALL first acquire row-level locks on the affected product rows via `SELECT ... FOR UPDATE ORDER BY id ASC`. This prevents the TOCTOU race between stock validation and decrement.

#### Scenario: Stock validated under lock
- **WHEN** the checkout service calls the product service to reserve stock for a set of product IDs
- **THEN** the product service opens (or joins) a transaction, issues `SELECT id, stock, price_cents FROM products WHERE id = ANY($1::text[]) ORDER BY id ASC FOR UPDATE`, validates each requested quantity against the locked `stock`, and only then issues the `UPDATE products SET stock = stock - $N WHERE id = $id` statements

#### Scenario: Insufficient stock raises before write
- **WHEN** the locked stock is less than the requested quantity for any product
- **THEN** the product service raises `InsufficientStockError` before any `UPDATE` runs
- **AND** the surrounding transaction rolls back, releasing all locks

#### Scenario: Deterministic lock order prevents deadlock
- **WHEN** two concurrent checkouts each involve products with the same set of IDs in different input orders
- **THEN** both `SELECT ... FOR UPDATE` statements order by `id ASC`, so locks are acquired in the same sequence and no deadlock is possible
