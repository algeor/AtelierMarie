## ADDED Requirements

### Requirement: List products with filtering
The system SHALL expose GET /products that returns a paginated list of products. It SHALL support query parameters for category filtering, sorting (price, name, created_at), and pagination (limit, offset).

#### Scenario: List all products
- **WHEN** a client sends GET /products
- **THEN** the API returns a JSON array of products with id, name, slug, price, category, image_url, and stock_quantity (default limit 20)

#### Scenario: Filter by category
- **WHEN** a client sends GET /products?category=dessert-candles
- **THEN** only products with category "dessert-candles" are returned

#### Scenario: Pagination
- **WHEN** a client sends GET /products?limit=10&offset=10
- **THEN** products 11–20 are returned with total count in response metadata

### Requirement: Get product by slug
The system SHALL expose GET /products/{slug} that returns full product details including all attributes (name, slug, description, price, category, scent, wax_type, burn_time, stock_quantity, image_url, created_at).

#### Scenario: Valid slug returns product
- **WHEN** a client sends GET /products/vanilla-dream-jar
- **THEN** the API returns the full product object with all attributes

#### Scenario: Invalid slug returns 404
- **WHEN** a client sends GET /products/nonexistent-product
- **THEN** the API returns HTTP 404 with error message "Product not found"

### Requirement: Admin product creation
The system SHALL expose POST /products/admin that creates a new product. The endpoint SHALL validate all required fields (name, price, category) and auto-generate slug from name. It SHALL require admin authentication.

#### Scenario: Create product with valid data
- **WHEN** an admin sends POST /products/admin with name "Vanilla Dream", price 34.99, category "luxury-jars"
- **THEN** the product is created with auto-generated slug "vanilla-dream" and returned with HTTP 201

#### Scenario: Missing required fields returns 422
- **WHEN** a client sends POST /products/admin with missing price field
- **THEN** the API returns HTTP 422 with validation error details

#### Scenario: Unauthenticated request returns 401
- **WHEN** an unauthenticated client sends POST /products/admin
- **THEN** the API returns HTTP 401

### Requirement: Product search endpoint
The system SHALL expose GET /products/search?q={query} that performs text search across product name, description, and category fields. Results SHALL be ranked by relevance.

#### Scenario: Search returns matching products
- **WHEN** a client sends GET /products/search?q=vanilla
- **THEN** products containing "vanilla" in name or description are returned, ordered by relevance

#### Scenario: Empty search returns empty array
- **WHEN** a client sends GET /products/search?q=xyznonexistent
- **THEN** the API returns an empty array with HTTP 200

### Requirement: Stock quantity validation
The system SHALL prevent adding out-of-stock products to cart. The stock_quantity SHALL be decremented atomically on successful checkout.

#### Scenario: Out-of-stock product rejected
- **WHEN** a client attempts to add a product with stock_quantity 0 to cart
- **THEN** the API returns HTTP 409 with message "Product out of stock"

#### Scenario: Stock decrements on checkout
- **WHEN** an order is placed for 2 units of a product with stock_quantity 5
- **THEN** the product's stock_quantity is updated to 3
