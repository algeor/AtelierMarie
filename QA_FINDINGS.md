# QA Findings

Source prompt: `bugs/bugs_prompt.md`

## Progress Snapshot

- Status: Investigating
- Started: 2026-07-29
- Environment: local workspace `/Users/I551270/PycharmProjects/AtelierMarie`
- Areas tested: initial prompt review, backend automated tests, backend lint, frontend lint, frontend unit test suite isolation, isolated cart/order API happy path and stock failure, admin product video update response consistency, route-level API error envelope consistency, backend discount contract tests, frontend checkout discount display consistency, frontend product listing discount sort consistency, auth returning-user profile persistence edge case, auth avatar fallback edge case, auth user-menu accessible-name check, admin bank-transfer payment email outbox idempotency, admin order status/payment-status filter validation, Stripe retry content-type/CSRF validation, admin CSV malformed encoding handling, admin CSV image max-count behavior, public comment sanitization and React text rendering behavior, public contact submission and owner-email subject handling, admin FAQ duplicate reorder handling, admin-managed atelier content entity rendering, checkout office-delivery catalogue validation
- Areas not yet tested: broader frontend browser workflows, frontend checkout submission in a real browser session, broader backend APIs beyond discount/cart/order and representative admin probes, auth/permissions beyond admin bearer probes and returning-user profile persistence probe, order email sweeper behavior under duplicated queued payment rows, database integrity beyond automated tests and video response probe, accessibility, performance, error handling outside representative route-level API envelope probes, concurrency
- Active hypotheses: frontend component test harness is missing shared browser and intl providers; admin ProductForm test fixture is stale relative to required product taxonomy fields; product/video attachment is inconsistent across admin product service paths; frontend discount display code may still use base price in cart-adjacent UI; frontend client-side product sorting may diverge from backend effective-price sort semantics; returning OAuth profile updates may clear optional user fields when provider omits them; auth avatar fallback may not normalize blank profile fields; bank-transfer payment confirmation may enqueue duplicate customer email intents; admin filter validation may be inconsistent between sibling order filters; state-changing order endpoints may not share the same content-type/CSRF guard; upload parsers may not consistently map malformed input to controlled validation errors; CSV import may hide secondary image attachment failures; stored pre-escaped user-generated text may be reused in plain-text React rendering contexts; public form text accepted by APIs may be reused in email header-like fields without control-character normalization; ordered-list mutation APIs may not reject duplicate IDs before persisting sort positions; admin-authored content may be storage-escaped and then rendered as plain React text; checkout delivery payloads may trust frontend-selected courier office data without server-side catalogue validation
- Unresolved anomalies: none currently
- Test accounts/data created: none yet
- Services manipulated: Next mock dev server on `127.0.0.1:3002`
- Major remaining attack surfaces: full application surface remains open

## Executive QA Summary

- Total confirmed bugs discovered: 18
- Severity counts: Critical 0, High 0, Medium 16, Low 2
- Major risk areas: frontend regression coverage reliability; admin product response consistency; API contract consistency; discount pricing consistency; auth profile persistence; payment email outbox idempotency; admin filter validation consistency; payment retry request-hardening consistency; admin upload validation hardening; user-generated content rendering consistency; public-form email notification hardening; admin ordered-list data integrity; admin content rendering consistency; checkout delivery destination integrity
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

### QA-008 — Admin order payment status filter accepts invalid values as empty results

- Severity: Medium
- Confidence: Confirmed
- Area: Backend / API / Admin Orders
- Environment: isolated temp SQLite DB, local ASGI admin route probe, `ENVIRONMENT=development`, admin bearer key
- Status: Confirmed
- Preconditions: admin bearer authentication is configured; no order data is required to reproduce the validation difference.
- Reproduction steps:
  1. Start the app against a fresh temp SQLite DB with `ADMIN_API_KEY=test-admin-key-realapp`.
  2. Send `GET /v1/admin/orders?status=bogus` with the admin bearer token.
  3. Send `GET /v1/admin/orders?payment_status=bogus` with the same token.
  4. Send `GET /v1/admin/orders?payment_status=paid` as a valid control.
- Expected result: invalid `payment_status` should be rejected with a validation error, matching invalid `status` behavior and the `PaymentStatus` enum.
- Actual result: `payment_status=bogus` returns `200` with an empty page, indistinguishable from a valid filter that simply has no matching orders.
- Reproduction rate: 1/1 isolated ASGI route probe.
- Evidence:
  - Probe output: `/v1/admin/orders?status=bogus -> 422 {'error': {'code': 'INVALID_STATUS', ...}}`.
  - Probe output: `/v1/admin/orders?payment_status=bogus -> 200 {'items': [], 'total': 0, 'page': 1, 'limit': 20}`.
  - Probe output: `/v1/admin/orders?payment_status=paid -> 200 {'items': [], 'total': 0, 'page': 1, 'limit': 20}`.
  - `app/models/orders.py:11` defines `PaymentStatus = Literal["pending", "paid", "cod_pending", "failed", "refunded"]`.
  - `app/routes/admin.py:647` through `app/routes/admin.py:661` validates `status`, but `app/routes/admin.py:663` through `app/routes/admin.py:666` passes raw `payment_status` into the service.
  - `app/services/order_service.py:575` through `app/services/order_service.py:602` accepts `payment_status: str | None` and builds `WHERE payment_status = ?` without enum validation.
- API requests/responses:
  - `GET /v1/admin/orders?status=bogus -> 422` with `INVALID_STATUS`.
  - `GET /v1/admin/orders?payment_status=bogus -> 200` with empty `items`.
  - `GET /v1/admin/orders?payment_status=paid -> 200` with empty `items`.
- Database state: fresh DB with no orders; the bug is visible before any records exist because it is a request validation issue.
- Relevant logs: local probe also logged courier office data loading; no backend error was emitted for the invalid payment status.
- Likely cause: `admin_list_orders()` validates the `status` query parameter against `OrderStatus` but does not perform the equivalent validation for `payment_status` against `PaymentStatus`.
- Impact: admin clients cannot distinguish a mistyped payment-status filter from a legitimate empty result, which can hide filtering mistakes and makes the admin API contract inconsistent across sibling enum filters.
- Suggested regression test: add an admin order list route test for `payment_status=bogus` asserting a 422 error and another valid payment-status control asserting 200.

### QA-009 — Stripe retry endpoint accepts form posts and creates a new checkout session

- Severity: Medium
- Confidence: Confirmed
- Area: Backend / API / Orders / Payments
- Environment: isolated temp SQLite DB, local ASGI route probe, fake Stripe module, `STRIPE_SECRET_KEY=sk_test_probe`
- Status: Confirmed
- Preconditions: a card order belongs to the current session and has `payment_status='failed'`; Stripe is configured; the caller has the session cookie.
- Reproduction steps:
  1. Seed a session, product, cart item, and card order in a fresh temp SQLite DB.
  2. Set the order to `payment_status='failed'` and `stripe_checkout_session_id='cs_old'`.
  3. Install a fake local `stripe.checkout.Session.create` returning `id='cs_form_retry'` and `url='https://stripe.test/retry'`.
  4. Send `POST /v1/orders/{order_id}/stripe-session` with the session cookie, body `x=1`, and `Content-Type: application/x-www-form-urlencoded`.
  5. Read the order's `stripe_checkout_session_id` from the database.
- Expected result: state-changing order/payment endpoints should reject form-encoded POSTs with the same content-type guard used by `POST /v1/orders`, or otherwise enforce an equivalent CSRF-safe request contract.
- Actual result: the retry endpoint returns `200 {'stripe_checkout_url': 'https://stripe.test/retry'}`, calls `stripe.checkout.Session.create` once, and updates the order row to `stripe_checkout_session_id='cs_form_retry'`.
- Reproduction rate: 1/1 isolated ASGI route probe.
- Evidence:
  - Probe output: `response 200 {'stripe_checkout_url': 'https://stripe.test/retry'}`.
  - Probe output: `db {'payment_status': 'failed', 'stripe_checkout_session_id': 'cs_form_retry'}`.
  - Probe output: `stripe_calls 1`.
  - `app/routes/orders.py:51` through `app/routes/orders.py:60` enforce `Content-Type: application/json` for checkout POSTs.
  - `app/routes/orders.py:169` through `app/routes/orders.py:222` implement the Stripe retry POST without reading `Request` or enforcing content type.
  - `tests/realapp/test_order_routes.py:463` through `tests/realapp/test_order_routes.py:492` cover form-encoded rejection only for `POST /v1/orders`.
- API requests/responses: `POST /v1/orders/{order_id}/stripe-session` with `Content-Type: application/x-www-form-urlencoded` and body `x=1` -> `200` with `stripe_checkout_url`.
- Database state: order remained `payment_status='failed'`, but `stripe_checkout_session_id` changed from `cs_old` to `cs_form_retry`.
- Relevant logs: local probe logged courier office data loading; no backend error was emitted.
- Likely cause: `create_stripe_retry_session()` is a cookie-authenticated state-changing POST but lacks the content-type/CSRF guard present on `create_order()`.
- Impact: a non-JSON form POST can trigger an external Stripe session creation and mutate the order's retry session id, bypassing the request-hardening policy applied to checkout.
- Suggested regression test: add a route-level test that posts form-encoded content to `/v1/orders/{id}/stripe-session` with a retryable card order and asserts a 422 `INVALID_CONTENT_TYPE` response and no Stripe call/session-id mutation.

### QA-010 — User avatar fallback renders blank when profile name is an empty string

- Severity: Low
- Confidence: Confirmed
- Area: Frontend / Auth / User Menu
- Environment: local workspace, direct backend auth service probe plus executable frontend fallback-expression probe
- Status: Confirmed
- Preconditions: an authenticated user has `name=""` and `avatar_url=null`, or their avatar image fails and `name=""` is present in the user response.
- Reproduction steps:
  1. Create or upsert a user through `auth_service.upsert_user(conn, "google-empty-name", "empty@example.com", "", None)`.
  2. Observe that the backend `UserResponse` and database row preserve `name=""` and `avatar_url=None`.
  3. Evaluate the `UserAvatar` fallback expression with `name=""` and `email="empty@example.com"`.
  4. Compare it with the same expression for `name=null`.
- Expected result: when the display name is blank, the avatar fallback should use the email initial, `E`, just as it does when `name` is `null`.
- Actual result: `name=""` produces an empty string initial with length 0, so the circular fallback avatar renders with no visible character.
- Reproduction rate: 1/1 backend state probe and 1/1 frontend expression probe.
- Evidence:
  - Backend probe output: `response {'email': 'empty@example.com', 'name': '', 'avatar_url': None, ...}` and `db_row {'email': 'empty@example.com', 'name': '', 'avatar_url': None}`.
  - Frontend expression probe output: `{"name":"","email":"empty@example.com","initial":"","initialLength":0}`.
  - Control output: `{"name":null,"email":"empty@example.com","initial":"E","initialLength":1}`.
  - `frontend/components/auth/UserAvatar.tsx:34` computes `name?.charAt(0).toUpperCase() ?? email.charAt(0).toUpperCase()`, so empty string short-circuits the nullish fallback.
  - `frontend/components/auth/UserAvatar.tsx:53` through `frontend/components/auth/UserAvatar.tsx:58` renders `{initial}` directly inside the fallback circle.
  - `frontend/__tests__/components/auth/UserMenu.test.tsx:128` through `frontend/__tests__/components/auth/UserMenu.test.tsx:154` cover `avatar_url=null` with `name="Marie"`, but not blank names.
- API requests/responses: not applicable; direct service and component-expression probes.
- Database state: `users` row for `google-empty-name` has `name=''` and `avatar_url=NULL`.
- Relevant logs: no backend error; the probes returned successfully.
- Likely cause: the avatar fallback treats only `null`/`undefined` names as absent and does not trim or test for a non-empty display name before deriving the initial.
- Impact: authenticated users with blank stored names, or users whose avatar image fails while their name is blank, see an apparently empty login/user avatar instead of a stable email initial.
- Suggested regression test: add a `UserAvatar` or `UserMenu` test where `name=""` and `avatar_url=null`, asserting the email initial is rendered; normalize blank names before computing initials.

### QA-011 — Authenticated user menu button has no descriptive accessible name

- Severity: Low
- Confidence: Confirmed
- Area: Frontend / Auth / Accessibility
- Environment: local workspace, source inspection plus `dom-accessibility-api` accessible-name probe
- Status: Confirmed
- Preconditions: the header renders an authenticated user with `avatar_url` present, or the avatar falls back to a single initial.
- Reproduction steps:
  1. Inspect `UserMenu` rendered inside the authenticated header.
  2. For the image-avatar state, compute the accessible name of a button with `aria-expanded="false"`, `aria-haspopup="menu"`, and an inner `<img alt="">`.
  3. For the fallback state, compute the accessible name of the same button with an inner `<span>M</span>`.
- Expected result: the menu trigger has a stable descriptive accessible name such as `Account menu`, `User menu`, or localized equivalent in both image and fallback states.
- Actual result: the image-avatar state has an empty accessible name, and the fallback state is named only `M`.
- Reproduction rate: 1/1 source inspection plus 1/1 accessible-name probe.
- Evidence:
  - Accessible-name probe output: `{"imageButtonName":"","imageButtonNameLength":0}`.
  - Accessible-name probe output: `{"fallbackButtonName":"M","fallbackButtonNameLength":1}`.
  - `frontend/components/auth/UserMenu.tsx:57` through `frontend/components/auth/UserMenu.tsx:67` render the trigger button with `aria-expanded` and `aria-haspopup`, but no `aria-label` or visible descriptive text.
  - `frontend/components/auth/UserAvatar.tsx:31` defaults `alt=""`, and `frontend/components/auth/UserAvatar.tsx:42` through `frontend/components/auth/UserAvatar.tsx:49` render the loaded avatar image as decorative.
  - `frontend/components/layout/Header.tsx:80` through `frontend/components/layout/Header.tsx:83` show the nearby cart button has an explicit `aria-label`, so this is inconsistent within the same header controls.
  - `frontend/__tests__/components/auth/UserMenu.test.tsx:114` through `frontend/__tests__/components/auth/UserMenu.test.tsx:124` assert ARIA expanded/menu attributes but do not assert an accessible name.
- API requests/responses: not applicable.
- Database state: not applicable.
- Relevant logs: no runtime error; this is semantic accessibility output.
- Likely cause: `UserMenu` relies on avatar visual content for the trigger and does not assign a descriptive label to the button.
- Impact: screen-reader and voice-control users cannot identify the account menu reliably; in the common loaded-image state, the control is effectively unnamed.
- Suggested regression test: add a `UserMenu` accessibility test asserting the trigger can be found by role and localized name, e.g. `getByRole("button", { name: /account|user/i })`, in both image and fallback states.

### QA-012 — Admin CSV import crashes on invalid UTF-8 upload instead of returning CSV validation error

- Severity: Medium
- Confidence: Confirmed
- Area: Backend / API / Admin Products / CSV Import
- Environment: isolated temp SQLite DB, local ASGI admin route probe, `raise_app_exceptions` true and false controls
- Status: Confirmed
- Preconditions: admin bearer authentication is configured; upload a `.csv` file whose bytes are not valid UTF-8.
- Reproduction steps:
  1. Start the app against a fresh temp SQLite DB with `ADMIN_API_KEY=test-admin-key-realapp`.
  2. Send `POST /v1/admin/products/import` as admin with multipart file `bad.csv`, content bytes `b"\xff\xfe\x00\x00"`, and content type `text/csv`.
  3. Run once with ASGI `raise_app_exceptions=False` to observe the HTTP response.
  4. Run once with ASGI `raise_app_exceptions=True` to observe the underlying exception.
- Expected result: malformed or non-UTF-8 CSV uploads should return a controlled `400` `INVALID_CSV` style response without an unhandled exception stack trace.
- Actual result: the endpoint raises `UnicodeDecodeError`; with app exceptions suppressed, the client receives `500 {"error":{"code":"INTERNAL_ERROR","message":"An unexpected error occurred","details":null}}`.
- Reproduction rate: 2/2 probe modes.
- Evidence:
  - HTTP probe output: `raise_false 500 {"error":{"code":"INTERNAL_ERROR","message":"An unexpected error occurred","details":null}}`.
  - Exception probe output: `raise_true_exception UnicodeDecodeError 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte`.
  - Logged stack trace points to `app/routes/admin.py:407`, `text = content.decode("utf-8-sig")`.
  - `app/routes/admin.py:395` through `app/routes/admin.py:407` read bounded upload bytes and decode directly without catching `UnicodeDecodeError`.
  - The route already maps oversize/missing-header/missing-column CSV cases to `INVALID_CSV`, so malformed encoding is inconsistent with adjacent validation behavior.
- API requests/responses: `POST /v1/admin/products/import` with invalid UTF-8 multipart CSV -> `500 INTERNAL_ERROR`.
- Database state: fresh DB; no product writes are required to reproduce.
- Relevant logs: backend logs `Unhandled exception on POST /v1/admin/products/import` followed by a `UnicodeDecodeError` stack trace.
- Likely cause: `admin_import_products()` decodes uploaded bytes with `content.decode("utf-8-sig")` outside a validation `try/except`, so malformed encodings escape to the global 500 handler.
- Impact: a bad CSV file produces an internal server error and noisy stack trace instead of actionable upload feedback; admins cannot tell the file encoding is invalid.
- Suggested regression test: add a route test uploading invalid UTF-8 bytes to `/v1/admin/products/import` and assert a controlled `400 INVALID_CSV` response with no product writes.

### QA-013 — CSV import reports success while silently dropping image_url when gallery is full

- Severity: Medium
- Confidence: Confirmed
- Area: Backend / API / Admin Products / CSV Import
- Environment: isolated temp SQLite DB, local ASGI admin route probe, product pre-seeded with six image rows
- Status: Confirmed
- Preconditions: an existing product already has six `product_images` rows; a CSV import row for that product includes a new `image_url`.
- Reproduction steps:
  1. Seed product `full-gallery` and six existing `product_images` rows for it.
  2. Upload CSV `id,name_en,price_cents,image_url\nfull-gallery,Full Gallery Updated,2500,/static/products/new-image.webp\n` through `POST /v1/admin/products/import` as admin.
  3. Read the API response.
  4. Query `product_images` for `full-gallery` and check whether `/static/products/new-image.webp` was added.
- Expected result: if the supplied `image_url` cannot be attached because the gallery is full, the import should report a row error or otherwise communicate that the image was skipped.
- Actual result: the API returns `200 {'created': 0, 'updated': 1, 'errors': []}` and updates the product text/price, but the submitted image URL is absent from `product_images`.
- Reproduction rate: 1/1 isolated ASGI route probe.
- Evidence:
  - Probe response: `response 200 {'created': 0, 'updated': 1, 'errors': []}`.
  - DB product row after import: `{'name_en': 'Full Gallery Updated', 'price_cents': 2500}`.
  - DB image state after import: `image_count 6`, `has_new_image False`.
  - Existing image URLs remained `['/static/products/full-0.webp', ..., '/static/products/full-5.webp']`.
  - `app/services/product_image_service.py:257` through `app/services/product_image_service.py:278` returns `None` when `current["count"] >= MAX_IMAGES_PER_PRODUCT`.
  - `app/routes/admin.py:617` through `app/routes/admin.py:624` ignores the return value from `add_existing_image_url()` and increments `updated`/`created` without adding an error.
- API requests/responses: `POST /v1/admin/products/import` with a valid CSV row including `image_url` for a full-gallery product -> `200`, `updated=1`, `errors=[]`.
- Database state: product fields changed, image count stayed at six, and the submitted image URL was not persisted.
- Relevant logs: no backend error; the row is treated as successful.
- Likely cause: `add_existing_image_url()` uses `None` as a max-images sentinel, but `admin_import_products()` treats any non-exception return as success and does not check for `None`.
- Impact: admins can import a CSV containing image URLs and receive a clean success report even though some images were dropped, leaving product media incomplete without any visible failure signal.
- Suggested regression test: add a CSV import test for an existing product with six images and an `image_url`, asserting the row reports an error or a skipped-image status and does not claim an unqualified success.

### QA-014 — Public comments display HTML entities literally for normal punctuation

- Severity: Medium
- Confidence: Confirmed
- Area: Backend / Frontend / Comments
- Environment: isolated temp SQLite DB, local ASGI client, React server-rendering probe using frontend dependencies
- Status: Confirmed
- Preconditions: an active product exists; a user posts a comment or display name containing normal escapable characters such as `&`, `<`, `>`, or quotes.
- Reproduction steps:
  1. Seed active product `entity-candle` in an isolated temp SQLite DB.
  2. `POST /v1/products/entity-candle/comments` with `{"display_name":"Tom & Jerry","body":"I use <this> & \"that\""}`.
  3. `GET /v1/products/entity-candle/comments` and `GET /v1/admin/comments`.
  4. Render returned strings as React text children, matching `frontend/components/products/CommentCard.tsx`.
- Expected result: public and admin comment surfaces display the user's text as entered, for example `Tom & Jerry` and `I use <this> & "that"`, while still preventing HTML execution.
- Actual result: the API stores and returns escaped entity strings (`Tom &amp; Jerry`, `I use &lt;this&gt; &amp; &quot;that&quot;`). React escapes those strings again as text children, so the visible UI shows literal entity text such as `&amp;` instead of `&`.
- Reproduction rate: 1/1 isolated ASGI probe plus 1/1 React rendering probe.
- Evidence:
  - POST response: `201 {'display_name': 'Tom &amp; Jerry', 'body': 'I use &lt;this&gt; &amp; &quot;that&quot;', ...}`.
  - Public list response returns the same escaped `display_name` and `body`.
  - Admin list response returns the same escaped `display_name` and `body`.
  - DB row: `{'display_name': 'Tom &amp; Jerry', 'body': 'I use &lt;this&gt; &amp; &quot;that&quot;'}`.
  - React rendering probe: `renderToStaticMarkup(<p>{'Tom &amp; Jerry'}</p>)` produced `<p>Tom &amp;amp; Jerry</p>`.
  - `frontend/components/products/CommentCard.tsx` renders `{comment.display_name}` and `{comment.body}` as normal React text children.
  - `app/services/comment_service.py` calls `sanitize_text()` before insert, and `app/utils/sanitize.py` implements it with `html.escape(text, quote=True)`.
- API requests/responses: `POST /v1/products/entity-candle/comments` with JSON body above -> `201` containing escaped entities; `GET /v1/products/entity-candle/comments` -> `200` containing escaped entities; `GET /v1/admin/comments` -> `200` containing escaped entities.
- Database state: `comments.display_name` and `comments.body` persist entity-escaped strings rather than the original text.
- Relevant logs: no backend error; courier office startup logs appeared during local app creation.
- Likely cause: the backend uses HTML entity encoding as storage-level sanitization, but the frontend consumes API strings as plain text and relies on React's own escaping, causing double-escaping at render time.
- Impact: customers and admins see corrupted comment text for common punctuation and names, making the comments feature look broken and reducing trust in submitted user content.
- Suggested regression test: add an API/comment UI integration test that posts text containing `&`, `<`, and quotes, then asserts the rendered comment displays the original characters as plain text without executing markup.

### QA-015 — Contact form newline names create multiline owner-email subjects

- Severity: Medium
- Confidence: Confirmed
- Area: Backend / Contact / Email Notifications
- Environment: isolated temp SQLite DB, local ASGI client, direct contact email drain with recording provider
- Status: Confirmed
- Preconditions: contact form endpoint is available; owner contact email drain processes queued contact messages.
- Reproduction steps:
  1. Initialize an isolated temp SQLite DB and app.
  2. `POST /v1/contact` with `{"name":"Ava\\nBcc: victim@example.com","email":"ava@example.com","message":"Can I order a custom candle?","locale":"en"}`.
  3. Query `contact_messages` for the stored name and email status.
  4. Run `drain_contact_message_emails()` with a recording email provider.
  5. Inspect the provider call subject.
- Expected result: public contact text that is reused in email header-like fields should reject or normalize line breaks before the message is accepted or before the email subject is rendered.
- Actual result: the submission is accepted with `201`, the name is persisted with an embedded newline, and the owner email subject becomes `New contact message from Ava\nBcc: victim@example.com`.
- Reproduction rate: 1/1 isolated ASGI + drain probe.
- Evidence:
  - Contact POST response: `201 {'status': 'received', 'message_id': 1}`.
  - DB row after POST: `{'name': 'Ava\nBcc: victim@example.com', 'email_status': 'queued'}`.
  - Drain result: `processed 1`; contact row changed to `email_status='sent'`, `email_attempts=1`.
  - Recording provider subject: `'New contact message from Ava\nBcc: victim@example.com'`.
  - Email body also starts a new line in the `Name:` field: `['Name: Ava', 'Bcc: victim@example.com', ...]`.
  - Python stdlib header check rejects the same value: `ValueError Header values may not contain linefeed or carriage return characters`.
  - `app/models/contact.py` trims leading/trailing whitespace but does not reject internal CR/LF in `name`.
  - `app/email/templates/en/contact_message.txt` places `{{ submitter_name }}` on the subject line.
- API requests/responses: `POST /v1/contact` with newline-containing `name` -> `201` and queued contact message.
- Database state: `contact_messages.name` persists the embedded newline, and the message is marked `sent` after drain with the malformed subject passed to the provider.
- Relevant logs: local app startup logged courier office data loads; drain logged `contact_email_sent` for the contact message.
- Likely cause: contact validation only strips outer whitespace and the plain-text email template renders untrusted `submitter_name` directly into the first-line subject.
- Impact: a public contact submission can produce malformed or header-like owner email subjects; real providers or future SMTP transports may reject the notification, and the displayed subject/body can mislead admins by making injected header-looking lines appear as part of the email metadata.
- Suggested regression test: add contact route/email rendering coverage for CR/LF in `name`, asserting the API rejects it with validation or normalizes it before rendering the owner email subject.

### QA-016 — FAQ reorder accepts duplicate IDs and creates duplicate sort_order values

- Severity: Medium
- Confidence: Confirmed
- Area: Backend / API / Admin FAQ / Data Integrity
- Environment: isolated temp SQLite DB, local ASGI admin route probe, seeded FAQ data
- Status: Confirmed
- Preconditions: FAQ section `care` has at least three items; admin bearer authentication is configured.
- Reproduction steps:
  1. Initialize an isolated temp SQLite DB and app.
  2. `GET /v1/admin/faq` as admin and collect the first three `care` item IDs, observed as `[7, 8, 9]`.
  3. `PATCH /v1/admin/faq/reorder` with `{"section":"care","ordered_ids":[7,7,8]}`.
  4. Read the response and query `faq_items` for `section='care'` ordered by `sort_order, id`.
- Expected result: reorder should reject duplicate item IDs with a validation error and leave existing FAQ order unchanged.
- Actual result: the route returns `200`; item `7` is updated twice and ends at `sort_order=1`, item `8` gets `sort_order=2`, and the omitted existing item `9` still has `sort_order=2`, leaving two items in the same section with the same order value.
- Reproduction rate: 1/1 isolated ASGI route probe.
- Evidence:
  - Initial care IDs: `[7, 8, 9]`.
  - Reorder response status: `200`.
  - Response first care items after reorder: `[(7, 1), (8, 2), (9, 2), (10, 3), (11, 4)]`.
  - DB first care rows after reorder: `[{id: 7, sort_order: 1}, {id: 8, sort_order: 2}, {id: 9, sort_order: 2}, ...]`.
  - Duplicate sort-order query: `[{sort_order: 2, c: 2}]`.
  - `app/services/faq_service.py` checks for missing and wrong-section IDs but does not check `ordered_ids` uniqueness before enumerating updates.
  - `app/database.py` has only `idx_faq_items_section_order` on `(section, sort_order)`, not a uniqueness constraint, so duplicate positions persist.
- API requests/responses: `PATCH /v1/admin/faq/reorder {"section":"care","ordered_ids":[7,7,8]}` -> `200` with duplicate `sort_order` values in the returned section.
- Database state: `faq_items` for `care` contains duplicate `sort_order=2` after the request.
- Relevant logs: no backend error; local app startup logged courier office data loads.
- Likely cause: `reorder_items()` treats the input list as trusted after existence checks; duplicate IDs collapse in the `found` map but still drive multiple update iterations, while omitted items keep their prior sort positions.
- Impact: an admin/API client can corrupt FAQ ordering state with a malformed reorder request; public and admin FAQ ordering then depends on secondary `id` ordering and may not match the intended sequence.
- Suggested regression test: add an admin FAQ reorder test with duplicate IDs, asserting `422 INVALID_FAQ` and no `faq_items.sort_order` changes.

### QA-017 — Atelier page renders admin-authored entities literally after text edits

- Severity: Medium
- Confidence: Confirmed
- Area: Backend / Frontend / Atelier Content
- Environment: isolated temp SQLite DB, local ASGI admin/public route probe, React server-rendering probe using frontend dependencies
- Status: Confirmed
- Preconditions: admin bearer authentication is configured; the seeded `hero` atelier section exists.
- Reproduction steps:
  1. Initialize an isolated temp SQLite DB and app.
  2. `PATCH /v1/admin/about/sections/hero` with `{"heading_en":"Ben & Co <Studio>","subheading_en":"Handmade \"A\" & B"}`.
  3. `GET /v1/about?locale=en` and inspect the `hero` section.
  4. Render the returned heading as a React text child, matching `frontend/components/atelier/AtelierSections.tsx`.
- Expected result: admin-authored atelier content displays the intended plain text (`Ben & Co <Studio>`, `Handmade "A" & B`) while remaining safe from markup execution.
- Actual result: the admin update response, public API response, and database row contain escaped entities (`Ben &amp; Co &lt;Studio&gt;`, `Handmade &quot;A&quot; &amp; B`). React text rendering escapes those strings again, so the visible page would show literal `&amp;` and `&lt;` sequences.
- Reproduction rate: 1/1 isolated ASGI probe plus 1/1 React rendering probe.
- Evidence:
  - PATCH response subset: `{'heading_en': 'Ben &amp; Co &lt;Studio&gt;', 'subheading_en': 'Handmade &quot;A&quot; &amp; B'}`.
  - Public hero response: `{'heading': 'Ben &amp; Co &lt;Studio&gt;', 'subheading': 'Handmade &quot;A&quot; &amp; B'}`.
  - DB row: `{'heading_en': 'Ben &amp; Co &lt;Studio&gt;', 'subheading_en': 'Handmade &quot;A&quot; &amp; B'}`.
  - React rendering probe: `renderToStaticMarkup(<h1>{'Ben &amp; Co &lt;Studio&gt;'}</h1>)` produced `<h1>Ben &amp;amp; Co &amp;lt;Studio&amp;gt;</h1>`.
  - `frontend/components/atelier/AtelierSections.tsx` renders `{section.heading}`, `{section.subheading}`, and item text as normal React text children.
  - `frontend/components/atelier/BodyRenderer.tsx` renders body blocks as normal React text children.
  - `app/services/about_service.py` sanitizes editable text with `sanitize_text()` before persistence.
  - Existing service test `tests/test_about_service.py::test_sanitization_escapes_html_on_write` asserts escaped storage but does not verify rendered output.
- API requests/responses: `PATCH /v1/admin/about/sections/hero` with escapable characters -> `200` containing entity-escaped fields; `GET /v1/about?locale=en` -> `200` containing entity-escaped public fields.
- Database state: `about_sections.heading_en` and `about_sections.subheading_en` persist entity-escaped strings rather than the original admin text.
- Relevant logs: no backend error; local app startup logged courier office data loads.
- Likely cause: the about service uses HTML entity encoding as storage-level sanitization, but the public React page renders API strings as plain text and relies on React's escaping, causing double-escaping at display time.
- Impact: admins editing atelier page copy can corrupt public page text for normal punctuation and branded names containing ampersands, quotes, or angle brackets; the admin edit response also echoes the corrupted entity text.
- Suggested regression test: add an about admin/public rendering test that edits heading/body text containing `&`, `<`, and quotes, then asserts the rendered atelier page displays the original characters as inert plain text.

### QA-018 — Checkout accepts and persists nonexistent courier office IDs

- Severity: Medium
- Confidence: Confirmed
- Area: Backend / API / Checkout / Delivery
- Environment: isolated temp SQLite DB, local ASGI client, seeded cart and product, courier office catalogue loaded from local JSON
- Status: Confirmed
- Preconditions: session cart contains at least one active product; customer selects office delivery.
- Reproduction steps:
  1. Initialize an isolated temp SQLite DB and app.
  2. Seed product `delivery-test-candle`, a session, and one cart item.
  3. `POST /v1/orders` with office delivery payload `courier=econt`, `office_id=not-a-real-econt-office`, `office_name=Injected Office Name`, `office_type=apt`, and a valid phone.
  4. `GET /v1/orders/{order_id}` with the same session.
  5. Query the Econt Sofia office catalogue for `not-a-real-econt-office`.
- Expected result: checkout should reject an office delivery selection whose `office_id` does not exist for the selected courier, or at minimum resolve the server-side office record instead of trusting client-supplied office metadata.
- Actual result: checkout returns `201`, persists the fake office ID/name/type, and the order detail returns the same fake office data. The local Econt Sofia catalogue has 132 offices and does not contain `not-a-real-econt-office`.
- Reproduction rate: 1/1 isolated ASGI route probe plus 1/1 catalogue check.
- Evidence:
  - Checkout response status: `201`.
  - Checkout response delivery details: `{'courier': 'econt', 'office_id': 'not-a-real-econt-office', 'office_name': 'Injected Office Name', 'office_type': 'apt', 'phone': '+359888123456'}`.
  - GET order response returns the same `delivery_method='office'`, `delivery_courier='econt'`, and fake `delivery_details`.
  - DB order row stores `delivery_details` JSON containing `not-a-real-econt-office` and `Injected Office Name`.
  - Catalogue check: `econt_sofia_count 132`, `fake_id_present False`, sample IDs were `['econt-48485', 'econt-1029', 'econt-48128', ...]`.
  - `app/models/delivery.py` validates only shape/literals/phone for `DeliveryOffice`; it does not validate `office_id` against `delivery_service` data.
  - `app/services/order_service.py` serializes `delivery.office.model_dump()` directly into `orders.delivery_details`.
- API requests/responses: `POST /v1/orders` with fake office delivery -> `201`; `GET /v1/orders/{order_id}` -> `200` returning the same fake office delivery details.
- Database state: `orders.delivery_method='office'`, `orders.delivery_courier='econt'`, and `orders.delivery_details` contains client-supplied nonexistent office metadata.
- Relevant logs: no backend error; local app startup logged courier office data loads.
- Likely cause: checkout treats the frontend's selected office object as trusted input and does not resolve or verify it against the backend courier office catalogue before creating the order.
- Impact: customers or manipulated clients can place pickup orders to nonexistent or mismatched offices, leaving staff with undeliverable courier details and corrupting order fulfilment data.
- Suggested regression test: add checkout route coverage for nonexistent and courier-mismatched `office_id` values, asserting a validation error and no order/cart mutation.

## Coverage Map

| Feature / Area | Status | Notes |
| --- | --- | --- |
| Build, lint, type checks, automated tests | Partially tested | Backend pytest passed; backend ruff passed; frontend lint passed with warnings; frontend Vitest fails, see QA-001; Next build passed with existing `<img>` warnings |
| Public storefront | Partially tested | Discount price sort semantics and atelier text entity rendering inspected/probed; broader browser workflows pending |
| Product detail, gallery, and social proof | Partially tested | Comment sanitization/rendering probed, see QA-014; gallery and broader product detail browser behavior pending |
| Cart and checkout | Partially tested | Backend cart/order discount contract passed; frontend checkout discount summary mismatch recorded in QA-004; office-delivery catalogue validation gap recorded in QA-018 |
| Orders and payment retry | Partially tested | Admin bank-transfer payment route creates duplicate placed email intents, see QA-007; admin payment-status filter accepts invalid values, see QA-008; Stripe retry accepts form POSTs, see QA-009; frontend payment retry pending |
| Auth and account | Partially tested | Returning-user OAuth profile persistence probe recorded in QA-006; blank avatar fallback recorded in QA-010; user-menu accessible-name issue recorded in QA-011; broader auth/permissions remain pending |
| Admin products, uploads, taxonomy, FAQ, promotions, atelier content, orders | Partially tested | Admin product video response, CSV malformed encoding and image max-count behavior, bank-transfer payment route, order filters, FAQ duplicate reorder handling, and atelier text rendering probed; taxonomy/promotions deeper flows pending |
| Backend API validation and error handling | Partially tested | Cart/order happy path, over-stock response, checkout delivery office validation, discount pricing contract, admin auth basics, admin product video response consistency, public comments entity handling, contact newline/header-like input handling, admin CSV malformed encoding/image feedback, admin order filter validation, Stripe retry content-type handling, and representative custom error envelopes probed |
| Database integrity | Partially tested | CSV image URL partial-success behavior recorded in QA-013; broader schema and persistence probes pending |
| Accessibility and responsive layout | Partially tested | User-menu accessible name probed, see QA-011; broader browser/screenshot checks pending |
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
- Ran direct auth/avatar fallback probes showing backend can return `name=""` and the frontend fallback initial becomes empty instead of using email.
- Ran accessible-name probe for the authenticated user-menu trigger, showing empty name in loaded-avatar state and only an initial in fallback state.
- Ran isolated ASGI admin payment route probe showing duplicate queued placed email rows after bank-transfer payment confirmation.
- Ran isolated ASGI admin order-list filter probe showing invalid `status` returns 422 while invalid `payment_status` returns 200 empty results.
- Ran isolated ASGI Stripe retry route probe showing form-encoded POST creates a new checkout session and mutates `stripe_checkout_session_id`.
- Ran isolated ASGI CSV import malformed-encoding probe showing invalid UTF-8 upload returns 500 and logs `UnicodeDecodeError`.
- Ran isolated ASGI CSV import max-images probe showing product fields update while a supplied `image_url` is silently dropped from a full gallery.
- Ran isolated ASGI comment probe showing comment display names/bodies are stored and returned as HTML entities, then a React rendering probe showing those strings are escaped again in text children.
- Ran isolated ASGI contact probe with an embedded newline in `name`, then drained the contact email queue with a recording provider and observed a multiline subject.
- Ran isolated ASGI admin FAQ reorder probe with duplicate IDs and observed a `200` response plus duplicate `sort_order` values in `faq_items`.
- Ran isolated ASGI atelier admin/public text probe showing edited section fields are stored and returned as HTML entities, then a React rendering probe showing those strings are escaped again in public page text.
- Ran isolated ASGI checkout probe with a nonexistent Econt office ID and observed a `201` order plus persisted fake delivery metadata; catalogue lookup confirmed the ID is absent.

## Systemic Findings

- Frontend tests have inconsistent render utilities and browser API setup for client components using `next-intl` and `window.matchMedia`.
- Admin product response assembly is inconsistent between update and read paths; video attachment is omitted from `update_product()`.
- Route handlers handcraft error envelopes inconsistently, bypassing the documented `details` field required by the global error shape.
- Frontend code has multiple price consumers; some use `effective_price_cents`, while checkout summary and product-listing sort still use base `price_cents`.
- Frontend auth UI does not consistently normalize blank optional profile fields before rendering fallbacks.
- Header controls have inconsistent accessible naming; cart is labelled, but the authenticated user menu is not.
- Some service/route boundaries both perform side effects, as seen with duplicate bank-transfer placed email enqueueing.
- Sibling enum filters are validated unevenly in admin routes; `status` is checked before querying while `payment_status` is treated as an arbitrary SQL parameter.
- State-changing order endpoints do not consistently apply the same content-type/CSRF guard.
- Upload/parsing paths can bypass row-level validation and fall through to the global 500 handler for malformed input.
- CSV import separates product upsert from image attachment and can report success even when the secondary image operation is skipped.
- User-generated text is HTML-escaped before persistence and then rendered as ordinary React text, causing entity double-escaping in comments.
- Public form fields are reused in email header-like template positions without rejecting internal line breaks.
- Ordered-list mutations validate item existence but not input-list uniqueness, allowing duplicate persisted positions.
- Admin-authored text is HTML-escaped before persistence and then rendered as ordinary React text, causing entity double-escaping in atelier page content.
- Checkout delivery validation trusts client-supplied office IDs/names instead of resolving selected offices server-side from the courier catalogue.

## Missing Safeguards

None confirmed yet.

## Recommended Regression Tests

- QA-001: Add global `matchMedia` shim, enforce/render translated components with `NextIntlClientProvider`, and keep admin form fixtures synchronized with required product fields.
- QA-002: Add admin update coverage for products that already have video rows.
- QA-003: Add API error schema tests for custom route-returned errors and centralize envelope creation.
- QA-004: Add checkout UI coverage for discounted cart items so line totals and subtotals both use effective prices.
- QA-005: Add product-listing sort tests where base price and effective price produce different orders.
- QA-006: Add returning-user OAuth coverage where optional name/avatar claims are omitted.
- QA-007: Add bank-transfer payment route coverage asserting only one queued `placed` email row.
- QA-008: Add admin order-list validation coverage for invalid `payment_status`.
- QA-009: Add form-encoded rejection coverage for the Stripe retry endpoint and assert no Stripe call or session-id mutation.
- QA-010: Add avatar fallback coverage for `name=""` and `avatar_url=null`, expecting the email initial.
- QA-011: Add `UserMenu` accessibility coverage asserting the account menu trigger has a descriptive accessible name in image and fallback states.
- QA-012: Add CSV import coverage for invalid UTF-8 uploads, expecting a controlled `400 INVALID_CSV` response.
- QA-013: Add CSV import coverage for full-gallery products with `image_url`, expecting an explicit row error or skipped-image signal.
- QA-014: Add comment API/UI coverage for `&`, `<`, and quotes, asserting rendered text matches the user's original plain text while markup remains inert.
- QA-015: Add contact route/email rendering coverage for CR/LF in `name`, asserting the subject is single-line by validation or normalization.
- QA-016: Add admin FAQ reorder coverage for duplicate IDs, asserting a validation error and unchanged sort orders.
- QA-017: Add atelier admin/public rendering coverage for `&`, `<`, and quotes, asserting rendered content matches the original plain text while markup remains inert.
- QA-018: Add checkout route coverage for nonexistent and courier-mismatched `office_id` values, asserting validation failure and no order/cart mutation.

## Remaining Attack Surface

- Full application surface remains to be tested.
