## 1. Shared Motion Primitives

- [x] 1.1 Add a reusable viewport visibility hook that uses `IntersectionObserver`, activates once, disconnects after reveal, and falls back to visible when unsupported.
- [x] 1.2 Add reduced-motion detection for client-side count-up behavior so final values render immediately when motion is reduced.
- [x] 1.3 Add a reusable `ScrollReveal` component or equivalent class/data-state contract for fade/slide entrance animation with optional stagger index.
- [x] 1.4 Add a reusable `CountUpMetric` component that accepts numeric values plus formatter/prefix/suffix support and preserves static text fallback.
- [x] 1.5 Add global CSS for reveal hidden/visible states, bounded stagger delays, transition timing, and reduced-motion final-state overrides.

## 2. Public Page Integration

- [x] 2.1 Update homepage section headers and repeated `cards`, `category_links`, `timeline`, `collections`, and `text_image` content in `frontend/app/[locale]/page.tsx` to use the shared reveal primitive.
- [x] 2.2 Update `frontend/components/products/FeaturedProductsShowcase.tsx` so featured product cards use the shared reveal behavior while preserving carousel, swipe, links, cart actions, and product analytics.
- [x] 2.3 Update `frontend/components/products/ProductCard.tsx` so listing cards reveal on scroll while preserving save, add-to-cart, navigation, and impression tracking.
- [x] 2.4 Update `frontend/components/atelier/AtelierSections.tsx` so editorial image/text blocks, card grids, collection cards, and timeline rows reveal consistently.

## 3. Admin Metric Integration

- [x] 3.1 Update `frontend/components/admin/StatsCard.tsx` to support numeric count-up values while keeping the existing string `value` API for static values.
- [x] 3.2 Update `frontend/app/[locale]/admin/page.tsx` to pass numeric admin dashboard stats into the count-up path and leave loading skeleton behavior unchanged.
- [x] 3.3 Update `frontend/app/[locale]/admin/analytics/page.tsx` so numeric, percentage, and currency metrics count up with identical final formatting while health/status text remains static.

## 4. Verification

- [x] 4.1 Add or update component tests for scroll reveal activation, unsupported `IntersectionObserver` fallback, and reduced-motion fallback.
- [x] 4.2 Add or update component tests for count-up formatting of integers, currency, percentages, and non-numeric static values.
- [x] 4.3 Run the relevant frontend test suite and type/lint checks for touched files.
- [x] 4.4 Manually verify homepage, product listing, atelier/about, admin dashboard, and admin analytics behavior in desktop and mobile viewports.
