# Atelier Story Page Manual Test Plan

OpenSpec change: `atelier-story-page`.
Manual gate moved from the change tasks before archive.

## Preconditions

- Backend and frontend are running against a database that includes the about-page seed.
- An admin user can access the admin Atelier page.
- Product category links referenced by the page are either valid or intentionally hidden/adjusted.

## Public Page Smoke

1. Open `/en/atelier`.
   - The page renders the seeded English story sections in order.
   - Section types render correctly: hero, text/image, cards, timeline, collections, and CTA band.
   - Placeholder imagery appears where no owner image has been uploaded.

2. Open `/bg/atelier`.
   - Bulgarian copy renders where present.
   - Missing Bulgarian fields fall back to English instead of blank text.

3. Open `/en/atelier#process` and any other seeded section anchors.
   - Deep links scroll to the correct section below the header.

## Admin Content Smoke

1. Open the admin Atelier page.
   - All seeded sections are visible in the expected order.
   - Published and hidden states are clear.

2. Upload an image for one section or item.
   - Valid image upload succeeds.
   - The admin preview updates.
   - The public page renders the uploaded image.

3. Edit one EN field and one BG field, then save.
   - The admin page keeps the saved values after refresh.
   - `/en/atelier` and `/bg/atelier` show the expected localized content.

4. Reorder one item group where supported.
   - The new order persists after refresh.
   - The public page follows the same order.

5. Toggle one non-critical item or section hidden.
   - The public page omits it.
   - Re-enable it and confirm it returns.

## Owner Review

1. Ask the owner to review all Bulgarian copy.
   - Record whether edits are needed.
   - Clear any uncertain BG field if English fallback is preferred for launch.

2. Ask the owner to review uploaded images.
   - Confirm each image is approved for public use.
   - Confirm placeholders are acceptable if any section remains image-free.

## Evidence To Record

- Browser, environment, and commit tested.
- Screenshots of EN page, BG page, admin image upload, and one edited section.
- Owner approval notes for BG copy and images.
