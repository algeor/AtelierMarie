## 1. Layout Components

- [x] 1.1 Create `frontend/components/layout/AnnouncementBar.tsx` — Client Component (`'use client'`). Uses `useState(false)` for dismissed state + `useEffect` to check sessionStorage (avoids hydration mismatch). Displays "Free shipping on orders over €50 ✨", muted-gold background, 44px touch target on dismiss. When dismissed via `useEffect`, one-frame flash is acceptable.
- [x] 1.2 Create `frontend/components/layout/Header.tsx` — Sticky header with "Atelier Marie" logo (Playfair Display), nav links (Home, Shop) visible on tablet+/hidden on mobile, cart icon with Badge (hardcoded 0 for Day 3; CartContext added in Day 4). Cart icon is non-interactive for Day 3 (`aria-disabled="true"`, no link).
- [x] 1.3 Create `frontend/components/layout/Footer.tsx` — Navigation links (Home /, Shop /products, About #, Contact #), "Handcrafted with love" text, dynamic copyright year
- [x] 1.4 Update `frontend/app/layout.tsx` — Configure next/font (Playfair Display + Inter via CSS variables `--font-playfair`, `--font-inter`), apply to `<html className={...}>`, set body `className="font-sans"`. Wire AnnouncementBar + Header + `<main>` (NO max-w-7xl — pages control their own width) + Footer. Update `tailwind.config.ts` to extend `fontFamily` with CSS variable references.

## 2. Product Components

- [x] 2.1 Create `frontend/lib/utils.ts` — Shared `formatPrice(cents: number): string` utility that formats price_cents as "€XX.XX" (euro prefix, period decimal, always two decimal places). Validates input: throws on negative/NaN/Infinity. `formatPrice(0)` returns "€0.00". All price displays import this.
- [x] 2.2 Create `frontend/components/products/ProductImage.tsx` — Wrapper around next/image that renders gradient placeholder (warm-ivory → dusty-pink, 135deg, with product name centered) when `image_url` is null OR when image fails to load (use `onError` prop to fall back to gradient); accepts sizes and priority props. Placeholder div uses `role="img"` and `aria-label={product.name}`.
- [x] 2.3 Create `frontend/components/products/ProductCard.tsx` — Entire card wrapped in `<Link href={/products/[id]}>`. Contains ProductImage (aspect-4/5), product name (`line-clamp-2` for overflow), price via `formatPrice()`. Hover `motion-safe:hover:scale-102` transition (respects prefers-reduced-motion via Tailwind `motion-safe:` prefix).
- [x] 2.4 Create `frontend/components/products/ProductGrid.tsx` — Responsive grid container (grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6), accepts children or product array
- [x] 2.5 Create `frontend/components/products/CategoryFilter.tsx` — Client Component with pill buttons (`<button aria-pressed>`) in a `role="group"` with `aria-label="Filter by category"`. Derived from non-null product categories, "All" first, active state (muted-gold bg). Includes visually-hidden `<div aria-live="polite" role="status">` that announces result count on filter change (e.g., "Showing 3 products in Floral"). If fewer than 2 total categories (counting "All"), hide the entire filter section. On mobile (<768px), pills container uses `overflow-x-auto` for horizontal scroll.
- [x] 2.6 Create `frontend/components/products/QuantitySelector.tsx` — Client Component with −/+ buttons (44px touch), min 1, max `Math.min(10, stock)`, disabled states, aria-label announcing current quantity for screen readers. **Not rendered when stock === 0** — parent component conditionally renders QuantitySelector only when stock > 0.

## 3. Homepage

- [x] 3.1 Create `frontend/components/products/HeroSection.tsx` — Full-width section (breaks out of max-w-7xl container) with gradient background (warm-ivory → dusty-pink), headline (Playfair), subtitle (Inter), "Shop Collection" CTA button linking to /products
- [x] 3.2 Create `frontend/app/page.tsx` — Server Component. Homepage with HeroSection (full-width, no container) + `<div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">` wrapping "Featured" heading + ProductGrid of featured products (fetches via `getProducts(1, 100)` then filters `.products.filter(p => p.is_featured)`). If no featured products, section is not rendered. Export metadata: "Atelier Marie | Luxury Handcrafted Candles"
- [x] 3.3 Create `frontend/app/loading.tsx` — Skeleton placeholders for hero area and featured products grid (shown during route transitions)

## 4. Product Listing Page

- [x] 4.1 Create `frontend/app/products/page.tsx` — Server Component. Fetches products via `getProducts(1, 100)`, passes to `ProductListingClient`. Exports metadata: "Our Collection | Atelier Marie"
- [x] 4.2 Create `frontend/components/products/ProductListingClient.tsx` — Client Component (`'use client'`). Receives products as props. Manages category filter state. Renders "Our Collection" heading, CategoryFilter, ProductGrid. Shows empty state message for no filter results.
- [x] 4.3 Create `frontend/app/products/loading.tsx` — Skeleton grid matching product card layout (shown during route transitions)
- [x] 4.4 Create `frontend/app/products/error.tsx` — Client Component (`'use client'`) error boundary. Receives `{ error, reset }` props. Shows friendly message ("Unable to load products. Please try again later.") and retry button that calls `reset()` (re-renders page, re-triggering fetch). Matches brand aesthetic.

## 5. Product Detail Page

- [x] 5.1 Create `frontend/app/products/[id]/page.tsx` — Server Component. Two-column desktop / single-column mobile layout. Fetches product via `getProduct(params.id)`. If product is null/not found or `is_active === false`, call `notFound()` from `next/navigation`. Renders large ProductImage (with priority), product name + price + category Badge + description + materials/crafting time when non-null. Export async `generateMetadata()` function (NOT static export): `{ title: "${product.name} | Atelier Marie" }`. Wrap content in `<div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">`.
- [x] 5.2 Integrate QuantitySelector + Add to Cart button — Only render QuantitySelector when `stock > 0`. Primary button (muted-gold), "Added ✓" confirmation for 1.5s on click (button disabled during confirmation, no double-click), disabled "Out of Stock" when stock=0, passes quantity to action. `aria-live="polite"` region announces confirmation to screen readers. Day 3 action: `console.log(\`[stub] Add to cart: ${productId} x${quantity}\`)` + visual confirmation.
- [x] 5.3 Create `frontend/app/products/[id]/loading.tsx` — Skeleton matching two-column layout (image area + text blocks for name, price, description)
- [x] 5.4 Create `frontend/app/products/[id]/not-found.tsx` — Friendly "Product not found" message with Link back to /products. Can be a Server Component. Displayed when page.tsx calls `notFound()` for invalid ID or inactive product.

## 6. Configuration & Integration

- [x] 6.1 Update `frontend/next.config.js` — For Day 3 (mock data with relative paths like `/static/products/...`), no `images.remotePatterns` is needed (relative paths served from `public/`). Add a comment noting Day 7 will need `remotePatterns` for the FastAPI backend domain.
- [x] 6.2 Verify mock API integration — Ensure all pages import from `lib/api.ts`, responses typed correctly, `NEXT_PUBLIC_USE_MOCK_API=true` works end-to-end
- [x] 6.3 Add component barrel exports — Create `frontend/components/layout/index.ts` and `frontend/components/products/index.ts` for clean imports

## 7. Accessibility & Polish

- [x] 7.1 Verify keyboard navigation — All interactive elements (nav links, filter pills, quantity buttons, Add to Cart) are focusable with visible focus rings (soft-brown 2px)
- [x] 7.2 Add aria-labels and semantic HTML — Landmark regions (nav, main, footer), aria-labels on icon buttons (cart icon: "Shopping cart"), proper heading hierarchy (h1 per page), aria-live regions for dynamic content
- [x] 7.3 Test responsive breakpoints — Verify 1-col (<768px), 2-col (768–1024px), 4-col (>1024px) grid behavior; mobile header (logo + cart only), tablet/desktop header (full nav)
- [x] 7.4 Verify reduced-motion support — Hover animations and transitions respect `prefers-reduced-motion: reduce`
