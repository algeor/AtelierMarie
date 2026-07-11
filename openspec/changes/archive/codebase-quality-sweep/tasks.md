## 1. Linting Cleanup (Quick Wins)

- [ ] 1.1 Run `ruff check --fix .` to auto-fix I001 (unsorted imports) and W292 (missing EOF newline)
- [ ] 1.2 Run `ruff format .` to reformat all 18 files with formatting violations
- [ ] 1.3 Manually wrap remaining E501 lines (long strings, docstrings, inline dicts) to ≤100 chars
- [ ] 1.4 Verify `ruff check .` and `ruff format --check .` both pass with zero violations

## 2. Backend Shared Infrastructure

- [ ] 2.1 Create `app/constants.py` with `SQLITE_DT_FMT` constant
- [ ] 2.2 Replace local `_SQLITE_DT_FMT` in `middleware/session.py`, `routes/auth.py`, and `services/order_service.py` with import from `app.constants`
- [ ] 2.3 Create `_ProductFieldValidators` mixin class in `app/models/products.py` with `strip_and_reject_blank` and `validate_image_url`
- [ ] 2.4 Refactor `CreateProductRequest` and `UpdateProductRequest` to inherit from the mixin
- [ ] 2.5 Create `_unauthorized(message)` helper in `app/routes/auth.py` and replace four inline JSONResponse blocks
- [ ] 2.6 Create `get_session_user_id` FastAPI dependency in `app/dependencies/session.py`
- [ ] 2.7 Refactor `app/routes/orders.py` to use `get_session_user_id` dependency instead of inline SQL
- [ ] 2.8 Extract `_build_field_map(data)` helper in `app/services/product_service.py` and use in both `upsert_product` and `update_product`
- [ ] 2.9 Remove redundant `limit = min(limit, 100)` from `app/routes/products.py` and `app/routes/admin.py`
- [ ] 2.10 Refactor list endpoints to use `PaginationParams` or typed aliases from `app/models/common.py`

## 3. Backend Query Optimization

- [ ] 3.1 Refactor `list_orders` in `order_service.py` to batch-fetch order items with `WHERE order_id IN (...)`
- [ ] 3.2 Refactor `list_orders_admin` similarly
- [ ] 3.3 Refactor product search in `app/routes/products.py` (or product_service) to push category/stock filters into the FTS5 SQL query with LIMIT/OFFSET
- [ ] 3.4 Refactor CSV import in `app/routes/admin.py` to pre-fetch existing product IDs in one batch query

## 4. Backend Consistency

- [ ] 4.1 Convert `create_order`, `list_my_orders`, and `get_order_detail` in `app/routes/orders.py` from `def` to `async def`

## 5. Frontend Performance

- [ ] 5.1 Wrap AuthContext provider `value` in `useMemo` with appropriate dependency array
- [ ] 5.2 Wrap CartContext provider `value` in `useMemo` with appropriate dependency array
- [ ] 5.3 Refactor `AdminProvider` to consume `useAuth()` instead of calling `getCurrentUser()` directly

## 6. Frontend Deduplication

- [ ] 6.1 Create `frontend/hooks/useAddToCart.ts` hook encapsulating the idle→loading→success→reset state machine
- [ ] 6.2 Refactor `AddToCartButton` to use `useAddToCart` hook
- [ ] 6.3 Refactor `AddToCartSection` to use `useAddToCart` hook
- [ ] 6.4 Create unified `ORDER_STATUS_STYLES` constant (e.g., in `frontend/lib/constants.ts` or alongside `OrderStatusBadge`)
- [ ] 6.5 Refactor `OrderStatusBadge` and admin orders page to import from the shared constant
- [ ] 6.6 Replace inline button class strings in orders/account/callback pages with the `Button` component

## 7. Frontend Convention Fixes

- [ ] 7.1 Replace raw `<img>` with `next/image` in `UserMenu.tsx` (configure `images.remotePatterns` in `next.config.js` for Google avatar domains)
- [ ] 7.2 Replace raw `<img>` with `next/image` in `app/account/page.tsx`
- [ ] 7.3 Refactor `StatusTimeline.tsx` to use `cn()` utility instead of template-literal className
- [ ] 7.4 Replace hand-rolled inputs in `app/checkout/page.tsx` with the `Input` component from `components/ui/Input`

## 8. Verification

- [ ] 8.1 Run `pytest` — all existing tests must pass
- [ ] 8.2 Run `ruff check . && ruff format --check .` — zero violations
- [ ] 8.3 Run frontend tests (`npm test` in `frontend/`) — all pass
- [ ] 8.4 Manual smoke test: product search with filters, order listing, CSV import, checkout flow
