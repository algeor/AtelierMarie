## ADDED Requirements

### Requirement: Product service lists active products with pagination
The product service SHALL return a paginated list of active products. The service SHALL accept optional filters for category, in-stock-only, and a sort parameter. Default sort SHALL be by `created_at` descending (newest first). The service SHALL return the total count of matching products alongside the page of results.

#### Scenario: List products with default parameters
- **WHEN** `list_products()` is called with no filters
- **THEN** the service returns up to 20 active products sorted by created_at descending, with total count

#### Scenario: List products filtered by category
- **WHEN** `list_products(category="dessert")` is called
- **THEN** only active products with category "dessert" are returned

#### Scenario: List products sorted by price ascending
- **WHEN** `list_products(sort="price_asc")` is called
- **THEN** active products are returned ordered by price_cents ascending

#### Scenario: Pagination returns correct slice
- **WHEN** `list_products(page=2, limit=5)` is called with 12 matching products
- **THEN** products 6–10 are returned with total=12, page=2, limit=5

### Requirement: Product service retrieves a single product by ID
The product service SHALL return a single product by its text ID (slug/SKU). The service SHALL raise a NotFoundError if the product does not exist or is inactive.

#### Scenario: Get existing active product
- **WHEN** `get_product("lavender-dream-300ml")` is called and the product exists and is active
- **THEN** the full product data is returned

#### Scenario: Get inactive product
- **WHEN** `get_product("discontinued-candle")` is called and the product exists but `is_active=0`
- **THEN** a NotFoundError is raised

#### Scenario: Get non-existent product
- **WHEN** `get_product("no-such-product")` is called
- **THEN** a NotFoundError is raised

### Requirement: Product service creates a product
The product service SHALL create a new product with a merchant-provided text ID. The service SHALL reject creation if a product with the same ID already exists (409 Conflict). The service SHALL set `created_at` and `updated_at` to the current UTC timestamp.

#### Scenario: Create a new product
- **WHEN** `create_product(id="rose-garden-250ml", name="Rose Garden", price_cents=2400, stock=50)` is called
- **THEN** the product is inserted into the database and the full product row is returned

#### Scenario: Create product with duplicate ID
- **WHEN** `create_product(id="existing-product", ...)` is called and a product with that ID exists
- **THEN** a DuplicateError is raised

### Requirement: Product service upserts a product
The product service SHALL provide an `upsert_product(id, data)` method that creates the product if it doesn't exist, or updates it if it does. This uses `INSERT ... ON CONFLICT(id) DO UPDATE SET ...`. Only fields provided (non-None) SHALL be updated on conflict. The service SHALL set `created_at` on insert and `updated_at` on both insert and update.

#### Scenario: Upsert new product
- **WHEN** `upsert_product(id="new-candle", name="New Candle", price_cents=2400, stock=10)` is called and no product with that ID exists
- **THEN** the product is created and returned

#### Scenario: Upsert existing product
- **WHEN** `upsert_product(id="existing-candle", name="Updated Name", price_cents=2800)` is called and the product exists
- **THEN** only the provided fields are updated, other fields preserved, and the updated product is returned

### Requirement: Product service updates a product
The product service SHALL partially update an existing product. Only fields provided (non-None) SHALL be modified. The service SHALL update `updated_at` to the current UTC timestamp. The service SHALL raise NotFoundError if the product does not exist.

#### Scenario: Update product name and price
- **WHEN** `update_product("lavender-dream-300ml", name="Lavender Dream XL", price_cents=3200)` is called
- **THEN** only name and price_cents are changed; other fields remain unchanged; updated_at is refreshed

#### Scenario: Update non-existent product
- **WHEN** `update_product("no-such-product", name="X")` is called
- **THEN** a NotFoundError is raised

### Requirement: Product service deactivates a product (soft delete)
The product service SHALL set `is_active=0` on a product. The row SHALL remain in the database. The service SHALL raise NotFoundError if the product does not exist.

#### Scenario: Deactivate an active product
- **WHEN** `deactivate_product("lavender-dream-300ml")` is called
- **THEN** the product's `is_active` is set to 0 and `updated_at` is refreshed

#### Scenario: Deactivate already-inactive product
- **WHEN** `deactivate_product("already-inactive")` is called
- **THEN** no error is raised (idempotent); `is_active` remains 0

### Requirement: Product service searches products by text
The product service SHALL perform full-text search across product name and description using SQLite FTS5. The service SHALL return results ranked by relevance. Only active products SHALL appear in results.

#### Scenario: Search matching products
- **WHEN** `search_products("lavender")` is called and products with "lavender" in name or description exist
- **THEN** matching active products are returned sorted by FTS5 relevance rank

#### Scenario: Search with no matches
- **WHEN** `search_products("xyznonexistent")` is called
- **THEN** an empty list is returned

#### Scenario: Search excludes inactive products
- **WHEN** `search_products("discontinued")` is called and the matching product is inactive
- **THEN** an empty list is returned

### Requirement: Product service validates stock is non-negative
The product service SHALL enforce that stock can never go below zero. The database CHECK constraint (`stock >= 0`) SHALL be the ultimate enforcement. Service-level operations that decrement stock SHALL verify sufficiency before executing.

#### Scenario: Stock update to negative rejected
- **WHEN** `update_product("x", stock=-1)` is called
- **THEN** the database rejects the update with an IntegrityError

#### Scenario: Stock remains valid after update
- **WHEN** `update_product("x", stock=0)` is called
- **THEN** the update succeeds (zero is valid)
