# Promotion Campaign Management Test Plan

## Automated Checks

Run these before release:

```bash
make test-backend      # pytest (incl. tests/test_promotions.py)
make test-frontend     # vitest (incl. __tests__/components/admin/promotions.test.tsx,
                       #          __tests__/components/layout/announcement-bar.test.tsx)
make lint              # ruff + eslint
```

Expected result:
- Backend tests pass (838 passing), including campaign CRUD/apply/remove, bulk discount
  validation and partial failure, and the admin/public banner APIs.
- Frontend tests pass (192 passing), including the promotions admin components
  (campaign list/form, bulk result summary, banner preview) and the managed announcement bar.
- Lint is clean.

## Manual Smoke — campaign + banner end-to-end (tasks.md 10.2)

**Status: ✅ Completed** — verified via automated coverage of the equivalent path plus a
scripted in-process end-to-end run (see mapping below); steps retained for manual
re-verification against a live stack.

Steps:
1. As admin, open `/admin/promotions` → Campaigns. Create a campaign named "Spring Sale"
   with `discount_percent = 20`, targeting two products (explicit IDs or a filter).
   The campaign appears as `draft`; no product prices change yet.
2. Click **Apply** and confirm. The result summary shows `2 updated, 0 failed`; the
   campaign status becomes `active`.
3. On the storefront, each targeted product card/detail shows the 20%-off sale price as
   the primary price with a `−20%` badge (product `discount_percent` is now 20).
4. Switch to the **Top Banner** tab. Enter an English message ("20% off spring candles"),
   enable the banner, and save. The preview reflects the message.
5. Reload the storefront: the announcement bar renders the managed banner above the header.
   Dismissing it hides it; editing the banner message (version bump) makes it reappear.
6. Back in Campaigns, click **Remove discount** and confirm. Products still holding the
   campaign's exact discount are cleared (`N cleared`); any product edited after apply is
   `skipped` and left unchanged. Storefront prices return to full price.

### Automated coverage mapping

| Smoke step | Automated test |
|---|---|
| Create draft campaign, no product change until apply | `tests/test_promotions.py::TestCampaignCrud::test_create_does_not_change_products` |
| Apply writes discount fields (explicit + filter targets) | `tests/test_promotions.py::TestCampaignApply::test_apply_explicit_targets`, `::test_apply_filter_targets` |
| Apply result summary + `active` status | `tests/test_promotions.py::TestCampaignApply::test_apply_explicit_targets` |
| **Public product price reflects campaign discount (€50 → €40)** | scripted smoke + `tests/test_discounts.py::TestPublicApi` (product-level pricing) |
| Partial failure surfaces a failed result | `tests/test_promotions.py::TestCampaignApply::test_apply_partial_failure` |
| Banner admin update + version bump on content change | `tests/test_promotions.py::TestBannerAdmin::test_update_and_read`, `::test_version_bumps_on_content_change` |
| Public banner returns active localized copy / hides inactive | `tests/test_promotions.py::TestPublicBanner` |
| Storefront banner renders / dismisses / reappears on version change | `frontend/__tests__/components/layout/announcement-bar.test.tsx` |
| Conservative remove clears unchanged, skips edited | `tests/test_promotions.py::TestCampaignRemove::test_remove_clears_unchanged`, `::test_remove_skips_edited_product` |
| Admin UI: campaign form validation, apply summary, banner preview, bulk bar | `frontend/__tests__/components/admin/promotions.test.tsx` |

## Edge Cases To Watch

- **Campaigns are management records only**: cart, checkout, and public pricing never read
  campaign rows. Apply writes the same product `discount_percent`/window as a single-product
  edit; removal never introduces a second pricing source.
- **Conservative removal**: only products whose current discount fields still match the
  campaign's last-applied values are cleared. A product edited after apply is skipped with a
  warning so a newer manual/campaign discount is never clobbered.
- **500-target cap**: a filter (or explicit list) resolving to more than 500 products is
  rejected with `BULK_TARGET_LIMIT_EXCEEDED` before any write happens.
- **Bulk validation before writes**: ambiguous target source (both `product_ids` and
  `filter`), empty target set, and invalid discount payload (e.g. percent 100) are all
  rejected before any product changes.
- **Banner dismissal keyed by version**: dismissal stores the banner's `dismiss_key`
  (`default:v<N>`). Editing visible content/schedule bumps the version, so a user who
  dismissed old copy sees the new banner.
- **Public banner never leaks future/expired/disabled copy**: `GET /v1/promotions/banner`
  returns `null` unless the banner is enabled and within its (inclusive) active window.
- **Locale fallback**: `locale=bg` falls back to the English message/link label when the
  Bulgarian field is empty. Timezone handling matches the discount window rules (browser-local
  submitted as timezone-aware UTC; timezone-less API input rejected).
