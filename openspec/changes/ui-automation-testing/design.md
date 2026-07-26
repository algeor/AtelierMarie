## Context

The AtelierMarie frontend (Next.js 14, App Router) has complete page coverage but zero automated browser tests. All QA is manual, meaning regressions in cart, checkout, admin, or auth flows can go undetected. The backend has a strong pytest suite; the frontend needs an equivalent end-to-end safety net.

The app uses locale-based routing (`/[locale]/...`) so all page URLs must be prefixed (e.g., `/en/products`). The frontend runs on port 3000 and depends on the backend API on port 8000.

## Goals / Non-Goals

**Goals:**
- Selenium test suite in Python covering every major user flow
- Page Object Model (POM) pattern for maintainability
- Headless Chrome execution for CI
- Tests runnable locally and in CI with a single command
- Cover: product browsing, cart, checkout, orders, auth callback stub, admin CRUD, reactions, comments, contact form
- Stable locator strategy via `data-testid` attributes on all E2E-tested components
- CI enforcement that `data-testid` hooks are never silently removed
- Path-based CI rule that forces E2E test files to be touched when paired frontend components change

**Non-Goals:**
- Visual regression / screenshot diffing
- Load or performance testing
- Testing the backend API directly (that's pytest's job)
- Full OAuth round-trip (Google login requires a real account — tested via session injection or skip)
- Testing Layer 2 analytics events in the browser

## Decisions

### D1: Python + pytest + Selenium (not Playwright or Cypress)
**Choice:** Python Selenium with `webdriver-manager` auto-downloading ChromeDriver.  
**Rationale:** The backend test suite is already Python/pytest; keeping E2E in the same language and runner means one `make test-e2e` target, shared CI config, and no Node test toolchain sprawl. The team is learning Python — a consistent toolchain lowers cognitive overhead.  
**Alternatives:** Playwright (Python) was considered — better async API, but Selenium is more universally documented and the task explicitly named it.

### D2: Page Object Model
**Choice:** One class per page in `tests/e2e/pages/`. Each class owns its locators and interaction methods.  
**Rationale:** Keeps test logic readable (`cart_page.add_item(sku)`) and isolates locator churn to one file per page when the frontend changes.  
**Alternatives:** Raw Selenium calls inline — fast to write, expensive to maintain.

### D3: Headless Chrome via webdriver-manager
**Choice:** `webdriver-manager` auto-downloads the matching ChromeDriver; `--headless=new` flag for CI.  
**Rationale:** Zero manual driver management. `HEADLESS=0` env var allows headed debug runs locally.

### D4: Session injection for auth-gated flows
**Choice:** Admin and account flows set the session cookie directly via `driver.add_cookie()` after seeding the DB with a known session, rather than driving the Google OAuth popup.  
**Rationale:** Google OAuth requires a real browser OAuth flow; automating it reliably requires test Google accounts and is brittle. Session injection is deterministic and tests the same protected-route logic.

### D5: Test isolation via API teardown
**Choice:** Each test that mutates state (cart, orders, comments) cleans up via the backend API at teardown using `httpx`.  
**Rationale:** Selenium tests are slower than unit tests — keeping them isolated without a full DB reset per test avoids multi-minute runs. The backend's `/v1/` API is already the integration boundary.

### D7: Centralized testid constants — shared contract between frontend and E2E
**Choice:** A single source-of-truth file `frontend/lib/testids.ts` exports every `data-testid` value as a named TypeScript constant. A `make generate-testids` script reads `testids.ts` and writes `tests/e2e/testids.py` automatically. CI runs `make generate-testids && git diff --exit-code tests/e2e/testids.py` — fails if the Python file is stale.  
**Rationale:** One source of truth; the Python file is always derived, can never silently drift. TypeScript compiler errors on unknown keys. Stale `testids.py` is caught by CI before any test runs, not silently at runtime.  
**Alternatives:** Manually maintained `testids.py` — drifts silently when `testids.ts` changes.

The required `data-testid` attributes (14 total across 7 frontend files):

```
frontend/lib/testids.ts constant        data-testid value              Component
──────────────────────────────────────────────────────────────────────────────
productCard                             product-card                   ProductCard
categoryFilter                          category-filter                CategoryFilter (products listing) — replaces productSearch (no search input in current UI)
cartBadge                               cart-badge                     CartBadge
cartDrawer                              cart-drawer                    CartDrawer container
cartItem(productId)                     cart-item-{productId}          CartItem row
cartRemove(productId)                   cart-remove-{productId}        CartItem remove button
addToCartBtn                            add-to-cart-btn                AddToCartButton
commentForm                             comment-form                   CommentForm
commentCard                             comment-card                   CommentCard
adminProductRow(id)                     admin-product-row-{id}         Admin products table row
adminEditLink(id)                       admin-edit-{id}                Admin edit Link (renamed from adminEditBtn — the edit UI is a Link, not a button)
orderRow(id)                            order-row-{id}                 Orders list row Link
orderStatus                             order-status                   OrderStatusBadge
loginButton                             login-button                   LoginButton (added — needed by header/auth tests)
```

### D8: Vitest contract test — CI enforcement of testid presence
**Choice:** A vitest test file `frontend/__tests__/testids.contract.test.tsx` renders each E2E-covered component and asserts its `data-testid` attribute is present. Runs as part of `make test-frontend`.  
**Rationale:** If a developer removes a `data-testid` from a component, `make test-frontend` fails immediately in CI before any PR merges — no browser needed, fast (<30s). This is the mechanical enforcement layer; it catches deletions and renames that bypass TypeScript (e.g. a `data-testid` set dynamically as a string).  
**Alternatives:** Runtime detection only (Selenium fails) — slower feedback, harder to diagnose.

### D9: Path-based CI rule — forces E2E test files to be touched with paired frontend changes
**Choice:** A CI job (GitHub Actions `paths` filter or equivalent) that blocks a PR if files in a frontend component directory changed but the paired E2E test file was not modified.

```
If changed:                              Then must also be modified:
frontend/components/cart/**          →   tests/e2e/test_cart.py
frontend/components/checkout/**      →   tests/e2e/test_checkout.py
frontend/app/[locale]/admin/**       →   tests/e2e/test_admin.py
frontend/components/products/**      →   tests/e2e/test_products.py
                                         tests/e2e/test_reactions.py
                                         tests/e2e/test_comments.py
frontend/app/[locale]/orders/**      →   tests/e2e/test_orders.py
```

**Rationale:** CI cannot verify that the test change is *meaningful* — a developer can add a comment to satisfy the rule. But it prevents the most common failure: forgetting tests exist and merging a UI change with zero test file touched. Friction is the right amount.  
**Limitation:** Does not enforce semantic correctness of the test update — that requires code review guided by the CLAUDE.md norm.

### D10: Checkout test uses door delivery path
**Choice:** The successful checkout E2E test fills the door delivery sub-fields (courier + address) rather than the office picker flow.  
**Rationale:** The DeliverySection has two paths: door delivery (courier + address fields) and office pickup (courier → async city search → async office picker). Door delivery has fewer async steps and is more deterministic for Selenium. Office picker requires waiting for two sequential async API calls and is tested as a separate, optional scenario.  
**Alternatives:** Office picker path — more realistic but adds two async waits and dependency on courier office API availability.

### D11: Admin session injection injects both cookies
**Choice:** The `inject_admin_session` fixture inserts a user row (`is_admin=1`) and session row directly into SQLite, then calls `driver.add_cookie()` twice: once for `session_id` (the session UUID) and once for `atelier_auth` (a PyJWT-signed token using `JWT_SECRET` from env). The JWT payload MUST include the full claim set expected by `verify_jwt` in `app/services/auth_service.py`: `user_id`, `email`, `is_admin=true`, `session_id` matching the session cookie, `iss="atelier-marie"`, `aud="atelier-marie-web"`, `iat`, and `exp`.
**Rationale:** The frontend `AdminContext` derives `isAdmin` from the response of `GET /v1/auth/me` (see `frontend/contexts/AdminContext.tsx`) — it does NOT decode the `atelier_auth` cookie client-side (it can't; the cookie is HttpOnly). The reason both cookies are still required is server-side: `app/dependencies/auth.py::get_current_user` requires a valid JWT AND its `session_id` claim to equal the `session_id` cookie AND a `sessions` row linking the same session to the same user. Missing any of these → `/v1/auth/me` returns null → `isAdmin=false` on the client → admin pages redirect. The `is_admin` value returned to the frontend comes from the `users` table row (line 43-57 of `dependencies/auth.py`), not the JWT claim; the fixture must set `users.is_admin=1` — the JWT `is_admin` claim alone is not enough.
**Alternatives:** Test-only backend endpoint to issue cookies — adds production surface area; rejected.

### D12: Reaction tests use per-test fresh sessions
**Choice:** Each reaction test gets a fresh WebDriver instance (or cleared cookies) so its session has zero prior reaction toggles.  
**Rationale:** The backend rate-limits reaction toggles per session within a time window. A session that has already toggled from a prior test can hit the rate limit, causing the next toggle to be rejected with 429 — the optimistic update rolls back, making the test assert the wrong count. Fresh sessions guarantee a clean rate-limit slate.  
**Alternatives:** Directly delete rate-limit log rows via DB — more fragile, couples test teardown to internal schema.

### D13: Page objects return the next page object (Selenium golden standard)
**Choice:** Navigation methods return a new page object representing the resulting page, not `None` or `self`. Methods with two possible outcomes (success vs. failure) are split into separate methods.  
**Rationale:** The official Selenium POM documentation requires this — it enables fluent test chains, makes navigation intent explicit, and produces loud failures when the wrong page is reached rather than silent locator misses downstream.  
**Examples:**
```python
# checkout_page.submit_expecting_success() → OrderConfirmationPage
# checkout_page.submit_expecting_error()   → CheckoutPage (self, errors visible)
# product_detail_page.click_add_to_cart()  → CartDrawerComponent
```
**Alternatives:** Methods return `None`, caller navigates manually — works but brittle and verbose in tests.

### D14: Component objects for cross-page UI (Selenium golden standard)
**Choice:** UI sections that appear on multiple pages are modelled as Component Objects in `tests/e2e/components/`, not as standalone pages. `BasePage` exposes them as properties.  
**Rationale:** The cart drawer and header appear on every page. Modelling the cart drawer as a full `CartPage` is architecturally wrong — it's a component overlaid on any page. A `CartDrawerComponent` and `HeaderComponent` owned by `BasePage` correctly represent the DOM structure and prevent duplicated locator definitions.  
**Structure:**
```
tests/e2e/
  pages/           ← full pages (inherit BasePage)
  components/      ← cross-page UI sections
    cart_drawer.py      CartDrawerComponent
    header.py           HeaderComponent (badge, login btn)
```
**Alternatives:** Cart methods on every page object — locator duplication, maintenance burden.

### D15: Screenshot on test failure
**Choice:** A `pytest_runtest_makereport` hook in conftest saves a screenshot to `tests/e2e/screenshots/{test_name}.png` whenever a test fails.  
**Rationale:** CI E2E failures without screenshots are nearly impossible to diagnose — the browser state at failure is the primary debugging signal. This is standard practice in every mature Selenium suite and costs nothing when tests pass.  
**Alternatives:** Manual screenshot calls in each test — easy to forget, inconsistent.

### D16: Page URL guard at construction (Selenium golden standard)
**Choice:** Each page object asserts it is on the correct URL in `__init__` using `WebDriverWait` on `EC.url_contains()`.  
**Rationale:** The Selenium documentation explicitly allows one assertion in a page object: confirming the page loaded correctly. Without this guard, a navigation bug that lands on the wrong page fails with a cryptic `NoSuchElementException` on the first locator lookup rather than a clear "wrong page" message at construction time.  
**Alternatives:** No URL guard — silent wrong-page failures that are hard to diagnose.

### D17: API state setup — Selenium only for what is being tested
**Choice:** Test setup that is not the subject of the test uses `httpx` API calls, not Selenium UI interactions. Selenium is reserved for the flow being asserted.  
**Rationale:** The official Selenium documentation explicitly states: "All repetitive actions and preparations for a test case should be done through other methods" — use APIs to set cookies and pre-load data. A checkout test that clicks Add to Cart via Selenium before testing the checkout form is testing two things, adds flakiness from the cart UI, and obscures test intent.  
**Applies to:**
- `test_checkout.py` — cart item added via `httpx POST /v1/cart/items`, not UI
- `test_orders.py` — order created via `httpx POST /v1/orders` for detail page test
- `test_reactions.py` — navigate directly to product URL, no product listing click
- `test_comments.py` — navigate directly to product URL, no product listing click  
**Exceptions:** `test_cart.py` and `test_products.py` — the UI interactions ARE the subject of the test.

### D6: Locale prefix
**Choice:** All URLs use `/en/` prefix by default; a `BASE_URL` env var points at `http://localhost:3000`.  
**Rationale:** The app uses `[locale]` dynamic routing; tests must reflect real URL structure.

## Risks / Trade-offs

- **testids.ts / testids.py drift** → Mitigated by `make generate-testids` codegen script (single source of truth in `testids.ts`) + `git diff --exit-code` in CI; stale `testids.py` fails the pipeline before any test runs.
- **Flakiness from timing** → Use explicit `WebDriverWait` + `expected_conditions` everywhere; ban `time.sleep()`. Cart context hydration and AddToCartButton success state (1500ms) require explicit waits before asserting badge counts.
- **Google OAuth untestable end-to-end** → Mitigated by session-injection approach (D4); the OAuth callback route itself gets a smoke test that redirects correctly.
- **Both servers must be running** → Conftest fixture checks port reachability at session start and skips with a clear message if either is down.
- **Locale changes break URL assumptions** → `BASE_LOCALE` fixture constant; change one place to run against `bg/`.
- **Admin seed data dependency** → Conftest creates a test product via the admin API before the suite runs, asserts it is reachable at `/en/products/{id}`, and deletes it after.
- **Checkout delivery complexity** → The checkout form has a multi-step delivery picker (courier → city search → office), not a plain address field. Successful checkout test uses door delivery path and fills all required delivery sub-fields explicitly.
- **Cart hydration race** → CartContext hydrates from API in a `useEffect` after mount. Page objects MUST wait for `[data-testid="cart-badge"]` to appear (or for hydration to settle) before reading badge count after any navigation.
- **Reaction rate limiting breaks toggle-off test** → The backend rate-limits reaction toggles per session. Each reaction test MUST use a fresh session (new WebDriver or cookie reset) to avoid hitting the rate limit from prior test runs.
- **Admin session requires two cookies** → The backend `/v1/auth/me` endpoint (which `AdminContext` calls to determine `isAdmin`) requires a JWT whose `session_id` claim matches the `session_id` cookie AND a `sessions` row linking that session to a user. Session injection MUST forge both `session_id` (DB insert) and `atelier_auth` (PyJWT-signed with full claim set: `user_id`, `email`, `is_admin=true`, `session_id`, `iss="atelier-marie"`, `aud="atelier-marie-web"`, `iat`, `exp`) using `JWT_SECRET` from env. Setting only `session_id` leaves `/v1/auth/me` returning null → the frontend treats the user as anonymous. The frontend never decodes the JWT itself (the cookie is HttpOnly).
- **Seed product must be active** → Public product routes filter `WHERE is_active = 1`. Conftest asserts the seeded product is reachable at its public URL before any test runs.

## Migration Plan

1. Add `selenium`, `webdriver-manager`, `pytest-selenium` to `tests/e2e/requirements.txt` (opt-in E2E deps; installed by `make setup-ui-testing`, kept out of `pyproject.toml` to keep package metadata clean). `pyjwt[crypto]` is already a runtime dependency and covers the admin-session fixture — no separate `PyJWT` install needed.
2. Create `tests/e2e/` directory with conftest, page objects, and test modules
3. Add `make test-e2e` target (starts servers if not running, or asserts they are up)
4. Document in README: `make test-e2e` requires both dev servers running

## Open Questions

- Should CI spin up both servers automatically, or gate E2E tests on a separate CI job that already has servers running? → Recommended: separate CI job with server startup step.
- Max acceptable test-suite runtime? → Target <3 minutes for the full suite in headless mode.
