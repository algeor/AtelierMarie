# QA Findings

Source prompt: `bugs/bugs_prompt.md`

## Progress Snapshot

- Status: Investigating
- Started: 2026-07-29
- Environment: local workspace `/Users/I551270/PycharmProjects/AtelierMarie`
- Areas tested: initial prompt review, backend automated tests, backend lint, frontend lint, frontend unit test suite isolation, isolated cart/order API happy path and stock failure, admin product video update response consistency, route-level API error envelope consistency, backend discount contract tests, frontend checkout discount display consistency, frontend product listing discount sort consistency, auth returning-user profile persistence edge case, admin bank-transfer payment email outbox idempotency
- Areas not yet tested: broader frontend browser workflows, frontend checkout submission in a real browser session, broader backend APIs beyond discount/cart/order and representative admin probes, auth/permissions beyond admin bearer probes and returning-user profile persistence probe, order email sweeper behavior under duplicated queued payment rows, database integrity beyond automated tests and video response probe, accessibility, performance, error handling outside representative route-level API envelope probes, concurrency
- Active hypotheses: frontend component test harness is missing shared browser and intl providers; admin ProductForm test fixture is stale relative to required product taxonomy fields; product/video attachment is inconsistent across admin product service paths; frontend discount display code may still use base price in cart-adjacent UI; frontend client-side product sorting may diverge from backend effective-price sort semantics; returning OAuth profile updates may clear optional user fields when provider omits them; bank-transfer payment confirmation may enqueue duplicate customer email intents
- Unresolved anomalies: `bugs/bugs_prompt.md` is staged as an empty new file while the worktree contains the QA prompt; `bugs/prompt.txt` is untracked and intentionally untouched
- Test accounts/data created: none yet
- Services manipulated: Next mock dev server on `127.0.0.1:3002`
- Major remaining attack surfaces: full application surface remains open

## Executive QA Summary

- Total confirmed bugs discovered: 7
- Severity counts: Critical 0, High 0, Medium 7, Low 0
- Major risk areas: frontend regression coverage reliability; admin product response consistency; API contract consistency; discount pricing consistency; auth profile persistence; payment email outbox idempotency
- Most fragile workflows: not yet established
- Systemic patterns: inconsistent reuse of backend/public pricing semantics in frontend UI code; duplicated cross-layer side effects between service and route code
- Areas that appear robust: none proven yet
- Areas difficult to validate: auth/OAuth and external integrations may require mocks or local-only probes

## Complete Bug Catalogue

### QA-001 — Full frontend test suite fails from broken ProductGallery/ProductVideo/ProductForm test setup

- Severity: Medium
- Confidence: Confirmed
- Area: Frontend / Tests
- Environment: local workspace, `frontend`, Vitest `v4.1.10`, jsdom
- Status: Confirmed
- Preconditions: dependencies installed; current worktree as of 2026-07-29
- Reproduction steps:
  1. Run `cd frontend && npm test`.
  2. Run the focused repro `cd frontend && npx vitest run __tests__/components/products/ProductGallery.test.tsx __tests__/components/ProductVideo.test.tsx __tests__/components/admin/ProductForm.test.tsx --reporter=verbose`.
- Expected result: frontend regression suite passes or fails only on real product regressions.
- Actual result: 8 tests fail across 3 files.
- Reproduction rate: 2/2 command runs.
- Evidence:
  - `npm test`: 3 failed files, 8 failed tests, 35 passed files, 230 passed tests.
  - `ProductGallery.test.tsx`: 4 failures with `TypeError: window.matchMedia is not a function` at `frontend/components/products/ProductGallery.tsx:38`.
  - `ProductVideo.test.tsx`: 3 failures with `Failed to call useTranslations because the context from NextIntlClientProvider was not found` at `frontend/components/products/ProductGallery.tsx:28`; the test renders `ProductGallery` with raw Testing Library `render` instead of `renderWithIntl`.
  - `ProductForm.test.tsx`: 1 failure in `keeps the large-image dialog modal and blocks submit until resolved`; `onSubmit` remains uncalled, and the rendered form shows `Could not load taxonomy.` plus `Product type is required`.
  - Code locations: `frontend/__tests__/components/products/ProductGallery.test.tsx`, `frontend/__tests__/components/ProductVideo.test.tsx`, `frontend/__tests__/components/admin/ProductForm.test.tsx`, `frontend/__tests__/test-utils.tsx`.
- API requests/responses: not applicable.
- Database state: not applicable.
- Relevant logs: frontend test output above.
- Likely cause: test setup lacks a global `window.matchMedia` shim, `ProductVideo.test.tsx` bypasses the shared intl wrapper for translated `ProductGallery`, and `ProductForm.test.tsx` uses a product fixture/mocks that do not satisfy the form's required `product_type`/taxonomy path.
- Impact: the canonical frontend test command is red, masking real regressions and making CI/local validation unreliable.
- Suggested regression test: add global browser API shims and require translated component renders through the shared helper; update the ProductForm fixture/API mock so the large-image modal test reaches submit for a valid product.

### QA-002 — Updating an admin product drops existing video from the update response

- Severity: Medium
- Confidence: Confirmed
- Area: Backend / API / Admin Products
- Environment: isolated temp SQLite DB, local ASGI client, `ENVIRONMENT=development`, admin bearer key
- Status: Confirmed
- Preconditions: product has an existing `product_videos` row with `status='ready'`.
- Reproduction steps:
  1. Seed product `video-candle` and a ready `product_videos` row for it.
  2. `GET /v1/admin/products/video-candle` with a valid admin bearer token.
  3. `PATCH /v1/admin/products/video-candle` with `{"name_en":"Video Candle Updated"}`.
  4. `GET /v1/admin/products/video-candle` again.
- Expected result: the PATCH response should include the same `video` object as the GET responses, because the product still has a video and the response model includes `video`.
- Actual result: the PATCH response returns `video: null`; both GET responses include the ready video object.
- Reproduction rate: 1/1 isolated API probe.
- Evidence:
  - Before PATCH: `GET` returned `video={'id':'video-1','product_id':'video-candle','status':'ready','video_url':'/static/products/video.mp4','poster_url':'/static/products/poster.webp',...}`.
  - PATCH response: status `200`, `name_en='Video Candle Updated'`, `video=None`.
  - After PATCH: `GET` returned the same ready video object, proving persistence was not removed.
  - Code location: `app/services/product_service.py` `update_product()` attaches image fields but returns before `product_video_service.attach_video_fields_one(...)`, unlike create/get/list/deactivate paths.
- API requests/responses: `GET /v1/admin/products/video-candle` then `PATCH /v1/admin/products/video-candle` with `{"name_en":"Video Candle Updated"}`.
- Database state: `product_videos` row remains present throughout.
- Relevant logs: no backend error; API returns 200.
- Likely cause: `update_product()` ends with `return product_image_service.attach_image_fields_one(product)` and does not attach video fields.
- Impact: admin UI/API consumers can believe a product video disappeared immediately after saving unrelated product metadata, causing stale UI state or accidental follow-up changes based on an incomplete response.
- Suggested regression test: add a backend admin product update test that seeds a ready video, patches a non-video field, and asserts the update response still includes `video`.

### QA-003 — Route-level API errors omit the documented `details` field

- Severity: Medium
- Confidence: Confirmed
- Area: Backend / API
- Environment: isolated temp SQLite DB, local ASGI client, `ENVIRONMENT=development`
- Status: Confirmed
- Preconditions: API app created from `create_app()`; admin bearer key configured for admin probes.
- Reproduction steps:
  1. Seed product `dup-candle`.
  2. `POST /v1/admin/products` with duplicate `id='dup-candle'`.
  3. `POST /v1/admin/products` with `product_type='missing-type'`.
  4. `GET /v1/admin/orders?status=bogus`.
  5. `GET /v1/products/nope`.
- Expected result: every error follows the documented app envelope: `{"error":{"code":"...","message":"...","details":null|object}}`.
- Actual result: these route-created errors include `code` and `message` but omit `details` entirely.
- Reproduction rate: 1/1 isolated API probe across 4 endpoints.
- Evidence:
  - Duplicate create: `409 {'error': {'code': 'DUPLICATE', 'message': 'Product with this ID already exists'}}`, `details` missing.
  - Invalid taxonomy: `422 {'error': {'code': 'INVALID_TAXONOMY', 'message': 'Unknown product type: missing-type'}}`, `details` missing.
  - Invalid admin order status: `422 {'error': {'code': 'INVALID_STATUS', 'message': "Invalid status 'bogus'. Must be one of: pending, confirmed, shipped, delivered, cancelled"}}`, `details` missing.
  - Missing public product: `404 {'error': {'code': 'NOT_FOUND', 'message': 'Product not found'}}`, `details` missing.
  - Contract source: `app/main.py` documents all errors with `details`; `app/exceptions.py` global handlers include it.
- API requests/responses: listed above.
- Database state: only seed product `dup-candle` required for duplicate path.
- Relevant logs: no backend error; responses are successful error responses.
- Likely cause: route handlers return handcrafted `JSONResponse` bodies instead of a shared error helper/global exception path, and many omit `details`.
- Impact: clients cannot rely on the advertised stable error schema; typed consumers or frontend error handling that expects `details` may behave inconsistently across validation, service, and route-generated errors.
- Suggested regression test: add schema assertions for representative custom route errors and centralize error response construction so `details` is always present.

### QA-004 — Checkout summary line items show full price for discounted products while subtotal uses discounted total

- Severity: Medium
- Confidence: Confirmed
- Area: Frontend / Checkout / Discounts
- Environment: local workspace, frontend checkout component, backend discount tests green
- Status: Confirmed
- Preconditions: cart contains a product with active discount fields, for example `price_cents=3200` and `effective_price_cents=2560`; cart `total_cents` is computed from `effective_price_cents`.
- Reproduction steps:
  1. Use a cart item whose product has `price_cents=3200`, `effective_price_cents=2560`, `discount_percent=20`, quantity `1`, and cart `total_cents=2560`.
  2. Render or inspect the checkout order summary in `frontend/app/[locale]/checkout/page.tsx`.
  3. Compare the line item unit/line total with the subtotal.
- Expected result: the checkout summary line item uses the same effective discounted price as the cart subtotal, for example `1 x €25.60` and subtotal `€25.60`.
- Actual result: the line item uses `product.price_cents`, so it displays `1 x €32.00` and line total `€32.00` while the subtotal displays `€25.60` from `total_cents`.
- Reproduction rate: 1/1 code-path inspection against the active checkout component plus passing backend discount contract tests.
- Evidence:
  - `frontend/app/[locale]/checkout/page.tsx:287` and `frontend/app/[locale]/checkout/page.tsx:291` format `item.product.price_cents` instead of `item.product.effective_price_cents`.
  - `frontend/lib/mock-api.ts` `buildCartResponse()` computes `total_cents` from `item.product.effective_price_cents`.
  - `.venv/bin/pytest tests/test_discounts.py -q` passed: 19 tests, including cart totals and checkout snapshot discount tests.
  - Mock discounted product `lavender-dreams-300ml` has `price_cents=3200` and `effective_price_cents=2560`.
- API requests/responses: not applicable.
- Database state: not applicable.
- Relevant logs: `.venv/bin/pytest tests/test_discounts.py -q -> 19 passed`.
- Likely cause: checkout summary uses the base `ProductResponse.price_cents` field for display math instead of the discounted `ProductResponse.effective_price_cents` field used by cart totals and order snapshots.
- Impact: customers can see internally inconsistent checkout totals for sale items; the line item says one price while the subtotal/order snapshot uses another.
- Suggested regression test: add a checkout page/component test with a discounted cart item and assert the unit price, line total, and subtotal all use `effective_price_cents`.

### QA-005 — Client-side product price sorting ignores active discounts

- Severity: Medium
- Confidence: Confirmed
- Area: Frontend / Product Listing / Discounts
- Environment: local workspace, frontend `ProductListingClient`, backend discount tests green
- Status: Confirmed
- Preconditions: product list contains at least one discounted product whose `effective_price_cents` changes its ordering relative to base price; user selects price ascending or price descending.
- Reproduction steps:
  1. Use products `sale-candle price_cents=5000 effective_price_cents=1000` and `plain-candle price_cents=2000 effective_price_cents=2000`.
  2. Apply the client `price_asc` sort from `ProductListingClient`.
  3. Compare the result to the backend/public contract that sorts by `effective_price_cents`.
- Expected result: `price_asc` orders `sale-candle` before `plain-candle` because `1000 < 2000`, matching backend effective-price sorting and the displayed sale prices.
- Actual result: `price_asc` orders `plain-candle` before `sale-candle` because the client sorts by base `price_cents`, `2000 < 5000`.
- Reproduction rate: 1/1 direct executable sort probe plus code inspection.
- Evidence:
  - Executable probe output: `client_price_asc=[plain-candle,sale-candle]`, `expected_effective_price_asc=[sale-candle,plain-candle]`.
  - `frontend/components/products/ProductListingClient.tsx:211` and `frontend/components/products/ProductListingClient.tsx:215` sort `price_asc`/`price_desc` by `price_cents`.
  - `app/services/product_service.py:218` through `app/services/product_service.py:260` documents and implements backend price sort by `effective_price_cents`.
  - `.venv/bin/pytest tests/test_discounts.py -q` passed: 19 tests, including effective-price asc/desc sort tests.
- API requests/responses: not applicable.
- Database state: not applicable.
- Relevant logs:
  - `node probe -> {"client_price_asc":["plain-candle","sale-candle"],"expected_effective_price_asc":["sale-candle","plain-candle"]}`
  - `.venv/bin/pytest tests/test_discounts.py -q -> 19 passed`
- Likely cause: `ProductListingClient` implements price sorting locally using `ProductResponse.price_cents`, while backend and price display semantics use `effective_price_cents` when discounts are active.
- Impact: sale products can appear in the wrong order when shoppers sort by price, contradicting the displayed discounted prices and backend sort behavior.
- Suggested regression test: add a `ProductListingClient` test where a discounted high-base-price product has the lowest effective price, then assert `price_asc`/`price_desc` order by `effective_price_cents`.

### QA-006 — Returning OAuth login clears stored name and avatar when Google omits optional claims

- Severity: Medium
- Confidence: Confirmed
- Area: Backend / Auth / User Profile
- Environment: isolated temp SQLite DB, direct `auth_service.upsert_user` probe
- Status: Confirmed
- Preconditions: a user already exists with `google_id`, `name`, and `avatar_url` populated; a later OAuth callback for the same `google_id` provides no `name` and no `picture` claim.
- Reproduction steps:
  1. Initialize a temp DB and call `auth_service.upsert_user(conn, "google-1", "a@test.com", "Old Name", "http://old-avatar.jpg")`.
  2. Call `auth_service.upsert_user(conn, "google-1", "a@test.com", None, None)` for the same `google_id`.
  3. Read `SELECT id, name, avatar_url FROM users WHERE google_id = "google-1"`.
- Expected result: the stored profile keeps the previous non-null name and avatar when the provider omits optional replacement values, or the returned `UserResponse` matches what was actually persisted.
- Actual result: the returned `UserResponse` still reports `Old Name` and `http://old-avatar.jpg`, but the `users` table row is updated to `name=NULL` and `avatar_url=NULL`.
- Reproduction rate: 1/1 direct service probe.
- Evidence:
  - Probe output: `second_return={name: Old Name, avatar_url: http://old-avatar.jpg}` while `db_row={name: None, avatar_url: None}`.
  - `app/services/auth_service.py:343` through `app/services/auth_service.py:345` update `name` and `avatar_url` directly from nullable OAuth claims.
  - `app/services/auth_service.py:350` and `app/services/auth_service.py:351` return fallback values from the old row, masking the persisted nulls in the immediate response.
  - Existing `TestUpsertUser` covers returning users with replacement name/avatar, not omitted optional claims.
- API requests/responses: not applicable; direct service probe.
- Database state: `users` row for `google-1` changed from `name=Old Name/avatar_url=http://old-avatar.jpg` to `name=NULL/avatar_url=NULL`.
- Relevant logs: `.venv/bin/python` direct probe showed the DB row had null profile fields after the second upsert.
- Likely cause: the returning-user update writes nullable `name`/`avatar_url` values directly, but the response object falls back to previous values instead of reflecting the database mutation.
- Impact: a returning OAuth login can silently erase stored display/profile data, which can later affect account UI and any feature that derives display identity from the persisted user row.
- Suggested regression test: add an `upsert_user` test for an existing user where `name` and `avatar_url` are omitted, asserting the stored row preserves existing non-null values or the response and persistence are intentionally aligned.

### QA-007 — Admin bank-transfer payment confirmation queues duplicate placed email rows

- Severity: Medium
- Confidence: Confirmed
- Area: Backend / Admin Orders / Email Outbox
- Environment: isolated temp SQLite DB, local ASGI admin route probe, `ENVIRONMENT=development`, admin bearer key
- Status: Confirmed
- Preconditions: an order exists with `payment_method=bank_transfer` and `payment_status=pending`; the admin marks it paid.
- Reproduction steps:
  1. Create a bank-transfer checkout order in an isolated temp DB.
  2. Before marking paid, query `order_emails` for that order.
  3. `PATCH /v1/admin/orders/{order_id}/payment` with a valid admin bearer token and `{"payment_status":"paid"}`.
  4. After the route returns 200, query `order_emails` for that order again.
- Expected result: exactly one queued `placed` email intent exists after payment is marked paid.
- Actual result: two queued `placed` rows exist for the same order and recipient after the route returns 200.
- Reproduction rate: 1/1 isolated ASGI route probe.
- Evidence:
  - Probe before: `payment_pending queued`, `admin_new_order queued`.
  - Probe after: `payment_pending queued`, `admin_new_order queued`, plus two `placed queued` rows for `test@example.com`.
  - `app/services/order_service.py:745` through `app/services/order_service.py:748` insert a queued `placed` row inside `mark_bank_transfer_paid()`.
  - `app/routes/admin.py:720` and `app/routes/admin.py:721` queue `placed` again after `mark_bank_transfer_paid()` returns.
  - `app/database.py:263` through `app/database.py:265` only enforce uniqueness for `status='sent'`, so duplicate queued rows are allowed.
- API requests/responses: `PATCH /v1/admin/orders/{order_id}/payment {"payment_status":"paid"} -> 200`, response has `payment_status=paid`.
- Database state: `order_emails` contains duplicate queued `placed` rows for the same `order_id/event/recipient` after the admin payment route.
- Relevant logs: route probe returned 200; DB after route showed two queued `placed` rows.
- Likely cause: both the service layer and the admin route enqueue the same `placed` email intent, and queued outbox rows are not deduplicated by schema or helper.
- Impact: the outbox/audit trail is polluted with duplicate customer email intents; if the first duplicate fails transiently, the second queued duplicate can bypass intended backoff by acquiring the failed claim immediately.
- Suggested regression test: add a route-level bank-transfer payment test that asserts a single `placed` row exists after `PATCH /v1/admin/orders/{id}/payment`; keep the enqueue responsibility in one layer or make `queue_order_email` idempotent for queued intents.

## Coverage Map

| Feature / Area | Status | Notes |
| --- | --- | --- |
| Build, lint, type checks, automated tests | Partially tested | Backend pytest passed; backend ruff passed; frontend lint passed with warnings; frontend Vitest fails, see QA-001; Next build passed with existing `<img>` warnings |
| Public storefront | Partially tested | Discount price sort semantics inspected/probed; broader browser workflows pending |
| Product detail and gallery | Not tested | Pending frontend/API probing |
| Cart and checkout | Partially tested | Backend cart/order discount contract passed; frontend checkout discount summary mismatch recorded in QA-004 |
| Orders and payment retry | Partially tested | Admin bank-transfer payment route creates duplicate placed email intents, see QA-007; frontend payment retry pending |
| Auth and account | Partially tested | Returning-user OAuth profile persistence probe recorded in QA-006; broader auth/permissions remain pending |
| Admin products, uploads, taxonomy, FAQ, promotions, atelier content, orders | Not tested | Pending permissions and state probes |
| Backend API validation and error handling | Partially tested | Cart/order happy path, over-stock response, discount pricing contract, admin auth basics, admin product video response consistency, and representative custom error envelopes probed |
| Database integrity | Not tested | Pending schema and persistence probes |
| Accessibility and responsive layout | Not tested | Pending browser/screenshot checks |
| Performance and resource behavior | Not tested | Pending after functional surface mapping |

## Scenario Inventory

- Ran full backend pytest and Python lint.
- Ran full frontend Vitest and focused failing frontend test files.
- Inspected failing component/test source to separate product defects from test harness defects.
- Used isolated temp SQLite + ASGI client to verify cart session behavior, order creation, stock decrement, admin bearer auth, and admin product video response consistency.
- Probed representative route-level API errors for contract consistency.
- Ran focused backend discount tests: `.venv/bin/pytest tests/test_discounts.py -q` passed 19 tests.
- Inspected frontend checkout and product-listing price paths against backend effective-price semantics.
- Ran executable sort probe showing client base-price order diverges from effective-price order for discounted products.
- Ran direct auth service probe showing returning-user optional OAuth claims clear persisted profile fields while response masks the change.
- Ran isolated ASGI admin payment route probe showing duplicate queued placed email rows after bank-transfer payment confirmation.

## Systemic Findings

- Frontend tests have inconsistent render utilities and browser API setup for client components using `next-intl` and `window.matchMedia`.
- Admin product response assembly is inconsistent between update and read paths; video attachment is omitted from `update_product()`.
- Route handlers handcraft error envelopes inconsistently, bypassing the documented `details` field required by the global error shape.
- Frontend code has multiple price consumers; some use `effective_price_cents`, while checkout summary and product-listing sort still use base `price_cents`.
- Some service/route boundaries both perform side effects, as seen with duplicate bank-transfer placed email enqueueing.

## Missing Safeguards

None confirmed yet.

## Recommended Regression Tests

- QA-001: Add global `matchMedia` shim, enforce/render translated components with `NextIntlClientProvider`, and keep admin form fixtures synchronized with required product fields.
- QA-002: Add admin update coverage for products that already have video rows.
- QA-003: Add API error schema tests for custom route-returned errors and centralize envelope creation.

## Remaining Attack Surface

- Full application surface remains to be tested.
