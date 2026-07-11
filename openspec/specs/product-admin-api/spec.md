## ADDED Requirements

### Requirement: Admin can create a product
The system SHALL expose `POST /v1/admin/products` accepting a JSON body matching CreateProductRequest. The endpoint SHALL return 201 with the created ProductResponse. The endpoint SHALL return 409 if a product with the given ID already exists. The product ID SHALL be provided in the request body as a slug/SKU string.

#### Scenario: Successful product creation
- **WHEN** `POST /v1/admin/products` is called with valid product data and admin auth
- **THEN** the response is 201 with the full product, and the product exists in the database

#### Scenario: Duplicate product ID
- **WHEN** `POST /v1/admin/products` is called with an ID that already exists
- **THEN** the response is 409 with `{error: {code: "DUPLICATE", message: "Product with this ID already exists"}}`

#### Scenario: Invalid product data (missing required fields)
- **WHEN** `POST /v1/admin/products` is called without `name` or `price_cents`
- **THEN** the response is 422 with validation error details

### Requirement: Admin can update a product
The system SHALL expose `PUT /v1/admin/products/{product_id}` accepting a JSON body matching UpdateProductRequest (all fields optional). The endpoint SHALL partially update only the provided fields. The endpoint SHALL return 200 with the updated ProductResponse. The endpoint SHALL return 404 if the product does not exist.

#### Scenario: Partial update (name only)
- **WHEN** `PUT /v1/admin/products/lavender-dream-300ml` is called with `{name: "Lavender Dream XL"}`
- **THEN** only name is changed, other fields are preserved, updated_at is refreshed

#### Scenario: Update non-existent product
- **WHEN** `PUT /v1/admin/products/no-such-id` is called
- **THEN** the response is 404

### Requirement: Admin can deactivate a product
The system SHALL expose `DELETE /v1/admin/products/{product_id}` which sets `is_active=0` (soft delete). The endpoint SHALL return 200 with the deactivated product. The endpoint SHALL return 404 if the product does not exist. The product row SHALL remain in the database.

#### Scenario: Successful deactivation
- **WHEN** `DELETE /v1/admin/products/lavender-dream-300ml` is called with admin auth
- **THEN** the product's is_active is set to 0, response is 200 with updated product

#### Scenario: Deactivate non-existent product
- **WHEN** `DELETE /v1/admin/products/no-such-id` is called
- **THEN** the response is 404

### Requirement: Admin can bulk import products via CSV
The system SHALL expose `POST /v1/admin/products/import` accepting a CSV file as multipart/form-data. The CSV SHALL have columns: `id`, `name`, `description`, `price_cents`, `category`, `stock`, `image_url`. The endpoint SHALL use upsert semantics (create new, update existing). The endpoint SHALL skip rows with validation errors and continue processing. The endpoint SHALL return `{created: N, updated: N, errors: [{row: N, message: "..."}]}`.

#### Scenario: Import new products
- **WHEN** a CSV with 5 new valid products is uploaded
- **THEN** all 5 are created and response shows `{created: 5, updated: 0, errors: []}`

#### Scenario: Import with upsert (mixed new and existing)
- **WHEN** a CSV contains 3 new products and 2 products with existing IDs
- **THEN** 3 are created, 2 are updated, response shows `{created: 3, updated: 2, errors: []}`

#### Scenario: Import with validation errors
- **WHEN** a CSV contains rows with missing `name` or negative `price_cents`
- **THEN** invalid rows are skipped, valid rows are processed, errors array contains row numbers and messages

#### Scenario: Import with missing required columns
- **WHEN** a CSV is uploaded without the `id` or `name` column headers
- **THEN** the response is 400 with an error message listing missing columns

#### Scenario: Import empty CSV (headers only)
- **WHEN** a CSV with only headers and no data rows is uploaded
- **THEN** the response is 200 with `{created: 0, updated: 0, errors: []}`

### Requirement: Admin endpoints require admin authentication
All admin endpoints (`/v1/admin/*`) SHALL require admin authentication. The system SHALL accept EITHER a valid JWT cookie with `is_admin=true` OR a valid `Authorization: Bearer <ATELIER_ADMIN_API_KEY>` header. If neither is provided, the response SHALL be 401 Unauthorized. If credentials are provided but the user is not admin, the response SHALL be 403 Forbidden.

#### Scenario: Access with valid API key
- **WHEN** an admin endpoint is called with `Authorization: Bearer <valid_key>`
- **THEN** the request is authorized and proceeds

#### Scenario: Access without any credentials
- **WHEN** an admin endpoint is called without auth headers
- **THEN** the response is 401

#### Scenario: Access with invalid API key
- **WHEN** an admin endpoint is called with `Authorization: Bearer wrong-key`
- **THEN** the response is 401

#### Scenario: Empty API key configuration denies all access
- **WHEN** `ATELIER_ADMIN_API_KEY` is not configured (empty string) AND a request is made with `Authorization: Bearer ` (empty value)
- **THEN** the response is 401 (empty key MUST NOT match empty config)

### Requirement: Admin can list all products including inactive
The system SHALL expose `GET /v1/admin/products` returning a paginated list of ALL products (active and inactive). This allows admins to see deactivated products and re-activate them.

#### Scenario: Admin list includes inactive products
- **WHEN** `GET /v1/admin/products` is called with admin auth and inactive products exist
- **THEN** both active and inactive products appear in the response

### Requirement: Admin can get a single product including inactive
The system SHALL expose `GET /v1/admin/products/{product_id}` returning a single product regardless of its active status. This allows admins to view deactivated products for re-activation or inspection. The endpoint SHALL return 404 if the product does not exist.

#### Scenario: Admin gets inactive product
- **WHEN** `GET /v1/admin/products/discontinued-candle` is called with admin auth and the product exists but is inactive
- **THEN** the response is 200 with the full ProductResponse (is_active=false visible)

#### Scenario: Admin gets non-existent product
- **WHEN** `GET /v1/admin/products/no-such-id` is called with admin auth
- **THEN** the response is 404
