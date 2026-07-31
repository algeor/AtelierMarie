# QA Findings

Source prompt: `its-showtime-prompts/QA.md`

## Progress Snapshot

- Status: Active QA snapshot; fixes started from the confirmed bug catalogue and browser/full-stack smoke coverage continued
- Started: 2026-07-29
- Environment: local workspace `/Users/I551270/PycharmProjects/AtelierMarie`
- Areas tested: initial prompt review, backend automated tests, backend lint, frontend lint/build, standalone frontend typecheck command, frontend unit test suite isolation, isolated cart/order API happy path and stock failure, admin product video update response consistency, route-level API error envelope consistency, backend discount contract tests, frontend checkout discount display consistency, frontend product listing discount sort consistency, auth returning-user profile persistence edge case, auth avatar fallback edge case, auth user-menu accessible-name check, auth logout session-cookie rotation, OAuth callback session rotation behavior, admin bank-transfer payment email outbox idempotency, admin order status/payment-status filter validation, Stripe retry content-type/CSRF validation, Stripe completed webhook out-of-order cancelled/non-card handling, admin CSV malformed encoding handling, admin CSV image max-count behavior, public comment sanitization and React text rendering behavior, public contact submission and owner-email subject handling, admin FAQ duplicate reorder handling, admin-managed atelier content entity rendering, admin atelier image clear file lifecycle, checkout office-delivery catalogue validation, checkout office-city mismatch persistence, checkout unsupported door served-place validation, checkout visual/mobile delivery field accessibility, checkout mobile order-summary placement, cart drawer empty/filled/low-stock/stale states, public/legal/product safety legal identity placeholder propagation, backend email legal context placeholder propagation, mobile header navigation availability, checkout shipping price transparency and persisted shipping cents, product-detail structured data coverage, storefront product-listing first-page cap/filter omission, public FAQ invalid-locale handling, checkout door-delivery whitespace address handling, mock-mode product media URL resolution, current-code revalidation of prior product video, discount, auth, comment, contact, atelier text, payment, and delivery findings, Chrome public-route smoke on home/products/checkout/legal/content pages, seeded full-stack Chrome checkout/admin shipping smoke with fake courier services, smoke-test external email side-effect isolation, transactional email plain-text line formatting, and desktop/mobile screenshot review of product listing/product detail media
- Deferred QA scope: broader frontend browser workflows, frontend checkout submission in a real browser session, backend APIs beyond representative probes, auth/permissions beyond the tested admin bearer and OAuth/session paths, order email sweeper behavior, deeper database integrity, broader accessibility, performance, error handling outside representative route-level envelopes, and concurrency.
- Confirmed risk themes: frontend test/typecheck reliability; API response contract consistency; pricing display consistency; auth/session rotation; payment/email idempotency; transactional email quality; product media integrity; cart recovery and inventory UX; checkout form accessibility; mobile checkout review flow; upload/import validation; user/admin-authored text rendering; ordered-list integrity; checkout delivery validation; legal identity completeness; mobile navigation; storefront discovery; SEO structured data; mock media resolution; admin media file lifecycle; local smoke-test isolation from real external providers.
- Unresolved anomalies: full backend pytest once exceeded the `/v1/about` 200 ms assertion at 279 ms, but the focused test passed in isolation
- Test accounts/data created: none yet
- Services manipulated: Next mock dev server on `127.0.0.1:3002`; local frontend audit server on `127.0.0.1:3003`; existing local frontend/backend on `localhost:3000` and `127.0.0.1:8000`; isolated Chrome smoke stack on `127.0.0.1:3010` and `127.0.0.1:8010` with fake courier services; isolated checkout visual audit stack on dynamic localhost ports with a temporary copied catalog database and fake courier calculate endpoints
- Fix backlog readiness: each catalogue entry includes reproduction steps, observed/expected behavior, evidence, likely cause, impact, and a suggested regression test.

## Executive QA Summary

- Total confirmed bugs discovered: 41
- Severity counts: Critical 0, High 3, Medium 32, Low 6
- Major risk areas: frontend regression/typecheck reliability; admin product response consistency; API contract consistency; discount pricing consistency; auth profile persistence; auth/session rotation reliability; payment email outbox idempotency; transactional email content quality; product media integrity; cart recovery and inventory UX; checkout delivery form accessibility; mobile checkout order review; admin filter validation consistency; payment retry request-hardening consistency; payment webhook state ordering; admin upload validation hardening; user-generated content rendering consistency; public-form email notification hardening; admin ordered-list data integrity; admin content rendering consistency; admin content media lifecycle; checkout delivery destination integrity; checkout delivery address integrity; public legal/compliance identity configuration; mobile storefront navigation; storefront catalogue discovery; checkout shipping price transparency; product-page SEO structured data; mock/deployment media reliability; QA/smoke harness isolation from live external providers
- Most fragile workflows: auth session rotation, checkout delivery integrity, payment/email side effects, admin import/media lifecycle, and storefront catalogue discovery
- Systemic patterns: inconsistent reuse of backend/public pricing semantics in frontend UI code; duplicated cross-layer side effects between service and route code; duplicated frontend/backend legal identity constants without a launch-time completeness guard; client-side storefront filtering over a fixed first page; inconsistent locale validation between sibling public endpoints; delivery text fields lack shared whitespace normalization and programmatic label associations; admin media clear paths can update database pointers without removing public static files; route-level cookie rotation can be overwritten by middleware-set session cookies
- Areas that appear robust in this snapshot: focused backend discount pricing contracts and several previously reported issues now have current-code evidence indicating fixes, pending final browser or end-to-end revalidation where noted.
- Areas difficult to validate: auth/OAuth and external integrations may require mocks or local-only probes
- Current fix notes: QA-029, QA-030, QA-031, and QA-032 are fixed in the current worktree with focused or full-stack verification.
- Current revalidation notes: QA-001, QA-002, QA-004, QA-005, QA-006, QA-007, QA-008, QA-009, QA-010, QA-011, QA-014, QA-015, QA-017, QA-018, QA-019, and QA-021 have current-run evidence indicating they may be fixed and should be revalidated before being treated as active defects.

## Complete Bug Catalogue

### QA-001 — Full frontend test suite fails from broken ProductGallery/ProductVideo/ProductForm test setup

- Severity: Medium
- Confidence: Confirmed
- Area: Frontend / Tests
- Environment: local workspace, `frontend`, Vitest `v4.1.10`, jsdom
- Status: Needs revalidation - full frontend Vitest passed in current run
- Preconditions: dependencies installed; current worktree as of 2026-07-29
- Reproduction steps:
  1. Run `cd frontend && npm test`.
  2. Run the focused repro `cd frontend && npx vitest run __tests__/components/products/ProductGallery.test.tsx __tests__/components/ProductVideo.test.tsx __tests__/components/admin/ProductForm.test.tsx --reporter=verbose`.
- Expected result: frontend regression suite passes or fails only on real product regressions.
- Actual result: 8 tests fail across 3 files.
- Reproduction rate: 2/2 command runs.
- Evidence:
  - Current rerun contradicted the earlier failure: `npm --prefix frontend run test` passed with 41 files and 248 tests, so this finding may have been fixed by later worktree changes.
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
- Status: Needs revalidation - current tests/code indicate fixed
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
- Current revalidation note: 2026-07-29 current run: app/services/product_service.py update_product now attaches video fields before returning, and tests/test_product_service.py::test_partial_update_preserves_video_in_response exists.
- Suggested regression test: add a backend admin product update test that seeds a ready video, patches a non-video field, and asserts the update response still includes `video`.

### QA-003 — Route-level API errors omit the documented `details` field

- Severity: Medium
- Confidence: Confirmed
- Area: Backend / API
- Environment: isolated temp SQLite DB, local ASGI client, `ENVIRONMENT=development`
- Status: Needs revalidation - current worktree adds a mobile menu implementation
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
- Status: Needs revalidation - current tests/code indicate fixed
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
- Current revalidation note: 2026-07-29 current run: frontend/app/[locale]/checkout/page.tsx uses item.product.effective_price_cents for unit and line totals; frontend/__tests__/app/checkout.test.tsx asserts effective-price summary.
- Suggested regression test: add a checkout page/component test with a discounted cart item and assert the unit price, line total, and subtotal all use `effective_price_cents`.

### QA-005 — Client-side product price sorting ignores active discounts

- Severity: Medium
- Confidence: Confirmed
- Area: Frontend / Product Listing / Discounts
- Environment: local workspace, frontend `ProductListingClient`, backend discount tests green
- Status: Needs revalidation - current tests/code indicate fixed
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
- Current revalidation note: 2026-07-29 current run: ProductListingClient sorts price_asc/price_desc by effective_price_cents, and ProductListingClient.test.tsx has sorts-by-effective-sale-price coverage.
- Suggested regression test: add a `ProductListingClient` test where a discounted high-base-price product has the lowest effective price, then assert `price_asc`/`price_desc` order by `effective_price_cents`.

### QA-006 — Returning OAuth login clears stored name and avatar when Google omits optional claims

- Severity: Medium
- Confidence: Confirmed
- Area: Backend / Auth / User Profile
- Environment: isolated temp SQLite DB, direct `auth_service.upsert_user` probe
- Status: Needs revalidation - current tests/code indicate fixed
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
- Current revalidation note: 2026-07-29 current run: auth_service.upsert_user normalizes blank profile fields and preserves existing name/avatar when Google omits them; tests/test_auth.py covers returning-user omitted fields.
- Suggested regression test: add an `upsert_user` test for an existing user where `name` and `avatar_url` are omitted, asserting the stored row preserves existing non-null values or the response and persistence are intentionally aligned.

### QA-007 — Admin bank-transfer payment confirmation queues duplicate placed email rows

- Severity: Medium
- Confidence: Confirmed
- Area: Backend / Admin Orders / Email Outbox
- Environment: isolated temp SQLite DB, local ASGI admin route probe, `ENVIRONMENT=development`, admin bearer key
- Status: Needs revalidation - current tests/code indicate fixed
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
- Current revalidation note: 2026-07-29 current evidence: `tests/realapp/test_order_routes.py::TestAdminMarkPaymentPaid::test_bank_transfer_paid_queues_one_placed_email` is present and current route code queues one `placed` email through `mark_bank_transfer_paid()` only.
- Suggested regression test: add a route-level bank-transfer payment test that asserts a single `placed` row exists after `PATCH /v1/admin/orders/{id}/payment`; keep the enqueue responsibility in one layer or make `queue_order_email` idempotent for queued intents.

### QA-008 — Admin order payment status filter accepts invalid values as empty results

- Severity: Medium
- Confidence: Confirmed
- Area: Backend / API / Admin Orders
- Environment: isolated temp SQLite DB, local ASGI admin route probe, `ENVIRONMENT=development`, admin bearer key
- Status: Needs revalidation - current tests/code indicate fixed
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
- Current revalidation note: 2026-07-29 current evidence: `tests/realapp/test_order_routes.py::TestAdminInvalidStatusFilter::test_invalid_payment_status_422` is present and current `app/routes/admin.py` validates `payment_status` before querying.
- Suggested regression test: add an admin order list route test for `payment_status=bogus` asserting a 422 error and another valid payment-status control asserting 200.

### QA-009 — Stripe retry endpoint accepts form posts and creates a new checkout session

- Severity: Medium
- Confidence: Confirmed
- Area: Backend / API / Orders / Payments
- Environment: isolated temp SQLite DB, local ASGI route probe, fake Stripe module, `STRIPE_SECRET_KEY=sk_test_probe`
- Status: Needs revalidation - current tests/code indicate fixed
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
- Current revalidation note: 2026-07-29 current evidence: `tests/realapp/test_order_routes.py::TestCsrfProtection::test_stripe_retry_form_encoded_rejected` is present and current `app/routes/orders.py` rejects non-JSON retry requests.
- Suggested regression test: add a route-level test that posts form-encoded content to `/v1/orders/{id}/stripe-session` with a retryable card order and asserts a 422 `INVALID_CONTENT_TYPE` response and no Stripe call/session-id mutation.

### QA-010 — User avatar fallback renders blank when profile name is an empty string

- Severity: Low
- Confidence: Confirmed
- Area: Frontend / Auth / User Menu
- Environment: local workspace, direct backend auth service probe plus executable frontend fallback-expression probe
- Status: Needs revalidation - current tests/code indicate fixed
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
- Current revalidation note: 2026-07-29 current run: UserAvatar trims name and falls back to email initial; UserMenu.test.tsx covers blank name/null avatar fallback.
- Suggested regression test: add a `UserAvatar` or `UserMenu` test where `name=""` and `avatar_url=null`, asserting the email initial is rendered; normalize blank names before computing initials.

### QA-011 — Authenticated user menu button has no descriptive accessible name

- Severity: Low
- Confidence: Confirmed
- Area: Frontend / Auth / Accessibility
- Environment: local workspace, source inspection plus `dom-accessibility-api` accessible-name probe
- Status: Needs revalidation - current tests/code indicate fixed
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
- Current revalidation note: 2026-07-29 current run: UserMenu trigger now has aria-label My Account and tests assert the accessible name and menu attributes.
- Suggested regression test: add a `UserMenu` accessibility test asserting the trigger can be found by role and localized name, e.g. `getByRole("button", { name: /account|user/i })`, in both image and fallback states.

### QA-012 — Admin CSV import crashes on invalid UTF-8 upload instead of returning CSV validation error

- Severity: Medium
- Confidence: Confirmed
- Area: Backend / API / Admin Products / CSV Import
- Environment: isolated temp SQLite DB, local ASGI admin route probe, `raise_app_exceptions` true and false controls
- Status: Fixed in current worktree - seeded smoke passed with console email delivery and no ZeptoMail calls observed
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
- Status: Needs revalidation - current tests/code indicate fixed
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
- Current revalidation note: 2026-07-29 current run: app/services/comment_service.py now unsanitizes comment display_name/body in create/list/admin output, and tests/realapp/test_comment_routes.py::TestPostCommentRoute::test_returns_plain_text_not_html_entities exists.
- Suggested regression test: add an API/comment UI integration test that posts text containing `&`, `<`, and quotes, then asserts the rendered comment displays the original characters as plain text without executing markup.

### QA-015 — Contact form newline names create multiline owner-email subjects

- Severity: Medium
- Confidence: Confirmed
- Area: Backend / Contact / Email Notifications
- Environment: isolated temp SQLite DB, local ASGI client, direct contact email drain with recording provider
- Status: Needs revalidation - current model and route test indicate fixed
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
- Current revalidation note: 2026-07-29 current run: app/models/contact.py now collapses contact name control whitespace with single_line_name, and tests/test_contact_routes.py::test_contact_name_newlines_are_single_line_in_subject exists.
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
- Status: Needs revalidation - current tests/code indicate fixed
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
- Current revalidation note: 2026-07-29 current run: app/services/about_service.py now unsanitizes public/admin section and item text output, and tests/test_about_service.py::test_sanitization_escapes_html_on_write asserts API output returns raw text while storage remains escaped.
- Suggested regression test: add an about admin/public rendering test that edits heading/body text containing `&`, `<`, and quotes, then asserts the rendered atelier page displays the original characters as inert plain text.

### QA-018 — Checkout accepts and persists nonexistent courier office IDs

- Severity: Medium
- Confidence: Confirmed
- Area: Backend / API / Checkout / Delivery
- Environment: isolated temp SQLite DB, local ASGI client, seeded cart and product, courier office catalogue loaded from local JSON
- Status: Needs revalidation - current tests/code indicate fixed
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
- Current revalidation note: 2026-07-29 current evidence: `tests/realapp/test_delivery_checkout.py::TestCheckoutDeliveryValidation::test_nonexistent_office_id_returns_422` is present and current checkout catches `InvalidDeliveryOfficeError`.
- Suggested regression test: add checkout route coverage for nonexistent and courier-mismatched `office_id` values, asserting a validation error and no order/cart mutation.

### QA-019 — Stripe completion trusts order IDs and mutates cancelled or non-card orders

- Severity: Medium
- Confidence: Confirmed
- Area: Backend / Payments / Webhooks / Order State
- Environment: isolated temp SQLite DB, direct payment-service webhook handler probe
- Status: Needs revalidation - current tests/code indicate fixed
- Preconditions: a valid Stripe `checkout.session.completed` webhook references an existing order ID that is not currently payable, such as a cancelled card order or a COD order.
- Reproduction steps:
  1. Initialize an isolated temp SQLite DB.
  2. Insert session `s-card` and order `order-cancelled-card` with `status='cancelled'`, `payment_method='card'`, `payment_status='failed'`, `stripe_checkout_session_id='cs_old'`, and customer email `paid-late@example.com`.
  3. Call `handle_payment_succeeded(conn, 'evt_cancelled_completed', 'order-cancelled-card', 'pi_cancelled', now)`, matching the service used by `POST /v1/webhooks/stripe` for `checkout.session.completed`.
  4. Query the order, `order_emails`, and `stripe_events`.
  5. Repeat with pending COD order `order-cod-stripe` (`payment_method='cod'`, `payment_status='cod_pending'`) and event `evt_cod_completed`.
- Expected result: a completed payment webhook should only mark an order paid when the order is a payable card order and the event matches the current Stripe checkout session; terminal cancelled orders and non-card orders should not receive Stripe payment success side effects.
- Actual result: the handler returns `True`, applies `payment_status='paid'`, stores the Stripe payment intent, records the Stripe event, and queues a `placed` customer email for both a cancelled card order and a COD order.
- Reproduction rate: 2/2 isolated service probes.
- Evidence:
  - Before handler: `{'status': 'cancelled', 'payment_method': 'card', 'payment_status': 'failed', 'stripe_payment_intent_id': None}`.
  - Handler result: `True`.
  - After handler: `{'status': 'cancelled', 'payment_method': 'card', 'payment_status': 'paid', 'stripe_payment_intent_id': 'pi_cancelled'}`.
  - Queued emails: `[{'event': 'placed', 'recipient': 'paid-late@example.com', 'status': 'queued'}]`.
  - Stripe event row: `{'event_id': 'evt_cancelled_completed', 'order_id': 'order-cancelled-card', 'event_type': 'checkout.session.completed'}`.
  - COD before handler: `{'status': 'pending', 'payment_method': 'cod', 'payment_status': 'cod_pending', 'stripe_payment_intent_id': None}`.
  - COD after handler: `{'status': 'pending', 'payment_method': 'cod', 'payment_status': 'paid', 'stripe_payment_intent_id': 'pi_cod'}`.
  - COD queued emails: `[{'event': 'placed', 'recipient': 'cod-stripe@example.com', 'status': 'queued'}]`.
  - `app/routes/webhooks.py` passes valid `checkout.session.completed` events directly to `handle_payment_succeeded()`.
  - `app/services/payment_service.py` updates `orders.payment_status='paid'` by `id` only and queues `placed` email when an order row exists; it does not check `orders.status`, previous `payment_status`, `payment_method`, or current `stripe_checkout_session_id`.
- API requests/responses: route-level path is `POST /v1/webhooks/stripe` with a valid Stripe-signed `checkout.session.completed` event whose `client_reference_id` is the affected order ID; direct service probes exercised the same handler branch without external Stripe signing.
- Database state: cancelled card probe leaves `orders.status='cancelled'` while changing `orders.payment_status` to `paid`; COD probe leaves `payment_method='cod'` while changing `payment_status` to `paid`; both probes queue `placed` emails and store Stripe events as processed.
- Relevant logs: service logged `stripe_payment_succeeded event_id=evt_cancelled_completed order_id=order-cancelled-card` and `stripe_payment_succeeded event_id=evt_cod_completed order_id=order-cod-stripe`.
- Likely cause: `handle_payment_succeeded()` is idempotent by event ID but not state-aware; it applies payment success side effects to any existing order ID regardless of order status, payment method, previous payment status, or matching checkout session.
- Impact: out-of-order or mismatched Stripe webhooks can produce contradictory order state (`cancelled` but `paid`) or convert COD orders to paid, then send customer placed/thank-you email for an order that should not have been confirmed through Stripe.
- Current revalidation note: 2026-07-29 current evidence: `tests/test_payment_integration.py` now covers cancelled, non-card, and mismatched-session Stripe success guards; current `payment_service` checks order state before marking paid.
- Suggested regression test: add payment webhook/service coverage for `checkout.session.completed` on cancelled, non-pending, and non-card orders, asserting no paid transition or placed email is queued unless the order is a payable card order and the session ID matches the current checkout session.

### QA-020 — Public pages and transactional email contexts expose TODO legal identity values

- Severity: Medium
- Confidence: Confirmed
- Area: Frontend / Backend / Legal / Email
- Environment: local workspace, Next.js build output, direct frontend/backend legal identity probes
- Status: Confirmed
- Preconditions: current worktree uses the checked-in legal identity constants.
- Reproduction steps:
  1. Run `node --experimental-strip-types` against `frontend/lib/legal.ts` and print `LEGAL_IDENTITY` plus keys containing `TODO`.
  2. Run `.venv/bin/python` against `app.legal.LEGAL_IDENTITY` and print keys containing `TODO`.
  3. Inspect the legal/product pages and email context builders that render these constants.
- Expected result: Public policy pages, product safety information, and transactional email templates should use complete legal identity data or fail closed before production when required legal values are still placeholders.
- Actual result: The frontend and backend legal identity constants contain TODO placeholder values, and those values are rendered by public legal/product pages and passed into transactional email contexts.
- Reproduction rate: 1/1 frontend legal constant probe and 1/1 backend legal constant probe.
- Evidence:
  - Frontend probe output includes `legalName=TODO: legal entity name`, `geographicAddress=TODO: geographic business address`, `registrationNumber=TODO: registration number`, `vatNumber=TODO: VAT number or not VAT registered`, and `responsiblePartyAddress=TODO: geographic business address`.
  - Backend probe output includes `legal_name=TODO: legal entity name`, `geographic_address=TODO: geographic business address`, `registration_number=TODO: registration number`, and `vat_number=TODO: VAT number or not VAT registered`.
  - `frontend/app/[locale]/privacy/page.tsx` renders `LEGAL_IDENTITY.legalName`, `geographicAddress`, and `registrationNumber` in the controller details section.
  - `frontend/app/[locale]/terms/page.tsx` renders `LEGAL_IDENTITY.legalName`, `geographicAddress`, `registrationNumber`, and `vatNumber` in trader identity details.
  - `frontend/app/[locale]/products/[id]/page.tsx` renders `LEGAL_IDENTITY.responsiblePartyAddress` in product safety information.
  - `app/services/email_service.py` injects `LEGAL_IDENTITY` legal name, address, registration number, and VAT number into order email template context.
  - `npm --prefix frontend run build` completed successfully, so the placeholder content does not block production builds.
- API requests/responses: not applicable.
- Database state: not applicable.
- Relevant logs: no runtime error; build succeeds with unrelated `<img>` warnings only.
- Likely cause: Legal identity values are duplicated as static frontend/backend constants with TODO placeholders and there is no startup/build-time guard that rejects incomplete required legal fields before those constants are rendered or used in emails.
- Impact: A production build can ship legally required policy, trader, product-safety, and email identity fields as `TODO` text, creating customer confusion and compliance risk.
- Suggested regression test: Add a build/test guard that fails when any required legal identity value contains TODO/placeholder text, and add page/email context tests asserting legal identity fields are complete before production release.

### QA-021 — Mobile header hides primary store navigation without a mobile menu

- Severity: Medium
- Confidence: Confirmed
- Area: Frontend / UX / Accessibility / Navigation
- Environment: local workspace, Header component code inspection, architecture runtime note
- Status: Confirmed
- Preconditions: viewport is below the Tailwind `md` breakpoint.
- Reproduction steps:
  1. Open or inspect the storefront header at a mobile viewport below `md`.
  2. Observe the header navigation links container uses `hidden md:flex`.
  3. Search the header/layout components for a mobile menu trigger or alternative primary navigation.
- Expected result: Mobile users should have a visible, keyboard-accessible way to navigate to primary storefront destinations such as Home, Shop, Atelier, FAQ, and Contact.
- Actual result: The primary nav list is hidden on mobile and the header renders no replacement menu trigger; mobile users only get the logo, language toggle, auth control, and cart button.
- Reproduction rate: 1/1 code inspection plus architecture runtime sampling note.
- Evidence:
  - `frontend/components/layout/Header.tsx` renders the primary links in `<ul className="hidden md:flex items-center gap-8">`.
  - The same Header component renders only `LanguageToggle`, auth, and cart controls on the right side; there is no `md:hidden` menu button or drawer.
  - `rg` over `frontend/components/layout` found no mobile menu/hamburger implementation for Header; only `LanguageToggle` has a menu role.
  - `ARCHITECT_FINDINGS.md` records runtime sampling of `/en` where desktop links were inside a `hidden md:flex` list.
- API requests/responses: not applicable.
- Database state: not applicable.
- Relevant logs: not applicable.
- Likely cause: The responsive header hides desktop navigation below `md` but no mobile navigation drawer/menu was implemented to replace it.
- Impact: Mobile shoppers cannot directly reach core store/support destinations from the header, which creates discovery friction and weakens keyboard/mobile navigation.
- Current revalidation note: 2026-07-29 current worktree: frontend/components/layout/Header.tsx now defines `NAV_LINKS`, renders a `md:hidden` menu button, opens a portal dialog with Home/Shop/Atelier/FAQ/Contact links, and uses the shared `useFocusTrap`; frontend/messages/en.json and bg.json now include open/close/menu labels; `npx vitest run __tests__/components/layout/Header.test.tsx --reporter=verbose` passed 5 tests. Browser/mobile interaction still needs revalidation before closing the historical finding.
- Suggested regression test: Add Header tests for a mobile menu trigger, menu contents, Escape/backdrop close behavior, focus restoration, and keyboard reachability of primary navigation links.

### QA-022 — Checkout can place orders before showing or persisting a real shipping cost

- Severity: High
- Confidence: Confirmed
- Area: Frontend / Backend / Checkout / Delivery Pricing
- Environment: local workspace, direct `order_service.checkout` probe, checkout UI code inspection
- Status: Confirmed
- Preconditions: cart contains at least one item and customer selects a valid delivery destination.
- Reproduction steps:
  1. Inspect the checkout order summary shipping row.
  2. Inspect `DeliverySection` pricing note and `order_service.checkout` shipping calculation.
  3. Run a direct checkout service probe with a valid office delivery selection and inspect `items_total_cents`, `shipping_cents`, and `total_cents`.
- Expected result: Before submitting an order, checkout should either show a real shipping price included in `total_cents` or clearly enforce a free-shipping business rule server-side.
- Actual result: Checkout displays shipping as not separately calculated, still enables Place Order, and backend checkout hardcodes `shipping_cents=0` so `total_cents` equals item subtotal.
- Reproduction rate: 1/1 direct checkout service probe.
- Evidence:
  - `frontend/app/[locale]/checkout/page.tsx` renders `shippingNotCalculated` and displays total due as `formatPrice(total_cents)` from the cart subtotal.
  - `frontend/components/checkout/DeliverySection.tsx` says shipping price, calculate API, courier comparison, and free-shipping threshold are intentionally out of scope for this change.
  - `app/services/order_service.py` sets `shipping_cents = 0` with a comment that the shipping-pricing follow-on adds real courier calculation and free-shipping threshold.
  - Direct checkout probe output: `{'items_total_cents': 2500, 'shipping_cents': 0, 'total_cents': 2500, 'db_total_cents': 2500}`.
  - `openspec/changes/shipping-pricing/tasks.md` leaves `/v1/delivery/calculate`, `CreateOrderRequest.shipping_cents`, checkout validation, and frontend calculate wiring unchecked.
- API requests/responses: direct service probe; no HTTP request required to prove the checkout invariant.
- Database state: direct probe persisted `orders.total_cents=2500` for a 2500-cent cart and returned `shipping_cents=0`.
- Relevant logs: direct probe logged courier office data loads, then returned `shipping_cents=0`.
- Likely cause: Structured delivery was implemented before the shipping-pricing follow-on, leaving a placeholder zero shipping amount in both UI and backend checkout.
- Impact: Customers can submit an order without knowing the delivered cost unless shipping is actually free; staff then inherit ambiguous fulfilment/payment expectations.
- Suggested regression test: Add checkout tests requiring selected shipping quote inclusion in `total_cents`, server-side range validation of `shipping_cents`, and explicit free-shipping override behavior when applicable.

### QA-023 — Product detail pages omit Product and Offer structured data

- Severity: Low
- Confidence: Confirmed
- Area: Frontend / SEO / Product Detail
- Environment: local workspace, product/FAQ/atelier page code inspection
- Status: Confirmed
- Preconditions: active product detail page is rendered.
- Reproduction steps:
  1. Inspect `frontend/app/[locale]/products/[id]/page.tsx` for `application/ld+json` output.
  2. Compare with FAQ and Atelier pages that already emit JSON-LD scripts.
  3. Search product detail route and SEO helpers for Product/Offer schema generation.
- Expected result: Each active product page should emit Product JSON-LD with offer price, currency, availability, URL, brand/seller, and product identity fields.
- Actual result: The product detail page renders product UI and basic metadata but no `application/ld+json` Product/Offer block.
- Reproduction rate: 1/1 code inspection.
- Evidence:
  - `frontend/app/[locale]/products/[id]/page.tsx` imports product data and renders the product page but has no `<script type="application/ld+json">`.
  - `frontend/app/[locale]/faq/page.tsx` emits `application/ld+json` via `buildFaqJsonLd` and `serializeJsonLd`.
  - `frontend/app/[locale]/atelier/page.tsx` emits `application/ld+json` via `getAboutJsonLd`.
  - `rg` found no Product/Offer structured-data builder or `application/ld+json` block under the product detail route.
- API requests/responses: not applicable.
- Database state: not applicable.
- Relevant logs: not applicable.
- Likely cause: Structured-data helpers were added for FAQ/About content but not extended to product detail pages.
- Impact: Product pages miss a standard e-commerce SEO signal for price, availability, and product identity, reducing eligibility for product-rich search results.
- Suggested regression test: Add a product detail render test that asserts a Product JSON-LD script with Offer `priceCurrency`, `price`, `availability`, `url`, `image`, `sku`/`productID`, `brand`, and `seller` fields.

### QA-024 — Storefront filters can hide matching products beyond the first 100

- Severity: Medium
- Confidence: Confirmed
- Area: Frontend / Product Listing / Discovery
- Environment: local workspace, temp SQLite DB, direct product service probe, storefront page code inspection
- Status: Confirmed
- Preconditions: active catalogue has more than 100 products; a product matching a filter/search is outside the first 100 newest products
- Reproduction steps:
  1. Seed a temp DB with 100 active medium products and one active small product created later.
  2. Inspect frontend/app/[locale]/products/page.tsx and frontend/lib/api.ts.
  3. Compare the storefront fixed getProducts(1, 100, locale) data set with the backend category=small result.
- Expected result: Filtered/search product listing views should include every active matching product, or the server page should request the filter/search from the backend API.
- Actual result: The page always fetches the first 100 products without search/filter/sort parameters, then ProductListingClient filters only that array. A matching product on page 2 is absent from the client data and the filter returns zero visible products.
- Reproduction rate: 1/1 temp DB service probe
- Evidence:
  - frontend/app/[locale]/products/page.tsx calls getProducts(1, 100, locale) and passes only the returned products array into ProductListingClient.
  - frontend/lib/api.ts getProducts only sends page, limit, and locale; it does not send type, category, labels, q, sort, or in_stock from the URL.
  - frontend/components/products/ProductListingClient.tsx applies product_type, category, label, stock, search, and sort on the received products array.
  - app/routes/products.py and product_service.list_products support server-side category/filter pagination, with limit capped at 100.
  - Probe output: {'storefront_fetch_total': 101, 'storefront_fetch_count': 100, 'first_page_last': 'bulk-medium-099', 'hidden_product_in_first_page': False, 'client_small_filter_ids': [], 'api_small_total': 1, 'api_small_ids': ['hidden-small-needle']}
- API requests/responses: Direct service equivalent of GET /v1/products?page=1&limit=100 and GET /v1/products?category=small&page=1&limit=100
- Database state: Temp DB contained 101 active products; hidden-small-needle existed and matched category small but was not in the first 100 unfiltered products.
- Relevant logs: not applicable
- Likely cause: The server-rendered listing page ignores URL search params and fetches a fixed first page for a client-only filtering model.
- Impact: As the catalogue grows, shoppers can use filters/search and get false zero-result pages even though matching products exist in the backend catalogue.
- Suggested regression test: Add a product listing integration test with more than 100 products, a filtered match outside the first page, and assert the page/API request includes the filter or paginates enough to show the match.

### QA-025 — Public FAQ accepts unsupported locales and silently falls back to English

- Severity: Low
- Confidence: Confirmed
- Area: Backend / API / Locale Validation
- Environment: temp SQLite DB, real FastAPI app via ASGI client
- Status: Confirmed
- Preconditions: public FAQ route is available
- Reproduction steps:
  1. Initialize a temp DB and create the real FastAPI app.
  2. Request GET /v1/faq?locale=fr.
  3. Compare with sibling localized endpoints GET /v1/about?locale=fr, GET /v1/taxonomy?locale=fr, and GET /v1/promotions/banner?locale=fr.
- Expected result: Unsupported locale values should be rejected consistently with the documented en/bg locale contract.
- Actual result: FAQ returns 200 with English content for locale=fr, while sibling endpoints reject the same invalid locale with 422 validation errors.
- Reproduction rate: 1/1 ASGI route comparison probe
- Evidence:
  - Probe output: /v1/faq?locale=fr -> 200 with sections.
  - Probe output: /v1/about?locale=fr -> 422 VALIDATION_ERROR, Input should be 'en' or 'bg'.
  - Probe output: /v1/taxonomy?locale=fr -> 422 VALIDATION_ERROR, Input should be 'en' or 'bg'.
  - Probe output: /v1/promotions/banner?locale=fr -> 422 VALIDATION_ERROR, String should match pattern '^(en|bg)$'.
  - app/routes/faq.py types locale as Locale | str, which accepts arbitrary strings.
  - app/services/faq_service.py _public_locale returns bg only for bg and otherwise falls back to en.
- API requests/responses: GET /v1/faq?locale=fr returned 200 {'sections': ...}; GET /v1/about?locale=fr returned 422 VALIDATION_ERROR; GET /v1/taxonomy?locale=fr returned 422 VALIDATION_ERROR; GET /v1/promotions/banner?locale=fr returned 422 VALIDATION_ERROR
- Database state: Fresh seeded FAQ content only.
- Relevant logs: courier office data load logs during app startup only
- Likely cause: FAQ route widened the locale parameter to Locale | str and the service fallback treats every non-bg value as en.
- Impact: API clients can ship typoed or unsupported locale URLs that appear successful, hiding localization bugs and producing inconsistent behavior across public pages.
- Suggested regression test: Add route tests asserting GET /v1/faq?locale=fr returns the same 422 validation shape as about/taxonomy/promotions.

### QA-026 — Checkout accepts whitespace-only door-delivery address fields

- Severity: Medium
- Confidence: Confirmed
- Area: Backend / Checkout / Delivery Data Integrity
- Environment: temp SQLite DB, real FastAPI app via ASGI client
- Status: Confirmed
- Preconditions: session cart contains at least one active product; customer selects door delivery
- Reproduction steps:
  1. Initialize a temp DB, seed an active product, and add it to a session cart through POST /v1/cart.
  2. POST /v1/orders with delivery.method=door and city, postal_code, street, building, and apartment set to spaces only.
  3. Inspect the response delivery_details.
- Expected result: Required delivery address fields should be trimmed and whitespace-only city/postal_code/street should be rejected before an order is created.
- Actual result: The order is created with 201 and persists whitespace-only city, postal_code, street, building, and apartment values in delivery_details.
- Reproduction rate: 1/1 ASGI checkout probe
- Evidence:
  - Probe output: {'cart_status': 201, 'order_status': 201, 'delivery_details': {'courier': 'econt', 'city': '   ', 'postal_code': '   ', 'street': '   ', 'building': '   ', 'apartment': '   ', 'phone': '+359888123456'}, 'error': None}.
  - app/models/delivery.py DeliveryDoor uses min_length/max_length for city, postal_code, and street but has no strip or whitespace-only validator for address fields.
  - The frontend DeliverySection validation also checks presence/truthiness, so a string of spaces is not treated as missing before submission.
- API requests/responses: POST /v1/cart -> 201; POST /v1/orders with whitespace-only door address -> 201 and returned whitespace fields
- Database state: Temp DB order was created and cart was cleared for the whitespace-only address payload.
- Relevant logs: courier office data load logs during app startup only
- Likely cause: Delivery text fields rely on length constraints without shared string normalization, unlike customer_name/contact/product validators that strip and reject blank strings.
- Impact: A customer can place an order with an unusable delivery address, leaving staff unable to fulfil the shipment without manual follow-up.
- Suggested regression test: Add delivery model and checkout route tests for whitespace-only city/postal_code/street/building/apartment, asserting required fields reject after trim and optional fields normalize to null/empty.

### QA-027 — Mock storefront product images resolve to backend-only URLs that do not exist

- Severity: Low
- Confidence: Confirmed
- Area: Frontend / Mock Mode / Media
- Environment: local workspace, mock API code inspection, filesystem probe
- Status: Confirmed
- Preconditions: frontend runs with NEXT_PUBLIC_USE_MOCK_API=true, which README documents as not requiring the backend
- Reproduction steps:
  1. Inspect README.md mock-mode guidance.
  2. Inspect mock product image URLs in frontend/lib/mock-api.ts.
  3. Inspect ProductImage URL resolution and api-client BASE_URL default.
  4. Check whether a mock product image exists under frontend/public and under backend static.
- Expected result: Mock mode should render bundled mock product images from the frontend without requiring backend static serving.
- Actual result: ProductImage rewrites /static/products/lavender-dreams-300ml.webp to http://localhost:8000/static/products/lavender-dreams-300ml.webp. The file exists in frontend/public/static/products, but not in backend static/products, so mock product cards fall back to placeholders unless an external backend happens to serve matching mock filenames.
- Reproduction rate: 1/1 code and filesystem probe
- Evidence:
  - README.md states NEXT_PUBLIC_USE_MOCK_API=true uses mock data and does not require the backend to be running.
  - frontend/lib/mock-api.ts returns primary_image_url values like /static/products/lavender-dreams-300ml.webp.
  - frontend/components/products/ProductImage.tsx prefixes any /static/ URL with BASE_URL from frontend/lib/api-client.ts.
  - frontend/lib/api-client.ts defaults BASE_URL to http://localhost:8000.
  - Filesystem probe output: {'mockPath': '/static/products/lavender-dreams-300ml.webp', 'resolved': 'http://localhost:8000/static/products/lavender-dreams-300ml.webp', 'frontendPublicExists': true, 'backendStaticExists': false}.
- API requests/responses: not applicable
- Database state: not applicable
- Relevant logs: not applicable
- Likely cause: Product media URL resolution treats all /static paths as backend media, even for frontend-bundled mock assets.
- Impact: The documented no-backend mock storefront can show product-name placeholders instead of bundled product images, reducing the usefulness of local/demo storefront review and hiding media regressions.
- Suggested regression test: Add ProductImage or mock-mode page coverage asserting bundled /static mock assets resolve to frontend-served paths when NEXT_PUBLIC_USE_MOCK_API=true, while backend-uploaded media still resolves through the configured media/API origin.

### QA-028 — Clearing atelier images leaves deleted files publicly served

- Severity: Medium
- Confidence: Confirmed
- Area: Backend / Admin About / Media Lifecycle
- Environment: temp SQLite DB, real FastAPI app via ASGI client, temp static directory
- Status: Confirmed
- Preconditions: admin bearer authentication is configured; seeded atelier/about content exists.
- Reproduction steps:
  1. Initialize a temp DB and temp static directory, then create the real FastAPI app.
  2. `POST /v1/admin/about/sections/hero/image` with a valid JPEG and note the returned `/static/products/about-hero_<id>.webp` URL.
  3. Verify the generated main, thumbnail, and zoom WebP files exist under the configured static directory.
  4. `DELETE /v1/admin/about/sections/hero/image` and confirm the admin response/listing now has `image_id: null` and `image: null`.
  5. Check the same generated files on disk. Repeat the flow for `POST`/`DELETE /v1/admin/about/sections/values/items/{item_id}/image`.
- Expected result: Clearing an atelier section or item image should remove the generated main, thumbnail, and zoom derivatives, or otherwise make the old public URL unavailable.
- Actual result: The API clears the database pointer and returns 200, but all generated image files remain under the public `/static` mount.
- Reproduction rate: 2/2 ASGI probes, covering one section image and one item image.
- Evidence:
  - Section probe output: `upload_status=200`, `clear_status=200`, `hero_after_clear={'image_id': None, 'image': None}`, while `files_after_clear` kept `about-hero_<id>.webp`, `about-hero_<id>_thumb.webp`, and `about-hero_<id>_zoom.webp` as `True`.
  - Item probe output: `upload_status=200`, `clear_status=200`, `item_after_clear={'image_id': None, 'image': None}`, while `files_after_clear` kept `about-item-18_<id>.webp`, `about-item-18_<id>_thumb.webp`, and `about-item-18_<id>_zoom.webp` as `True`.
  - `app/main.py` mounts `/static` with `StaticFiles(directory=settings.static_file_path, check_dir=False)`.
  - `app/services/about_service.py` `clear_section_image()` and `clear_item_image()` only set `image_id = NULL`; they do not look up the previous image ID or unlink derivatives.
  - `app/services/about_service.py` `set_section_image()` and `set_item_image()` save files with `process_image(...)` under `/static/products/{owner_slug}_{image_id}.webp`.
  - `app/services/product_image_service.py` `delete_image()` unlinks main, thumbnail, and zoom files, showing the expected cleanup pattern already exists elsewhere.
- API requests/responses: `POST /v1/admin/about/sections/hero/image -> 200` with `/static/products/about-hero_<id>.webp`; `DELETE /v1/admin/about/sections/hero/image -> 200` with `image_id=null`; `POST /v1/admin/about/sections/values/items/{item_id}/image -> 200`; `DELETE /v1/admin/about/sections/values/items/{item_id}/image -> 200` with `image_id=null`.
- Database state: After each clear, the corresponding `about_sections.image_id` or `about_items.image_id` is null, but the generated files remain in static storage.
- Relevant logs: local app startup logged courier office data loads; no backend error was raised.
- Likely cause: About image clear paths update only database state and do not share the media unlink cleanup used by product image deletion.
- Impact: Admins cannot actually remove a mistaken, outdated, or sensitive atelier image from public static storage; stale URLs remain fetchable if cached/bookmarked, and repeated edits leak storage over time.
- Suggested regression test: Add real-app tests for section and item image upload/clear with a temp static directory, asserting the main, thumbnail, and zoom files are removed and old `/static/products/...` URLs no longer resolve.

### QA-029 — Logout session rotation is overwritten by a duplicate old session cookie

- Severity: Medium
- Confidence: Confirmed
- Area: Backend / Auth / Session Management
- Environment: temp SQLite DB, real FastAPI app via ASGI client
- Status: Fixed in current worktree - targeted tests pass
- Preconditions: an existing session row is linked to a user; the browser sends that `session_id` cookie to `POST /v1/auth/logout`.
- Reproduction steps:
  1. Initialize a temp DB and real FastAPI app.
  2. Insert a user and a session row with `user_id` set to that user.
  3. Send `POST /v1/auth/logout` with the existing `session_id` cookie.
  4. Inspect all `Set-Cookie` headers and the `sessions` table after the response.
- Expected result: Logout should emit one effective `session_id` cookie for the newly rotated anonymous session, and the client should continue with that new session ID.
- Actual result: The route emits a new `session_id` cookie first, but `SessionMiddleware` appends a second `session_id` cookie for the old session after the route returns. The last cookie value is the old session ID, so clients can keep the old session despite `X-Session-Rotated: true`.
- Reproduction rate: 2/2 ASGI probes: one hit `httpx.CookieConflict` when reading the cookie jar, and one captured duplicate `Set-Cookie` headers.
- Evidence:
  - Probe output: `x_session_rotated='true'` and `session_cookie_headers=['session_id=9722d69b-070c-432b-a228-191a759b58e0; ...', 'session_id=cbdebf17-722c-443d-9855-06689b203b1e; ...']`.
  - Probe output: `old_sid='cbdebf17-722c-443d-9855-06689b203b1e'`, `new_sid_from_first_session_cookie='9722d69b-070c-432b-a228-191a759b58e0'`, and `last_session_cookie_value='cbdebf17-722c-443d-9855-06689b203b1e'`.
  - Probe output DB rows: old session remains with `user_id=None`; new session is also created with `user_id=None`, so the database rotation work happens but the final cookie can point back to the old row.
  - First probe raised `httpx.CookieConflict: Multiple cookies exist with name=session_id` after logout, confirming the duplicate cookie state reaches clients.
  - `app/routes/auth.py` `logout()` sets a new `session_id` cookie and `X-Session-Rotated: true` when it creates the fresh session.
  - `app/middleware/session.py` always calls `response.set_cookie(... value=session_id ...)` after `call_next(request)`, where `session_id` is the pre-route request session.
  - Existing logout tests in `tests/test_auth.py` and `tests/test_auth_integration.py` parse the first matching `Set-Cookie` header and therefore miss the later duplicate old-session cookie.
- API requests/responses: `POST /v1/auth/logout -> 200` with `X-Session-Rotated: true` and two `Set-Cookie` headers for `session_id`.
- Database state: After logout, both old and new anonymous session rows exist; the old row is unlinked from the user, but the final duplicate cookie still points to it.
- Relevant logs: local app startup logged courier office data loads; no backend error was raised.
- Likely cause: Session rotation is implemented in the auth route, while the session middleware unconditionally refreshes the original request session cookie after every route response.
- Impact: Logout does not reliably rotate the browser's session despite claiming it did, weakening session-fixation hardening and creating ambiguous client cookie state that can break cookie handling or leave the user on the pre-logout anonymous session.
- Current fix note: 2026-07-29 current worktree: `SessionMiddleware` now skips its automatic session cookie refresh when a route already set/cleared `session_id`; `tests/realapp/test_session_hardened.py::test_logout_sets_single_rotated_session_cookie` asserts exactly one rotated session cookie.
- Suggested regression test: Keep logout integration coverage asserting exactly one `session_id` `Set-Cookie` header is emitted and that its value is the new rotated session, not the request session.

### QA-030 — OAuth login links the pre-login anonymous session instead of rotating it

- Severity: Medium
- Confidence: Confirmed
- Area: Backend / Auth / Session Management
- Environment: temp SQLite DB, real FastAPI app via ASGI client, mocked Google token exchange and ID-token verification
- Status: Fixed in current worktree - targeted tests pass
- Preconditions: an anonymous session exists before starting OAuth login.
- Reproduction steps:
  1. Initialize a temp DB and real FastAPI app with OAuth settings configured.
  2. Establish an anonymous session and note its `session_id` cookie.
  3. Build a valid OAuth state token for that session, then call `GET /v1/auth/callback` with mocked Google token exchange and ID-token verification.
  4. Inspect the callback `Set-Cookie` headers, the JWT session claim, `sessions`, and cart rows.
- Expected result: Successful login should rotate the anonymous session ID before binding the authenticated user, using the existing session-rotation helper so the browser and JWT move to a fresh session while anonymous cart state is migrated.
- Actual result: The callback updates the existing anonymous session row with `user_id`, sets a JWT whose `session_id` claim is the same pre-login session ID, and middleware refreshes the same old `session_id` cookie.
- Reproduction rate: 1/1 ASGI OAuth callback probe.
- Evidence:
  - Probe output: `old_sid='3b060f0d-a185-4eb4-bf95-6078a4f9ea8f'`.
  - Probe output: `session_cookie_headers=['session_id=3b060f0d-a185-4eb4-bf95-6078a4f9ea8f; ...']` and `new_sid_from_callback='3b060f0d-a185-4eb4-bf95-6078a4f9ea8f'`.
  - Probe output: `jwt_session_claim='3b060f0d-a185-4eb4-bf95-6078a4f9ea8f'`.
  - Probe output DB sessions: a single row remains, with the same ID and `user_id` set to the new user.
  - Probe output cart rows: the cart still belongs to the same pre-login session ID, proving no rotation/migration occurred.
  - `app/routes/auth.py` callback uses `UPDATE sessions SET user_id = ? WHERE id = ?` and then creates the JWT with the same `session_id` dependency value.
  - `app/middleware/session.py` defines `rotate_session()` with the docstring `Rotate session ID on login to prevent session fixation`, migrates cart items, deletes the old session, and returns a new session ID.
  - `rg` found `rotate_session()` used in tests but not in `app/routes/auth.py`.
- API requests/responses: `GET /v1/auth/callback?code=code&state=<valid_state> -> 302` to frontend success URL; response includes a refreshed `session_id` cookie with the original pre-login value.
- Database state: After callback, the original anonymous session row is now authenticated; no new session row was created and no old row was deleted.
- Relevant logs: local app startup logged courier office data loads; no backend error was raised.
- Likely cause: The OAuth callback predates or bypasses the login rotation helper and directly links the current session to the user.
- Impact: Login does not apply the session-fixation hardening the codebase already defines; any pre-login session ID that is known or controlled before OAuth remains valid after authentication and is embedded into the JWT.
- Current fix note: 2026-07-29 current worktree: OAuth callback now rotates the pre-login session with the shared rotation path, migrates cart rows, issues the JWT for the new session, and sets one new `session_id` cookie; focused callback tests assert the old session is gone and the JWT claim matches the new cookie.
- Suggested regression test: Keep OAuth callback integration coverage asserting successful login rotates `session_id`, migrates cart rows, deletes/unlinks the old session, and issues a JWT bound to the new cookie.

### QA-031 — Seeded Chrome smoke test can send real transactional emails through ZeptoMail

- Severity: High
- Confidence: Confirmed
- Area: Infrastructure / Tests / Integration Safety
- Environment: local workspace, `CHROME_SMOKE_START_SERVERS=1`, isolated temp SQLite DB, fake Speedy/Econt servers, local environment with ZeptoMail email provider configured
- Status: Confirmed
- Preconditions: local `.env` or process environment configures `EMAIL_PROVIDER=zeptomail`, a ZeptoMail API key, and an admin notification recipient; run the seeded smoke harness with `CHROME_SMOKE_START_SERVERS=1`.
- Reproduction steps:
  1. Run `CHROME_SMOKE_START_SERVERS=1 CHROME_SMOKE_KEEP_DB=1 FRONTEND_URL=http://127.0.0.1:3010 BACKEND_URL=http://127.0.0.1:8010 node scripts/chrome_smoke.mjs` from the repository root.
  2. Let the customer checkout and admin shipping smoke flows complete.
  3. Inspect the backend log output from the smoke run.
- Expected result: A local smoke test that creates fake orders must not contact real external email providers or send real customer/admin transactional emails. It should force console/no-op email settings or use a fake provider, the same way it fakes courier APIs.
- Actual result: The isolated backend inherited the real local email configuration and sent queued order emails through ZeptoMail during the smoke flow.
- Reproduction rate: 1/1 seeded Chrome smoke run.
- Evidence:
  - Smoke output included three external provider calls: `HTTP Request: POST https://api.zeptomail.eu/v1.1/email "HTTP/1.1 201 "`.
  - Smoke output logged `email_sent` for `email_event=placed`, `email_event=admin_new_order`, and `email_event=shipped` for the fake smoke order.
  - `scripts/chrome_smoke.mjs` starts the managed backend with fake courier settings and test auth/session settings, but does not override `EMAIL_PROVIDER`, `EMAIL_API_KEY`, `ADMIN_NOTIFICATION_EMAIL`, or related email side-effect settings.
  - The local environment has ZeptoMail enabled; the specific API key value is intentionally not recorded here.
  - Current fix: `scripts/chrome_smoke.mjs` now overrides the managed backend with `EMAIL_PROVIDER=console`, empty `EMAIL_API_KEY`, empty `ADMIN_NOTIFICATION_EMAIL`, and empty `ZEPTOMAIL_WEBHOOK_AUTH_KEY`.
  - Post-fix verification: the same seeded smoke command completed with `email_console_send` and `email_skipped_no_recipient` logs and no ZeptoMail HTTP request observed.
- API requests/responses: Browser checkout/admin flows created fake orders through the local backend; backend then made real outbound `POST https://api.zeptomail.eu/v1.1/email` requests that returned `201`.
- Database state: The smoke harness used a temp SQLite database and fake order data; the external email calls were the non-isolated side effect.
- Relevant logs: `email_sent email_event=placed`, `email_sent email_event=admin_new_order`, `email_sent email_event=shipped`, followed by `Drained email outbox count=3`.
- Likely cause: `startManagedServers()` passes through the parent process environment and overrides courier/auth/database settings, but it does not force `EMAIL_PROVIDER=console`, clear `EMAIL_API_KEY`, clear `ADMIN_NOTIFICATION_EMAIL`, or otherwise replace outbound email delivery with a fake provider.
- Impact: Running a local smoke test can contact a real third-party email service and potentially send test transactional emails to real admin/customer addresses. This violates the QA prompt's non-production/no-irreversible-external-side-effects rule, creates privacy/compliance risk, and can pollute provider reputation or production-like operational inboxes.
- Suggested regression test: Add a smoke harness/self-test that starts the managed backend with side-effecting email env vars set and asserts the child process effective email provider is console/no-op and no outbound ZeptoMail request is possible. Also make the harness explicitly override email provider settings whenever `CHROME_SMOKE_START_SERVERS=1`.

### QA-032 — Plain-text order emails concatenate shipping and total lines

- Severity: Medium
- Confidence: Confirmed
- Area: Backend / Email / Customer Communications
- Environment: seeded full-stack Chrome smoke with console email provider; direct template/source inspection
- Status: Fixed in current worktree - renderer tests pass
- Preconditions: render customer order placed or payment pending email templates with `shipping_is_fallback` false or true.
- Reproduction steps:
  1. Run the seeded full-stack smoke after forcing console email delivery.
  2. Inspect the `email_console_send` body for the generated order placed emails.
  3. Inspect `app/email/templates/en/order_placed.txt`, `app/email/templates/en/order_payment_pending.txt`, `app/email/templates/bg/order_placed.txt`, and `app/email/templates/bg/order_payment_pending.txt` with `app/email/renderer.py`.
- Expected result: Plain-text transactional emails should show financial lines on separate lines, for example `Shipping: €6.50` followed by `Total: €31.50` on the next line.
- Actual result: Rendered order emails concatenate the shipping and total lines, for example `Shipping: €6.50Total: €31.50` and `Shipping: €5.90Total: €40.90`.
- Reproduction rate: 2/2 customer order placed emails observed in the seeded smoke run.
- Evidence:
  - Smoke output body for the Speedy order contained `Subtotal: €25.00\nShipping: €6.50Total: €31.50`.
  - Smoke output body for the Econt order contained `Subtotal: €35.00\nShipping: €5.90Total: €40.90`.
  - `app/email/renderer.py` configures Jinja with `trim_blocks=True`.
  - The affected templates put an inline block tag at the end of the shipping line: `Shipping: {{ shipping_display }}{% if shipping_is_fallback %} (estimated){% endif %}` and Bulgarian equivalent. With `trim_blocks=True`, the newline after `{% endif %}` is removed.
  - Existing renderer tests assert shipping substrings but do not assert that total/delivery labels start on a new line.
  - Current fix: affected templates now use inline conditional expressions instead of inline block tags, preserving line breaks under `trim_blocks=True`.
  - Post-fix verification: `.venv/bin/pytest tests/test_email_renderer.py -q` passed 17 tests, including new line-boundary checks for English/Bulgarian placed/payment-pending emails and the admin order email.
- API requests/responses: not applicable; defect is in rendered email content produced after successful local order creation.
- Database state: orders and outbox rows are valid; rendered plain-text body is malformed.
- Relevant logs: `email_console_send` output from the seeded smoke run.
- Likely cause: Plain-text templates use block tags inside line-oriented text while the global Jinja environment trims the following newline after a block.
- Impact: Customer order emails present monetary totals in a visually broken way, reducing professionalism and making order totals harder to scan. For a small luxury store, transactional email polish directly affects trust after purchase.
- Suggested regression test: Add renderer tests that assert `Total:`/`Общо:` and `Delivery:` labels start on their own lines after the shipping line for placed, payment-pending, and admin order templates.

### QA-033 — Standalone frontend typecheck fails on stale `.next/types` references

- Severity: Medium
- Confidence: Confirmed
- Area: Frontend / Build Tooling / Developer Experience
- Environment: local workspace, `frontend`, TypeScript via `npm --prefix frontend run typecheck`, Next.js custom dist dirs `.next-build` and `.next-dev`
- Status: Confirmed
- Preconditions: repository contains a stale `.next/types` directory that references generated route type files no longer present in `.next/types/app/[locale]`.
- Reproduction steps:
  1. Run `npm --prefix frontend run typecheck` from the repository root.
  2. Compare `frontend/tsconfig.json` includes with the generated type directories present after `npm --prefix frontend run build`.
  3. Inspect `frontend/.next/types/validator.ts` and `frontend/.next/types/app`.
- Expected result: the standalone typecheck command should complete or check the current generated type directory used by the configured Next build/dev scripts.
- Actual result: `tsc --noEmit` exits with code 2 before checking the application because it tries to include missing generated files from stale `.next/types`.
- Reproduction rate: 1/1 local command run.
- Evidence:
  - `npm --prefix frontend run typecheck` failed with `TS6053: File '/Users/I551270/PycharmProjects/AtelierMarie/frontend/.next/types/app/[locale]/admin/layout.ts' not found`, plus missing `.next/types/app/[locale]/layout.ts` and `.next/types/server.d.ts`.
  - `frontend/tsconfig.json` includes `.next-build/types/**/*.ts`, `.next-dev/types/**/*.ts`, and `.next/types/**/*.ts`.
  - `npm --prefix frontend run build` sets `NEXT_DIST_DIR=.next-build` and passed type validation/build successfully, proving current build-generated types live under `.next-build`.
  - `frontend/.next/types/validator.ts` imports route/layout generated files that are not all present in `frontend/.next/types/app`, while `.next-build/types` is regenerated by the build.
  - Backend pytest, backend ruff, frontend Vitest, and frontend build all passed in the same QA pass; the standalone typecheck command is the isolated failing validation command.
- API requests/responses: not applicable.
- Database state: not applicable.
- Relevant logs: `error TS6053: File .../.next/types/app/[locale]/admin/layout.ts not found. The file is in the program because: Matched by include pattern '.next/types/**/*.ts' in frontend/tsconfig.json`.
- Likely cause: the project uses custom Next output directories for dev/build, but `tsconfig.json` still includes the default `.next/types` directory. A stale generated `.next/types/validator.ts` can reference missing files and break `npm run typecheck` independently of the real build output.
- Impact: the documented standalone frontend typecheck command is unreliable and can fail from local generated-artifact drift instead of real type errors. This blocks CI/local validation if the script is used directly and can hide actual TypeScript regressions behind stale artifact errors.
- Suggested regression test: Update the typecheck script or `tsconfig` generated-type includes so it only targets the active dist dir, then add a clean-worktree validation that `npm --prefix frontend run typecheck` passes without requiring stale `.next` artifacts.

### QA-034 — Checkout stores client-supplied city for validated courier office IDs

- Severity: Medium
- Confidence: Confirmed
- Area: Backend / Checkout / Delivery Data Integrity
- Environment: isolated temp SQLite DB, direct cart and checkout service probe, real courier office catalogue data
- Status: Confirmed
- Preconditions: cart contains an active product; checkout uses a real Econt office ID and the matching `office_type`, but supplies a city string that does not match the catalogue city.
- Reproduction steps:
  1. Initialize a temp DB, create session `sid-office-city`, seed active product `qa-office-city-candle`, and add it to the cart.
  2. Resolve a real Econt office from `delivery_service.get_offices("econt", city, locale="bg")`; probe used `office_id=econt-100001255`, catalogue city `Абланица`, office type `apt`.
  3. Build `DeliveryInfo(method="office")` with that valid office ID/type but `city="Definitely Not Абланица"`.
  4. Call `order_service.checkout(...)` and inspect the persisted `orders.delivery_details` JSON.
- Expected result: checkout should either reject the payload because the office city does not match the selected catalogue office, or persist the canonical catalogue city together with the canonical office name/type.
- Actual result: checkout succeeds and persists the fake client-supplied city while canonicalizing only `office_name` and `office_type`.
- Reproduction rate: 1/1 direct service probe.
- Evidence:
  - Probe output: `status=created`, `office_id=econt-100001255`, `catalogue_city=Абланица`, `submitted_city=Definitely Not Абланица`, `stored_city=Definitely Not Абланица`.
  - The same persisted details used the catalogue `office_name` and `office_type`, proving the service looked up the office but did not canonicalize `city`.
  - `app/services/order_service.py` validates `catalogue_office = delivery_service.get_office(...)` and overwrites `office_name`/`office_type`, but leaves `delivery_details["city"]` from `delivery_sub.model_dump()`.
- API requests/responses: not applicable; direct service probe exercises the same checkout service used by `POST /v1/orders`.
- Database state: `orders.delivery_details` contains a valid office ID paired with a fabricated city string.
- Relevant logs: no backend error; order creation returned normally.
- Likely cause: the office delivery branch normalizes selected fields from the catalogue after validation but omits `city`, allowing client-supplied display/address data to survive in the persisted order snapshot.
- Impact: admin order detail, customer order detail, labels, emails, analytics, or later shipping reconciliation can show contradictory office destination data. A valid office ID may be paired with an impossible city, making fulfilment and customer support more error-prone.
- Suggested regression test: Add checkout/service coverage with a valid office ID and mismatched city, asserting either `INVALID_DELIVERY_OFFICE` or persisted canonical `city` from `delivery_service.get_office()`.

### QA-035 — Door checkout accepts unsupported city/postcode combinations

- Severity: Medium
- Confidence: Confirmed
- Area: Backend / Checkout / Delivery Validation
- Environment: isolated temp SQLite DB, direct cart and checkout service probe, real served-place catalogue data
- Status: Confirmed
- Preconditions: cart contains an active product; checkout uses door delivery for Econt with a city/postcode that is absent from `GET /v1/delivery/places` / `delivery_service.get_places()`.
- Reproduction steps:
  1. Initialize a temp DB, create session `sid-door-place`, seed active product `qa-door-place-candle`, and add it to the cart.
  2. Confirm `delivery_service.get_places("econt", query="Not A Served Place QA", locale="bg")` returns `[]`.
  3. Build `DeliveryInfo(method="door")` with `courier="econt"`, `city="Not A Served Place QA"`, `postal_code="0000"`, `street="Unknown Street 1"`, and a valid phone.
  4. Call `order_service.checkout(...)` and inspect the persisted `orders.delivery_details` JSON.
- Expected result: checkout should reject door delivery to a place/postcode that the courier served-place catalogue does not contain, or canonicalize against a selected served-place row before order creation.
- Actual result: checkout creates the order and persists the unsupported city/postcode exactly as submitted.
- Reproduction rate: 1/1 direct service probe.
- Evidence:
  - Probe output: `served_place_matches=[]`, `status=created`, `stored_city=Not A Served Place QA`, `stored_postal_code=0000`.
  - `app/routes/delivery.py` exposes `/v1/delivery/places` specifically so door delivery can select a courier-served place with postcode/region disambiguation.
  - `app/services/order_service.py` only checks whether the selected courier/method is enabled for door delivery; it does not validate `delivery.door.city` or `postal_code` against `delivery_service.get_places()`.
- API requests/responses: not applicable; direct service probe exercises the same checkout service used by `POST /v1/orders`.
- Database state: `orders.delivery_details` contains a door delivery destination with no matching served-place catalogue row.
- Relevant logs: no backend error; order creation returned normally.
- Likely cause: served-place lookup exists for the frontend and shipping quote flow, but checkout does not enforce that the final door-delivery payload still corresponds to a served place/postcode.
- Impact: customers or scripted clients can create orders for destinations the courier data does not recognize. Fulfilment may fail later during quote reconciliation or waybill creation, after the cart is cleared and customer/admin emails are queued.
- Suggested regression test: Add checkout/service coverage for unsupported door city/postcode values and assert `INVALID_DELIVERY_PLACE`/422 with no order, stock decrement, cart clear, or outbox enqueue.

### QA-036 — Lavender Dream gallery shows unrelated pet and document images instead of candle photography

- Severity: High
- Confidence: Confirmed
- Area: Frontend / Merchandising / Product Media
- Environment: isolated visual stack on `127.0.0.1:3011` / `127.0.0.1:8011`, temporary copy of current `atelier_marie.db`, headless Chrome screenshots at 1440 desktop, 390 mobile, and 320 mobile widths
- Status: Confirmed
- Preconditions: current catalog data is copied from `atelier_marie.db`; product `lavender-dream-300ml` is active and has four `product_images` rows.
- Reproduction steps:
  1. Start the backend against a temporary copy of `atelier_marie.db` and the frontend against that backend.
  2. Visit `/en/products` at mobile or desktop width.
  3. Visit `/en/products/lavender-dream-300ml` at mobile or desktop width.
  4. Inspect the product listing card and PDP gallery thumbnails.
- Expected result: Active product media should accurately show the candle, vessel, packaging, scale, ingredients, or gift presentation for Lavender Dream.
- Actual result: The product listing and PDP hero image show an unrelated pet/outdoor photo. The PDP thumbnail strip also includes other non-product images, including a document/screenshot-like image and unrelated people/pet imagery.
- Reproduction rate: 5/5 screenshots across product listing desktop/mobile and PDP desktop/mobile/narrow-mobile captures.
- Evidence:
  - Screenshot: `/Users/I551270/PycharmProjects/AtelierMarie/qa-artifacts/screenshots/2026-07-31/clean-products-desktop-1440.png` shows the first product card image as an unrelated pet photo while other products show placeholders.
  - Screenshot: `/Users/I551270/PycharmProjects/AtelierMarie/qa-artifacts/screenshots/2026-07-31/clean-products-mobile-390.png` shows the same unrelated pet photo above `Lavender Dream`.
  - Screenshot: `/Users/I551270/PycharmProjects/AtelierMarie/qa-artifacts/screenshots/2026-07-31/clean-pdp-mobile-390.png` shows the PDP hero image and gallery thumbnails as unrelated pet/document/people imagery.
  - Database query on the copied DB shows four `product_images` rows for `lavender-dream-300ml` and no image rows for other active products.
  - Image dimension probe confirmed the current static files are real uploaded/generated media under `static/products/lavender-dream-300ml_*.webp`, not a missing-image fallback.
  - The clean visual stack reported no route errors, no console errors, and no horizontal overflow, so this is content/media integrity, not a failed render.
- API requests/responses: page/API requests returned normally on the isolated stack; defect is in displayed product media content.
- Database state: `product_images` contains four rows for `lavender-dream-300ml`, with the unrelated pet photo marked primary through `is_primary=1`.
- Relevant logs: screenshot capture output had `routeErrors: []` for the clean visual stack.
- Likely cause: non-product files were uploaded or retained as product gallery media, and there is no owner/media-readiness review gate preventing an active product from using misleading images.
- Impact: This is worse than a placeholder. It can make the shop look fake, careless, or compromised, and it actively misrepresents the product at the exact point where candle photography should build desire and trust.
- Suggested regression test: Add a product media readiness workflow rather than trying to infer image semantics automatically: active products should require owner-reviewed media status, and launch checks should fail when active products have unreviewed or placeholder media. Keep screenshot review as a manual launch gate for catalog content.

### QA-037 — Cart drawer hides unavailable items returned by the cart API

- Severity: Medium
- Confidence: Confirmed
- Area: Frontend / Cart / Recovery
- Environment: isolated cart audit stack on `127.0.0.1:3012` / `127.0.0.1:8012`, temporary copy of current catalog DB, headless Chrome mobile viewport 390x844
- Status: Confirmed
- Preconditions: cart contains `lavender-dream-300ml` and `honey-tobacco-oak-300ml`; `honey-tobacco-oak-300ml` is then deactivated in the database before the cart is reloaded.
- Reproduction steps:
  1. Add `lavender-dream-300ml` quantity 1 and `honey-tobacco-oak-300ml` quantity 8 to the cart.
  2. Update the database so `honey-tobacco-oak-300ml.is_active = 0`.
  3. Fetch `GET /v1/cart?locale=en`.
  4. Reload `/en/products`, open the cart drawer, and compare the drawer to the API response.
- Expected result: The cart drawer should show that Honey Tobacco & Oak is no longer available, explain why, and let the customer remove or recover the stale item.
- Actual result: The API returns `unavailable_items: [{ product_id: "honey-tobacco-oak-300ml", product_name: "Honey Tobacco & Oak", reason: "deactivated" }]`, but the drawer silently shows only Lavender Dream with a reduced subtotal and no unavailable-item notice.
- Reproduction rate: 1/1 isolated browser/API run.
- Evidence:
  - API response after deactivation contained `unavailable_items` with `Honey Tobacco & Oak` and reason `deactivated`.
  - Screenshot: `/Users/I551270/PycharmProjects/AtelierMarie/qa-artifacts/screenshots/2026-07-31/cart-stale-item-mobile-390.png` shows only Lavender Dream, subtotal `€32.00`, and no stale-item message.
  - `frontend/components/cart/CartDrawer.tsx` reads `items`, `total_cents`, and `item_count` from `useCart()` but never renders `unavailable_items`.
  - `frontend/contexts/CartContext.tsx` does not expose unavailable items to the drawer state in the reviewed path.
- API requests/responses: `GET /v1/cart?locale=en -> 200` with one active item and one `unavailable_items` entry.
- Database state: `cart_items` still contained the stale product row; product row was deactivated; backend correctly identified it as unavailable.
- Relevant logs: screenshot capture output had `routeErrors: []`.
- Likely cause: The backend cart contract supports unavailable item recovery, but frontend cart state/drawer rendering drops that part of the response.
- Impact: Customers can lose visible cart items without explanation when stock/catalog state changes. This creates confusion near checkout and removes the customer recovery path the backend already exposes.
- Suggested regression test: Add `CartContext` and `CartDrawer` tests with mixed active and unavailable cart response data, asserting the unavailable product name/reason is visible and removable.

### QA-038 — Cart quantity increment stays enabled at the product stock limit

- Severity: Medium
- Confidence: Confirmed
- Area: Frontend / Cart / Inventory UX
- Environment: isolated cart audit stack on `127.0.0.1:3012` / `127.0.0.1:8012`, temporary copy of current catalog DB, headless Chrome mobile viewport 390x844
- Status: Confirmed
- Preconditions: `honey-tobacco-oak-300ml` has stock 8; cart contains that product at quantity 8.
- Reproduction steps:
  1. Add `honey-tobacco-oak-300ml` quantity 8 to the cart.
  2. Open the cart drawer on mobile.
  3. Inspect the increase quantity button for Honey Tobacco & Oak.
  4. Click the plus button.
- Expected result: The plus button should be disabled or clearly explain that 8 is the available quantity. If a race still happens, the error should identify the product and available quantity.
- Actual result: The plus button is enabled at quantity 8. Clicking it triggers a generic `Insufficient stock` banner, leaves the plus button enabled, and does not tell the customer the maximum available quantity.
- Reproduction rate: 1/1 isolated browser/API run.
- Evidence:
  - Cart API product data for Honey Tobacco & Oak showed `stock: 8` and cart quantity `8`.
  - Browser metrics before clicking plus showed the Honey Tobacco increase button had `disabled: false`.
  - Screenshot: `/Users/I551270/PycharmProjects/AtelierMarie/qa-artifacts/screenshots/2026-07-31/cart-low-stock-after-plus-mobile-390.png` shows `Insufficient stock`, quantity still `8`, and the plus button still visible/enabled.
  - `frontend/components/cart/CartItem.tsx` sets `canIncrement = quantity < 10`, independent of `product.stock`.
- API requests/responses: the cart update request after clicking plus was rejected by backend stock validation; frontend surfaced only the generic stock message.
- Database state: product stock remained 8 and cart quantity remained 8.
- Relevant logs: screenshot capture output had `routeErrors: []`; backend protected stock integrity.
- Likely cause: Frontend quantity controls only know the per-item quantity cap, not the product stock cap already present in embedded cart product data.
- Impact: The UI invites customers to perform an action the system already knows will fail, creating avoidable checkout friction and weak inventory confidence.
- Suggested regression test: Add cart item UI tests where product stock is below the per-item limit and quantity equals stock, asserting the increment button is disabled and a helpful limit message is shown.

### QA-039 — Cart error dismiss control is only 16x16 pixels on mobile

- Severity: Low
- Confidence: Confirmed
- Area: Frontend / Accessibility / Cart
- Environment: isolated cart audit stack on `127.0.0.1:3012` / `127.0.0.1:8012`, headless Chrome mobile viewport 390x844
- Status: Confirmed
- Preconditions: cart drawer shows an error banner, reproduced by clicking plus on a cart item already at its stock limit.
- Reproduction steps:
  1. Add `honey-tobacco-oak-300ml` quantity 8 to the cart.
  2. Open the cart drawer on mobile and click the enabled plus button.
  3. Inspect the dismiss button in the `Insufficient stock` error banner.
- Expected result: The error-dismiss control should have a practical mobile touch target, at least matching the app's other 44x44 icon buttons or the minimum target size policy used elsewhere.
- Actual result: Browser metrics show the `Dismiss error` button is `16x16`, making it much smaller than the drawer close button and difficult to tap reliably.
- Reproduction rate: 1/1 isolated browser run.
- Evidence:
  - Screenshot: `/Users/I551270/PycharmProjects/AtelierMarie/qa-artifacts/screenshots/2026-07-31/cart-low-stock-after-plus-mobile-390.png` shows the small dismiss X in the error banner.
  - Browser metrics for the same state reported `{ name: "Dismiss error", width: 16, height: 16 }`.
  - `frontend/components/cart/CartDrawer.tsx` gives the dismiss button `shrink-0 text-red-800/70...` but no minimum width/height, while the drawer close button uses `min-w-[44px] min-h-[44px]`.
- API requests/responses: not applicable beyond triggering the stock error.
- Database state: not applicable.
- Relevant logs: screenshot capture output had `routeErrors: []`.
- Likely cause: Error banner icon button lacks the minimum target-size styling used on the main drawer close button.
- Impact: Mobile and motor-impaired users may struggle to dismiss cart errors, especially after an avoidable stock error. The rest of the drawer remains usable, so severity is low.
- Suggested regression test: Add cart drawer accessibility/layout coverage asserting interactive error-dismiss controls meet the shared minimum target size.

### QA-040 — Checkout delivery fields are visually labelled but programmatically named by placeholders

- Severity: Medium
- Confidence: Confirmed
- Area: Frontend / Accessibility / Checkout
- Environment: isolated checkout visual audit stack on dynamic localhost ports, temporary copy of current catalog DB, fake Speedy/Econt calculate endpoints, headless Chrome mobile viewport 390x844 and desktop viewport 1440x1000
- Status: Confirmed
- Preconditions: cart contains `lavender-dream-300ml` quantity 1; customer opens checkout and selects door delivery or office pickup.
- Reproduction steps:
  1. Start the storefront against a temporary copy of `atelier_marie.db` with `NEXT_PUBLIC_USE_MOCK_API=false` and fake courier calculate endpoints.
  2. In headless Chrome mobile 390x844, add `lavender-dream-300ml` to the cart and open `/en/checkout`.
  3. Select Door delivery, Speedy, Sofia, enter street and courier phone, and wait for the shipping quote to be ready.
  4. Inspect the live DOM and Chrome accessibility tree for the delivery text/tel fields.
  5. Repeat the office pickup path on desktop with Econt office selection and inspect the courier phone field.
- Expected result: Every checkout delivery input should have a persistent programmatic label matching its visible label, such as City, Postal code, Street and number, Building, Floor/Apartment, and Phone for courier.
- Actual result: The delivery inputs render visible label text, but the input elements have no `id`, no associated `label`, no `aria-label`, and no `aria-labelledby`. Chrome names the fields from placeholders or current values, e.g. `e.g., Sofia`, `1000`, `e.g., Vitosha Blvd 100`, `e.g., A`, `e.g., 12`, and `+359...`, rather than the visible field labels.
- Reproduction rate: 1/1 isolated browser run across mobile door delivery and desktop office pickup states.
- Evidence:
  - Screenshot: `/Users/I551270/PycharmProjects/AtelierMarie/qa-artifacts/screenshots/2026-07-31/checkout-door-ready-mobile-390.png` captures the mobile door-delivery form after a ready quote.
  - Screenshot: `/Users/I551270/PycharmProjects/AtelierMarie/qa-artifacts/screenshots/2026-07-31/checkout-office-ready-desktop-1440.png` captures the desktop office-pickup form after a ready quote.
  - Live DOM metrics for six door-delivery text/tel inputs reported `id=null`, `ariaLabel=null`, `ariaLabelledby=null`, and `labels=[]` while visual labels such as `Postal code *`, `Street and number *`, `Building / Entrance (optional)`, `Floor / Apartment (optional)`, and `Phone for courier *` were visible nearby.
  - Chrome accessibility tree reported textbox names from placeholders/current values: `Email *` and `Name *` were labelled correctly, but delivery fields were named `1000`, `e.g., Vitosha Blvd 100`, `e.g., A`, `e.g., 12`, `+359...`, and `e.g., Sofia`.
  - Desktop office-pickup phone field showed the same pattern: `id=null`, `ariaLabel=null`, `labels=[]`, `visualLabel=Phone for courier *`.
  - `frontend/components/checkout/DeliverySection.tsx` renders standalone visual `<label>` elements for delivery fields without `htmlFor`/`id` pairs or equivalent ARIA wiring; email, name, and order notes use the correct pattern in the checkout page.
  - The isolated browser run recorded `routeErrors: []` and backend `/v1/delivery/calculate` returned `200`, so this is not a failed-render artifact.
- API requests/responses: `POST /v1/cart?locale=en -> 201`; `POST /v1/delivery/calculate -> 200` for Speedy door quote; `POST /v1/delivery/calculate -> 200` for Econt office quote; `GET /v1/cart?locale=en -> 200` after checkout interactions.
- Database state: temporary copied DB only; shared `atelier_marie.db` was not mutated.
- Relevant logs: browser capture output had `routeErrors: []`; backend log tail included successful delivery settings, city/office lookup, cart, and calculate requests.
- Likely cause: `DeliverySection` renders standalone visual label elements without `htmlFor`/`id` pairs and without `aria-labelledby`/`aria-describedby` wiring for the associated inputs.
- Impact: Screen-reader and voice-input users cannot reliably identify required delivery fields during checkout. Placeholder-derived names are especially weak once fields are filled or examples disappear, and checkout accessibility defects can directly block revenue.
- Suggested regression test: Add checkout/DeliverySection accessibility tests using Testing Library `getByRole`/`getByLabelText` for every delivery input in door and office states, plus a browser accessibility-tree or axe check asserting delivery text/tel inputs are named by visible labels, not placeholders.

### QA-041 — Mobile checkout shows Place Order before the order summary and final total

- Severity: Medium
- Confidence: Confirmed
- Area: Frontend / UX / Checkout / Mobile
- Environment: isolated checkout visual audit stack on dynamic localhost ports, temporary copy of current catalog DB, fake Speedy/Econt calculate endpoints, headless Chrome mobile viewport 390x844
- Status: Confirmed
- Preconditions: cart contains `lavender-dream-300ml` quantity 1; customer completes delivery enough for a shipping quote on mobile checkout.
- Reproduction steps:
  1. Start the storefront against a temporary copy of `atelier_marie.db` with fake courier calculate endpoints.
  2. In headless Chrome mobile 390x844, add `lavender-dream-300ml` to the cart and open `/en/checkout`.
  3. Fill email/name, choose Door delivery, Speedy, Sofia, street, and courier phone, then wait for the quote to be ready.
  4. Inspect the mobile page order and viewport positions for the `Place Order` button and `Order Summary` block.
- Expected result: Before the customer can submit the order on mobile, the order summary and final payable total should be visible before or directly above the `Place Order` action, or the action should live inside a clearly reviewed summary step.
- Actual result: On mobile, the primary `Place Order` button appears before the `Order Summary` block and before the final total. Browser metrics at 390x844 showed the visible `Place Order` button at `top=731` while the `Order Summary` heading started below the viewport at `top=924`.
- Reproduction rate: 1/1 isolated mobile browser run.
- Evidence:
  - Screenshot: `/Users/I551270/PycharmProjects/AtelierMarie/qa-artifacts/screenshots/2026-07-31/checkout-door-ready-mobile-390.png` shows the `Place Order` button and legal text before the `Order Summary` card and final `Total` row.
  - Browser layout metrics reported viewport height `844`, visible `Place Order` button `top=731`, `height=48`, and `Order Summary` heading `top=924`.
  - `frontend/app/[locale]/checkout/page.tsx` renders the `lg:hidden` mobile submit button inside the form before the sibling `<aside>` that contains the order summary. On mobile, the grid stacks the form before the aside.
  - The isolated browser run recorded `routeErrors: []` and successful delivery quote calls, so this is the intended rendered layout, not a loading/error state.
- API requests/responses: `POST /v1/cart?locale=en -> 201`; `POST /v1/delivery/calculate -> 200` for Speedy door quote.
- Database state: temporary copied DB only; shared `atelier_marie.db` was not mutated.
- Relevant logs: browser capture output had `routeErrors: []`; backend log tail included successful delivery calculate requests before screenshot capture.
- Likely cause: The responsive layout renders the mobile submit control inside the form before the aside. Since the aside contains the summary and follows the form in DOM order, mobile stacking puts the submit action before the final review block.
- Impact: Mobile customers can submit before seeing the final order summary, shipping line, and payable total in the natural page flow. That weakens checkout trust and increases the risk of order-review hesitation or post-order support questions.
- Suggested regression test: Add mobile checkout layout coverage asserting the final total/order summary is visible before the primary submit action, or that the submit action is placed inside/after a mobile summary review block.

## Coverage Map

| Feature / Area | Status | Notes |
| --- | --- | --- |
| Build, lint, type checks, automated tests | Partially tested | Backend pytest and ruff passed; frontend Vitest passed; Next build passed with existing `<img>` warnings; standalone frontend typecheck failed on stale `.next/types` references, see QA-033 |
| Public storefront | Partially tested | Chrome smoke passed for home, products, empty-cart checkout redirect, atelier, FAQ, contact, terms, privacy, and cookies; desktop/mobile screenshots of product listing found misleading Lavender Dream media, see QA-036; mobile navigation availability, first-100 product listing cap, mock-mode media URL behavior, discount price sort semantics, atelier text entity rendering, legal/product-safety placeholder propagation, and Product/Offer structured-data coverage inspected/probed; broader browser workflows pending |
| Product detail, gallery, and social proof | Partially tested | Desktop/mobile PDP screenshots found misleading Lavender Dream gallery media, see QA-036; comment sanitization/rendering probed, see QA-014; broader product detail browser behavior pending |
| Cart and checkout | Partially tested | Seeded full-stack Chrome smoke passed Speedy door-delivery and Econt office-delivery checkout flows against fake courier APIs; checkout visual/mobile screenshots covered initial, door-ready, and office-ready states; cart drawer screenshots covered empty, item, low-stock, stock-error, and stale-item states; backend cart/order discount contract passed; QA-004 and QA-018 have current evidence indicating fixes; unresolved shipping price transparency recorded in QA-022; whitespace-only door address acceptance recorded in QA-026; office city mismatch persistence recorded in QA-034; unsupported door place acceptance recorded in QA-035; stale cart item hiding recorded in QA-037; stock-limit control failure recorded in QA-038; checkout delivery label accessibility recorded in QA-040; mobile submit-before-summary layout recorded in QA-041 |
| Orders and payment retry | Partially tested | Current tests/code indicate QA-007, QA-008, QA-009, and QA-019 may be fixed; frontend payment retry browser workflow still pending |
| Auth and account | Partially tested | QA-006, QA-010, QA-011, QA-029, and QA-030 now have current code/test evidence indicating fixes; broader auth/permissions remain pending |
| Admin products, uploads, taxonomy, FAQ, promotions, atelier content, orders | Partially tested | Seeded full-stack Chrome smoke passed admin confirm/ship/tracking/label checks for Speedy and manual Econt shipping; admin product video response now has current evidence indicating a fix; CSV malformed encoding/image max-count behavior, FAQ duplicate reorder handling, atelier text rendering, and atelier image file cleanup remain recorded; taxonomy/promotions deeper flows pending |
| Backend API validation and error handling | Partially tested | Cart/order happy path, over-stock response, checkout delivery office validation, checkout door address whitespace validation, invalid FAQ locale behavior, discount pricing contract, admin auth basics, public comments entity handling, contact newline/header-like input handling, admin CSV malformed encoding/image feedback, current admin order/payment/webhook validation, backend email legal context placeholders, and representative custom error envelopes probed |
| Database integrity | Partially tested | CSV image URL partial-success behavior recorded in QA-013; broader schema and persistence probes pending |
| Accessibility and responsive layout | Partially tested | Seeded Chrome mobile smoke passed product-detail and checkout body rendering; checkout delivery fields are visually labelled but programmatically named by placeholders, see QA-040; cart error dismiss target-size issue recorded in QA-039; user-menu accessible name probed, see QA-011; broader browser/screenshot checks pending |
| Performance and resource behavior | Not tested | Pending after functional surface mapping |

## Scenario Inventory

- Ran mobile header navigation code inspection showing primary nav hidden below `md` with no replacement menu trigger.
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
- Ran isolated payment-service webhook probes showing `handle_payment_succeeded()` changes a cancelled card order to `payment_status='paid'` while leaving `status='cancelled'`, and also changes a COD order from `cod_pending` to `paid`; both queue `placed` email.
- Ran direct frontend/backend legal identity probes showing TODO placeholder values in public page constants and backend email context constants.
- Ran direct checkout service probe showing a valid delivery order returns and persists `shipping_cents=0` and `total_cents=items_total_cents`.
- Ran product detail structured-data inspection showing FAQ/Atelier emit JSON-LD while product detail pages do not emit Product/Offer JSON-LD.
- Ran temp DB storefront listing probe showing a category-matching product outside the first 100 unfiltered products is hidden from client-side filters.
- Ran ASGI route comparison showing GET /v1/faq?locale=fr returns 200 while sibling localized endpoints reject locale=fr with 422.
- Ran ASGI checkout probe showing whitespace-only door delivery city/postal_code/street values create a 201 order and persist as delivery_details.
- Ran mock media URL resolution probe showing a bundled mock product image exists in frontend/public but ProductImage resolves it to a missing backend static URL.
- Ran isolated ASGI atelier image probes showing section and item image clear endpoints null the database pointer but leave generated main/thumb/zoom files under the public static directory.
- Ran isolated ASGI logout probe showing the route emits a new session cookie first, then middleware appends the old session cookie last, producing duplicate `session_id` cookies and `httpx.CookieConflict`.
- Ran isolated ASGI OAuth callback probe with mocked Google exchange/verification showing login binds the user and JWT to the same pre-login anonymous session ID instead of rotating it.
- Implemented current-worktree fixes for QA-029 and QA-030, then ran focused auth/session tests covering logout duplicate-cookie prevention, OAuth session rotation, JWT session claim alignment, cart migration, and existing rotation rollback behavior.
- Revalidated current code/tests for prior product-video, discount-price, auth-profile, user-menu, comment text, contact-name, atelier text, payment, and delivery findings; several older entries now need revalidation before being treated as active.
- Ran Chrome public-route smoke against the existing local stack on `localhost:3000`, covering home, products, empty-cart checkout redirect, atelier, FAQ, contact, terms, privacy, and cookies with no browser/page/server errors.
- Ran seeded full-stack Chrome smoke with a temp database and fake courier APIs, covering Speedy door checkout, Econt office checkout, admin confirm/ship/tracking/label flows, and mobile product/checkout rendering.
- Observed the seeded smoke backend inherit real ZeptoMail settings and make external `POST https://api.zeptomail.eu/v1.1/email` calls while sending fake order emails, recorded as QA-031.
- Observed console-rendered order emails concatenate `Shipping` and `Total` labels, then traced the issue to Jinja `trim_blocks=True` plus inline block tags in plain-text templates, recorded as QA-032.
- Ran `npm --prefix frontend run typecheck` and observed `TS6053` failures from stale `.next/types` references while backend pytest/ruff, frontend Vitest, and the configured Next build passed, recorded as QA-033.
- Ran a direct checkout service probe with a valid Econt office ID/type but mismatched city and observed a created order whose `delivery_details.city` retained the fake city, recorded as QA-034.
- Ran a direct checkout service probe with an Econt door city/postcode that returned no served-place matches and observed a created order persisting that unsupported destination, recorded as QA-035.
- Ran an isolated visual stack from a temporary copy of the current catalog and captured desktop/mobile product listing plus PDP screenshots; observed Lavender Dream displaying unrelated pet/document/people images instead of candle photography, recorded as QA-036.
- Ran an isolated cart audit stack and captured mobile cart drawer screenshots for empty, one-item, low-stock, post-stock-error, and stale-item states; recorded QA-037 through QA-039.
- Ran an isolated checkout visual/accessibility stack with a temporary copied catalog database and fake courier calculate endpoints; captured mobile initial, mobile door-ready, and desktop office-ready screenshots, then inspected live DOM and Chrome accessibility-tree field names; recorded QA-040.
- Used the same mobile checkout screenshot and layout metrics to confirm the primary `Place Order` button appears before the order summary/final total on mobile; recorded QA-041.

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
- Stripe webhook idempotency is event-based but not order-state-aware; completed events can apply payment success side effects to terminal cancelled orders and non-card orders.
- Legal identity values are duplicated between frontend and backend constants and can remain incomplete without breaking tests or production builds.
- Responsive header behavior hides primary navigation below `md` without an equivalent mobile menu pattern.
- Checkout delivery and order total semantics are split across structured delivery and an unfinished shipping-pricing change, leaving placeholder shipping cost behavior in the live order path.
- SEO structured-data coverage is page-specific; FAQ and Atelier have JSON-LD helpers while product detail pages lack Product/Offer coverage.
- Storefront product discovery is split between a server-fetched first page and client-side filters, so filters/search can only see already-fetched products.
- Public locale validation is not centralized; FAQ accepts arbitrary locale strings while sibling routes reject unsupported locales.
- Delivery data validation normalizes phone numbers but does not normalize required text address fields.
- Mock API media paths and product media URL resolution disagree about whether /static assets are frontend-bundled or backend-served.
- Admin content media lifecycle is database-only for atelier clear operations; generated static files are not removed with the content pointer.
- Session cookie ownership between auth routes and middleware was split; current worktree now prevents middleware from appending a stale request-session cookie when routes rotate the session.
- Login and logout paths did not share one session-rotation mechanism; current worktree routes OAuth callback through the shared rotation path.
- The managed browser smoke harness isolates database and courier dependencies but not email delivery settings, so local test runs can still trigger real provider side effects.
- Plain-text email templates use Jinja block tags inside single text lines while the renderer trims block newlines, which can join adjacent customer-facing labels.
- Frontend type validation is split between custom Next output directories and a default `.next/types` include, so stale generated artifacts can break the standalone typecheck command.
- Checkout office validation canonicalizes some catalogue fields but not all persisted destination fields, leaving client-supplied city data attached to validated office IDs.
- Checkout door delivery uses the served-place catalogue for discovery but not as a final server-side invariant before order creation.
- Product media publication has no reviewed/approved state or launch gate, allowing active products to carry unrelated uploaded media into the storefront.
- Backend cart responses include recovery data that the frontend cart state/drawer does not preserve or render.
- Cart controls use a generic quantity cap instead of product-specific stock data already present in cart item responses.
- Checkout delivery subcomponents render visual labels without programmatic label associations, unlike the main checkout contact fields.
- Mobile checkout stacks the form submit action before the order-summary review block, so the final total is not in the natural pre-submit flow.

## Missing Safeguards

- SEO structured-data implementation is page-specific; FAQ and Atelier have JSON-LD helpers while product detail pages lack Product/Offer coverage.
- Checkout delivery and order total semantics are split across a structured-delivery implementation and an unfinished shipping-pricing change, leaving placeholder cost behavior in the live order path.
- Responsive header behavior hides primary navigation below `md` without an equivalent mobile menu pattern.
- Stripe payment success handling lacks guards for terminal order statuses, non-card payment methods, and current checkout session identity before marking an order paid and queuing placed email.
- There is no launch/build/startup guard preventing `LEGAL_IDENTITY` TODO placeholders from reaching public policy pages, product safety information, or transactional emails.
- Storefront listing URLs do not have a server-side filter/search/pagination source of truth once the catalogue exceeds the first 100 products.
- Required door-delivery text fields do not share the blank-string rejection used by other customer/product text inputs.
- Mock-mode media resolution does not distinguish frontend-bundled assets from backend-uploaded media.
- Atelier section/item image clear operations do not unlink generated public static derivatives.
- Logout/session-rotation tests now include current-worktree coverage for exactly one rotated `session_id` `Set-Cookie` header.
- OAuth callback tests now include current-worktree coverage that the authenticated session ID rotates away from the pre-login anonymous session.
- Seeded smoke tests do not force no-op email delivery, so test orders can leave the local machine through a real provider when the parent environment has email configured.
- Renderer tests do not currently assert line-boundary formatting for financial totals and delivery labels in transactional emails.
- The standalone frontend typecheck command does not guard against stale default `.next/types` artifacts when the app's dev/build scripts use `.next-dev` and `.next-build`.
- Office-delivery checkout does not reject or canonicalize mismatched city data after resolving the selected courier office from the catalogue.
- Door-delivery checkout does not enforce that the final submitted city/postcode matches a served-place catalogue row before clearing the cart and queueing emails.
- Active product media can be technically present but commercially wrong; there is no media-review safeguard distinguishing accurate product photography from arbitrary uploaded files.
- Cart drawer has no customer-visible stale-item recovery state even though the backend exposes `unavailable_items`.
- Cart drawer error controls do not consistently inherit the app's minimum touch-target styling.
- Checkout delivery fields do not have a tested label-accessibility contract, allowing placeholder-derived names to reach a core purchase form.
- Mobile checkout does not enforce a clear final order-review-before-submit layout.

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
- QA-019: Add Stripe completed webhook coverage for cancelled, non-pending, and non-card orders, asserting no paid transition or placed email unless the order is a payable card order and the session ID matches.
- QA-020: Add a build/test guard that fails when required legal identity values contain TODO/placeholder text, plus page/email context tests for complete legal identity fields.
- QA-021: Add mobile header menu coverage for trigger visibility, core link reachability, Escape/backdrop close, and focus restoration.
- QA-022: Add checkout shipping quote and server validation tests covering non-zero shipping, free-shipping override, and unresolved quote rejection.
- QA-023: Add product detail JSON-LD coverage for Product and Offer schema fields.
- QA-024: Add product listing coverage with more than 100 active products and a filtered match outside the first unfiltered page.
- QA-025: Add FAQ route coverage for unsupported locale values, expecting the same 422 validation shape as sibling localized routes.
- QA-026: Add delivery model and checkout route coverage for whitespace-only door-delivery address fields.
- QA-027: Add mock-mode media URL coverage asserting bundled mock product images do not resolve to missing backend static URLs.
- QA-028: Add atelier section/item image upload-clear coverage asserting generated main, thumbnail, and zoom files are removed from static storage.
- QA-029: Added current-worktree logout coverage asserting exactly one `session_id` cookie is emitted and its value is the rotated session ID, not the request session ID.
- QA-030: Added current-worktree OAuth callback coverage asserting login rotates the session ID, migrates cart rows, and issues a JWT bound to the rotated session.
- QA-031: Add smoke-harness coverage that side-effecting parent email env vars are overridden to console/no-op delivery and no ZeptoMail request can be made during `CHROME_SMOKE_START_SERVERS=1` runs.
- QA-032: Add renderer coverage asserting shipping, total, and delivery labels stay on separate lines in English and Bulgarian customer/admin email templates.
- QA-033: Add clean-artifact typecheck coverage asserting `npm --prefix frontend run typecheck` passes with the active Next generated types and cannot read stale `.next/types` references.
- QA-034: Add checkout/service coverage with a valid office ID and mismatched city, asserting either validation failure or persisted canonical city from the courier catalogue.
- QA-035: Add checkout/service coverage for unsupported door city/postcode values, asserting 422 and no order, stock decrement, cart clear, or outbox enqueue.
- QA-036: Add a catalog media readiness gate: active products should require owner-reviewed media status, and launch checks should fail when active products have unreviewed, placeholder, or obviously non-product media. Keep manual screenshot review for semantic image accuracy.
- QA-037: Add `CartContext` and `CartDrawer` coverage for `unavailable_items`, asserting stale product name/reason are visible and removable.
- QA-038: Add cart item UI coverage where product stock is lower than the per-item limit, asserting increment is disabled at stock and errors name the affected product/available quantity.
- QA-039: Add cart drawer accessibility/layout coverage asserting the error dismiss button meets the shared minimum mobile target size.
- QA-040: Add checkout/DeliverySection accessibility coverage asserting every door and office delivery input is reachable by its visible label and is not named only by placeholder/example text.
- QA-041: Add mobile checkout layout coverage asserting the order summary and final total precede the primary submit action or are included in the same reviewed submit block.

## Deferred Attack Surface

This document is an active actionable QA snapshot. Future QA should continue into broader browser workflows, concurrency, performance, accessibility, and deeper API/database coverage, while the confirmed findings above are ready to drive fix work now.
