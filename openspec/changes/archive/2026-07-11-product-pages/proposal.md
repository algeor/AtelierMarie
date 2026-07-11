## Why

The storefront needs its customer-facing pages to start selling candles. The design system (Day 2) delivered tokens and base components; now we need the actual shopping experience — a global layout shell, homepage with hero and featured products, a filterable product listing, and product detail pages with Add to Cart. All backed by mock data so frontend development proceeds independently of backend.

## What Changes

- **Global layout shell** — Header (logo, navigation, cart icon with badge), Footer (links, branding), and a dismissible announcement bar that persists dismissal in session storage
- **Homepage** (`/`) — Hero section with headline and single CTA ("Shop Collection"), featured products grid (pulls `is_featured` products from API)
- **Product listing page** (`/products`) — Responsive grid (4-col desktop, 2-col tablet, 1-col mobile), category filter pills with instant client-side filtering, product cards with hover animation
- **Product detail page** (`/products/[id]`) — Large product image, name, price, description, materials/crafting time details, quantity selector (±), Add to Cart button with confirmation feedback
- **Product image handling** — `next/image` with lazy loading and responsive srcset; CSS gradient placeholder for products missing `image_url`
- **Loading and empty states** — Skeleton placeholders during data fetch, friendly empty state for no results after filtering
- **Mobile-first responsive design** — All pages work from 320px up, touch targets ≥44px

## Capabilities

### New Capabilities
- `global-layout`: Header, footer, announcement bar, and root layout shell shared across all pages
- `product-listing`: Product grid page with category filtering, responsive columns, product cards
- `product-detail`: Individual product page with image, details, quantity selector, Add to Cart
- `homepage`: Hero section and featured products showcase

### Modified Capabilities
- `frontend-scaffold`: Adding page routes, integrating layout into existing root layout, wiring mock API calls into pages

## Impact

- **Frontend:** New pages under `frontend/app/`, new components under `frontend/components/`, layout modifications to `frontend/app/layout.tsx`
- **Dependencies:** May need `next/image` configuration in `next.config.js` for image domains; uses existing mock API (no backend changes)
- **Design system:** Consumes Button, Badge, Skeleton, Input components and all Tailwind tokens from Day 2
- **API contract:** No changes — uses existing `ProductResponse`, `ProductListResponse` types from `frontend/lib/types.ts`
