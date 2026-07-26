## 1. Database schema (`app/database.py`)

- [x] 1.1 Add `promotion_campaigns` table for campaign metadata, discount fields, status/applied metadata, timestamps
- [x] 1.2 Add `promotion_campaign_products` table for campaign target product IDs and last applied discount values
- [x] 1.3 Add `site_banners` or equivalent singleton/versioned table for top banner settings
- [x] 1.4 Add migration/seed path for existing static announcement copy so the current banner behavior is preserved

## 2. Promotion models

- [x] 2.1 Add campaign create/update/list/detail request and response schemas
- [x] 2.2 Add campaign target schemas for explicit product IDs and admin product-list filters
- [x] 2.3 Add campaign apply/remove response schemas with per-product results
- [x] 2.4 Add banner admin request/response schemas
- [x] 2.5 Add public localized banner response schema

## 3. Product discount bulk helper (`app/services/product_service.py`)

- [x] 3.1 Extract reusable single-product discount update logic from `promotional-discounts`
- [x] 3.2 Add target resolution for explicit IDs and admin-list filters, excluding pagination
- [x] 3.3 Enforce request-level validation before writes: one target source, non-empty target set, max 500 targets, valid discount payload
- [x] 3.4 Process product updates in one transaction with per-product savepoints
- [x] 3.5 Return per-item `{id, status, error?}` results and aggregate success/failure counts
- [x] 3.6 Implement conservative campaign removal: clear only products whose current discount fields still match the campaign's last applied values

## 4. Promotion services and routes

- [x] 4.1 Add `promotion_service.py` for campaign CRUD, apply, remove, and status derivation
- [x] 4.2 Add `banner_service.py` or equivalent for admin banner updates and public active-banner reads
- [x] 4.3 Add admin campaign routes under `/v1/admin/promotions/campaigns`
- [x] 4.4 Add admin banner routes under `/v1/admin/promotions/banner`
- [x] 4.5 Add `PATCH /v1/admin/products/bulk-discount` for direct bulk product discount operations
- [x] 4.6 Add public `GET /v1/promotions/banner?locale=en|bg`
- [x] 4.7 Register new routers in `app/main.py`

## 5. Frontend types/API/mock

- [x] 5.1 Add campaign, campaign target, bulk result, and banner types to `frontend/lib/types.ts`
- [x] 5.2 Add API client methods for campaign CRUD/apply/remove, banner get/update, public banner read, and direct bulk discount
- [x] 5.3 Add mock API support for campaigns, banner, and per-item bulk results

## 6. Admin promotions UI

- [x] 6.1 Add `/admin/promotions` route and AdminSidebar nav item
- [x] 6.2 Build campaign list with status, discount summary, target count, active window, and actions
- [x] 6.3 Build campaign create/edit form with name, note, discount percent, start/end, target selection, and optional banner copy helper
- [x] 6.4 Build product target picker using admin product filters plus explicit row selection across pages
- [x] 6.5 Build apply/remove confirmation flows with per-item result summaries
- [x] 6.6 Build top banner editor with localized message, optional link fields, enabled flag, start/end window, and preview
- [x] 6.7 Ensure completed campaign/banner operations refresh relevant admin data
- [x] 6.8 Add inline row multi-select + "select all matching filter" to the admin products list with a visible selection count
- [x] 6.9 Add an inline bulk action bar (apply/clear discount with percent + optional window) that calls the bulk discount endpoint and shows the per-item "N updated, M failed" summary

## 7. Storefront banner

- [x] 7.1 Update `AnnouncementBar` to fetch/render the active managed banner instead of static copy
- [x] 7.2 Localize banner text with fallback from BG to EN
- [x] 7.3 Hide banner when endpoint returns null or banner is dismissed
- [x] 7.4 Key dismissal by banner ID/version so edited banners reappear
- [x] 7.5 Ensure banner layout remains responsive above the header

## 8. i18n

- [x] 8.1 Add English strings for admin promotions navigation, campaign forms, bulk results, banner editor, validation, and confirmations
- [x] 8.2 Add Bulgarian strings for the same UI states

## 9. Tests

- [x] 9.1 Campaign CRUD: create, update, list, detail, validation, admin auth required
- [x] 9.2 Campaign apply: explicit IDs and filter targets update product discount fields via shared logic
- [x] 9.3 Campaign remove: matching products clear; products edited after apply are skipped with warning
- [x] 9.4 Bulk endpoint validation: rejects ambiguous target source, empty target set, over-500 target set, invalid discount payload before writes
- [x] 9.5 Bulk partial failure: one product failure returns failed result while other products commit
- [x] 9.6 Banner admin API: update localized copy, link, enabled flag, and active window validation
- [x] 9.7 Public banner API: returns active localized banner, falls back to EN, hides disabled/future/expired banners
- [x] 9.8 Frontend admin: promotions nav, campaign form validation, target selection, apply/remove result summaries, banner editor preview
- [x] 9.9 Frontend storefront: managed banner renders, dismisses, reappears when version changes, and hides when inactive
- [x] 9.10 Frontend admin products list: row multi-select, select-all-matching-filter targeting, inline bulk apply/clear, and "N updated, M failed" summary rendering

## 10. Verify

- [x] 10.1 `make test-backend`, `make test-frontend`, `make lint`
- [x] 10.2 Manual smoke: create campaign -> target products -> apply 20% -> set banner -> confirm storefront banner and discounted prices -> remove campaign discount
