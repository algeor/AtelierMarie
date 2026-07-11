# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AtelierMarie is a luxury candle e-commerce platform for a small family business. The primary goal is selling candles reliably. A secondary goal is learning ML/analytics through an optional sandbox layer.

**Status:** Planning phase complete; implementation in progress (skeleton FastAPI app with models, routes stubs, session middleware).

## Architecture: Two Strict Layers

### Layer 1 — Production E-Commerce (Critical Path)
- Products, cart, checkout, orders, auth, admin
- SQLite only (WAL mode) — never touches DuckDB
- Must work perfectly if Layer 2 is completely OFF
- All responses <200ms

### Layer 2 — Analytics & ML Sandbox (Non-Critical)
- Event collection (async, fire-and-forget)
- DuckDB for analytics storage
- ML recommendations (pre-computed cache, fallback to popular)
- Can crash, be disabled, or be deleted without affecting the store

**Cardinal rule:** Layer 1 code NEVER imports from Layer 2 modules (`app/analytics/`, `app/ml/`). This is a hard blocker in code review — no exceptions.

See `ARCHITECTURE.md` for full system design and `IMPLEMENTATION_PLAN.md` for the build sequence.

## Technology Stack

- **Backend:** Python 3.11, FastAPI, Pydantic 2, Uvicorn
- **Database:** SQLite (WAL mode) — system of record
- **Auth:** Google OAuth 2.0 + JWT (PyJWT)
- **Frontend:** Next.js 14 (App Router, TypeScript, Tailwind CSS)
- **Analytics (optional):** DuckDB
- **Hosting:** Oracle Cloud Free Tier (single VPS), Nginx, systemd

## Development Commands

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the backend
uvicorn app.main:app --reload --port 8000

# Run tests
pytest

# Run tests with coverage
pytest --cov=app --cov-report=term-missing

# Lint
ruff check .

# Format
ruff format .
```

## Application Structure

```
app/
├── main.py              # FastAPI app factory + lifespan
├── config.py            # pydantic-settings (env vars)
├── database.py          # SQLite connection management + schema
├── middleware/
│   └── session.py       # Session cookie middleware (eager DB row creation)
├── models/              # Pydantic request/response schemas
│   ├── products.py
│   ├── cart.py
│   ├── orders.py
│   ├── users.py
│   ├── auth.py
│   └── common.py       # Shared types (pagination, errors)
├── routes/              # FastAPI routers (thin — HTTP only)
│   ├── products.py
│   ├── cart.py
│   ├── orders.py
│   ├── auth.py
│   └── admin.py
├── services/            # Business logic (testable, no HTTP)
│   ├── product_service.py
│   ├── cart_service.py
│   ├── order_service.py
│   └── auth_service.py
├── analytics/           # Layer 2: event collection + DuckDB (optional)
└── ml/                  # Layer 2: recommendations (experimental)

frontend/                # Next.js 14 app (separate)
├── app/                 # App Router pages
├── components/          # React components
├── lib/
│   ├── types.ts         # TypeScript interfaces (mirrors Pydantic models)
│   ├── api-client.ts    # Real API client
│   ├── mock-api.ts      # Mock API for dev without backend
│   └── api.ts           # Switches between real/mock via env
├── next.config.js
└── tailwind.config.ts

deploy/                  # Nginx, systemd, provisioning scripts
openspec/                # Feature specifications
├── changes/             # Active and archived specs
│   ├── core-ecommerce/  # Main e-commerce spec
│   ├── product-catalog/ # Product catalog spec (Day 2)
│   ├── frontend-init-design-system/
│   ├── analytics-sandbox/
│   └── ml-experiments/
└── specs/               # Shared reference specs
```

## Coding Standards — Python Backend

### Data Modeling
- **Pydantic 2 `BaseModel`** for all request/response schemas and validated data
- Pydantic v2 API: `model_validate()`, `model_dump()`, `model_json_schema()`
- **Pydantic Settings** (`app/config.py`) for all configuration — NEVER `os.environ`/`os.getenv` in app code
- Prices ALWAYS in cents as `int` — field name: `price_cents` (never `price` alone, never `float`)
- Product IDs are text (SKU/slug, e.g., `lavender-dream-300ml`) — not auto-increment integers
- Use `typing.Literal` for constrained string values (e.g., `OrderStatus = Literal["pending", "confirmed", "shipped", "delivered", "cancelled"]`)

### Type Annotations
- Modern syntax: `str | None` (not `Optional[str]`), `list[str]` (not `List[str]`)
- All function signatures fully typed (parameters and return)
- FastAPI dependencies typed with `Annotated[Type, Depends(dep_fn)]`

### Module Organization
- **Routes (thin):** Validate input (Pydantic does this), call service, format HTTP response. No business logic.
- **Services (fat):** All business logic. Testable without HTTP. Take explicit parameters, return data or raise custom exceptions.
- **Models:** Pure Pydantic schemas. No logic beyond validators.
- Import order: stdlib → third-party → local (alphabetical within groups)
- No circular imports. Services don't import from routes. Models don't import from services.

### Naming
- `snake_case` for functions, variables, modules
- `PascalCase` for classes (Pydantic models, exceptions)
- `UPPER_SNAKE_CASE` for module-level constants
- Full descriptive names — never abbreviate (`product_service` not `prod_svc`)
- Comments only when answering "why not the obvious thing?" — code should be self-documenting

### Database (SQLite)
- Context manager for connections: `with get_db() as conn:`
- **Always** parameterized queries with `?` — NEVER f-strings or `.format()` in SQL
- Transactions: explicit `BEGIN`/`COMMIT` for multi-statement operations (checkout, stock updates)
- `CHECK (stock >= 0)` constraint at DB level — last line of defense against negative stock
- FTS5 virtual table for product search (synced via triggers on INSERT/UPDATE/DELETE)
- Schema created on app startup in `database.py`

### Error Handling
- Custom exception classes in services (e.g., `ProductNotFoundError`, `InsufficientStockError`, `InvalidStateTransitionError`)
- Routes translate service exceptions to HTTP responses (404, 409, 422, etc.)
- `raise CustomError("message") from original_error` — always chain
- Never bare `except Exception:` without re-raise or specific handling
- Layer 2 code catches ALL its own exceptions — never propagates to Layer 1

### Authentication & Authorization
- Session cookie: UUID4, HttpOnly, Secure, SameSite=Lax, 30-day expiry
- Session row created eagerly in middleware (not lazily)
- Session ID rotated on logout (new ID issued, old invalidated)
- Admin auth: `require_admin` dependency checks JWT `is_admin` claim OR Bearer API key
- API key comparison uses `hmac.compare_digest` (constant-time)
- First Google OAuth user auto-promoted to admin (no manual DB edits)
- JWT: validate audience, issuer, and expiry

### FastAPI Patterns
- Router instances in each route module, included via `app.include_router()`
- All routes under `/v1/` prefix
- Dependencies via `Depends()` — auth, session, DB connection
- Response models specified on route decorator: `response_model=ProductResponse`
- Status codes explicit: `status_code=201` for creation, `204` for delete, etc.
- Background tasks for non-critical work (event emission)

## Coding Standards — Frontend (Next.js)

### TypeScript
- Strict mode — no `any` types
- Interfaces in `lib/types.ts` mirror Pydantic models exactly (same field names, `price_cents` as number)
- All API responses typed; API client functions return typed promises

### Architecture
- App Router (not Pages Router)
- Server Components by default; Client Components only when interactivity needed
- Mock API (`lib/mock-api.ts`) and real API (`lib/api-client.ts`) share identical response shapes
- Environment flag (`NEXT_PUBLIC_USE_MOCK_API`) switches between mock/real
- No hardcoded URLs — API base from `NEXT_PUBLIC_API_URL` env var

### UI/Design System
- Tailwind CSS with custom design tokens (luxury palette from storefront spec)
- `cn()` utility for conditional class merging (clsx + tailwind-merge)
- Mobile-first responsive design
- Proper `next/image` with sizes, alt text, blur placeholder
- Loading skeletons for async data; user-friendly error messages (never raw JSON)
- Accessibility: semantic HTML, ARIA labels, keyboard navigation

### Data Flow
- Prices: convert cents to display currency at the UI layer (never store formatted strings)
- Cart: optimistic updates with rollback on error
- Forms: client-side validation mirrors server-side rules

## Key Design Decisions

- **Anonymous-first:** Full cart/checkout works without login. Session cookie = identity.
- **Prices in cents:** All monetary values stored as integers to avoid float errors.
- **Order snapshots:** `order_items` stores product name + price at purchase time (immutable — never re-joined to products).
- **Order state machine:** pending → confirmed → shipped → delivered. Cancel from pending/confirmed only. Invalid transitions → 422.
- **Stock validation on cart add:** Returns 409 Conflict immediately if out of stock (not just at checkout).
- **Session rotation on logout:** New session ID issued, old one invalidated. Prevents reuse.
- **Dual admin auth:** JWT (is_admin) for browser, API key for scripts/automation.
- **First-user-is-admin:** First Google OAuth login auto-promoted. No manual DB edits needed.
- **CSV bulk import:** For initial product catalog load (`POST /v1/admin/products/import`). Streaming parse, batch upsert, per-row error reporting.
- **API prefix:** All routes under `/v1/`.
- **Service layer pattern:** Thin routes (HTTP concerns only), fat services (business logic). Services are testable without HTTP.
- **FTS5 search:** Product search uses SQLite FTS5 virtual table, synced via triggers. Not LIKE queries.
- **Offset pagination:** `?page=1&limit=20` with `{items, total, page, limit}` response. Sufficient for <1000 products.

## Layer 2 Design Decisions

- **Event collection:** Fire-and-forget JSONL append (O_APPEND, crash-safe, multi-worker safe). Background thread loads into DuckDB every 60s.
- **Recommendations:** Pre-computed cache updated every 30min. Fallback chain: ML → popularity → featured → random. Never errors — always returns something.
- **GDPR:** NULL-ification of PII fields (not cascade delete) — preserves order structure.
- **Analytics isolation:** DuckDB has its own connection; never shares SQLite's. All analytics code optional-import guarded.
- **Failure mode:** Layer 2 crashes → log the error, return empty/default data. Never 500. Never affects checkout.

## Feature Specifications

Lean specs live in `openspec/changes/`:
- `core-ecommerce/` — Products, cart, checkout, orders, auth, admin (421-line design doc)
- `product-catalog/` — Day 2 implementation: service layer, FTS5, CSV import, admin CRUD
- `frontend-init-design-system/` — Tailwind tokens, base components, luxury palette
- `analytics-sandbox/` — Event collection, DuckDB, admin stats dashboard
- `ml-experiments/` — Recommendations (experimental, no deadline)

Archived specs: `openspec/changes/archive/`

## Testing Standards

- **Framework:** pytest
- **Database:** In-memory SQLite per test (`:memory:`), schema initialized in fixture
- **Isolation:** Each test gets fresh `TestClient` + fresh DB. No test interdependencies.
- **Service tests:** Call service functions directly (no HTTP). Verify business logic.
- **Route tests:** Use `TestClient`. Verify HTTP status codes, response shapes, error cases.
- **Naming:** `test_<behavior>_<scenario>()` — e.g., `test_checkout_fails_when_cart_empty()`
- **Coverage:** Target ≥80%. New code must have tests.
- **What to test:**
  - All order state transitions (valid AND invalid)
  - Stock edge cases (add to cart when 0 stock, concurrent checkout race)
  - Auth paths (unauthenticated, authenticated non-admin, admin JWT, admin API key)
  - Cart operations (add, update, remove, anonymous user, quantity limits)
  - CSV import (valid, malformed, upsert, empty file)
  - Pydantic validation (invalid inputs → ValidationError)
- **Layer 2 tests:** Verify failures don't propagate. Mock the analytics/ML layer and have it raise; confirm Layer 1 still works.

## Code Review Standards

Reviews prioritize (in order):
1. **Layer boundary violations** — always a blocker
2. **Data integrity** — money calculations, stock consistency, order snapshots
3. **Security** — SQL injection, auth bypass, credential exposure
4. **Logic bugs** — state machine violations, race conditions, edge cases
5. **Spec compliance** — does the code match `openspec/changes/*/design.md`?
6. **Test coverage** — new code paths need tests
7. **Style/patterns** — only flagged if it causes confusion or maintenance burden

Use `/code-review-local` to run the multi-agent review council.
