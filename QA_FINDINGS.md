# QA Findings

Source prompt: `bugs/bugs_prompt.md`

## Progress Snapshot

- Status: Investigating
- Started: 2026-07-29
- Environment: local workspace `/Users/I551270/PycharmProjects/AtelierMarie`
- Areas tested: initial prompt review, backend automated tests, backend lint, frontend lint, frontend unit test suite isolation, isolated cart/order API happy path and stock failure, admin product video update response consistency, route-level API error envelope consistency
- Areas not yet tested: frontend browser workflows, broader backend API edge cases, auth/permissions beyond admin bearer probes, database integrity beyond automated tests and video response probe, accessibility, performance, error handling, concurrency
- Active hypotheses: frontend component test harness is missing shared browser and intl providers; admin ProductForm test fixture is stale relative to required product taxonomy fields; product/video attachment is inconsistent across admin product service paths; custom route errors bypass the global envelope shape
- Unresolved anomalies: `bugs/bugs_prompt.md` is staged as an empty new file while the worktree contains the QA prompt; `bugs/prompt.txt` is untracked and intentionally untouched
- Test accounts/data created: none yet
- Services manipulated: none yet
- Major remaining attack surfaces: full application surface remains open

## Executive QA Summary

- Total confirmed bugs discovered: 3
- Severity counts: Critical 0, High 0, Medium 3, Low 0
- Major risk areas: frontend regression coverage reliability; admin product response consistency; API contract consistency
- Most fragile workflows: not yet established
- Systemic patterns: not yet established
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

## Coverage Map

| Feature / Area | Status | Notes |
| --- | --- | --- |
| Build, lint, type checks, automated tests | Partially tested | Backend pytest passed; backend ruff passed; frontend lint passed with warnings; frontend Vitest fails, see QA-001; Next build passed with existing `<img>` warnings |
| Public storefront | Not tested | Pending frontend/API probing |
| Product detail and gallery | Not tested | Pending frontend/API probing |
| Cart and checkout | Not tested | Pending frontend/API probing |
| Orders and payment retry | Not tested | Pending frontend/API probing |
| Auth and account | Not tested | Pending auth/API probing |
| Admin products, uploads, taxonomy, FAQ, promotions, atelier content, orders | Not tested | Pending permissions and state probes |
| Backend API validation and error handling | Partially tested | Cart/order happy path, over-stock response, admin auth basics, admin product video response consistency, and representative custom error envelopes probed |
| Database integrity | Not tested | Pending schema and persistence probes |
| Accessibility and responsive layout | Not tested | Pending browser/screenshot checks |
| Performance and resource behavior | Not tested | Pending after functional surface mapping |

## Scenario Inventory

- Ran full backend pytest and Python lint.
- Ran full frontend Vitest and focused failing frontend test files.
- Inspected failing component/test source to separate product defects from test harness defects.
- Used isolated temp SQLite + ASGI client to verify cart session behavior, order creation, stock decrement, admin bearer auth, and admin product video response consistency.
- Probed representative route-level API errors for contract consistency.

## Systemic Findings

- Frontend tests have inconsistent render utilities and browser API setup for client components using `next-intl` and `window.matchMedia`.
- Admin product response assembly is inconsistent between update and read paths; video attachment is omitted from `update_product()`.
- Route handlers handcraft error envelopes inconsistently, bypassing the documented `details` field required by the global error shape.

## Missing Safeguards

None confirmed yet.

## Recommended Regression Tests

- QA-001: Add global `matchMedia` shim, enforce/render translated components with `NextIntlClientProvider`, and keep admin form fixtures synchronized with required product fields.
- QA-002: Add admin update coverage for products that already have video rows.
- QA-003: Add API error schema tests for custom route-returned errors and centralize envelope creation.

## Remaining Attack Surface

- Full application surface remains to be tested.
