## Context

AtelierMarie is a luxury candle e-commerce platform. Day 2 delivered the design system (Tailwind tokens, base components: Button, Badge, Skeleton, Input, `cn()` utility). The frontend has typed API contracts (`frontend/lib/types.ts`) and a mock API with 4 sample products. The backend is being built in parallel — frontend uses mock data until Day 7 integration.

The Next.js 14 app exists with App Router structure but has no pages beyond the root placeholder. We need the full shopping experience: layout shell, homepage, product listing, and product detail pages.

**Current state:**
- Design system tokens and base components ready (Playfair Display headings, Inter body, muted-gold CTAs, warm-ivory backgrounds)
- Mock API returns `ProductResponse[]` with 4 products across categories (Floral, Woody, Fresh, Gourmand)
- `next/image` available; `next.config.js` exists but needs image domain config
- No page components, no layout components, no product-specific components

## Goals / Non-Goals

**Goals:**
- Deliver a fully browsable storefront experience using mock data
- Global layout shell reusable across all current and future pages
- Responsive product browsing from mobile (320px) to desktop (1440px+)
- Image handling that degrades gracefully when `image_url` is null
- Category filtering without page reloads
- Accessible (WCAG AA), keyboard-navigable, reduced-motion safe

**Non-Goals:**
- Cart drawer/panel (Day 4 scope — Add to Cart button wires up later)
- Search functionality (future scope)
- User authentication UI (Day 5)
- Real API integration (Day 7)
- Animations beyond hover states (keep it simple for Day 3)
- SEO metadata optimization (can layer on later)
- "You might also like" recommendations section (depends on ML layer, future scope)

## Decisions

### 1. Server Components by default, Client Components only for interactivity

**Choice:** Page route files (`app/page.tsx`, `app/products/page.tsx`, `app/products/[id]/page.tsx`) are Server Components that fetch data at render time. Interactive portions are composed as Client Component children:
- `app/products/page.tsx` (Server) → fetches products → passes as props to `ProductListingClient` (Client, `'use client'`) which manages category filter state
- `app/products/[id]/page.tsx` (Server) → fetches product → passes to Client Components for QuantitySelector and Add to Cart button
- Announcement bar is a Client Component (sessionStorage)

Loading states are implemented via Next.js `loading.tsx` route-level files (shown during client-side navigation transitions, NOT on initial direct page load). On initial server render, the page renders immediately with data.

**Rationale:** Server Components are the Next.js 14 default; they produce less client JS. The mock API is async (returns Promises), which Server Components handle natively with `await`. When we switch to the real API (Day 7), server-side fetch with `cache: 'no-store'` will work identically. All API fetch calls must use `cache: 'no-store'` (or `next: { revalidate: 30 }`) to ensure fresh product/stock data — the Next.js default of `cache: 'force-cache'` would serve stale inventory.

**Alternative considered:** Full client-side SPA approach with `useEffect` fetching — rejected because it adds unnecessary loading spinners when data is available at render time, and doesn't match Next.js App Router patterns.

### 2. Component composition over page-level monoliths

**Choice:** Build small, focused components (`ProductCard`, `ProductGrid`, `CategoryFilter`, `QuantitySelector`, `AnnouncementBar`, `Header`, `Footer`, `HeroSection`) and compose them in page files.

**Rationale:** Reusability across pages (ProductCard used on homepage featured grid AND listing page). Easier to test, style, and modify independently. Matches the existing design-system component pattern (Button, Badge, etc.).

### 3. CSS gradient placeholder for missing images

**Choice:** When `image_url` is null, render a styled `<div>` with a brand-palette gradient (warm-ivory → dusty-pink, fixed 135deg direction) and the product name centered in Playfair Display.

**Rationale:** Avoids broken image icons. Maintains visual consistency in the grid. Uses existing brand colors. The fixed gradient direction keeps implementation simple and consistent across all placeholder instances.

**Alternative considered:** A single static placeholder image — rejected because it looks repetitive when multiple products lack images.

### 4. Category filtering as client-side pill buttons

**Choice:** Products loaded with `getProducts(1, 100)` on initial render; category pills filter in-memory with React state. "All" pill shown first, then unique categories from the product list.

**Rationale:** With <100 products in the near term, loading all with a single paginated call (limit=100) is fine. Instant filtering feels snappy. No API call needed per filter change. Categories are derived from data (not hardcoded) so they stay in sync.

**Pagination note:** The `getProducts()` API uses offset pagination (default limit=20, max=100). The product listing page MUST call `getProducts(1, 100)` explicitly — the default limit of 20 would break client-side filtering for catalogs with >20 products. The homepage similarly calls `getProducts(1, 100)` before filtering for `is_featured`.

**Scaling plan:** When the catalog exceeds 100 products, migrate to server-side filtering via `?category=X` query param (supported by the backend product-public-api spec). At that point, category pills trigger a new server fetch instead of in-memory filtering.

**Alternative considered:** Server-side filtering with query params (`/products?category=Floral`) — a valid future optimization but unnecessary overhead for <100 products and adds complexity when using mock data.

### 5. Announcement bar state in sessionStorage

**Choice:** When dismissed, write `announcement_dismissed=true` to `sessionStorage`. Check on mount; if dismissed, don't render.

**Rationale:** Session-scoped (resets on new browser session, matching "session-persistent" requirement). No server state needed. No layout shift because the bar renders conditionally before hydration via a Client Component.

### 6. next/image with explicit sizes

**Choice:** Use `next/image` with `sizes` prop matching the responsive grid columns. For product listing: `sizes="(max-width: 768px) 100vw, (max-width: 1024px) 50vw, 25vw"`. For product detail: `sizes="(max-width: 1024px) 100vw, 50vw"` with `priority` loading (product images are always the primary visual content). Use `placeholder="empty"` since product images are served remotely (not statically imported), meaning Next.js cannot auto-generate blur data.

**Rationale:** Proper `sizes` ensures the browser picks the right srcset resolution. Avoids downloading 1200px images on mobile. Product detail images use `priority` because they are the main content regardless of viewport. Hero uses a gradient background (no external image dependency for Day 3).

### 7. File structure under `frontend/components/`

```
frontend/components/
├── ui/           # Design system atoms (Button, Badge, Skeleton, Input — from Day 2)
├── layout/       # Global shell (Header, Footer, AnnouncementBar)
└── products/     # Product-specific (ProductCard, ProductGrid, CategoryFilter, QuantitySelector, ProductImage)
```

**Rationale:** Clean separation between reusable design-system pieces, structural layout, and domain-specific product components. `layout/` components are imported in `app/layout.tsx`; `products/` components are imported in product pages.

### 8. Full-width hero layout pattern

**Choice:** `app/layout.tsx` does NOT wrap children in `max-w-7xl`. Instead, each page controls its own width. Standard pages wrap their content in `<div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">`. The homepage renders HeroSection full-width (no container), then wraps the featured products section in the standard container.

**Rationale:** This avoids negative margin hacks and Tailwind arbitrary values. Each page explicitly controls which sections are full-width vs. contained. The layout provides only Header + main + Footer without constraining the main content width.

**Alternative considered:** Negative margins (`-mx-4 md:-mx-8`) to break out of a parent container — rejected because it's fragile and requires matching the parent's exact padding values.

## Risks / Trade-offs

**[API contract for inactive products]** → The real backend API returns 404 for inactive products on `GET /v1/products/{id}`. The mock API matches this behavior (filters by `is_active`). The product detail page should still defensively check `is_active` if received — call `notFound()` if false. This makes the code portable across mock/real without dead code.

**[Layout shift from announcement bar]** → The AnnouncementBar is a Client Component that uses `useState(false)` for initial dismissed state, then checks sessionStorage in `useEffect`. This ensures SSR and initial client render are identical (bar visible), avoiding hydration mismatch. On the next render tick after mount, the bar hides if previously dismissed. Acceptable tradeoff: one-frame flash for returning users who dismissed the bar.

**[Mock data divergence from real API]** → Mitigated by using the exact same TypeScript interfaces for mock and real. The `api.ts` switch layer ensures shape compatibility. The mock `getProduct()` filters inactive products to match real API behavior. Day 7 integration will validate.

**[Image optimization disabled in dev]** → next/image optimizes in production only; dev shows unoptimized. This is expected Next.js behavior. Not a risk for the spec.

**[Image load failures]** → If a product's `image_url` returns 404 or times out, ProductImage uses `onError` prop to fall back to the gradient placeholder. This reuses the same placeholder as null `image_url` — no broken image icons.

**[Category list may be empty or single-item]** → If all products have `category: null`, only the "All" pill renders — the entire filter section is hidden (fewer than 2 categories means no filtering is useful). If all products share one non-null category, "All" + that category renders but filtering provides no value; acceptable.

**[Category pill overflow]** → On desktop, pills wrap to multiple rows. On mobile (<768px), use horizontal scroll container with `overflow-x-auto`. If the catalog grows to 20+ categories, consider a dropdown (not in Day 3 scope).

**[Product name overflow in cards]** → Product names use `line-clamp-2` for consistent card height in the grid. Long names show ellipsis on the second line.

**[Quantity selector without cart backend]** → The selector manages local state only. The "Add to Cart" button will be wired to the cart API in Day 4. For Day 3, clicking it shows a console log + brief visual confirmation (button text changes to "Added ✓" for 1.5s) so the UX feels complete even without backend. When `stock === 0`, the QuantitySelector is NOT rendered — only the disabled "Out of Stock" button appears.

**[Tailwind arbitrary values]** → The spec uses 135deg gradient and 200ms transition. The 200ms transition is available as Tailwind's `duration-200`. The 135deg gradient requires a custom utility — add to `tailwind.config.ts` as a custom background-image, or use an inline style. This is acceptable for design-spec-driven values.

**[Cart icon (Day 3)]** → The cart icon in the header links to `/cart` which does not exist yet. For Day 3, the cart icon is rendered as a non-interactive element (`aria-disabled="true"`, `cursor-default`) with no link. Day 4 will add the link and CartContext.

**[Homepage with no featured products]** → If no products have `is_featured: true`, the featured section is not rendered. The homepage shows only the hero with "Shop Collection" CTA. This is acceptable — the CTA directs users to the full catalog. No fallback section needed for Day 3.
