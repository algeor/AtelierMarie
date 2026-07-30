# Architect Findings

Source prompt: `its-showtime-prompts/architect.md`

## Progress Snapshot

- Status: Initial storefront architecture and conversion audit recorded
- Started: 2026-07-29
- Environment: local workspace `/Users/I551270/PycharmProjects/AtelierMarie`; frontend sampled at `http://127.0.0.1:3003/en` with `NEXT_PUBLIC_USE_MOCK_API=true`
- Areas reviewed: homepage, global header/footer, product listing, product detail page, checkout summary, delivery flow, media URL handling, SEO structured-data coverage, measurement/cookie posture
- Areas not yet reviewed: full browser interaction with screenshots, completed checkout flow, payment-provider handoff, admin operations, real backend deployment topology, accessibility tooling, performance/Core Web Vitals, security beyond visible CSRF/media concerns

## Executive Assessment

- Overall maturity: solid MVP foundation, but commercially incomplete for a live shop.
- Strongest areas: bilingual routing, product catalogue/admin depth, legal pages, structured delivery data capture, product safety/compliance content, basic SEO alternates.
- Weakest areas: mobile discovery, checkout price transparency, measurement, production media strategy, scalable product discovery, product-page rich SEO.
- Biggest commercial opportunities: remove mobile navigation friction, show true delivered cost before order submission, strengthen first-viewport product desirability, add funnel analytics, expose Product/Offer structured data.
- Biggest risks: customers cannot confidently evaluate delivery cost before placing an order; mobile shoppers lack direct global navigation; future catalogue growth will break the current client-side listing model; site improvements cannot be measured.
- Top priorities: checkout shipping price transparency, mobile navigation, first-party measurement, product media/static hosting hardening, Product/Offer JSON-LD.

## Finding ARCH-001 - Mobile Header Hides Store Navigation

### Finding

The main navigation links are hidden below the `md` breakpoint, and the header does not replace them with a mobile menu. Mobile users see only the logo, language selector, auth control, and cart.

### Why It Matters

Mobile shoppers need fast access to Shop, Atelier, FAQ, and Contact. Hiding navigation raises discovery friction, especially for returning users who land on non-home pages or need trust/support information before purchase.

### Evidence / Reasoning

- `frontend/components/layout/Header.tsx:37-63` renders the navigation list as `hidden md:flex`.
- `frontend/components/layout/Header.tsx:65-102` renders only language/auth/cart controls on the right side; there is no mobile menu trigger.
- Runtime HTML from `/en` confirms the desktop links are inside a `hidden md:flex` list.

### Recommendation

Add a compact mobile navigation button that opens a focus-trapped menu with Shop, Atelier, FAQ, Contact, account/auth, and language actions. Keep Shop as the first item.

### Implementation Direction

Reuse the existing drawer/focus-trap patterns from `CartDrawer` or `ProductListingClient`. The menu should be reachable by keyboard, close on Escape/backdrop, restore focus to the trigger, and include clear active route state.

### Priority

Impact: High / Effort: Medium / Confidence: High / Area: UX, Conversion, Accessibility

### Measurement

Track mobile navigation open rate, Shop clicks from mobile menu, product-listing sessions from mobile menu, and mobile conversion rate before/after.

## Finding ARCH-001 - Mobile Header Hides Store Navigation

### Finding

The homepage first viewport is a text-and-gradient hero. It does not show candle photography, packaging, scale, materials, or any concrete product cue.

### Why It Matters

For a luxury candle shop, the product is the trust and desirability signal. A generic gradient and broad value proposition are weaker than showing the actual candle, finish, vessel, flame, packaging, or gifting context.

### Evidence / Reasoning

- `frontend/components/products/HeroSection.tsx:8-21` renders only heading, subtitle, CTA, and `bg-brand-gradient`.
- Product visuals appear later through featured cards, not in the hero itself.

### Recommendation

Replace the gradient-only hero with a product-led hero: full-bleed or strong background product image, concise copy, Shop CTA, and a visible hint of featured products below the fold.

### Implementation Direction

Use a real product image from the catalogue or a curated hero asset. Keep the text overlay readable with a restrained scrim. Avoid adding a decorative card around the hero content.

### Priority

Impact: High / Effort: Medium / Confidence: High / Area: Conversion, Trust, Brand

### Measurement

Track hero CTA clicks, scroll depth to featured products, product-card click-through from home, and conversion from homepage sessions.

## Finding ARCH-003 - Checkout Does Not Show Final Shipping Cost Before Order Submission

### Finding

Checkout collects delivery method/courier/destination, but the order summary still says shipping is not calculated and total due equals item subtotal. Backend checkout persists `shipping_cents = 0` as a placeholder.

### Why It Matters

Customers should know the delivered cost before committing. Hidden or unresolved shipping cost is a classic abandonment and trust risk. If shipping is intentionally free, the UI should say that clearly and the backend should enforce it as a policy, not as a placeholder.

### Evidence / Reasoning

- `frontend/app/[locale]/checkout/page.tsx:324-332` displays `shippingNotCalculated` and total due as `total_cents` only.
- `frontend/components/checkout/DeliverySection.tsx:12-13` says shipping price is intentionally out of scope.
- `app/services/order_service.py:311-314` sets `shipping_cents = 0` as a placeholder.
- `openspec/changes/shipping-pricing/tasks.md` shows real shipping pricing work is still unchecked.

### Recommendation

Build shipping pricing before live checkout, or explicitly make shipping free under a clear business rule. Do not launch with unresolved delivery cost language.

### Implementation Direction

Use the existing `shipping-pricing` plan: add `/v1/delivery/calculate`, calculate approximate and exact quotes, show courier comparison, persist `shipping_cents`, and server-validate/free-shipping override at checkout.

### Priority

Impact: Critical / Effort: High / Confidence: High / Area: Conversion, Trust, Operations, Architecture

### Measurement

Track checkout delivery-step completion, quote load failures, shipping quote selection, checkout abandonment after delivery selection, and final order conversion.

## Finding ARCH-004 - Product Media URL Strategy Is Fragile Across Environments

### Finding

Storefront image components convert every `/static/*` media path into `${NEXT_PUBLIC_API_URL || "http://localhost:8000"}/static/...`. In mock/dev storefront sampling on port 3003, rendered product images pointed to `http://localhost:8000/static/...`, so the storefront needs a separate backend/static server to show product media.

### Why It Matters

Product photos are the sales surface. If static serving, API host, CDN, or environment variables are misaligned, the shop silently degrades to placeholders. This is especially risky for a small operation deploying frontend/backend behind different hosts.

### Evidence / Reasoning

- `frontend/components/products/ProductImage.tsx:24-26` prefixes `/static/` URLs with `BASE_URL` from the API client.
- `frontend/lib/api-client.ts:8-9` defaults `BASE_URL` to `http://localhost:8000`.
- Runtime HTML from `/en/products` rendered image sources such as `http://localhost:8000/static/products/lavender-dreams-300ml_thumb.webp`.

### Recommendation

Introduce an explicit public media origin, for example `NEXT_PUBLIC_MEDIA_URL`, and document/deploy static serving as a first-class storefront dependency. In mock mode, either serve local placeholder assets from the frontend public folder or use stable bundled assets.

### Implementation Direction

Add `resolveMediaUrl()` in one shared frontend utility. It should handle absolute URLs, root-relative frontend assets, backend media paths, and missing images. Configure Next image remote patterns if optimization is re-enabled later.

### Priority

Impact: High / Effort: Medium / Confidence: High / Area: Trust, Conversion, Performance, Deployment

### Measurement

Track image load errors client-side, monitor 404s for `/static/products`, and include storefront media rendering in deployment smoke tests.

## Finding ARCH-005 - No Funnel Measurement Exists

### Finding

The current app intentionally has no analytics, advertising pixels, profiling, or non-essential tracking. That avoids consent complexity, but it also means the business cannot measure discovery, product consideration, cart, checkout, or retention behavior.

### Why It Matters

Commercial decisions become guesswork without funnel data. Changes to hero, navigation, pricing, delivery, checkout, and product pages cannot be evaluated responsibly.

### Evidence / Reasoning

- `frontend/messages/en.json:1004-1008` states the current app contains no analytics, advertising pixels, behavioral profiling, or newsletter marketing tracking.
- Code search found no `gtag`, `dataLayer`, or comparable analytics instrumentation in storefront code.

### Recommendation

Add a privacy-conscious first-party event layer before doing serious conversion work. Keep it minimal and consent-aware.

### Implementation Direction

Define events for `product_view`, `listing_filter`, `add_to_cart`, `cart_open`, `checkout_start`, `delivery_selected`, `shipping_quote_selected`, `order_submit`, `payment_redirect`, and `purchase_confirmed`. Start with aggregated first-party server events or a consent-compatible analytics provider. Update the cookie policy before enabling non-essential tracking.

### Priority

Impact: High / Effort: Medium / Confidence: High / Area: Data, Conversion, Operations

### Measurement

The event layer itself should be validated by event coverage tests, event delivery success rate, and dashboard parity against backend order counts.

## Finding ARCH-006 - Product Pages Lack Product/Offer Structured Data

### Finding

FAQ and Atelier pages emit JSON-LD, but product detail pages do not emit Product/Offer structured data.

### Why It Matters

Product structured data helps search engines understand price, availability, images, brand, and product identity. For a small shop, rich product eligibility and clean organic discovery are high-leverage acquisition opportunities.

### Evidence / Reasoning

- `frontend/app/[locale]/faq/page.tsx` and `frontend/app/[locale]/atelier/page.tsx` contain `application/ld+json` blocks.
- `frontend/app/[locale]/products/[id]/page.tsx:19-35` only generates basic metadata; the page body renders product UI but no JSON-LD script.

### Recommendation

Add Product JSON-LD to every active product detail page.

### Implementation Direction

Generate `Product` with `name`, `description`, `image`, `sku`/`productID`, `brand`, `offers.price`, `offers.priceCurrency`, `offers.availability`, `offers.url`, and `offers.seller`. Add `AggregateRating` only if real review data exists; do not fake ratings.

### Priority

Impact: Medium / Effort: Low / Confidence: High / Area: SEO, Acquisition

### Measurement

Validate with schema tests and Google Rich Results tooling; monitor Search Console product enhancement coverage and organic product-page clicks.

## Finding ARCH-007 - Product Listing Is Client-Side and Capped at 100 Products

### Finding

The product listing page fetches the first 100 products server-side, then performs search, filtering, sorting, and URL state updates in the client.

### Why It Matters

This is acceptable for a tiny catalogue, but it does not scale. Once the catalogue grows, filters and search can omit products beyond the first 100, filtered URLs are not true server-rendered category/search pages, and SEO value for collection pages remains weak.

### Evidence / Reasoning

- `frontend/app/[locale]/products/page.tsx:19-20` calls `getProducts(1, 100, locale)`.
- `frontend/components/products/ProductListingClient.tsx:194-227` filters and sorts the fetched array in the browser.
- `frontend/components/products/ProductListingClient.tsx:71-83` writes filter state into the URL via `history.replaceState`, but the server page still fetches the same unfiltered first 100 products.

### Recommendation

Keep the current approach only while the catalogue is small. Before catalogue growth, move filtering/search/sort/pagination into the public products API and server-render canonical collection views.

### Implementation Direction

Extend `/v1/products` with product type, category, label, query, stock, and sort parameters. Have the Next page read `searchParams`, fetch the filtered result server-side, and hydrate the client controls from the server state. Add category/type landing URLs for high-value collections.

### Priority

Impact: Medium / Effort: Medium / Confidence: High / Area: Discovery, SEO, Architecture, Performance

### Measurement

Track listing query latency, zero-result rates, filter usage, product-listing click-through, and organic traffic to collection URLs.

## Build Now

- Shipping price transparency or explicit free-shipping policy.
- Mobile navigation menu.
- First-party funnel measurement design.
- Media URL/static hosting hardening.

## Build Next

- Product/Offer JSON-LD on PDPs.
- Product-led homepage hero.
- Server-side listing filters and collection URLs.

## Test

- Hero product-image variants against the current text-only hero.
- Mobile menu label/order: `Shop` first versus category-first.
- Shipping quote copy and fallback messaging.

## Later

- Reviews/ratings, only after real customer review collection exists.
- Recommendation widgets, only after enough catalogue and interaction data exists.
- Loyalty/reorder flows, after repeat purchase volume justifies it.

## Do Not Build

- ML recommendations before basic funnel analytics and merchandising foundations.
- Marketing tracking pixels before consent policy and event taxonomy are ready.
- Enterprise search infrastructure while the catalogue remains small.

## Questions For Me

- Is shipping intended to be free, flat-rate, or courier-calculated at launch?
- What is the expected first-year catalogue size?
- Which market is primary at launch: Bulgaria-only, EU, or broader?
- Is the production deployment one origin, split frontend/API origins, or CDN-backed media?
- Which analytics/privacy posture is acceptable for the business?
