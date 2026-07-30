# 🕯️ AtelierMarie — Intern Developer Onboarding Guide

Welcome to the team! This guide will take you from zero to productive contributor over your first week. Every step includes a verification checkpoint — if you don't see the expected output, check the troubleshooting section before moving on.

> **How to use this guide:** Work through it sequentially. Each section builds on the previous one. When you see a 📖 icon, it means "read this file in the repo." When you see ✅, that's a checkpoint — verify before continuing.

---

## Table of Contents

1. [Welcome & Overview](#1-welcome--overview)
2. [Day 1: Environment Setup](#2-day-1-environment-setup)
3. [Day 1–2: Understand the Architecture](#3-day-12-understand-the-architecture)
4. [Day 2–3: Code Patterns Deep Dive](#4-day-23-code-patterns-deep-dive)
5. [Day 3–4: Frontend Patterns](#5-day-34-frontend-patterns)
6. [Day 4: Testing & Quality](#6-day-4-testing--quality)
7. [Day 5: Development Workflow](#7-day-5-development-workflow)
8. [Common Pitfalls & FAQ](#8-common-pitfalls--faq)
9. [Graduated First Tasks](#9-graduated-first-tasks)
10. [Resources & Key Files](#10-resources--key-files)

---

## 1. Welcome & Overview

### What is AtelierMarie?

AtelierMarie is a luxury candle e-commerce platform for a small family business. The primary goal is **selling candles reliably**. Everything else (analytics, ML, recommendations) is secondary and optional.

### The Tech Stack at a Glance

| Layer | Technology | Why |
|-------|-----------|-----|
| Backend API | Python 3.11 + FastAPI | Type-safe, fast, modern Python web framework |
| Database | SQLite (WAL mode) | Simple, zero-config, perfect for our scale |
| Auth | Google OAuth 2.0 + JWT | One-click login for customers |
| Frontend | Next.js 14 (TypeScript, Tailwind) | React with server-side rendering |
| Testing | pytest (backend) + vitest (frontend) | Fast, parallel test execution |
| Linting | ruff (Python) + ESLint (TS) | Automated code quality |

### What You'll Be Working On

As an intern, you'll start with small, well-scoped tasks and graduate to larger features. The codebase is fully implemented for the core e-commerce flow (products → cart → checkout → orders), so you'll be adding polish, fixing edge cases, and potentially building new features from the backlog.

### The Two-Layer Rule (Critical!)

The project has two strict layers:

- **Layer 1 — Production E-Commerce** (products, cart, checkout, orders, auth, admin): Must work perfectly. This is the money-maker.
- **Layer 2 — Analytics & ML Sandbox** (deferred, not yet built): Optional, can crash without affecting the store.

**Cardinal rule:** Layer 1 code **NEVER** imports from Layer 2 modules (`app/analytics/`, `app/ml/`). This is enforced by pre-commit hooks and is an automatic blocker in code review.

---

## 2. Day 1: Environment Setup

### Prerequisites

Before you begin, ensure you have installed:

- **Python 3.11+** — check with `python3 --version` (must show 3.11.x or higher)
- **Node.js 18+** — check with `node --version` (must show v18.x or higher)
- **npm** — comes with Node.js; check with `npm --version`
- **Git** — check with `git --version`
- **Make** — check with `make --version` (pre-installed on macOS/Linux)

If any of these are missing, install them before proceeding.

### Step 1: Clone the Repository

```bash
git clone <repo-url> AtelierMarie
cd AtelierMarie
```

### Step 2: Install All Dependencies

```bash
make setup
```

This runs two sub-targets:
- `make setup-backend` — creates a Python virtual environment at `.venv/` and installs all packages
- `make setup-frontend` — runs `npm install` in the `frontend/` directory

✅ **Checkpoint:** Both commands should complete without errors. Verify:
```bash
.venv/bin/python --version   # Should show Python 3.11.x
cd frontend && node -e "require('./package.json').name" && cd ..
# Should print the project name without errors
```

### Step 3: Configure Environment Variables

```bash
cp .env.example .env
```

Open `.env` and review — for local development, the defaults work. Key settings:

| Variable | Default | Notes |
|----------|---------|-------|
| `ENVIRONMENT` | `development` | Enables debug features |
| `DATABASE_PATH` | `./atelier_marie.db` | SQLite file, auto-created |
| `JWT_SECRET` | `change-me-in-production` | Fine for local dev |
| `GOOGLE_CLIENT_ID` | (empty) | Optional — auth still works without it |
| `ADMIN_API_KEY` | (empty) | Set any string to test admin endpoints |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allows frontend to call backend |

For the frontend:
```bash
cp frontend/.env.local.example frontend/.env.local
```

The key frontend env vars:
- `NEXT_PUBLIC_USE_MOCK_API=true` — Frontend works without the backend running (uses mock data)
- `NEXT_PUBLIC_API_URL=http://localhost:8001` — Where to find the backend (update from the template's default of 8000 to match the Makefile's actual port)

> **Tip:** Start with `NEXT_PUBLIC_USE_MOCK_API=true` until you've verified the backend runs. Then switch to `false` to test real integration.

### Step 4: Start the Backend Server

```bash
make dev-backend
```

✅ **Checkpoint:** You should see output like:
```
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to stop)
INFO:     Started reloader process
```

Test it in another terminal:
```bash
curl http://localhost:8001/v1/products | python3 -m json.tool
```

You should see a JSON response with a `products` array (empty until you seed data).

### Step 5: Seed the Database

```bash
.venv/bin/python scripts/seed_products.py
```

✅ **Checkpoint:** Run the curl command again — you should now see 10 luxury candle products.

### Step 6: Start the Frontend Server

In a new terminal:
```bash
make dev-frontend
```

✅ **Checkpoint:** Open `http://localhost:3000` in your browser. You should see the AtelierMarie storefront with product cards.

### Step 7: Run the Tests

```bash
make test
```

✅ **Checkpoint:** All tests should pass. You'll see output from both pytest (backend) and vitest (frontend). If anything fails, note the error — don't spend more than 15 minutes debugging; ask for help.

### Step 8: Install Pre-commit Hooks

```bash
.venv/bin/pre-commit install
```

✅ **Checkpoint:** Make a trivial change and test:
```bash
echo "" >> README.md
git add README.md
git commit --dry-run
# Should show pre-commit hooks running (ruff, trailing-whitespace, etc.)
git checkout -- README.md   # Undo the change
```

### 🎉 Setup Complete!

You now have:
- Backend running on port 8001 with seeded data
- Frontend running on port 3000
- Tests passing
- Pre-commit hooks installed

---

## 3. Day 1–2: Understand the Architecture

### Guided Reading

Read these files in order. Don't skim — read carefully and take notes on anything confusing.

| Order | File | What to Focus On | Time |
|-------|------|-----------------|------|
| 1 | 📖 `README.md` | Quick overview, development commands | 5 min |
| 2 | 📖 `ARCHITECTURE.md` | System design, data flow diagrams, API surface | 30 min |
| 3 | 📖 `CLAUDE.md` (sections: "Architecture", "Key Design Decisions") | Why decisions were made | 20 min |

### Key Concepts to Understand

After reading, you should be able to answer these questions (write your answers down):

1. **Why SQLite instead of PostgreSQL?** (Hint: scale, simplicity, Oracle Cloud Free Tier)
2. **What does "anonymous-first" mean?** (Hint: users can buy without creating an account)
3. **Why are prices stored in cents as integers?** (Hint: floating-point math errors)
4. **What is the order state machine?** (Draw it: pending → confirmed → shipped → delivered, with cancel rules)
5. **Why does the session middleware create rows eagerly?** (Hint: every request gets a session, even anonymous)
6. **What happens if Layer 2 code crashes?** (Answer: nothing — Layer 1 keeps working)

### Exercise: Trace a Purchase

Using `ARCHITECTURE.md` as your guide, trace the full journey of a customer buying a candle:

1. Customer opens the site → What middleware runs? What's in `request.state`?
2. Customer views products → Which endpoint? Which service function?
3. Customer adds to cart → How is stock validated? What error if out-of-stock?
4. Customer checks out → What happens in a transaction? What's an "order snapshot"?
5. Order is confirmed → Who changes the state? What's the state machine rule?

Write your answers in a scratch file. We'll discuss them in your first 1:1.

### Exercise: Explore the API

With the backend running, try these requests:

```bash
# List products (paginated)
curl "http://localhost:8001/v1/products?page=1&limit=5" | python3 -m json.tool

# Get a single product (use an ID from the list above)
curl "http://localhost:8001/v1/products/lavender-dream-300ml" | python3 -m json.tool

# Search products
curl "http://localhost:8001/v1/products?search=lavender" | python3 -m json.tool

# Add to cart (note: you need a session cookie)
curl -c cookies.txt -b cookies.txt \
  -X POST http://localhost:8001/v1/cart/items \
  -H "Content-Type: application/json" \
  -d '{"product_id": "lavender-dream-300ml", "quantity": 1}' | python3 -m json.tool

# View cart
curl -b cookies.txt http://localhost:8001/v1/cart | python3 -m json.tool
```

✅ **Checkpoint:** You should be able to add items to a cart and retrieve the cart contents.

---

## 4. Day 2–3: Code Patterns Deep Dive

### The Request Lifecycle

Every request flows through these layers:

```
HTTP Request
    → Session Middleware (creates/validates session cookie)
    → Request ID Middleware (adds X-Request-Id header)
    → FastAPI Route (thin — validates input, calls service)
        → Service Function (business logic, DB access)
            → Database (SQLite with parameterized queries)
        ← Service returns dict or raises exception
    ← Route wraps result in Pydantic response model
    ← Global exception handler catches errors → JSON envelope
HTTP Response
```

### Exercise: Read One Full Vertical Slice

Read these files in order to understand the complete "get product by ID" flow:

| Order | File | What to Notice |
|-------|------|---------------|
| 1 | `app/routes/products.py` | Find the `GET /{product_id}` handler. Notice how thin it is — it calls the service and returns a response model. |
| 2 | `app/services/product_service.py` | Find `get_product()`. Notice it takes explicit parameters, accesses the DB, and returns a plain dict. |
| 3 | `app/models/products.py` | Find `ProductResponse`. Notice how it defines the API contract (what the client sees). |
| 4 | `app/database.py` | Understand `get_db()` context manager and how connections are managed. |
| 5 | `app/exceptions.py` | Notice the standard error envelope format. |

### Pattern 1: Thin Routes, Fat Services

**Routes** (`app/routes/`) do three things only:
1. Declare HTTP method, path, and response model
2. Accept validated input (FastAPI + Pydantic handle this)
3. Call a service function and return the result

**Services** (`app/services/`) contain all business logic:
- Pure functions with explicit parameters (no global state)
- Accept a `sqlite3.Connection` when they need DB access
- Return plain Python dicts (not Pydantic models)
- Raise custom exceptions for error cases

```python
# ✅ Good — route is thin
@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str, locale: str = "en"):
    product = product_service.get_product(product_id, locale=locale)
    return product

# ❌ Bad — business logic in route
@router.get("/{product_id}")
async def get_product(product_id: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Not found")
        return dict(row)
```

### Pattern 2: Pydantic Models for Everything

All request/response data uses Pydantic v2 models:

```python
# Request validation
class CreateProductRequest(BaseModel):
    id: str = Field(..., min_length=1, max_length=100)
    name_en: str = Field(..., min_length=1, max_length=200)
    price_cents: int = Field(..., gt=0, le=99_999_99)  # Always cents!

# Response shape
class ProductResponse(BaseModel):
    id: str
    name: str
    price_cents: int
    stock: int
```

Key rules:
- Prices are **always** `price_cents: int` — never `price: float`
- Product IDs are **text slugs** (e.g., `lavender-dream-300ml`) — not integers
- Use `str | None` (not `Optional[str]`) and `list[str]` (not `List[str]`)

### Pattern 3: Database Access

```python
# ✅ Always use context manager
with get_db() as conn:
    row = conn.execute(
        "SELECT * FROM products WHERE id = ?",  # ✅ Parameterized
        (product_id,)
    ).fetchone()

# ❌ NEVER do this — SQL injection risk
conn.execute(f"SELECT * FROM products WHERE id = '{product_id}'")
```

### Pattern 4: Error Handling

Services raise domain-specific exceptions:
```python
# In service:
class NotFoundError(Exception): pass
class InsufficientStockError(Exception):
    def __init__(self, product_id, requested, available): ...

# Global handler converts to HTTP response:
{
    "error": {
        "code": "NOT_FOUND",
        "message": "Product 'xyz' not found",
        "details": null
    }
}
```

### Pattern 5: Dependency Injection

FastAPI's `Depends()` provides auth, sessions, and validated data:

```python
from app.dependencies.auth import require_admin
from app.dependencies.session import require_session

@router.post("/admin/products")
async def create_product(
    request: CreateProductRequest,
    _admin: Annotated[dict, Depends(require_admin)],      # Must be admin
    session_id: Annotated[str, Depends(require_session)],  # Must have session
):
    ...
```

### Exercise: Add a Mental Model

Read `app/routes/cart.py` and `app/services/cart_service.py`. Then answer:

1. What happens when you add a product that doesn't exist?
2. What happens when you add more items than available stock?
3. How does the cart know which user it belongs to? (Hint: session_id)
4. What's the difference between `POST /cart/items` and `PATCH /cart/items/{product_id}`?

---

## 5. Day 3–4: Frontend Patterns

### Architecture Overview

The frontend uses **Next.js 14 App Router** with:
- **Server Components** (default) — fetch data on the server, no client JS needed
- **Client Components** — only when interactivity is required (forms, buttons, state)
- **React Contexts** — global state (Cart, Auth, Admin)
- **API Facade** — single abstraction over real/mock backends

### File Structure

```
frontend/
├── app/[locale]/          # Pages (routes) — locale-aware
│   ├── products/          # Product listing + detail pages
│   ├── checkout/          # Checkout flow
│   ├── orders/            # Order history
│   ├── admin/             # Admin panel
│   └── layout.tsx         # Root layout with providers
├── components/            # Reusable UI
│   ├── ui/                # Primitives (Button, Input, Badge, Skeleton)
│   ├── products/          # ProductCard, ProductGrid, ReactionBar
│   ├── cart/              # CartDrawer, AddToCartButton
│   └── layout/            # Header, Footer
├── contexts/              # State management
│   ├── CartContext.tsx     # Cart state + API sync
│   ├── AuthContext.tsx     # Auth state + JWT management
│   └── AdminContext.tsx    # Admin context
├── lib/
│   ├── types.ts           # TypeScript interfaces (mirrors Pydantic models)
│   ├── api.ts             # Facade — ALL API calls go through here
│   ├── api-client.ts      # Real fetch wrapper (internal)
│   ├── mock-api.ts        # Mock data for dev without backend
│   └── utils.ts           # cn() helper, formatters
└── __tests__/             # Unit tests (vitest + testing-library)
```

### Pattern 1: Server Components Fetch, Client Components Interact

```tsx
// Server component — fetches data at request time
// No "use client" directive = server component by default
export default async function ProductsPage() {
  const { products } = await getProducts(1, 100);
  return <ProductGrid products={products} />;
}

// Client component — handles user interaction
"use client";
export function AddToCartButton({ productId }: { productId: string }) {
  const { addItem } = useCart();
  return <button onClick={() => addItem(productId, 1)}>Add to Cart</button>;
}
```

### Pattern 2: The API Facade

**Never import `api-client.ts` directly in components.** Always go through `lib/api.ts`:

```typescript
// lib/api.ts — single source of truth
export async function getProducts(page: number, limit: number) {
  if (USE_MOCK) return (await getMock()).getProducts(page, limit);
  return apiClient.get<ProductListResponse>(`/v1/products?page=${page}&limit=${limit}`);
}
```

This lets the frontend work in two modes:
- **Mock mode** (`NEXT_PUBLIC_USE_MOCK_API=true`): No backend needed, uses fake data
- **Real mode** (`NEXT_PUBLIC_USE_MOCK_API=false`): Calls the FastAPI backend

### Pattern 3: Optimistic Updates with Rollback

The CartContext shows the pattern for responsive UI:

```typescript
// 1. Save current state for rollback
const previousState = structuredClone(stateRef.current);

// 2. Optimistically update UI immediately
dispatch({ type: "OPTIMISTIC_ADD", payload: { productId, quantity } });

// 3. Call API in background
try {
  const cart = await addToCart(productId, quantity);
  dispatch({ type: "API_SUCCESS", payload: cart });
} catch (error) {
  // 4. Rollback on failure
  dispatch({ type: "API_FAILURE", payload: { previousState, error: "Failed" } });
}
```

### Pattern 4: TypeScript Types Mirror Pydantic

```typescript
// frontend/lib/types.ts
interface Product {
  id: string;              // Same as Pydantic ProductResponse.id
  name: string;            // Locale-resolved
  price_cents: number;     // Always cents — format at display time
  stock: number;
}
```

Price formatting happens at the UI layer:
```typescript
function formatPrice(cents: number): string {
  return `€${(cents / 100).toFixed(2)}`;
}
```

### Exercise: Trace a Frontend Feature

Open `frontend/contexts/CartContext.tsx` and answer:

1. What state does the cart hold? (items, totals, loading, error?)
2. When does the cart hydrate from the API? (on mount? on demand?)
3. What happens if the user adds an item while offline?
4. How does the cart know when a user logs in and the session rotates?

---

## 6. Day 4: Testing & Quality

### Backend Testing

Two test directories with different purposes:

| Directory | Purpose | Fixtures | Speed |
|-----------|---------|----------|-------|
| `tests/` | Unit + route tests | Module-scoped, fake middleware | Fast ⚡ |
| `tests/realapp/` | Integration tests | Function-scoped, real middleware | Slower |

### Running Tests

```bash
# All tests (backend + frontend)
make test

# Backend only (parallel execution)
make test-backend

# Backend with coverage report
make test-backend-cov

# Frontend only
make test-frontend

# Frontend in watch mode (re-runs on file change)
make test-frontend-watch

# Run a specific test file
.venv/bin/pytest tests/test_product_routes.py -v

# Run a specific test by name
.venv/bin/pytest tests/ -k "test_get_product_returns_404" -v
```

### How Backend Tests Are Structured

📖 Read `conftest.py` (at the repo root) — this is the root fixture file.

Key fixtures:
- **`db`** (module-scoped): Creates an in-memory SQLite database with schema
- **`app`** (module-scoped): FastAPI app instance with fake session middleware
- **`client`** (module-scoped): Async HTTP test client
- **`_clean_tables`** (function-scoped, autouse): Deletes all data between tests for isolation

### Writing a Test — Template

```python
import pytest
from httpx import AsyncClient

class TestGetProduct:
    """Tests for GET /v1/products/{product_id}"""

    @pytest.mark.asyncio
    async def test_returns_product_when_exists(self, client: AsyncClient, _seed_product):
        response = await client.get("/v1/products/lavender-dream-300ml")
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == "lavender-dream-300ml"
        assert body["price_cents"] > 0

    @pytest.mark.asyncio
    async def test_returns_404_when_not_found(self, client: AsyncClient):
        response = await client.get("/v1/products/nonexistent")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOT_FOUND"
```

### What to Test (Priority Order)

1. **Happy path** — Does it work when everything is correct?
2. **Validation errors** — Bad input returns 422 with helpful message?
3. **Not found** — Missing resources return 404?
4. **Auth boundaries** — Unauthenticated users can't access admin endpoints?
5. **Business logic edges** — Out of stock? Cart empty at checkout? Invalid state transition?

### Frontend Testing

```typescript
// frontend/__tests__/components/ProductCard.test.tsx
import { render, screen } from "@testing-library/react";
import { ProductCard } from "@/components/products/ProductCard";

describe("ProductCard", () => {
  it("renders product name and formatted price", () => {
    render(<ProductCard product={mockProduct} />);
    expect(screen.getByText("Lavender Dream")).toBeInTheDocument();
    expect(screen.getByText("€24.99")).toBeInTheDocument();
  });
});
```

### Exercise: Write Your First Test

1. Find a service function in `app/services/product_service.py` that doesn't have full test coverage
2. Look at existing tests in `tests/test_product_service.py` for patterns
3. Write one new test case that tests an edge case (e.g., searching with special characters)
4. Run it: `.venv/bin/pytest tests/test_product_service.py -v -k "your_test_name"`

---

## 7. Day 5: Development Workflow

### Git Workflow

```bash
# 1. Always start from main
git checkout main
git pull origin main

# 2. Create a feature branch
git checkout -b feat/add-product-sorting

# 3. Make changes, commit often
git add app/services/product_service.py
git commit -m "[feat] add sorting options to product listing"

# 4. Push and open a PR
git push -u origin feat/add-product-sorting
```

### Commit Message Convention

```
[type] short description

Types:
  [feat]  — New feature
  [fix]   — Bug fix
  [test]  — Adding/fixing tests
  [docs]  — Documentation
  [refactor] — Code change that doesn't add features or fix bugs
  [chore] — Maintenance tasks
```

### Pre-commit Hooks (Automated Quality Gates)

When you run `git commit`, these hooks run automatically:

1. **ruff format** — Auto-formats Python code
2. **ruff check --fix** — Fixes lint violations
3. **Trailing whitespace** — Removes trailing spaces
4. **Layer boundary check** — Blocks Layer 1 → Layer 2 imports
5. **No os.environ** — Blocks `os.environ`/`os.getenv` (use `get_settings()`)
6. **No float prices** — Blocks `price: float` patterns
7. **Secrets detection** — Blocks committed secrets/keys

If a hook fails, it will tell you exactly what to fix. Fix it, `git add` the changes, and commit again.

### Code Review Standards

When your PR is reviewed, reviewers check (in priority order):

1. **Layer boundary violations** — Always a blocker (instant rejection)
2. **Data integrity** — Money calculations, stock consistency, order snapshots
3. **Security** — SQL injection, auth bypass, XSS
4. **Logic bugs** — State machine violations, race conditions
5. **Spec compliance** — Does the code match the feature spec in `openspec/`?
6. **Test coverage** — New code must have tests
7. **Style/patterns** — Only flagged if confusing

### The Development Loop

```
┌─────────────────────────────────────────────────────────┐
│  1. Pick a task (from your assigned issues)              │
│  2. Read the relevant spec in openspec/changes/          │
│  3. Understand existing code (service + route + model)   │
│  4. Write the implementation                             │
│  5. Write tests                                          │
│  6. Run: make test && make lint                          │
│  7. Commit (hooks validate automatically)                │
│  8. Open PR → Get review → Address feedback → Merge      │
└─────────────────────────────────────────────────────────┘
```

---

## 8. Common Pitfalls & FAQ

### ❌ "I activated the venv and things broke"

**Never** run `source .venv/bin/activate`. Use the `.venv/bin/` prefix directly:

```bash
# ✅ Correct
.venv/bin/pytest tests/ -v
.venv/bin/python scripts/seed_products.py

# ❌ Wrong — don't do this
source .venv/bin/activate
pytest tests/ -v
```

Why? The `make` targets and CI all use the prefix approach. Activating the venv can conflict with system Python and cause subtle issues.

### ❌ "My test passes alone but fails in parallel"

Tests run in parallel via pytest-xdist. Each test file gets its own database, but tests **within** a file share one DB (module-scoped fixtures). The `_clean_tables` fixture deletes data between tests.

Fix: Make sure your test doesn't depend on data from another test in the same file. Each test should set up its own data.

### ❌ "I used os.environ and the commit was rejected"

All configuration goes through Pydantic settings:

```python
# ❌ Rejected by pre-commit hook
import os
db_path = os.environ.get("DATABASE_PATH")

# ✅ Correct
from app.config import get_settings
settings = get_settings()
db_path = settings.database_path
```

### ❌ "I used a float for price and the hook blocked me"

Prices are **always** integers in cents:

```python
# ❌ Blocked
price: float = 24.99

# ✅ Correct
price_cents: int = 2499
```

### ❌ "I put business logic in the route"

Routes are thin wrappers. Move logic to the service layer:

```python
# ❌ Logic in route
@router.post("/checkout")
async def checkout(session_id: str):
    with get_db() as conn:
        cart = conn.execute("SELECT ...").fetchall()
        if not cart:
            raise HTTPException(400, "Cart empty")
        # ... 50 more lines of logic ...

# ✅ Route calls service
@router.post("/checkout")
async def checkout(session_id: Annotated[str, Depends(require_session)]):
    order = order_service.checkout(session_id)
    return OrderResponse(**order)
```

### ❌ "I imported api-client.ts directly in a component"

Always go through the facade:

```typescript
// ❌ Wrong — breaks mock mode
import { apiClient } from "@/lib/api-client";
const products = await apiClient.get("/v1/products");

// ✅ Correct — works in both real and mock mode
import { getProducts } from "@/lib/api";
const products = await getProducts(1, 20);
```

### ❌ "My SQL query uses string formatting"

This is a security vulnerability (SQL injection):

```python
# ❌ NEVER — SQL injection risk
conn.execute(f"SELECT * FROM products WHERE id = '{user_input}'")

# ✅ ALWAYS — parameterized query
conn.execute("SELECT * FROM products WHERE id = ?", (user_input,))
```

### FAQ

**Q: Where do I find the API documentation?**
A: Run the backend and visit `http://localhost:8001/docs` — FastAPI generates interactive Swagger docs automatically.

**Q: How do I test admin endpoints?**
A: Set `ADMIN_API_KEY=test-key` in your `.env`, then use the header `Authorization: Bearer test-key`:
```bash
curl -H "Authorization: Bearer test-key" http://localhost:8001/v1/admin/dashboard
```

**Q: How do I reset the database?**
A: Delete `atelier_marie.db` and restart the backend — the schema recreates on startup. Then re-run `seed_products.py`.

**Q: How do I run only one test file?**
A: `.venv/bin/pytest tests/test_product_routes.py -v --tb=short`

**Q: The frontend shows "mock" data even though my backend is running?**
A: Check `frontend/.env.local` — set `NEXT_PUBLIC_USE_MOCK_API=false` and restart the frontend dev server.

**Q: What's the `openspec/` directory?**
A: Feature specifications. Before implementing a feature, read its spec in `openspec/changes/<feature>/design.md` for requirements and acceptance criteria.

---

## 9. Graduated First Tasks

These are ordered from easiest to most challenging. Complete them in order to build confidence.

### 🟢 Level 1: Orientation (No code changes)

1. **Explore the API docs** — Visit `http://localhost:8001/docs`, try 5 different endpoints using the interactive UI
2. **Read a feature spec** — Pick any spec in `openspec/changes/` and summarize it in 3 sentences
3. **Trace a test failure** — Intentionally break a service function and see what the test output looks like. Then fix it.

### 🟡 Level 2: Small Fixes (1-2 files)

4. **Add a test case** — Find a service function with an untested edge case and write a test for it
5. **Improve error messages** — Find a generic error message in a service and make it more descriptive
6. **Add field validation** — Add a `max_length` or `min_length` constraint to a Pydantic model field that's missing one

### 🟠 Level 3: Small Features (2-4 files)

7. **Add a new query parameter** — Add a `sort_by` parameter to the product listing endpoint (route + service + test)
8. **Add a response field** — Add a computed field to a response model (e.g., `is_in_stock: bool` derived from `stock > 0`)
9. **Frontend component** — Create a small UI component (e.g., a "back to top" button) following existing component patterns

### 🔴 Level 4: Meaningful Feature (Full vertical slice)

10. **New endpoint** — Implement a new API endpoint end-to-end: model → service → route → test → frontend integration

For Level 4, your mentor will assign a specific feature from the backlog with clear requirements.

---

## 10. Resources & Key Files

### Files to Bookmark

| File | Purpose | When to Reference |
|------|---------|-------------------|
| `ARCHITECTURE.md` | System design, data flows, API surface | Understanding the big picture |
| `CLAUDE.md` | Coding standards, commands, conventions | Writing code, opening PRs |
| `Makefile` | All development commands | Daily work |
| `app/config.py` | Environment variables | Adding new config |
| `app/exceptions.py` | Error handling patterns | Handling new error cases |
| `conftest.py` (repo root) | Test fixture patterns | Writing new tests |
| `openspec/changes/` | Feature specifications | Before implementing any feature |

### Interactive Resources

- **API Docs**: `http://localhost:8001/docs` (Swagger UI, auto-generated)
- **Design System**: `http://localhost:3000/design-system` (component gallery)
- **Frontend in Mock Mode**: Set `NEXT_PUBLIC_USE_MOCK_API=true` to develop UI without backend

### Getting Help

- **Stuck on setup?** → Re-read this guide's checkpoints; if still stuck after 15 minutes, ask.
- **Don't understand a pattern?** → Read the surrounding code for examples; most patterns repeat.
- **Not sure where code goes?** → Check `CLAUDE.md` section "Module Organization."
- **Don't know if something is a bug or feature?** → Check the spec in `openspec/changes/`.
- **Pre-commit hook is blocking you?** → Read the error message; it tells you exactly what's wrong.

---

## Checklist: End of Week 1

By the end of your first week, you should be able to check off all of these:

- [ ] Environment running (backend + frontend + tests passing)
- [ ] Can explain the two-layer architecture and why it matters
- [ ] Can trace a request from HTTP to database and back
- [ ] Can explain what the session middleware does
- [ ] Understand the difference between routes, services, and models
- [ ] Have run tests and know how to write a new one
- [ ] Have made at least one commit that passes pre-commit hooks
- [ ] Have completed at least 2 tasks from the graduated list above
- [ ] Know where to find API docs, feature specs, and coding standards

If you can't check something off, that's completely normal — flag it for discussion in your next 1:1.

---

*Welcome aboard! 🕯️ — The AtelierMarie Team*
