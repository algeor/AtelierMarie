## Why

A full-codebase review uncovered 20 findings across the Python backend and TypeScript frontend: N+1 query patterns that will miss the <200ms response target, copy-pasted validators and constants that have already diverged, unmemoized React contexts causing unnecessary re-renders site-wide, and 46 ruff lint violations. Addressing these now — while the codebase is small — prevents compounding maintenance debt and performance regressions before they reach production.

## What Changes

- **Backend query optimization**: Batch-fetch order items (fix N+1), push category/stock filters into FTS5 SQL, eliminate per-row SELECT in CSV import.
- **Backend deduplication**: Extract shared constants (`_SQLITE_DT_FMT`), validator mixins, response helpers (`_unauthorized`), and a `get_session_user_id` dependency.
- **Backend consistency**: Convert sync order handlers to `async def`, apply unused `PaginationParams`, remove dead `min(limit, 100)` code.
- **Frontend performance**: Memoize AuthContext/CartContext provider values; remove duplicate `getCurrentUser()` call in AdminProvider.
- **Frontend deduplication**: Extract `useAddToCart` hook, unify status color maps, replace inline button/input styling with existing UI components.
- **Frontend conventions**: Use `next/image` for avatars, `cn()` for all className composition, `Input` component in checkout.
- **Linting**: Auto-fix all ruff violations (E501, I001, W292) and reformat 18 files.

## Capabilities

### New Capabilities
- `backend-query-optimization`: Fix N+1 in order listing, push filters into SQL, batch CSV import lookups
- `backend-deduplication`: Extract shared constants, validator mixins, response helpers, FastAPI dependencies
- `frontend-performance`: Memoize context values, remove duplicate fetches
- `frontend-deduplication`: Extract hooks, unify color maps, replace inline styling with shared components
- `linting-cleanup`: Auto-fix ruff violations and reformat all Python files

### Modified Capabilities

_(No existing spec-level requirements are changing — this is purely internal quality improvement.)_

## Impact

- **Backend files touched**: `app/services/order_service.py`, `app/services/product_service.py`, `app/routes/products.py`, `app/routes/admin.py`, `app/routes/auth.py`, `app/routes/orders.py`, `app/models/products.py`, `app/models/common.py`, `app/middleware/session.py`, `app/config.py` (or new `app/constants.py`)
- **Frontend files touched**: `frontend/contexts/AuthContext.tsx`, `frontend/contexts/CartContext.tsx`, `frontend/contexts/AdminContext.tsx`, `frontend/components/cart/AddToCartButton.tsx`, `frontend/components/orders/StatusTimeline.tsx`, `frontend/components/auth/UserMenu.tsx`, `frontend/app/checkout/page.tsx`, `frontend/app/orders/page.tsx`, `frontend/app/admin/orders/page.tsx`
- **APIs**: No external API changes — all improvements are internal.
- **Tests**: Existing tests must continue passing; no new endpoints or behaviors introduced.
