## Why

The storefront already has a warm visual system and some motion, but scroll-based movement is uneven: some sections use static CSS classes, product/category cards do not consistently enter as they become visible, and metric values appear all at once. Adding a small, reusable scroll-triggered motion layer will make key public pages feel more crafted while keeping admin metrics easier to scan.

## What Changes

- Add reusable scroll-reveal primitives for section/card entry animations: slide up slightly, fade in, and stagger repeated items as they enter the viewport.
- Add a reusable count-up metric primitive that animates numeric values when visible, including localized number formatting and static fallback for non-numeric values.
- Apply card reveal behavior to homepage dynamic sections, category links, featured product cards, collection cards, timeline rows, product listing cards, and existing editorial/about-style card grids where appropriate.
- Apply count-up behavior to admin metric cards and analytics metric blocks where values are numeric, while preserving existing labels, currency formatting, percentages, and non-numeric health/status values.
- Respect `prefers-reduced-motion` globally: reveal targets render visible without movement, carousel rotation stays disabled where already configured, and count-up values render their final value immediately.
- Avoid backend/API changes; this is a frontend-only enhancement.

No breaking changes are intended.

## Capabilities

### New Capabilities

- `scroll-triggered-motion`: Reusable viewport-triggered reveal and metric count-up behavior for public and admin frontend surfaces.

### Modified Capabilities

- `homepage`: Homepage sections and repeated items reveal consistently as they enter the viewport.
- `product-listing`: Product cards reveal consistently as users scroll through listings.
- `about-page`: Atelier/about editorial sections, card grids, collections, and timelines reveal consistently as users scroll.
- `admin-dashboard`: Dashboard stat cards count up when visible for numeric values.
- `admin-analytics`: Analytics metric cards count up when visible for numeric, currency, and percentage values while preserving non-numeric health text.

## Impact

- Frontend components likely affected:
  - `frontend/app/[locale]/page.tsx` for homepage sections and category/card/timeline reveals.
  - `frontend/components/products/FeaturedProductsShowcase.tsx` and `frontend/components/products/ProductCard.tsx` for product card reveal behavior.
  - `frontend/components/atelier/AtelierSections.tsx` for about/editorial section reveals.
  - `frontend/components/admin/StatsCard.tsx`, `frontend/app/[locale]/admin/page.tsx`, and `frontend/app/[locale]/admin/analytics/page.tsx` for count-up metrics.
  - `frontend/app/globals.css` for shared keyframes, CSS custom properties, reduced-motion handling, and any existing `.landing-scroll-reveal` refinement.
- New frontend primitives may live under `frontend/components/motion/` or `frontend/lib/` depending on whether the implementation is component-based or hook-based.
- Tests should cover reduced-motion behavior, viewport-triggered activation, numeric formatting, and unchanged rendering for static/non-numeric values.
