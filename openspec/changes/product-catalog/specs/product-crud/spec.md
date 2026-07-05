## ADDED Requirements

### Requirement: Admin can create a product
The system SHALL accept a POST request to `/v1/admin/products` with product data and create a new product in the catalog. The request body MUST include `id`, `name`, and `price`. Optional fields: `description`, `category`, `image_url`, `is_active`, `is_featured`. The system SHALL return the created product with `201 Created`.

#### Scenario: Successful product creation
- **WHEN** admin sends POST `/v1/admin/products` with `{"id": "blue-widget", "name": "Blue Widget", "price": 9.99}`
- **THEN** system creates the product and returns 201 with the full product object including `created_at` and `updated_at` timestamps

#### Scenario: Duplicate product ID
- **WHEN** admin sends POST `/v1/admin/products` with an `id` that already exists
- **THEN** system returns 409 Conflict with error message indicating the ID is taken

#### Scenario: Missing required fields
- **WHEN** admin sends POST `/v1/admin/products` without `name` or `price`
- **THEN** system returns 422 Unprocessable Entity with validation error details

### Requirement: Admin can list all products
The system SHALL accept a GET request to `/v1/admin/products` and return a paginated list of ALL products (including inactive). The system SHALL support query parameters: `page` (default 1), `per_page` (default 20, max 100), `category` (filter), `is_active` (filter), `is_featured` (filter).

#### Scenario: List products with default pagination
- **WHEN** admin sends GET `/v1/admin/products` with no parameters
- **THEN** system returns page 1 with up to 20 products and metadata `{"items": [...], "total": N, "page": 1, "per_page": 20}`

#### Scenario: Filter by category
- **WHEN** admin sends GET `/v1/admin/products?category=electronics`
- **THEN** system returns only products where category equals "electronics"

#### Scenario: Filter by active status
- **WHEN** admin sends GET `/v1/admin/products?is_active=false`
- **THEN** system returns only soft-deleted (inactive) products

#### Scenario: Empty catalog
- **WHEN** admin sends GET `/v1/admin/products` and no products exist
- **THEN** system returns `{"items": [], "total": 0, "page": 1, "per_page": 20}`

### Requirement: Admin can get a single product
The system SHALL accept a GET request to `/v1/admin/products/{id}` and return the product regardless of its active status.

#### Scenario: Get existing product
- **WHEN** admin sends GET `/v1/admin/products/blue-widget`
- **THEN** system returns the product with 200 OK

#### Scenario: Get non-existent product
- **WHEN** admin sends GET `/v1/admin/products/no-such-product`
- **THEN** system returns 404 Not Found

### Requirement: Admin can update a product
The system SHALL accept a PUT request to `/v1/admin/products/{id}` with updated fields and apply the changes. Only provided fields SHALL be updated (partial update semantics). The system SHALL update the `updated_at` timestamp on every modification.

#### Scenario: Update product price
- **WHEN** admin sends PUT `/v1/admin/products/blue-widget` with `{"price": 12.99}`
- **THEN** system updates the price and `updated_at`, returns the full updated product with 200 OK

#### Scenario: Update non-existent product
- **WHEN** admin sends PUT `/v1/admin/products/no-such-product` with any body
- **THEN** system returns 404 Not Found

#### Scenario: Reactivate a soft-deleted product
- **WHEN** admin sends PUT `/v1/admin/products/blue-widget` with `{"is_active": true}`
- **THEN** system sets `is_active` to true, making the product visible on the public API again

### Requirement: Admin can soft-delete a product
The system SHALL accept a DELETE request to `/v1/admin/products/{id}` and set `is_active = FALSE` on the product. The product row SHALL NOT be physically deleted.

#### Scenario: Soft delete existing product
- **WHEN** admin sends DELETE `/v1/admin/products/blue-widget`
- **THEN** system sets `is_active = FALSE` and `updated_at` to current time, returns 200 OK with the updated product

#### Scenario: Delete non-existent product
- **WHEN** admin sends DELETE `/v1/admin/products/no-such-product`
- **THEN** system returns 404 Not Found

#### Scenario: Delete already-inactive product
- **WHEN** admin sends DELETE `/v1/admin/products/blue-widget` where product is already inactive
- **THEN** system returns 200 OK (idempotent — no error, `updated_at` refreshed)
