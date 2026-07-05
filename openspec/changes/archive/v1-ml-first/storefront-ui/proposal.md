# Storefront UI — Proposal

## Why

Atelier Marie currently has no frontend. The brand targets women aged 25–60 who value elegant, handcrafted home décor — specifically luxury candles. Without a storefront, there is no way to convert visitors into customers. The brand's identity demands a conversion-oriented luxury experience that communicates craftsmanship, quiet elegance, and attention to detail from the first interaction.

## What Changes

A new responsive luxury storefront built with **Next.js 14 App Router + TypeScript + Tailwind CSS**. The frontend delivers a mobile-first editorial aesthetic appropriate for a boutique candle brand.

Key surfaces:

- **Announcement bar** — rotating promotional messages, session-dismissible
- **Mega-navigation** — sticky header with shop dropdown (categories), utility icons
- **Hero section** — editorial imagery with headline and dual CTAs
- **Product grid** — responsive luxury card layout with quick-add functionality
- **Product detail page (PDP)** — image gallery, variant selectors, accordions, recommendations
- **Cart drawer** — slide-in from right with quantity controls and totals
- **Search overlay** — full-screen modal with live suggestions and 300ms debounce
- **Contact form** — validated form with success confirmation
- **Newsletter signup** — email capture with success state
- **Footer** — navigation links, social icons, payment placeholders

## Capabilities

### `layout-design-system` (new)
Luxury design tokens (warm ivory, cream, champagne beige, dusty pink, soft brown, muted gold), responsive component library (Button, Card, Badge, Input, Textarea, Accordion, Typography, Container), mobile-first breakpoints (mobile <768px, tablet 768–1024px, desktop >1024px), smooth hover animations (200–300ms ease).

### `navigation-header` (new)
Sticky header with logo, navigation links, and utility icons (search, account, cart with live badge). Announcement bar with rotating messages and session-persistent dismissal. Mega-nav Shop dropdown with subcategories. Mobile hamburger drawer.

### `homepage-hero` (new)
Editorial hero section with large image placeholder, brand headline, descriptive subtext, and two call-to-action buttons (Explore collection, Custom order).

### `product-pages` (new)
Product grid (4-col desktop, 2-col tablet, 1-col mobile) with luxury card design. Product cards with quick-add/choose-options logic. Full PDP with image gallery, variant selectors, burn time/wax type metadata, quantity controls, add-to-cart/buy-now buttons, accordions (Candle Care, Shipping/Returns), and recommended products section. IntersectionObserver impression tracking.

### `cart-drawer` (new)
Slide-in cart drawer from right edge. Cart items with image, name, price, quantity +/- controls, remove button, line subtotal. Estimated total and checkout button. Empty state with "Continue shopping" link. Optimistic UI updates with server sync.

### `search-overlay` (new)
Full-screen search modal triggered by header search icon. Auto-focus input. Live product suggestions with 300ms debounce fetching GET /v1/products/search?q=. Trending products when input is empty. search_query event emission.

### `forms-newsletter` (new)
Contact form (name, email, phone optional, message) with client-side validation and inline error messages. Success confirmation on submit. Newsletter signup section with email input, persuasive copy, subscribe button, and success state. Events: newsletter_signup, contact_submit.

### `footer` (new)
Site-wide footer with navigation links (About, Candle Care, Shipping, Returns, Privacy Policy, Contact), social media icons (Instagram, TikTok), and payment method icon placeholders (Visa, Mastercard, etc.).

## Impact

- **New directory**: `frontend/` containing the entire Next.js application
- **Dependencies**: Next.js 14+, React 18+, TypeScript 5+, Tailwind CSS 3.4+, @next/font
- **API consumption**: All product/cart/search endpoints at `/v1/` prefix
- **No impact** on existing backend code — purely additive
