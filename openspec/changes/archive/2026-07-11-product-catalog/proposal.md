## Why

The store skeleton exists (FastAPI app, SQLite database with schema, Pydantic models, stub routes) but has no working endpoints. The product catalog is the foundation of the e-commerce system — nothing else (cart, checkout, orders) can function without real product data and working product queries. This is Day 2 of the implementation plan.

## What Changes

- Implement `app/services/product_service.py` — business logic for listing, getting, creating, updating, deactivating, and searching products
- Implement `app/routes/products.py` — public GET endpoints with category filtering, text search, pagination, and product detail
- Implement `app/routes/admin.py` — admin CRUD (create, update, deactivate) and CSV bulk import with upsert semantics
- Add stock CHECK constraint (`stock >= 0`) to the products table schema
- Add indexes on `category`, `is_active`, and FTS5 virtual table for search
- Create a seed script with ~10 sample candle products for development
- Align `ProductResponse.price` field name to `price_cents` (matching the DB column and architecture decision)

## Capabilities

### New Capabilities

- `product-service`: Core business logic for product CRUD, search, listing with filters/pagination, stock validation, and soft-delete (deactivate)
- `product-public-api`: Public read-only endpoints — list active products with category filter, text search, sort options, pagination; get product detail by slug/SKU
- `product-admin-api`: Admin-protected endpoints — create, update, deactivate products; CSV bulk import with streaming parse, upsert semantics, and per-row error reporting
- `product-seed`: Development seed script to populate the database with ~10 sample candle products

### Modified Capabilities

<!-- No existing capability specs have requirement-level changes. The existing `api-models` spec defined the Pydantic shapes; we're implementing against them. -->

## Impact

- **New files**: `app/services/product_service.py`, `scripts/seed_products.py`
- **Modified files**: `app/routes/products.py` (replace stub), `app/routes/admin.py` (replace stub), `app/database.py` (add CHECK constraint + indexes), `app/models/products.py` (rename `price` → `price_cents` for consistency)
- **API surface**: 6 endpoints become functional — `GET /v1/products`, `GET /v1/products/{id}`, `POST /v1/admin/products`, `PUT /v1/admin/products/{id}`, `DELETE /v1/admin/products/{id}`, `POST /v1/admin/products/import`
- **Dependencies**: None new (csv module is stdlib)
- **Database**: Adds CHECK constraint, indexes, and FTS5 virtual table to existing products schema
