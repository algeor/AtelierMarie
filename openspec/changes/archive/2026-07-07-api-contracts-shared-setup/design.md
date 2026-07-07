## Context

The project skeleton (Phase 1) established a running FastAPI app with SQLite/WAL, session middleware, and a health endpoint. The database schema already defines all core tables (products, users, sessions, cart_items, orders, order_items). However, no Pydantic models exist for request/response serialization, no routers are registered beyond health, and no frontend project exists.

This change bridges the gap: it defines the complete API contract layer (Pydantic models) and a frontend scaffold (Next.js + TypeScript types + mock API) so that backend route implementation and frontend UI development can proceed in parallel without blocking each other.

**Current state:**
- `app/config.py` — has core settings (DB, JWT, OAuth, session)
- `app/database.py` — full schema DDL, `get_db()` context manager
- `app/main.py` — app factory with lifespan, session middleware, health endpoint
- No `app/models/` directory
- No `frontend/` directory
- No routers beyond health

## Goals / Non-Goals

**Goals:**
- Define all Pydantic request/response models as the single source of truth for API shape
- Create TypeScript types that mirror the Python models exactly
- Provide a mock API layer so frontend can develop without a running backend
- Register empty routers in the app factory (wired but returning 501)
- Extend config with CORS origins and static file path settings
- Keep all models Layer 1 only — no analytics or ML model shapes

**Non-Goals:**
- Implementing any business logic or service layer
- Implementing actual route handlers (those come in subsequent phases)
- Adding authentication middleware or JWT validation logic
- Database migrations or schema changes (schema already exists)
- Production deployment config
- Layer 2 (analytics/DuckDB) anything

## Decisions

### 1. Model organization: one file per domain entity

**Decision:** `app/models/products.py`, `app/models/cart.py`, `app/models/orders.py`, `app/models/users.py`, `app/models/auth.py`, `app/models/common.py`

**Rationale:** Matches the database tables 1:1, easy to find, prevents circular imports. `common.py` holds shared types (pagination, error responses).

**Alternative considered:** Single `models.py` file — rejected because it would grow to 300+ lines and mix unrelated domains.

### 2. ID generation: UUID strings

**Decision:** All entity IDs are `str` (UUID4 format), generated server-side at creation time.

**Rationale:** Already defined this way in the database schema (`TEXT PRIMARY KEY`). UUIDs avoid sequential ID enumeration and work well for eventual multi-writer scenarios.

### 3. Timestamps: ISO 8601 strings

**Decision:** All `created_at`, `updated_at`, `added_at` fields are `str` in ISO 8601 format (e.g., `2024-01-15T10:30:00Z`).

**Rationale:** SQLite stores these as TEXT via `datetime('now')`. Pydantic `datetime` type adds parsing complexity without benefit since we're not doing timezone math in Python. Frontend can parse ISO strings natively with `new Date()`.

### 4. Frontend mock API pattern: static typed functions

**Decision:** `frontend/lib/mock-api.ts` exports async functions matching the real API surface (e.g., `getProducts()`, `addToCart()`). Each returns hardcoded data matching the TypeScript types. A single `USE_MOCK_API` flag switches between mock and real fetch calls.

**Rationale:** Frontend components call the same function signature whether using mocks or real API. Switching to real API requires only changing the implementation inside each function, not the component code.

**Alternative considered:** MSW (Mock Service Worker) — rejected as overkill for this project size; adds a service worker dependency and more moving parts.

### 5. Router stub pattern: 501 Not Implemented

**Decision:** Register routers for `/v1/products`, `/v1/cart`, `/v1/orders`, `/v1/auth`, `/v1/admin` in `main.py`. Each router file has empty route definitions that return `501 Not Implemented` with the error response shape.

**Rationale:** Establishes the URL structure and verifies router wiring works. Frontend mock API can target these URLs knowing they'll be filled in later. Tests can verify the routing table.

### 6. Error response: consistent shape across all endpoints

**Decision:** All errors return `{"error": {"code": "ERROR_CODE", "message": "Human-readable detail", "details": {...} | null}}`.

**Rationale:** Frontend needs one error handling path. Code is machine-readable (for conditional logic), message is human-readable (for display), details carries validation errors or context.

### 7. Next.js 14 with App Router

**Decision:** Frontend uses Next.js 14 with the App Router (not Pages Router).

**Rationale:** App Router is the current standard, supports React Server Components, and has better data fetching patterns. Project is greenfield so no migration concerns.

## Risks / Trade-offs

**[Risk] Models drift from database schema** → Mitigation: Models are defined once and reference the existing DDL. A test will verify all model fields map to existing columns.

**[Risk] TypeScript types diverge from Pydantic models** → Mitigation: Types are hand-written once during this change. Future changes must update both. A comment in each file cross-references the other.

**[Risk] Mock API returns data that real API won't** → Mitigation: Mock data uses the same TypeScript types as return values, enforcing shape at compile time. Response content (e.g., realistic product names/prices) is secondary.

**[Trade-off] 501 stubs add dead code temporarily** → Acceptable because it validates routing and gives frontend real URLs to target. Stubs are replaced 1:1 during implementation phases.

**[Trade-off] No OpenAPI spec generation yet** → FastAPI will auto-generate OpenAPI from the models once routes are implemented. During the mock phase, the Pydantic models ARE the spec.
