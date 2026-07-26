## 1. Infrastructure & Dependencies

- [x] 1.1 Add Selenium E2E deps (`selenium>=4.20.0`, `webdriver-manager>=4.0.0`, `pytest-selenium>=4.1.0`) to `tests/e2e/requirements.txt` — kept OUT of `pyproject.toml` to keep package metadata clean; E2E is opt-in via `make setup-ui-testing`. `httpx` remains a runtime dep (do not re-add). `PyJWT` is not needed as a separate line — the runtime `pyjwt[crypto]>=2.8.0` covers the admin-session fixture.
- [x] 1.2 Create `tests/e2e/` and `tests/e2e/screenshots/` directories with `__init__.py` (screenshots/ gets a `.gitkeep`, not `__init__.py`)
- [x] 1.3 Create `tests/e2e/conftest.py` with: session-scoped WebDriver fixture (headless Chrome, respects `HEADLESS=0`), server reachability check, admin API seed/teardown for `e2e-test-candle`, assertion that seed product is reachable before any test runs, `pytest_runtest_makereport` hook that saves `screenshots/{test_name}.png` on failure
- [x] 1.4 Create `tests/e2e/pages/__init__.py` and `tests/e2e/pages/base_page.py` with `BasePage` — `BASE_URL`, `BASE_LOCALE` constants, `wait_for()` helper, `cart` property returning `CartDrawerComponent`, `header` property returning `HeaderComponent`, URL guard helper `assert_url_contains(pattern)`
- [x] 1.5 Add `make setup-ui-testing` and `make test-e2e` targets to `Makefile` — `setup-ui-testing` depends on `setup-backend` and installs `-r tests/e2e/requirements.txt` into `.venv`; `test-e2e` assumes both dev servers are already running (does NOT start them); conftest emits a helpful skip message if either port is unreachable

## 2. Testid Constants — Single Source of Truth

- [x] 2.1 Create `frontend/lib/testids.ts` exporting the 14 testid constants as a typed `TEST_IDS` object — static strings for simple elements, arrow functions for dynamic ids (`cartItem`, `cartRemove`, `adminProductRow`, `adminEditLink`, `orderRow`). NOTE: adds `loginButton` (needed by header/auth tests); the admin edit link uses `<Link>`, so the constant is `adminEditLink` (not `adminEditBtn`). Drops `productSearch` — no search UI exists on the products page (the page uses `CategoryFilter`; a `categoryFilter` testid is added instead for the filter group).
- [x] 2.2 Create `scripts/generate_testids.py` — reads `frontend/lib/testids.ts`, extracts all string values from `TEST_IDS` using regex, writes `tests/e2e/testids.py` with matching Python constants and lambdas
- [x] 2.3 Add `make generate-testids` target to `Makefile` (runs `scripts/generate_testids.py`); run it now to produce the initial `tests/e2e/testids.py`
- [x] 2.4 Add CI step to `.github/workflows/frontend-unit-tests.yml`: run `make generate-testids && git diff --exit-code tests/e2e/testids.py` — fails if `testids.py` is stale

## 3. Add data-testid Attributes to Frontend Components

- [x] 3.1 Add `data-testid={TEST_IDS.productCard}` to `frontend/components/products/ProductCard.tsx`
- [x] 3.2 Add `data-testid={TEST_IDS.categoryFilter}` to the filter group in `frontend/components/products/CategoryFilter.tsx` (replaces the original `productSearch` testid — no search input exists)
- [x] 3.3 Add `data-testid={TEST_IDS.cartBadge}` to the badge span in `frontend/components/cart/CartBadge.tsx`
- [x] 3.4 Add `data-testid={TEST_IDS.cartDrawer}` to the drawer container in `frontend/components/cart/CartDrawer.tsx`
- [x] 3.5 Add `data-testid={TEST_IDS.cartItem(product_id)}` and `data-testid={TEST_IDS.cartRemove(product_id)}` to `frontend/components/cart/CartItem.tsx`
- [x] 3.6 Add `data-testid={TEST_IDS.addToCartBtn}` to `frontend/components/cart/AddToCartButton.tsx`
- [x] 3.7 Add `data-testid={TEST_IDS.commentForm}` to `frontend/components/products/CommentForm.tsx` (on the `<form>`) and `data-testid={TEST_IDS.commentCard}` to `CommentCard.tsx` (on the `<article>`)
- [x] 3.8 Add `data-testid={TEST_IDS.adminProductRow(product.id)}` to the `<tr>` and `data-testid={TEST_IDS.adminEditLink(product.id)}` to the edit `<Link>` in `frontend/app/[locale]/admin/products/page.tsx`
- [x] 3.9 Add `data-testid={TEST_IDS.orderRow(order.id)}` to the order `<Link>` on `frontend/app/[locale]/orders/page.tsx` and `data-testid={TEST_IDS.orderStatus}` to `frontend/components/orders/OrderStatusBadge.tsx`
- [x] 3.10 Add `data-testid={TEST_IDS.loginButton}` to the `<button>` in `frontend/components/auth/LoginButton.tsx`

## 4. Vitest Contract Test

- [x] 4.1 Create `frontend/__tests__/testids.contract.test.tsx` — renders each E2E-covered component in isolation and asserts its `data-testid` attribute is present; one `it()` per component; runs as part of `make test-frontend`

## 5. Path-Based CI Pairing Rule

- [x] 5.1 Create `.github/workflows/e2e-pairing.yml` — on `pull_request` only, uses `dorny/paths-filter` to detect changed directories; fails if `frontend/components/cart/**` changed without `tests/e2e/test_cart.py`, same pairing for checkout, admin, products/reactions/comments, orders

## 6. Component Objects

- [x] 6.1 Create `tests/e2e/components/__init__.py`
- [x] 6.2 Create `tests/e2e/components/header.py` — `HeaderComponent(driver)` with `get_badge_count()` (waits for CartContext to hydrate, returns 0 if badge absent after wait), `click_login_button()`
- [x] 6.3 Create `tests/e2e/components/cart_drawer.py` — `CartDrawerComponent(driver)` with `open_drawer()`, `get_items()`, `update_quantity(product_id, qty)`, `remove_item(product_id)`, `close_drawer()`

## 7. Admin Session Injection Fixture

- [x] 7.1 Add `inject_admin_session` fixture to `tests/e2e/conftest.py` — inserts a user row (`is_admin=1`, this DB value is what `/v1/auth/me` returns to the frontend) and session row directly into SQLite (reads `DB_PATH` from env, defaults to `./atelier_marie.db`), calls `driver.get(BASE_URL)` first, then `driver.add_cookie()` for both `session_id` (UUID matching the inserted `sessions.id`) and `atelier_auth` (PyJWT-signed using `JWT_SECRET` from env; default `dev-secret-do-not-use-in-production` matches `app/config.py`). The JWT payload MUST include the full claim set expected by `app/services/auth_service.py::verify_jwt`: `user_id`, `email`, `is_admin=true`, `session_id` (equal to the session cookie), `iss="atelier-marie"`, `aud="atelier-marie-web"`, `iat`, `exp` — any missing/mismatched claim → `verify_jwt` returns None → `/v1/auth/me` returns null → `AdminContext.isAdmin=false` → admin pages redirect. Teardown deletes both rows.

## 8. Page Object Classes

- [x] 8.1 Create `tests/e2e/pages/product_listing_page.py` — URL guard (`/products`), locators via `testids.py`; `navigate()`, `filter_category(name)` (replaces `search(term)`; clicks a category chip in the CategoryFilter group), `get_product_cards()`, `click_first_product() → ProductDetailPage`
- [x] 8.2 Create `tests/e2e/pages/product_detail_page.py` — URL guard (`/products/`), `get_title()`, `get_price()`, `click_add_to_cart() → CartDrawerComponent` (waits for button success state), `click_reaction(reaction_type)` where `reaction_type ∈ {"heart", "thumbs_up"}` — locator uses `aria-label` mapping (not per-reaction testid); `get_reaction_count(reaction_type)`, `submit_comment(text, display_name)` (both required for anonymous), `get_comments()`
- [x] 8.3 Create `tests/e2e/pages/checkout_page.py` — URL guard (`/checkout`), `navigate()`, `fill_email()`, `fill_name()`, `select_door_delivery(courier, address)`, `submit_expecting_success() → OrderConfirmationPage`, `submit_expecting_error() → CheckoutPage`, `get_validation_errors()`
- [x] 8.4 Create `tests/e2e/pages/order_confirmation_page.py` — URL guard `/orders/` AND `/confirmation` (route is `/orders/[id]/confirmation`, not `/confirmation` alone), `get_order_id()`
- [x] 8.5 Create `tests/e2e/pages/orders_page.py` — URL guard (`/orders` exact — not `/orders/`), `navigate()`, `get_order_rows()`, `navigate_to_order(order_id) → OrderDetailPage`
- [x] 8.6 Create `tests/e2e/pages/order_detail_page.py` — URL guard (`/orders/{id}` — path segment after `/orders/` present and NOT `/confirmation`), `get_status()`, `get_items()`, `get_total()`
- [x] 8.7 Create `tests/e2e/pages/admin_page.py` — URL guard (`/admin`), `navigate_dashboard()`, `navigate_products()`, `navigate_new_product() → AdminProductFormPage`, `click_edit(product_id) → AdminProductFormPage` (uses `adminEditLink` testid, navigates to `/admin/products/{id}/edit`), `get_product_rows()`
- [x] 8.8 Create `tests/e2e/pages/admin_product_form_page.py` — URL guard (`/admin/products` — matches both `/new` and `/{id}/edit`), `fill_product_form(data)`, `submit_expecting_success() → AdminPage`, `submit_expecting_error() → AdminProductFormPage`
- [x] 8.9 Create `tests/e2e/pages/auth_page.py` — `click_login_button()`, `get_current_url()`, `navigate_auth_callback()`
- [x] 8.10 Create `tests/e2e/pages/contact_page.py` — URL guard (`/contact`), `navigate()`, `fill_form(name, email, message)`, `submit()`, `get_validation_errors()`

## 9. Test Modules — Product & Cart

- [x] 9.1 Create `tests/e2e/test_products.py` — products page loads with cards, category filter narrows visible cards (was: search filters results — replaced because no search UI exists), product detail loads with name/price/add-to-cart visible (waits for client components to hydrate)
- [x] 9.2 Create `tests/e2e/test_cart.py` — add to cart increments badge (with hydration wait), drawer shows item, update quantity updates line total, remove item decrements badge, badge persists after navigation

## 10. Test Modules — Checkout & Orders

- [x] 10.1 Create `tests/e2e/test_checkout.py` — setup: add item to cart via `httpx POST /v1/cart/items` (not Selenium); Selenium tests: checkout page shows cart items and total, empty form submission shows validation errors, successful checkout with door delivery redirects to confirmation with order ID, missing delivery selection shows validation error
- [x] 10.2 Create `tests/e2e/test_orders.py` — setup: create order via `httpx POST /v1/orders` for order detail test; orders page loads without 500 for anonymous user, order detail shows status/items/total

## 11. Test Modules — Auth

- [x] 11.1 Create `tests/e2e/test_auth.py` — login button initiates OAuth redirect (URL contains `accounts.google.com`), auth callback page renders without 500 when hit without params

## 12. Test Modules — Admin (Session-Injected)

- [x] 12.1 Create `tests/e2e/test_admin.py` — admin dashboard renders stats cards with both cookies injected, product list shows seed product, admin can create a new product and it appears in list, admin can edit stock value, non-admin session is redirected from `/en/admin`

## 13. Test Modules — Reactions & Comments

- [x] 13.1 Create `tests/e2e/test_reactions.py` — setup: navigate directly to product URL (no UI clicks); each test clears cookies (fresh session, clean rate-limit slate); reaction toggles on (count +1, active state via `aria-pressed`), reaction toggles off (count -1, inactive state). Uses reaction-type strings (`"heart"`, `"thumbs_up"`), not emoji chars.
- [x] 13.2 Create `tests/e2e/test_comments.py` — setup: navigate directly to product URL; comment appears after submission (fills both display_name + body for anonymous users), empty body rejected, XSS content stripped in displayed comment

## 14. Test Modules — Contact

- [x] 14.1 Create `tests/e2e/test_contact.py` — contact page loads with required fields, empty submit shows validation errors

## 15. CI Integration & Documentation

- [x] 15.1 Document `make test-e2e` and `make generate-testids` in README under "Testing"
- [x] 15.2 Add CLAUDE.md norm: E2E-covered components MUST use `TEST_IDS` from `lib/testids.ts`; never hardcode testid strings; testid renames must run `make generate-testids` and commit `testids.py` in the same PR
- [x] 15.3 Verify full suite runs headless in under 3 minutes — achieved with `pytest -n 4 --dist worksteal` (18 passed, 9 skipped in 2:32). Sequential wall-clock was 6:23; four parallel Chrome sessions cut it to under target. Set as the default in the `make test-e2e` target.
