# Storefront UI — Tasks

## 1. Project Setup & Design System

- [ ] 1.1 Initialize Next.js 14 App Router project with TypeScript in /frontend
- [ ] 1.2 Configure Tailwind with luxury design tokens (colors, typography, spacing, border-radius, shadows)
- [ ] 1.3 Create base component library: Button (primary/secondary/ghost), Card, Badge, Input, Textarea, Accordion, Typography (H1-H4, Body, Caption), Container
- [ ] 1.4 Set up responsive breakpoints: mobile (<768px), tablet (768-1024px), desktop (>1024px)
- [ ] 1.5 Create layout wrapper component with consistent spacing and max-width

## 2. Navigation & Header

- [ ] 2.1 Implement announcement bar (rotating messages, dismissible, session-persistent dismiss)
- [ ] 2.2 Implement sticky header (logo, nav links, utility icons: search, account, cart with badge)
- [ ] 2.3 Implement Shop mega-dropdown (All candles, Dessert candles, Luxury jars, Gift sets, Seasonal, Custom orders)
- [ ] 2.4 Implement mobile hamburger menu with slide-out drawer
- [ ] 2.5 Wire cart badge to cart context (live item count)

## 3. Homepage & Hero

- [ ] 3.1 Implement hero section (editorial image placeholder, headline, subtext, two CTAs)
- [ ] 3.2 Implement featured products section (curated grid below hero)
- [ ] 3.3 Implement newsletter CTA section on homepage

## 4. Product Pages

- [ ] 4.1 Implement product grid component (4-col desktop, 2-col tablet, 1-col mobile)
- [ ] 4.2 Implement product card (image, name, price, quick-add/choose-options, wishlist heart)
- [ ] 4.3 Implement /shop page with category filtering and sort controls
- [ ] 4.4 Implement PDP: image gallery, title, price, scent/size selectors, burn time, wax type
- [ ] 4.5 Implement PDP: quantity selector, Add to cart, Buy now buttons
- [ ] 4.6 Implement PDP: Candle Care accordion, Shipping/Returns accordion
- [ ] 4.7 Implement recommended products section on PDP (consumes /v1/recommendations)
- [ ] 4.8 Implement IntersectionObserver impression tracking on product grid

## 5. Cart Drawer

- [ ] 5.1 Implement cart React context + localStorage persistence + server sync
- [ ] 5.2 Implement slide-in cart drawer (from right, overlay background)
- [ ] 5.3 Implement cart item row (image, name, price, quantity +/-, remove button)
- [ ] 5.4 Implement cart totals (subtotal, estimated total) and checkout button
- [ ] 5.5 Implement empty cart state with "Continue shopping" link

## 6. Search Overlay

- [ ] 6.1 Implement search overlay trigger (search icon in header)
- [ ] 6.2 Implement search modal/fullscreen with auto-focus input
- [ ] 6.3 Implement 300ms debounced product suggestions (GET /v1/products/search?q=)
- [ ] 6.4 Implement trending products display when input empty
- [ ] 6.5 Wire search_query event emission on search

## 7. Forms & Newsletter

- [ ] 7.1 Implement contact form (name, email, phone optional, message) with client-side validation
- [ ] 7.2 Implement form submission with success confirmation
- [ ] 7.3 Implement newsletter signup section (email input, copy, submit, success state)
- [ ] 7.4 Wire newsletter_signup and contact_submit events

## 8. Footer & Polish

- [ ] 8.1 Implement footer (About, Candle Care, Shipping, Returns, Privacy, Contact links)
- [ ] 8.2 Implement social icons (Instagram, TikTok) and payment method placeholders
- [ ] 8.3 Add smooth hover animations (200-300ms ease) to cards and buttons
- [ ] 8.4 Add loading skeletons for async content
- [ ] 8.5 Implement error boundary with user-friendly error states
- [ ] 8.6 Add gradient/pattern placeholder images for products
