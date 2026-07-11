## Context

AtelierMarie has a working FastAPI skeleton with SQLite (WAL mode), a session middleware that creates DB rows eagerly, and Pydantic models already defined for products. The `products` table schema exists in `database.py` but all route handlers are stubs returning 501. The implementation plan designates this as "Day 2: Product Catalog" — the first feature with real business logic.

**Current state:**
- `app/database.py` — Schema defined, `get_db()` context manager working. Note: schema is missing `materials TEXT` and `days_to_craft INTEGER` columns that the Pydantic model already declares — these must be added.
- `app/models/products.py` — Pydantic schemas defined (ProductResponse, CreateProductRequest, UpdateProductRequest, ProductImportRequest)
- `app/routes/products.py` — Stub returning 501
- `app/routes/admin.py` — Stub returning 501
- `app/services/` — Directory doesn't exist yet

**Constraints:**
- All responses <200ms
- SQLite only (no external DB)
- Layer 1 code — must never import Layer 2 modules
- Prices in cents (integer, never float)
- Product ID is text (SKU/slug, e.g. `lavender-dream-300ml`)
- Soft delete only (is_active flag) — never hard-delete products

## Goals / Non-Goals

**Goals:**
- Implement full CRUD product service as a testable business-logic layer (no HTTP concerns)
- Public listing with category filter, text search, sort, and offset pagination
- Admin CRUD with dual auth (JWT is_admin OR API key)
- CSV bulk import with streaming parse, upsert semantics, and per-row error reporting
- Stock CHECK constraint in DB to guarantee non-negative stock
- FTS5 search on product name + description
- Seed script for development

**Non-Goals:**
- Image upload (Day 5 — separate change)
- Full-text search on product attributes beyond name/description
- Product variants/options (single SKU = single product)
- Price history or multi-currency
- Category hierarchy (flat string for now)
- Caching layer (not needed at this scale)
- Elasticsearch or external search engine

## Decisions

### 1. Service layer pattern (thin routes, fat services)

**Decision:** All business logic lives in `app/services/product_service.py`. Routes are thin — validate input, call service, format response.

**Rationale:** Services are testable without HTTP. Routes just handle request/response concerns. Matches the project's stated architecture (`services/` for testable logic, `routes/` for thin HTTP).

### 2. Rename `price` → `price_cents` in Pydantic models

**Decision:** Align the Pydantic field name with the DB column (`price_cents`) and the architecture decision (prices in cents, never float). The existing model has `price: int` which is ambiguous.

**Rationale:** Explicitness prevents confusion. The frontend TypeScript types already use `price_cents`. This is a pre-launch change with no migration burden.

### 3. FTS5 for search — contentless variant (not LIKE)

**Decision:** Create a **contentless** FTS5 virtual table (`content=''`) storing only the index. Search queries JOIN `products_fts` back to `products` by rowid/id to fetch full data. Synced via triggers on the `products` table (INSERT/UPDATE/DELETE → mirror to products_fts).

**Why contentless:** The products table uses a TEXT primary key (no stable rowid). A content-sync FTS5 table requires rowid alignment, which is fragile with text PKs. Contentless avoids this — it stores the index independently, and we join on `products_fts.rowid` matching an internal mapping we maintain via triggers that INSERT/DELETE by the same rowid.

**Alternatives considered:**
- `LIKE '%term%'`: No indexing, full table scan, no relevance ranking. Rejected.
- External search (Meilisearch, etc.): Overkill for <1000 products, adds deployment complexity. Rejected.
- Content-sync FTS5 (`content='products'`): Requires stable integer rowid alignment. Fragile with text PK. Rejected.

**Rationale:** FTS5 is built into SQLite, zero-dependency, fast on small catalogs, supports ranking. Contentless variant is simplest for text-PK tables.

### 4. Offset-based pagination

**Decision:** `?page=1&limit=20` with response `{products, total, page, limit}`.

**Rationale:** Simple, sufficient for <1000 products. Cursor-based adds complexity with no benefit at this scale. Frontend can show page numbers.

### 5. CSV streaming parse with UPSERT (ON CONFLICT)

**Decision:** Use stdlib `csv.DictReader` on SpooledTemporaryFile. Validate each row, collect errors. Upsert valid rows using SQLite's `INSERT INTO products (...) VALUES (...) ON CONFLICT(id) DO UPDATE SET name=excluded.name, ...` in batches of 100 within a single transaction. Only columns present in the CSV are included in the SET clause — absent columns are preserved.

**Rationale:** Streaming keeps memory constant. Batch size of 100 balances speed vs transaction size. `ON CONFLICT ... DO UPDATE` (available since SQLite 3.24) provides true merge semantics — existing columns not in the CSV are preserved, unlike `INSERT OR REPLACE` which deletes the row first and loses unspecified columns.

### 6. Admin auth via dependency injection

**Decision:** A shared `require_admin` dependency checks JWT `is_admin` claim first, falls back to Bearer API key. Applied to the admin router as a router-level dependency.

**Rationale:** Matches the architecture's "dual admin auth" design. Router-level dep means all admin routes are protected without per-endpoint repetition.

### 7. Stock CHECK constraint at DB level

**Decision:** Add `CHECK (stock >= 0)` to the products table. This is the last line of defense against negative stock (race condition in checkout).

**Rationale:** Application-level checks can have races. The DB constraint guarantees integrity. SQLite evaluates CHECK on every INSERT/UPDATE — negligible cost.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| FTS5 contentless requires manual trigger management | Triggers are created in schema init and tested in CI. Rebuild index with `INSERT INTO products_fts(products_fts) VALUES('rebuild')` if drift suspected. |
| `ON CONFLICT DO UPDATE` only updates columns listed in SET | CSV import dynamically builds SET clause from CSV headers — only columns present in the file are updated. Unlisted columns preserved automatically. |
| Offset pagination performance on large datasets | Acceptable: <1000 products. Revisit if catalog grows past 10k. |
| Rename `price` → `price_cents` breaks existing tests/frontend | No tests exist beyond stubs. Frontend types updated in the same change. Pre-launch with zero migration cost. |
| Admin auth not yet implemented (Day 5) | Use a temporary API-key-only `require_admin` dependency. JWT path added on Day 5 when auth is built. Reject empty API key — if `admin_api_key` is not configured, all admin access is denied. |
