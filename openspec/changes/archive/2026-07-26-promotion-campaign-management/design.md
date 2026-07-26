## Context

There are two related admin needs:

1. Set the same product discount on many products.
2. Edit the customer-facing banner at the top of the website.

The existing `AnnouncementBar` is static frontend copy, and `promotional-discounts` intentionally stores discounts per product. This change adds campaign management as an admin convenience layer over those product fields. It does not move pricing source of truth away from products.

## Goals / Non-Goals

**Goals:**
- Provide `/admin/promotions` as the single admin place for promotional campaigns and the top banner.
- Let admins create a named campaign, choose products, apply/remove the campaign discount, and see per-product results.
- Let admins edit the top storefront announcement banner without a deploy.
- Reuse the discount validation, datetime normalization, and clear behavior from `promotional-discounts`.

**Non-Goals:**
- Coupon codes, cart-level discounts, free shipping rules, stacked campaigns, automatic category rules, or customer segments.
- Moving runtime price computation to a campaign table.
- Background jobs in the first version.
- A durable audit-log subsystem.

## Decisions

### 1. Campaigns are management records, not pricing records

Campaigns store metadata and intended targets, but checkout and cart never read campaign rows. Applying a campaign writes `discount_percent`, `discount_starts_at`, and `discount_ends_at` onto target products using the existing product discount path. Runtime pricing still uses product fields and `app/services/pricing.py`.

This avoids a second pricing source of truth and keeps order snapshots unchanged.

### 2. `/admin/promotions` owns both campaigns and banner

The admin UI should add a Promotions nav item. The page contains tabs or adjacent sections:

- Campaigns: list, create/edit, apply, remove discount.
- Top Banner: edit the active banner message and schedule.

This is preferable to hiding the banner under generic settings because banner copy is campaign work, and admins need to manage the customer-facing message alongside the discount.

### 3. Campaign targeting supports IDs or filters

Campaign application accepts exactly one target source:

```
product_ids: ["lavender-dreams-300ml", ...]
```

or

```
filter: {
  q?: string,
  category?: string,
  is_active?: boolean,
  in_stock?: boolean
}
```

Explicit IDs cover hand-picked products across pages. Filters cover "all matching current filter" without making the UI fetch every page.

### 4. Synchronous campaign application with a target cap

AtelierMarie is a small SQLite-backed catalog, so campaign application is synchronous. To avoid long write locks, a single campaign application or bulk discount request is capped at 500 resolved products. If filters match more than 500 products, the request is rejected before any writes.

### 5. Best-effort per-product results after request validation

Request-level validation happens first: operation, target source, target count, and discount payload. If this fails, no products are changed.

After validation, product updates run in one transaction with per-product savepoints. One product failure rolls back only that product and returns a failed result entry. Successful products commit together. The UI can show summaries such as `12 updated, 2 failed`.

### 6. Campaign removal is conservative

Removing a campaign discount clears discount fields only for campaign target products whose current discount fields still match that campaign's last applied discount values. If a product was edited after campaign application, removal skips that product with a per-item warning instead of clearing a newer discount accidentally.

### 7. Managed top banner has its own active window

The top banner stores localized text and optional link fields:

- `message_en` required, `message_bg` optional with fallback
- `link_label_en`, `link_label_bg`, `link_url` optional
- `is_enabled`
- `starts_at`, `ends_at` optional UTC canonical timestamps
- `dismiss_version` or equivalent stable version key

The public endpoint returns the active localized banner or `null`. It must not expose future scheduled banner content. Stored timestamps follow the same normalization rules as discount windows.

### 8. Banner dismissal resets when content changes

The storefront announcement bar may remain dismissible, but dismissal must be keyed by banner ID/version rather than one static sessionStorage key. When admins change the banner message or schedule, users who dismissed an older banner can see the new one.

### 9. Audit trail deferred, structured logs required

No durable audit table is introduced. Campaign apply/remove and banner update operations should emit structured logs with admin identity when available, operation, campaign ID or banner ID, target count, success count, failure count, and duration.

## Risks / Trade-offs

- **A campaign table becomes a competing pricing source** -> campaigns are management records only; product discount fields remain runtime source of truth.
- **Ending a campaign clears newer product discounts** -> removal clears only matching last-applied campaign values and reports skipped products.
- **Large filter-based campaigns hold SQLite locks too long** -> synchronous requests are capped at 500 targets.
- **Static banner dismissal hides changed campaign messages** -> key dismissal by banner version.
- **Public endpoint leaks future campaign copy** -> public banner endpoint returns only the currently active banner.

## Migration Plan

1. Add promotion campaign and banner tables with nullable fields and no changes to existing products beyond the `promotional-discounts` columns.
2. Seed the banner table from existing static announcement copy, disabled or enabled according to the current desired default.
3. Ship admin UI and public banner read path together so the existing top banner does not disappear.

## Open Questions

None for this version. Campaigns are synchronous, capped, best-effort per product, and do not add a new pricing runtime.
