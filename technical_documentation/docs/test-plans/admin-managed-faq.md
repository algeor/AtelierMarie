# Admin Managed FAQ Manual Test Plan

OpenSpec change: `admin-managed-faq`.
Manual gate moved from the change tasks before archive.

## Preconditions

- Backend and frontend are running against a database that includes the FAQ seed migration.
- An admin user can access the admin FAQ page.
- The public product detail page has FAQ deep links enabled.

## Public FAQ Smoke

1. Open `/en/faq`.
   - The page renders the seeded English FAQ sections.
   - Published items are grouped under the expected section anchors.
   - Empty or unpublished content is not shown.

2. Open `/bg/faq`.
   - The page renders Bulgarian copy where present.
   - Any missing Bulgarian field falls back to English instead of rendering blank text.

3. Open each public anchor directly:
   - `/en/faq#candles`
   - `/en/faq#care`
   - `/en/faq#custom`
   - `/en/faq#shipping`
   - The page scrolls to the correct section below the fixed header.

## Admin Edit Smoke

1. Open the admin FAQ page.
   - All seeded sections and items are visible.
   - EN and BG fields are editable side by side.

2. Edit one FAQ item in English and Bulgarian, then save.
   - The admin page shows the saved values after refresh.
   - `/en/faq` shows the English edit.
   - `/bg/faq` shows the Bulgarian edit.

3. Hide one item.
   - The admin page shows it as hidden.
   - The public FAQ omits it.

4. Reorder items within one section.
   - The admin order persists after refresh.
   - The public order matches the admin order.

## Product Deep Link Smoke

1. Open a product detail page.
   - The candle care, custom order, shipping, or questions link appears where expected.

2. Click the product FAQ link.
   - It lands on the correct FAQ section.
   - The target section is not hidden behind the header.

## Evidence To Record

- Browser, environment, and commit tested.
- Screenshots of `/en/faq`, `/bg/faq`, and one admin edit.
- The item edited and whether the public page updated correctly.
