## Why

AtelierMarie is event-first, but events reference product IDs that don't exist yet. The recommendation engine needs product metadata (category, featured flag) for cold-start fallback and diversity. Orders (future) need a product table for FK constraints. Without a product catalog, the platform has no entities for events to reference or recommendations to serve.

## What Changes

- Add a `products` table in SQLite as the system of record for product data
- Implement CRUD admin API (`/v1/admin/products`) protected by API key authentication
- Implement public read-only API (`/v1/products`) for active products (no auth required)
- Add CSV bulk import endpoint for bootstrapping and batch updates (upsert semantics)
- Introduce API key authentication middleware for admin routes
- Set up SQLite connection management with WAL mode for concurrent read safety

## Capabilities

### New Capabilities

- `product-crud`: Admin CRUD operations (create, read, update, soft-delete) with pagination and filtering
- `product-public-api`: Public read-only endpoint serving active products with category filtering, text search (GET /v1/products/search?q=), stock quantity visibility, and atomic stock decrement service for cart/checkout
- `product-import`: CSV bulk import with upsert semantics, streaming parse, and error reporting
- `admin-auth`: API key bearer token authentication for `/v1/admin/*` routes

### Modified Capabilities

<!-- No existing capabilities to modify — this is the first transactional data feature -->

## Impact

- **New dependency**: none beyond existing (FastAPI, pydantic-settings, uvicorn already installed)
- **New files**: `app/api/v1/products.py`, `app/api/v1/admin/products.py`, `app/models/products.py`, `app/db/sqlite.py`, `app/dependencies/auth.py`
- **Database**: Creates `products` table in SQLite (new `app/data/atelier.db` file at runtime)
- **API surface**: 7 new endpoints under `/v1/products` and `/v1/admin/products`
- **Environment**: Requires `ATELIER_ADMIN_API_KEY` env var for admin access
- **Port 8000**: API contract extended (coexists with event pipeline's `/v1/events`)
