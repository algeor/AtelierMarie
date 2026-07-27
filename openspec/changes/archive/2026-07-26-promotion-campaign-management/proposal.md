## Why

`promotional-discounts` adds product-level discounts, but it is still a product-by-product editing workflow. The shop also needs a simple way to run a promotion as an admin concept: choose products, apply a shared discount window, optionally show a top-of-site message, and later remove or update the promotion without editing every product manually.

The storefront already has a static announcement bar. Making that banner editable from admin closes the loop for small campaigns: the same admin area can set the discount and publish the customer-facing message.

## What Changes

- Add an admin Promotions area at `/admin/promotions` with two primary surfaces:
  - Campaigns: create/edit/apply/remove product discount campaigns.
  - Top Banner: edit the site announcement shown above the storefront header.
- Add campaign management over the existing product discount model:
  - campaign name and optional internal note
  - `discount_percent`, optional `discount_starts_at`, optional `discount_ends_at`
  - target products chosen by explicit IDs or by current admin product filters
  - apply and remove actions that reuse the same per-product discount write logic from `promotional-discounts`
- Add bulk product discount support for campaign application:
  - `PATCH /v1/admin/products/bulk-discount`
  - explicit IDs or filter descriptor target
  - per-item result list for partial failures
- Make the top announcement banner admin-managed:
  - localized message (`message_en`, `message_bg`)
  - optional localized link label and URL
  - enabled flag and optional start/end window
  - public endpoint returns only the currently active banner for the requested locale
- Update the existing frontend `AnnouncementBar` to render the managed banner instead of static i18n copy.

## Capabilities

### New Capabilities

- `admin-promotions`: admin UI for campaigns, bulk discount actions, and top banner settings.
- `promotion-admin-api`: admin APIs for campaign metadata and managed banner settings.
- `site-banner`: data model and public read behavior for the top storefront announcement banner.

### Modified Capabilities

- `product-admin-api`: adds reusable bulk product discount endpoint for campaign application/removal.
- `admin-products`: the admin products list gains inline row multi-select and a bulk "Apply/clear discount" action bar, so a campaign discount can be applied directly from the product list (in addition to the `/admin/promotions` target picker).
- `global-layout`: storefront layout renders the managed announcement banner above the header.

## Impact

- **Backend:** new promotion/banner models and service; campaign and banner admin routes; public banner route; product service bulk discount helper reused by campaigns; no checkout/cart pricing changes.
- **Frontend:** `/admin/promotions` route; sidebar nav item; campaign form/list; product target picker or filter-based target summary; inline products-list multi-select + bulk action bar; banner editor; managed `AnnouncementBar`; API/mock API/types; i18n strings.
- **Database:** campaign metadata table, campaign target table, and singleton or versioned banner table. Product pricing remains stored on `products` via the fields from `promotional-discounts`.
- **Not affected:** effective-price computation, cart totals, checkout snapshots, and customer-facing product discount rendering.

## Dependencies

- Depends on `promotional-discounts`. Campaign application writes the discount fields introduced there and must reuse the same validation and normalization behavior.
