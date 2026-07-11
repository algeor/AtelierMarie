## Context

AtelierMarie is a luxury candle e-commerce platform with a FastAPI backend (SQLite, WAL mode) and a Next.js 14 frontend. A full-codebase review identified 20 findings across performance, duplication, and convention adherence. The codebase is small (~30 Python modules, ~50 frontend files) making this the ideal time to address structural debt before it compounds.

Current state:
- Backend has N+1 query patterns in order listing (41 queries per page-load)
- FTS5 search fetches all results into Python memory before filtering
- CSV import probes the DB per-row instead of batching
- Frontend React contexts recreate value objects every render, triggering unnecessary re-renders
- Validators, constants, and UI patterns are copy-pasted in 2-6 locations
- 46 ruff lint violations and 18 unformatted files

## Goals / Non-Goals

**Goals:**
- Eliminate N+1 queries and in-Python filtering to meet <200ms response target
- Reduce code duplication to single-source-of-truth for validators, constants, helpers, and UI patterns
- Memoize React context values to prevent unnecessary re-render cascades
- Pass all ruff checks cleanly (zero violations)
- Maintain full backward compatibility (no API changes, all tests pass)

**Non-Goals:**
- Introducing new features or endpoints
- Changing the database schema
- Migrating to an ORM or query builder
- Refactoring the overall architecture (service layer pattern stays)
- Addressing correctness/logic bugs (separate concern)

## Decisions

### 1. Batch order-item fetch with `WHERE order_id IN (...)`

**Choice**: Replace per-order `_fetch_order_with_items` loop with a single `SELECT * FROM order_items WHERE order_id IN (?, ?, ...)` query, then group in Python.

**Why not JOINs**: A JOIN with order + items creates duplicate order rows per item, complicating pagination. Two queries (orders + items) is simpler and still reduces 41→2 queries.

### 2. Push filters into FTS5 SQL via subquery

**Choice**: Use `SELECT * FROM products WHERE id IN (SELECT rowid FROM products_fts WHERE products_fts MATCH ?) AND category = ? AND stock > 0 LIMIT ? OFFSET ?`

**Alternatives considered**: CTE, FTS5 external content table with category column. The subquery approach requires no schema changes and pushes filtering+pagination into SQLite.

### 3. Shared constants module `app/constants.py`

**Choice**: New `app/constants.py` for `SQLITE_DT_FMT` and any future cross-module constants. Import from there in all three current consumers.

**Why not `database.py`**: That module manages connections; constants don't belong to connection management. A dedicated module is clearer.

### 4. Validator mixin for product models

**Choice**: Define `_ProductFieldValidators` mixin class with `strip_and_reject_blank` and `validate_image_url` as `@field_validator` methods. Both `CreateProductRequest` and `UpdateProductRequest` inherit it.

**Why not standalone functions**: Pydantic v2 `@field_validator` decorators need to live on a class. A mixin composes cleanly.

### 5. `useMemo` for context values

**Choice**: Wrap the context `value` object in `useMemo` with explicit dependency arrays in AuthContext and CartContext.

**Why not `useReducer`**: The current state shape is fine; the issue is purely reference stability of the value object, which `useMemo` solves with minimal refactoring.

### 6. AdminContext consumes AuthContext instead of re-fetching

**Choice**: `AdminProvider` calls `useAuth()` to get the user, checks `is_admin`, and provides admin-specific state. No separate `getCurrentUser()` call.

**Why**: Eliminates the duplicate HTTP request and keeps a single source of truth for current-user data.

### 7. `useAddToCart` custom hook

**Choice**: Extract the idle→loading→success→reset state machine into a `hooks/useAddToCart.ts` hook. Both `AddToCartButton` and `AddToCartSection` consume it.

**Why not a shared component**: The two components have different UI (button-only vs section with quantity selector); only the logic is shared.

## Risks / Trade-offs

- **[Risk] Large `IN (...)` clause for order items** → Mitigation: Paginated to max 100 orders, so the IN clause is bounded. SQLite handles this fine.
- **[Risk] Mixin inheritance order in Pydantic** → Mitigation: Place mixin first in MRO (`class Create(_Validators, BaseModel)`). Test both models after change.
- **[Risk] Ruff auto-fix may break long strings** → Mitigation: Run test suite after `ruff format`; manually fix any string-wrapping issues.
- **[Risk] useMemo dependency arrays may be incomplete** → Mitigation: Enable `eslint-plugin-react-hooks` exhaustive-deps rule to catch missing deps.
- **[Trade-off]** Adding `app/constants.py` introduces a new module for just one constant today — but it's the canonical place for future shared values.
