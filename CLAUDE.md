# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AtelierMarie is a luxury candle e-commerce platform for a small family business. The primary goal is selling candles reliably. A secondary goal is learning ML/analytics through an optional sandbox layer.

**Status:** Core e-commerce backend fully implemented (products, cart, checkout, orders, auth, admin, reactions, comments). Next.js frontend with full page coverage (products, cart, checkout, orders, admin, auth/account). Layer 2 (analytics/ML) deferred — not yet started.

## Architecture: Two Strict Layers

### Layer 1 — Production E-Commerce (Critical Path)
- Products, cart, checkout, orders, auth, admin, reactions, comments
- SQLite only (WAL mode) — never touches DuckDB
- Must work perfectly if Layer 2 is completely OFF
- All responses <200ms

### Layer 2 — Analytics & ML Sandbox (Non-Critical)
- Event collection (async, fire-and-forget)
- DuckDB for analytics storage
- ML recommendations (pre-computed cache, fallback to popular)
- Can crash, be disabled, or be deleted without affecting the store
- **Currently deferred** — no code exists yet

**Cardinal rule:** Layer 1 code NEVER imports from Layer 2 modules (`app/analytics/`, `app/ml/`). This is a hard blocker in code review — no exceptions.

See `ARCHITECTURE.md` for full system design and `IMPLEMENTATION_PLAN.md` for the build sequence.

## Technology Stack

- **Backend:** Python 3.11, FastAPI, Pydantic 2, Uvicorn, structlog
- **Database:** SQLite (WAL mode) — system of record
- **Auth:** Google OAuth 2.0 + JWT (PyJWT)
- **Frontend:** Next.js 14 (App Router, TypeScript, Tailwind CSS)
- **Testing:** pytest + pytest-xdist (parallel), vitest (frontend)
- **Analytics (deferred):** DuckDB
- **Hosting:** Oracle Cloud Free Tier (single VPS), Nginx, systemd

## Development Commands

```bash
# NEVER use `source .venv/bin/activate` — use .venv/bin/ prefix or make targets

# Setup
make setup              # Install all deps (backend + frontend)
make setup-backend      # Python venv + pip install
make setup-frontend     # npm install

# Run servers
make dev-backend        # FastAPI on port 8001 (uvicorn --reload)
make dev-frontend       # Next.js on port 3000

# Tests
make test               # Run ALL tests (backend + frontend)
make test-backend       # pytest (parallel via xdist)
make test-backend-cov   # pytest with coverage report
make test-frontend      # vitest run

# Lint & format
make lint               # Lint everything (ruff + eslint)
make format             # Auto-format Python (ruff format + ruff check --fix)

# Direct commands (when make isn't preferred)
.venv/bin/pytest tests/ -v --tb=short
.venv/bin/ruff check .
.venv/bin/ruff format .
```

## Application Structure

```
app/
├── main.py              # FastAPI app factory + lifespan (session cleanup task)
├── config.py            # pydantic-settings (env vars)
├── constants.py         # Cross-module constants (single source of truth)
├── database.py          # SQLite connection management + schema + session cleanup
├── exceptions.py        # Global exception handlers (standard error envelope)
├── logging_config.py    # structlog configuration
├── middleware/
│   ├── session.py       # Session cookie middleware (eager DB row creation)
│   └── request_id.py    # X-Request-Id middleware
├── dependencies/        # FastAPI Depends() callables
│   ├── auth.py          # require_admin, get_current_user
│   └── session.py       # require_session
├── models/              # Pydantic request/response schemas
│   ├── products.py
│   ├── cart.py
│   ├── orders.py
│   ├── users.py
│   ├── auth.py
│   ├── comments.py
│   ├── reactions.py
│   ├── admin.py
│   └── common.py        # Shared types (pagination, errors)
├── routes/              # FastAPI routers (thin — HTTP only)
│   ├── products.py
│   ├── cart.py
│   ├── orders.py
│   ├── auth.py
│   ├── admin.py
│   ├── comments.py
│   └── reactions.py
├── services/            # Business logic (testable, no HTTP)
│   ├── product_service.py
│   ├── cart_service.py
│   ├── order_service.py
│   ├── auth_service.py
│   ├── admin_service.py
│   ├── comment_service.py
│   └── reaction_service.py
└── utils/               # Shared utilities
    ├── blocklist.py     # Session/token blocklist
    ├── circuit_breaker.py
    ├── row_access.py    # Dict-like access for sqlite3.Row
    └── sanitize.py      # Input sanitization (HTML/XSS)

frontend/                # Next.js 14 app
├── app/                 # App Router pages
│   ├── products/        # Product listing + detail
│   ├── checkout/        # Checkout flow
│   ├── orders/          # Order history + detail
│   ├── admin/           # Admin dashboard + product management
│   ├── auth/            # Login/callback
│   ├── account/         # User account
│   └── design-system/   # Component gallery
├── components/
│   ├── ui/              # Base components (Button, Input, Badge, Skeleton)
│   ├── products/        # ProductCard, ProductGrid, ReactionBar, CommentThread
│   ├── cart/            # CartDrawer, CartItem, AddToCartButton, CartBadge
│   ├── admin/           # AdminGuard, AdminSidebar, ProductForm, StatsCard
│   ├── orders/          # OrderStatusBadge, StatusTimeline
│   ├── auth/            # LoginButton, UserMenu
│   └── layout/          # Header, Footer, AnnouncementBar
├── contexts/            # React contexts
│   ├── CartContext.tsx
│   ├── AuthContext.tsx
│   └── AdminContext.tsx
├── lib/
│   ├── types.ts         # TypeScript interfaces (mirrors Pydantic models)
│   ├── api-client.ts    # Real API client
│   ├── mock-api.ts      # Mock API for dev without backend
│   ├── api.ts           # Switches between real/mock via env
│   ├── utils.ts         # cn() helper, formatters
│   └── validateRedirectPath.ts
├── __tests__/           # Frontend unit tests (vitest + testing-library)
├── next.config.js
├── tailwind.config.ts
└── vitest.config.ts

tests/                   # Backend tests
├── conftest.py          # Shared fixtures (module-scoped app/client/db)
├── test_*.py            # Unit/service/route tests (mocked session middleware)
└── realapp/             # Integration tests (real middleware, real DB flow)
    ├── conftest.py      # Real app fixtures (no fake middleware)
    └── test_*.py        # End-to-end route tests

scripts/
└── seed_products.py     # Seed product catalog

deploy/
└── nginx-ratelimit.conf

openspec/                # Feature specifications
├── config.yaml
├── changes/             # Active specs
│   ├── core-ecommerce/
│   ├── product-reactions-comments/
│   ├── admin-polish-edge-cases/
│   ├── auth-image-upload/
│   ├── add-ons/         # owner-stories-blog, shipping, social buttons
│   └── deferred/        # analytics-sandbox, ml-experiments
├── changes/archive/     # Completed/superseded specs
└── specs/               # Shared reference specs (per-feature)
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
- **Utils:** Shared helpers (sanitize, blocklist, circuit breaker). No business logic.
- **Dependencies:** FastAPI `Depends()` callables for auth, session.
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
- Expired session cleanup runs as a background asyncio task (hourly)

### Error Handling
- Custom exception classes in services (e.g., `ProductNotFoundError`, `InsufficientStockError`, `RateLimitExceededError`)
- Global exception handlers in `app/exceptions.py` — standard JSON envelope: `{"error": {"code": "...", "message": "...", "details": ...}}`
- Routes translate service exceptions to HTTP responses (404, 409, 422, etc.)
- `raise CustomError("message") from original_error` — always chain
- Never bare `except Exception:` without re-raise or specific handling
- Layer 2 code catches ALL its own exceptions — never propagates to Layer 1

### Logging
- **structlog** for structured JSON logging (configured in `app/logging_config.py`)
- Use `structlog.get_logger(__name__)` — never `print()` or stdlib `logging` directly

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
- Request ID middleware adds `X-Request-Id` header to all responses

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
- React contexts for global state (Cart, Auth, Admin)

### UI/Design System
- Tailwind CSS with custom design tokens (luxury palette from storefront spec)
- `cn()` utility for conditional class merging (clsx + tailwind-merge)
- Mobile-first responsive design
- Proper `next/image` with sizes, alt text, blur placeholder
- Loading skeletons for async data; user-friendly error messages (never raw JSON)
- Accessibility: semantic HTML, ARIA labels, keyboard navigation
- Design system gallery at `/design-system` route

### Data Flow
- Prices: convert cents to display currency at the UI layer (never store formatted strings)
- Cart: optimistic updates with rollback on error
- Forms: client-side validation mirrors server-side rules

### Testing (Frontend)
- **Framework:** vitest + @testing-library/react
- Component tests in `frontend/__tests__/`
- Run with `make test-frontend` or `cd frontend && npx vitest run`

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
- **Product reactions:** Emoji-style reactions (heart, fire, etc.) per session. Toggle on/off, rate-limited.
- **Product comments:** Session-based comments with input sanitization (XSS prevention). Admin moderation (hide/delete).
- **Input sanitization:** All user-generated text (comments, display names) runs through `app/utils/sanitize.py` to strip HTML/scripts.

## Layer 2 Design Decisions (Planned — Not Yet Implemented)

- **Event collection:** Fire-and-forget JSONL append (O_APPEND, crash-safe, multi-worker safe). Background thread loads into DuckDB every 60s.
- **Recommendations:** Pre-computed cache updated every 30min. Fallback chain: ML → popularity → featured → random. Never errors — always returns something.
- **GDPR:** NULL-ification of PII fields (not cascade delete) — preserves order structure.
- **Analytics isolation:** DuckDB has its own connection; never shares SQLite's. All analytics code optional-import guarded.
- **Failure mode:** Layer 2 crashes → log the error, return empty/default data. Never 500. Never affects checkout.

## Feature Specifications

Lean specs live in `openspec/changes/`:
- `core-ecommerce/` — Products, cart, checkout, orders, auth, admin
- `product-reactions-comments/` — Reactions & comments on products
- `admin-polish-edge-cases/` — Admin UX refinements
- `auth-image-upload/` — Profile images, auth enhancements
- `add-ons/` — Future nice-to-haves (blog, shipping integration, social buttons)
- `deferred/` — analytics-sandbox, ml-experiments (paused)

Archived (completed) specs: `openspec/changes/archive/`
Shared reference specs: `openspec/specs/` (per-feature granular specs)

## Testing Standards

- **Framework:** pytest with pytest-xdist (parallel execution: `-n auto --dist worksteal`)
- **Database:** In-memory SQLite per test module (`:memory:`), schema initialized in fixture
- **Fixture scoping:** Module-scoped `app`, `client`, `db`; function-scoped `_clean_tables` (autouse) for isolation via DELETE between tests
- **FakeSessionMiddleware:** Route tests use a fake session middleware to avoid per-request DB round-trips. Real middleware tested separately in `tests/realapp/`.
- **Two test directories:**
  - `tests/` — Unit and service tests. Mocked middleware. Fast.
  - `tests/realapp/` — Integration tests with real middleware, real session flow, real DB lifecycle.
- **Service tests:** Call service functions directly (no HTTP). Verify business logic.
- **Route tests:** Use `httpx.AsyncClient` (async). Verify HTTP status codes, response shapes, error cases.
- **Naming:** `test_<behavior>_<scenario>()` — e.g., `test_checkout_fails_when_cart_empty()`
- **Coverage:** Target ≥80%. New code must have tests.
- **What to test:**
  - All order state transitions (valid AND invalid)
  - Stock edge cases (add to cart when 0 stock, concurrent checkout race)
  - Auth paths (unauthenticated, authenticated non-admin, admin JWT, admin API key)
  - Cart operations (add, update, remove, anonymous user, quantity limits)
  - CSV import (valid, malformed, upsert, empty file)
  - Pydantic validation (invalid inputs → ValidationError)
  - Reactions (toggle, rate-limit, counts)
  - Comments (create, list, sanitization, admin moderation)
- **Layer 2 tests:** (When implemented) Verify failures don't propagate. Mock the analytics/ML layer and have it raise; confirm Layer 1 still works.

## Code Review Standards

Reviews prioritize (in order):
1. **Layer boundary violations** — always a blocker
2. **Data integrity** — money calculations, stock consistency, order snapshots
3. **Security** — SQL injection, auth bypass, credential exposure, XSS
4. **Logic bugs** — state machine violations, race conditions, edge cases
5. **Spec compliance** — does the code match `openspec/changes/*/design.md`?
6. **Test coverage** — new code paths need tests
7. **Style/patterns** — only flagged if it causes confusion or maintenance burden

Use `/code-review-local` to run the multi-agent review council.
