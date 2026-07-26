## ADDED Requirements

### Requirement: Test infrastructure setup
The system SHALL provide a pytest-based Selenium test suite in `tests/e2e/` with a shared conftest that manages browser lifecycle, server reachability checks, and seed data, runnable via `make test-e2e`.

#### Scenario: Suite skips gracefully when servers are down
- **WHEN** either `localhost:3000` (frontend) or `localhost:8000` (backend) is not reachable
- **THEN** all E2E tests are skipped with a human-readable message identifying which server is missing

#### Scenario: Browser session setup
- **WHEN** any E2E test starts
- **THEN** a headless Chrome WebDriver is provided, respecting `HEADLESS=0` env var for headed mode

#### Scenario: Seed product reachable before suite runs
- **WHEN** the E2E suite starts and the seed product has been created via the admin API
- **THEN** a GET request to `/en/products/e2e-test-candle` returns the product page (not 404) before any test is allowed to run

---

### Requirement: Product listing flow
The system SHALL have tests verifying that a user can browse the product catalog.

#### Scenario: Products page loads
- **WHEN** user navigates to `/en/products`
- **THEN** at least one product card is visible on the page

#### Scenario: Category filter narrows visible cards
- **WHEN** user clicks a category chip in the CategoryFilter on `/en/products`
- **THEN** only products in that category remain visible

  (NOTE: original scenario "Product search filters results" removed — no search input exists in the current UI; the products listing uses a CategoryFilter instead. If a search input is added later, add a matching scenario.)

#### Scenario: Product detail page loads
- **WHEN** user clicks a product card
- **THEN** the product detail page loads with the product name, price, and Add to Cart button visible

---

### Requirement: Cart operations
The system SHALL have tests covering cart add, update, and remove flows.

#### Scenario: Add product to cart
- **WHEN** user clicks "Add to Cart" on a product detail page
- **THEN** the test waits for the cart context to hydrate, then the cart badge count increments and the cart drawer shows the product

#### Scenario: Cart badge readable after navigation
- **WHEN** user adds a product to the cart and navigates to another page
- **THEN** the page object waits for `[data-testid="cart-badge"]` to be present in the DOM before reading its count (not immediately after navigation)

#### Scenario: Update cart item quantity
- **WHEN** user opens the cart drawer and changes the quantity of an item
- **THEN** the line total updates to reflect the new quantity

#### Scenario: Remove item from cart
- **WHEN** user clicks the remove button for a cart item
- **THEN** the item disappears from the cart and the badge count decrements

#### Scenario: Cart persists across page navigation
- **WHEN** user adds a product to the cart and navigates to `/en/products`
- **THEN** the cart badge still shows the correct item count

---

### Requirement: Checkout flow
The system SHALL have tests verifying the checkout form submission and order creation.

#### Scenario: Checkout page loads with cart items
- **WHEN** user has items in cart and navigates to `/en/checkout`
- **THEN** the order summary shows the cart items and a total

#### Scenario: Checkout form validation rejects empty required fields
- **WHEN** user submits the checkout form with required fields empty
- **THEN** validation error messages appear for the empty fields and no order is created

#### Scenario: Successful checkout creates order
- **WHEN** user fills email, name, selects door delivery, chooses a courier, fills the address fields, and submits the checkout form
- **THEN** user is redirected to the order confirmation page showing the order ID

#### Scenario: Checkout delivery validation rejects missing courier selection
- **WHEN** user fills email and name but does not select a delivery option and submits
- **THEN** a validation error appears for the delivery section and no order is created

---

### Requirement: Order history and detail
The system SHALL have tests for the orders list and order detail pages.

#### Scenario: Orders page loads for anonymous user
- **WHEN** an anonymous user navigates to `/en/orders`
- **THEN** either an empty state is shown or a login prompt is displayed (no 500 error)

#### Scenario: Order detail page loads for a known order
- **WHEN** user navigates to `/en/orders/<order-id>` for an order created in the session
- **THEN** the order status, items, and total are visible

---

### Requirement: Authentication flow smoke test
The system SHALL have a smoke test verifying the auth entry point is reachable.

#### Scenario: Login button navigates to auth initiation
- **WHEN** user clicks the login/sign-in button in the header
- **THEN** the browser initiates a redirect toward the Google OAuth URL (HTTP 302 or new URL contains `accounts.google.com`)

#### Scenario: Auth callback page does not 500
- **WHEN** user navigates directly to `/en/auth/callback` without OAuth params
- **THEN** the page renders (either an error message or redirect) without an unhandled 500

---

### Requirement: Admin dashboard flows (session-injected)
The system SHALL have tests for the admin section using session injection to bypass OAuth.

#### Scenario: Admin dashboard renders for admin session
- **WHEN** both `session_id` and `atelier_auth` JWT cookies are injected with admin privileges and user navigates to `/en/admin`
- **THEN** the admin dashboard loads with stats cards visible

#### Scenario: Admin product list shows existing products
- **WHEN** admin navigates to `/en/admin/products`
- **THEN** the product table lists at least the seeded test product

#### Scenario: Admin can create a new product
- **WHEN** admin navigates to `/en/admin/products/new` and fills in the product form (name, SKU, price, stock) and submits
- **THEN** the new product appears in the `/en/admin/products` list

#### Scenario: Admin can edit a product
- **WHEN** admin clicks "Edit" on an existing product and changes the stock value and saves
- **THEN** the product list shows the updated stock value

#### Scenario: Non-admin session redirected from admin pages
- **WHEN** a non-admin session navigates to `/en/admin`
- **THEN** the page redirects to `/en/` or shows a 403/unauthorized message

---

### Requirement: Product reactions
The system SHALL have tests verifying emoji reactions can be toggled on a product. Each reaction test MUST use a fresh session (cleared cookies) to avoid triggering the backend rate limit from prior test runs.

#### Scenario: Reaction button toggles on
- **WHEN** a fresh session navigates to a product detail page and clicks a reaction button (identified by reaction type: `heart` or `thumbs_up`)
- **THEN** the reaction count increments by 1 and the button shows `aria-pressed="true"`

#### Scenario: Reaction button toggles off
- **WHEN** a fresh session clicks a reaction button to activate it, then clicks it again
- **THEN** the reaction count decrements by 1 and the button returns to `aria-pressed="false"`

  (NOTE: reactions are two fixed types — `heart` and `thumbs_up` — with `aria-label` locators, not per-reaction testids. Tests reference reaction *type* strings, not emoji characters.)

---

### Requirement: Product comments
The system SHALL have tests verifying comment submission and display.

#### Scenario: Comment appears after submission
- **WHEN** user fills the display-name field (required for anonymous users) and the body, then submits
- **THEN** the new comment appears in the comment list without page reload

#### Scenario: Empty comment submission is rejected
- **WHEN** user submits with an empty body (or empty display name when anonymous)
- **THEN** the comment is not added; the submit button is disabled while body is empty, and a validation error appears if submission is attempted with only body/only name filled

#### Scenario: XSS content is stripped from displayed comments
- **WHEN** user submits a comment containing `<script>alert(1)</script>`
- **THEN** the displayed comment shows the text stripped of HTML tags (no script execution)

---

### Requirement: Page object return types and URL guards
The system SHALL implement page objects following the Selenium golden standard: navigation methods return the next page object, success/failure outcomes are split into separate methods, and each page object asserts the correct URL at construction.

#### Scenario: Navigation method returns next page object
- **WHEN** a test calls `checkout_page.submit_expecting_success()`
- **THEN** an `OrderConfirmationPage` instance is returned, allowing the test to chain `order_page.get_order_id()` immediately

#### Scenario: Failure method returns self with errors accessible
- **WHEN** a test calls `checkout_page.submit_expecting_error()`
- **THEN** the same `CheckoutPage` instance is returned with validation errors accessible via `get_validation_errors()`

#### Scenario: Page object raises on wrong URL at construction
- **WHEN** a page object is instantiated but the browser is not on the expected URL
- **THEN** construction raises a `TimeoutException` with a message identifying the expected URL pattern

---

### Requirement: Component objects for cross-page UI
The system SHALL model the cart drawer and header as Component Objects in `tests/e2e/components/`, exposed as properties on `BasePage`, rather than as standalone page objects.

#### Scenario: Cart drawer accessible from any page
- **WHEN** a test calls `any_page.cart.open_drawer()`
- **THEN** the `CartDrawerComponent` methods are available regardless of which page the browser is currently on

#### Scenario: Header component accessible from any page
- **WHEN** a test calls `any_page.header.get_badge_count()`
- **THEN** the badge count is returned from the `HeaderComponent` without duplicating locator definitions

---

### Requirement: Screenshot on test failure
The system SHALL automatically capture a screenshot to `tests/e2e/screenshots/{test_name}.png` whenever an E2E test fails.

#### Scenario: Screenshot saved on failure
- **WHEN** any E2E test fails for any reason
- **THEN** a PNG screenshot is saved to `tests/e2e/screenshots/` named after the test, before teardown runs

#### Scenario: No screenshot saved on pass
- **WHEN** an E2E test passes
- **THEN** no screenshot file is written for that test

---

### Requirement: Testid constants codegen — stale detection
The system SHALL provide a `make generate-testids` script that derives `tests/e2e/testids.py` from `frontend/lib/testids.ts` as the single source of truth, with CI failing if the generated file differs from the committed one.

#### Scenario: CI fails when testids.py is stale
- **WHEN** `frontend/lib/testids.ts` is modified without regenerating `tests/e2e/testids.py`
- **THEN** CI runs `make generate-testids && git diff --exit-code tests/e2e/testids.py` and fails with a diff showing the stale constants

#### Scenario: Regeneration produces identical output when in sync
- **WHEN** `tests/e2e/testids.py` is up to date with `testids.ts`
- **THEN** `make generate-testids && git diff --exit-code tests/e2e/testids.py` exits 0

---

### Requirement: Testid contract enforcement
The system SHALL ensure that all `data-testid` hooks required by the E2E suite are present in the frontend components and cannot be silently removed.

#### Scenario: Vitest contract test passes when all testids present
- **WHEN** `make test-frontend` runs and all E2E-required `data-testid` attributes are present in their components
- **THEN** the contract test passes with no failures

#### Scenario: Vitest contract test fails when a testid is removed
- **WHEN** a developer removes a `data-testid` attribute from a component covered by the contract test
- **THEN** `make test-frontend` fails with a clear message identifying the missing attribute before any PR can merge

#### Scenario: TypeScript enforces testid constant usage
- **WHEN** a developer references a testid key that does not exist in `frontend/lib/testids.ts`
- **THEN** the TypeScript compiler reports an error and the build fails

#### Scenario: Python import fails on unknown testid
- **WHEN** an E2E page object references a constant not present in `tests/e2e/testids.py`
- **THEN** Python raises an `ImportError` at collection time, before any test runs

---

### Requirement: Path-based CI pairing rule
The system SHALL have a CI check that requires E2E test files to be modified when their paired frontend component directories change.

#### Scenario: PR touching cart components requires test_cart.py update
- **WHEN** a pull request modifies files under `frontend/components/cart/`
- **THEN** CI blocks merge unless `tests/e2e/test_cart.py` is also modified in the same PR

#### Scenario: PR touching admin pages requires test_admin.py update
- **WHEN** a pull request modifies files under `frontend/app/[locale]/admin/`
- **THEN** CI blocks merge unless `tests/e2e/test_admin.py` is also modified in the same PR

#### Scenario: PR touching product components requires paired test updates
- **WHEN** a pull request modifies files under `frontend/components/products/`
- **THEN** CI blocks merge unless `tests/e2e/test_products.py`, `test_reactions.py`, or `test_comments.py` is also modified

---

### Requirement: Contact form
The system SHALL have a smoke test for the contact page.

#### Scenario: Contact form page loads
- **WHEN** user navigates to `/en/contact`
- **THEN** the contact form is visible with name, email, and message fields

#### Scenario: Contact form validates required fields
- **WHEN** user submits the contact form with empty fields
- **THEN** validation errors appear for the required fields
