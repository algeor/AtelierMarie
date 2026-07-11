## Context

AtelierMarie is a fresh FastAPI project (Python 3.11) targeting zero-budget free-tier deployment. The event ingestion pipeline (designed separately) captures behavioral events referencing product IDs. This change introduces the product catalog — the transactional system of record for product data that events reference and recommendations will serve.

**Current state:** Empty project with hello-world endpoint. The event-ingestion-pipeline change establishes DuckDB for analytics and a `app/` package structure. This change introduces SQLite as the transactional store (separate concern from DuckDB analytics).

**Constraints:**
- Zero budget — no managed databases, no cloud storage
- Free-tier VPS (1GB RAM typical) — SQLite fits perfectly
- Must coexist with event pipeline's DuckDB usage
- Admin access needed but no user identity system yet
- Must support bulk bootstrapping (merchants may have 10k+ products in CSV)

## Goals / Non-Goals

**Goals:**
- Establish SQLite as the transactional data layer (products, future: users, orders)
- Provide full CRUD for admin product management with simple auth
- Expose public read-only product API for frontend consumption
- Support CSV bulk import for initial catalog population and batch updates
- Enable concurrent read access via WAL mode
- Keep product IDs as business identifiers (SKUs/slugs) for CSV import compatibility

**Non-Goals:**
- Full-text search on product names/descriptions (add later with SQLite FTS5)
- Image upload/hosting (image_url points to external CDN/hosting)
- Product variants/options (single product = single SKU for MVP)
- Price history or multi-currency support
- Category hierarchy (flat string for now)
- Rate limiting on public endpoints
- Caching layer (add when needed)

## Decisions

### 1. SQLite for transactional data, separate from DuckDB

**Decision:** Products live in SQLite (`app/data/atelier.db`). DuckDB remains the analytics-only store for events.

**Alternatives considered:**
- *DuckDB for everything*: Single-writer model causes contention with event batch loader. DuckDB is optimized for OLAP, not OLTP CRUD. Rejected.
- *JSON file store*: No query capability, no concurrent access safety. Rejected.
- *PostgreSQL*: Adds infrastructure cost and complexity. Rejected for zero-budget constraint.

**Rationale:** SQLite in WAL mode supports unlimited concurrent readers + one writer. Product CRUD is low-write (~10 writes/day from admin), high-read (every page view). Perfect fit.

### 2. Text primary key (business identifier)

**Decision:** `id TEXT PRIMARY KEY` — product IDs are merchant-defined SKUs or slugs (e.g., `blue-widget-xl`, `SKU-12345`).

**Alternatives considered:**
- *Auto-increment integer + separate SKU field*: Creates mapping complexity for CSV import and events. Rejected.
- *UUID*: Not human-readable, makes CSV import awkward. Rejected.

**Rationale:** Business identifiers eliminate the impedance mismatch between CSV files, events, and the database. CSV import becomes a simple upsert on the natural key.

### 3. Soft delete via `is_active` flag

**Decision:** `DELETE` endpoint sets `is_active = FALSE`. Rows are never physically deleted.

**Rationale:** Events reference `product_id` and are immutable in DuckDB. Hard delete creates orphan references. Soft delete preserves referential integrity for historical analytics while hiding products from public API.

### 4. API key authentication (not OAuth/JWT)

**Decision:** Single bearer token stored in `ATELIER_ADMIN_API_KEY` environment variable. FastAPI `Depends()` checks `Authorization: Bearer <key>` header.

**Alternatives considered:**
- *OAuth2/JWT*: Requires user database, token management, refresh flow. Massive overkill for single-admin MVP. Rejected.
- *Basic auth*: Less standard for APIs, harder to use in scripts. Rejected.
- *No auth*: Unacceptable even for MVP — anyone could modify catalog. Rejected.

**Rationale:** One env var, one `Depends()` function, zero infrastructure. Sufficient until multi-user admin is needed.

### 5. Offset-based pagination

**Decision:** `?page=1&per_page=20` with response metadata `{"items": [...], "total": N, "page": P, "per_page": PP}`.

**Alternatives considered:**
- *Cursor-based*: Better for large datasets with real-time changes, but adds complexity (encode/decode cursor, no random page access). Overkill for ~10k products. Rejected for now.
- *No pagination*: Memory explosion with large catalogs. Rejected.

**Rationale:** Simple, predictable, sufficient for catalog sizes under 100k. Frontend can show page numbers. Easy to understand and debug.

### 6. CSV streaming parse with batch inserts

**Decision:** Use Python's `csv.reader` on the uploaded file stream. Insert in batches of 500 rows using `executemany()` within a single transaction.

**Alternatives considered:**
- *Read entire file to memory then insert*: Fails on large files (10k+ rows × large descriptions). Rejected.
- *One row at a time*: Too slow (10k individual INSERTs). Rejected.
- *pandas*: Heavy dependency for simple CSV parsing. Rejected.

**Rationale:** Streaming parse keeps memory constant. Batch `executemany()` in a transaction is the fastest SQLite bulk insert pattern. 10k products completes in <2 seconds.

### 7. SQLite connection management via contextmanager

**Decision:** A module-level function `get_db()` returns a connection from a simple pool (or creates one). Connections use WAL mode, foreign keys enabled, and are yielded via FastAPI's `Depends()`.

**Rationale:** SQLite connections are lightweight (~1ms to open). A simple pattern of open-use-close per request avoids connection leaks. WAL mode is set once on first connection via `PRAGMA journal_mode=WAL`.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| **Float price precision** → rounding errors on display | Acceptable for MVP. Price-at-purchase is captured in event metadata, not recalculated. Document as known limitation. |
| **No category validation** → inconsistent category strings | Admin is the only writer. Add category enum/table when needed. |
| **Single API key** → no audit trail of who made changes | Sufficient for solo/small-team admin. Add user-level auth when multi-admin needed. |
| **SQLite write lock** → concurrent admin writes block | Admin writes are rare (~10/day). Lock duration is microseconds. Not a real concern. |
| **Large CSV import** → request timeout on slow connections | Streaming parse means server processes fast regardless of upload speed. Set reasonable timeout (60s). Return partial success with error details. |
| **No schema migration tool** → schema changes are manual | Single table, greenfield project. Add Alembic when schema evolves. |

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  FastAPI Application                                         │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Public Routes (no auth)                            │    │
│  │  GET /v1/products        → list active products     │    │
│  │  GET /v1/products/{id}   → get active product       │    │
│  └──────────────────────────────┬──────────────────────┘    │
│                                 │                           │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Admin Routes (API key required)                    │    │
│  │  POST   /v1/admin/products         → create         │    │
│  │  GET    /v1/admin/products         → list all       │    │
│  │  GET    /v1/admin/products/{id}    → get any        │    │
│  │  PUT    /v1/admin/products/{id}    → update         │    │
│  │  DELETE /v1/admin/products/{id}    → soft delete    │    │
│  │  POST   /v1/admin/products/import  → CSV upsert     │    │
│  └──────────────────────────────┬──────────────────────┘    │
│                                 │                           │
│  ┌──────────────────────────────┼──────────────────────┐    │
│  │  Dependencies                │                      │    │
│  │  ┌───────────────┐  ┌───────▼──────────┐           │    │
│  │  │  auth.py      │  │  sqlite.py       │           │    │
│  │  │  verify_key() │  │  get_db()        │           │    │
│  │  │  (Depends)    │  │  init_schema()   │           │    │
│  │  └───────────────┘  └───────┬──────────┘           │    │
│  └──────────────────────────────┼──────────────────────┘    │
│                                 │                           │
│                                 ▼                           │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  SQLite (WAL mode)                                  │    │
│  │  app/data/atelier.db                                │    │
│  │  ┌───────────────────────────────────────────────┐  │    │
│  │  │  products table                               │  │    │
│  │  │  - id TEXT PK (business identifier)           │  │    │
│  │  │  - name, description, price, category         │  │    │
│  │  │  - image_url, is_active, is_featured          │  │    │
│  │  │  - created_at, updated_at                     │  │    │
│  │  └───────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Open Questions

- **Index strategy**: Should we add indexes on `category` and `is_active` upfront, or wait for query patterns to emerge? (Leaning: add them — catalog queries will always filter by these.)
- **`updated_at` trigger**: SQLite doesn't have auto-update triggers by default. Use an application-level update or a SQL trigger? (Leaning: application-level in the UPDATE handler for simplicity.)
