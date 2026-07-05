# Storefront UI — Design

## Context

Greenfield frontend for Atelier Marie, a luxury handcrafted candle brand. The storefront must feel boutique — not like a template. Budget is zero for hosting (Vercel free tier or self-hosted). The target audience (women 25–60) expects refined aesthetics, intuitive navigation, and a seamless mobile experience.

## Goals

- Beautiful, conversion-oriented UX that communicates luxury craftsmanship
- Mobile-first responsive design across all breakpoints
- Fast page loads: React Server Components where possible for SEO and performance
- SEO-friendly product pages with proper meta tags and structured data potential
- Clean component architecture that scales as the product catalog grows

## Non-Goals

- CMS integration (content is code-managed for MVP)
- Internationalization (i18n) — single-language (English) for launch
- A/B testing framework
- Animation library — pure CSS transitions only (200–300ms ease)
- Payment processing UI (checkout redirects externally for MVP)

## Decisions

### 1. Next.js 14 App Router with React Server Components

Product pages, the homepage, and static content pages use RSC for SEO and performance. Client components are used only where interactivity is required: cart drawer, search overlay, forms, quantity selectors, and mobile menu. This minimizes client-side JavaScript while keeping the UI responsive.

**Route structure:**
```
app/
├── (shop)/
│   ├── shop/page.tsx          — Product grid with filters
│   ├── products/[slug]/page.tsx — PDP
│   └── layout.tsx
├── (account)/
│   └── ... (future auth pages)
├── (admin)/
│   └── ... (future dashboard)
├── contact/page.tsx
├── layout.tsx                  — Root layout (header + footer)
└── page.tsx                    — Homepage
```

### 2. Tailwind CSS with Custom Luxury Design Tokens

Custom color palette reflecting the brand:

| Token | Hex | Usage |
|-------|-----|-------|
| `warm-ivory` | #FEFCF3 | Page backgrounds |
| `cream` | #F5F0E8 | Card backgrounds, sections |
| `champagne-beige` | #E8DFD0 | Borders, dividers |
| `dusty-pink` | #D4A5A5 | Accent highlights, badges |
| `soft-brown` | #8B7355 | Body text, icons |
| `muted-gold` | #C9A96E | CTAs, links, hover states |

Typography:
- **Headings**: Playfair Display (serif) — conveys elegance
- **Body**: Inter (sans-serif) — clean readability
- **Sizes**: fluid scale from mobile to desktop

Spacing: generous whitespace (padding 6–12 on containers), soft rounded corners (rounded-lg to rounded-2xl), minimal borders, subtle shadows.

### 3. Route Groups for Logical Separation

- `(shop)` — product listing, product detail, category pages
- `(account)` — login, register, order history (future)
- `(admin)` — dashboard, product management (future)

Route groups keep layouts scoped without polluting URLs.

### 4. Cart State: React Context + localStorage + Server Sync

Cart state lives in a React context provider wrapping the app. On every mutation (add, remove, update quantity), the state is:
1. Updated optimistically in context (instant UI feedback)
2. Persisted to localStorage (survives refresh)
3. Synced to server via POST /v1/cart (background, non-blocking)

On page load, cart hydrates from localStorage first, then reconciles with server state.

### 5. Atomic Design Component Library

Components are organized by complexity:
- **Atoms**: Button, Badge, Input, Textarea, Typography (H1–H4, Body, Caption)
- **Molecules**: Card, Accordion, ProductCard, CartItem, SearchResult
- **Organisms**: Header, Footer, CartDrawer, SearchOverlay, ProductGrid, HeroSection

No external UI library (no shadcn, no Radix, no MUI). All components are custom-built to ensure the luxury aesthetic is pixel-perfect and bundle size stays minimal.

### 6. Image Strategy

- `next/image` for all product images with automatic optimization
- Blur placeholder data URLs for perceived performance
- For MVP (no real product photography): CSS gradient placeholders with brand colors + subtle pattern overlays
- Image hosting TBD — initially public/ folder, later CDN or cloud storage

### 7. API Communication

Custom fetch wrapper (`lib/api.ts`) that:
- Prepends `/v1/` base path to all endpoints
- Injects `X-Session-ID` header from session context
- Handles error responses with typed error objects
- Provides typed response generics: `api.get<Product[]>('/products')`
- Includes retry logic for transient failures (1 retry, 1s delay)

## Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Vercel free-tier cold starts slow initial load | Medium | Static generation for product pages where possible; consider self-hosting |
| No real product photography for MVP | High | Gradient/pattern placeholders designed to still look premium |
| Image hosting costs at scale | Low (MVP) | Start with public/ folder; migrate to R2/S3 when needed |
| Cart sync race conditions | Low | Optimistic UI with server reconciliation; last-write-wins |
| Tailwind bundle size with many custom tokens | Low | PurgeCSS (built into Tailwind) eliminates unused styles |
