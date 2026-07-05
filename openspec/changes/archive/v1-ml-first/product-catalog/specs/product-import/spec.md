## ADDED Requirements

### Requirement: Admin can bulk import products via CSV
The system SHALL accept a POST request to `/v1/admin/products/import` with a CSV file upload and upsert products into the catalog. The CSV MUST have columns: `id`, `name`, `description`, `price`, `category`, `image_url`. On conflict (existing `id`), the system SHALL update all fields (upsert semantics).

#### Scenario: Successful CSV import with new products
- **WHEN** admin uploads a CSV with 100 new products (IDs not in database)
- **THEN** system creates all 100 products and returns `{"imported": 100, "updated": 0, "errors": []}`

#### Scenario: CSV import with existing products (upsert)
- **WHEN** admin uploads a CSV where 50 product IDs already exist in the database
- **THEN** system updates those 50 products with the CSV data and returns `{"imported": 0, "updated": 50, "errors": []}`

#### Scenario: Mixed import (new and existing)
- **WHEN** admin uploads a CSV with 80 new and 20 existing products
- **THEN** system returns `{"imported": 80, "updated": 20, "errors": []}`

#### Scenario: CSV with invalid rows
- **WHEN** admin uploads a CSV where some rows have missing `name` or invalid `price` (non-numeric)
- **THEN** system skips invalid rows, processes valid ones, and returns errors with row numbers: `{"imported": N, "updated": M, "errors": [{"row": 5, "error": "price must be numeric"}]}`

#### Scenario: Large CSV file (10k+ products)
- **WHEN** admin uploads a CSV with 10,000+ rows
- **THEN** system processes all rows without timeout, using streaming parse and batch inserts

#### Scenario: Empty CSV file
- **WHEN** admin uploads a CSV with only a header row and no data rows
- **THEN** system returns `{"imported": 0, "updated": 0, "errors": []}`

#### Scenario: CSV with wrong columns
- **WHEN** admin uploads a CSV missing required columns (no `id` or `name` header)
- **THEN** system returns 400 Bad Request with error indicating which required columns are missing

### Requirement: CSV import preserves existing is_active and is_featured
The system SHALL NOT override `is_active` or `is_featured` flags during CSV import. These fields are admin-managed via the CRUD API only.

#### Scenario: Upsert does not reset flags
- **WHEN** admin imports a CSV updating a product that was soft-deleted (`is_active = FALSE`)
- **THEN** system updates name/description/price/category/image_url but `is_active` remains FALSE

#### Scenario: New products from CSV get default flags
- **WHEN** admin imports a CSV with new product IDs
- **THEN** system creates them with `is_active = TRUE` and `is_featured = FALSE` (defaults)
