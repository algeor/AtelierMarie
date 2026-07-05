# Storefront Layout & UI Design

## Design Direction

Luxury candle brand targeting women 25–60. The aesthetic is warm, minimal, editorial — think Diptyque / Le Labo / Byredo websites. Premium feel without excessive decoration.

## Color Palette

| Token | Hex | Usage |
|-------|-----|-------|
| warm-ivory | `#FFFDF7` | Page background |
| cream | `#FFF8F0` | Card backgrounds, alternate sections |
| champagne-beige | `#F5E6D3` | Borders, subtle accents |
| dusty-pink | `#E8C4B8` | Hover states, highlights |
| soft-brown | `#8B6F5C` | Body text |
| charcoal | `#2D2D2D` | Headings |
| muted-gold | `#C4A265` | CTAs, accent elements |

## Typography

- **Headings:** Playfair Display (serif) — elegant, editorial
- **Body:** Inter (sans-serif) — clean, readable
- **Hierarchy:** h1 (2.5rem/3rem), h2 (2rem), h3 (1.5rem), body (1rem), small (0.875rem)

## Page Layout

### Global Shell

```
┌──────────────────────────────────────────────────────┐
│  Announcement Bar (optional, dismissible)             │
│  "Free shipping on orders over €50"                   │
├──────────────────────────────────────────────────────┤
│  Header: Logo | Nav Links | Search | Account | Cart  │
│  (sticky on scroll)                                   │
├──────────────────────────────────────────────────────┤
│                                                       │
│  Page Content                                         │
│                                                       │
├──────────────────────────────────────────────────────┤
│  Footer: Links | Social | Newsletter | Copyright      │
└──────────────────────────────────────────────────────┘

Cart Drawer: slides in from right (overlay)
Search: full-screen overlay with autofocus
```

### Homepage

```
┌──────────────────────────────────────────────────────┐
│  Hero Section                                         │
│  Full-width image + headline + dual CTAs              │
│  "Handcrafted candles for beautiful moments"          │
│  [Explore Collection]  [Custom Order]                 │
├──────────────────────────────────────────────────────┤
│  Featured Products (4-col grid)                       │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐                        │
│  │    │ │    │ │    │ │    │                        │
│  │img │ │img │ │img │ │img │                        │
│  │name│ │name│ │name│ │name│                        │
│  │€XX │ │€XX │ │€XX │ │€XX │                        │
│  └────┘ └────┘ └────┘ └────┘                        │
├──────────────────────────────────────────────────────┤
│  About / Story Section (optional)                     │
│  Brand narrative + image                              │
├──────────────────────────────────────────────────────┤
│  Newsletter Signup                                    │
│  "Join our list for new releases and exclusive offers"│
│  [email input] [Subscribe]                            │
└──────────────────────────────────────────────────────┘
```

### Product Listing (`/products`)

```
┌──────────────────────────────────────────────────────┐
│  Page Title: "Our Collection"                         │
├──────────────────────────────────────────────────────┤
│  Filter Bar: [All] [Dessert] [Luxury Jar] [Gift Set] │
├──────────────────────────────────────────────────────┤
│  Product Grid                                         │
│  Desktop: 4 columns                                   │
│  Tablet: 2 columns                                    │
│  Mobile: 1 column (full-width cards)                  │
│                                                       │
│  Each card:                                           │
│  ┌─────────────────┐                                  │
│  │   Product Image  │  (aspect-ratio: 4/5)            │
│  │                  │  (hover: subtle zoom 1.02)      │
│  ├─────────────────┤                                  │
│  │  Name            │                                  │
│  │  €24.00          │                                  │
│  │  [Add to Cart]   │  (appears on hover / always     │
│  └─────────────────┘   visible on mobile)             │
└──────────────────────────────────────────────────────┘
```

### Product Detail (`/products/[id]`)

```
┌──────────────────────────────────────────────────────┐
│  ┌─────────────────────┬────────────────────────┐    │
│  │                     │  Product Name            │    │
│  │   Product Image     │  €24.00                  │    │
│  │   (large, zoomable) │                          │    │
│  │                     │  Short description       │    │
│  │                     │                          │    │
│  │                     │  Quantity: [- 1 +]       │    │
│  │                     │  [Add to Cart]           │    │
│  │                     │                          │    │
│  │                     │  ▸ Description            │    │
│  │                     │  ▸ Ingredients            │    │
│  │                     │  ▸ Burn Time & Care       │    │
│  └─────────────────────┴────────────────────────┘    │
├──────────────────────────────────────────────────────┤
│  "You might also like" (4 product cards)              │
│  (from recommendations API — or popular/random)       │
└──────────────────────────────────────────────────────┘
```

### Cart Drawer (Slide-in from right)

```
┌──────────────────────────────┐
│  Your Cart (3 items)    [✕]  │
├──────────────────────────────┤
│  ┌─────┬─────────────────┐   │
│  │ img │ Product Name     │   │
│  │     │ €24.00           │   │
│  │     │ [- 1 +]  [Remove]│   │
│  └─────┴─────────────────┘   │
│  ┌─────┬─────────────────┐   │
│  │ img │ Product Name     │   │
│  │     │ €18.00           │   │
│  │     │ [- 2 +]  [Remove]│   │
│  └─────┴─────────────────┘   │
├──────────────────────────────┤
│  Subtotal:          €66.00   │
│  [Continue to Checkout]       │
│  ──────────────────────────  │
│  Free shipping over €50 ✓    │
└──────────────────────────────┘
```

### Checkout (`/checkout`)

```
┌──────────────────────────────────────────────────────┐
│  ┌────────────────────────┬────────────────────────┐ │
│  │  Contact Information   │  Order Summary          │ │
│  │  Email*                │  ┌───┬──────────┬────┐ │ │
│  │  Name*                 │  │img│ Name ×2  │€48 │ │ │
│  │                        │  │img│ Name ×1  │€18 │ │ │
│  │  Shipping Address      │  └───┴──────────┴────┘ │ │
│  │  Street*               │                         │ │
│  │  City*                 │  Subtotal:    €66.00    │ │
│  │  Postal Code*          │  Shipping:    Free      │ │
│  │  Country*              │  ─────────────────────  │ │
│  │                        │  Total:       €66.00    │ │
│  │  Notes (optional)      │                         │ │
│  │                        │                         │ │
│  │  [Place Order]         │                         │ │
│  └────────────────────────┴────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

## Responsive Breakpoints

| Breakpoint | Width | Layout Changes |
|------------|-------|---------------|
| Mobile | <768px | Single column, hamburger menu, full-width cards, bottom-sticky cart button |
| Tablet | 768–1024px | 2-column grid, compact header |
| Desktop | >1024px | 4-column grid, full navigation, hover effects |

## Interaction Patterns

- **Add to cart:** Button → brief animation (checkmark) → cart badge increments → optional cart drawer opens
- **Cart drawer:** Slides in from right, page dimmed behind overlay, close on click outside or ✕
- **Search:** Opens full-screen overlay, input autofocused, results appear as you type (300ms debounce)
- **Category filter:** Pill buttons, instant filter (no page reload), smooth transitions
- **Image hover:** Subtle scale (1.02) with 200ms ease transition
- **Touch targets:** Minimum 44×44px, 8px spacing between interactive elements

## Navigation Links

| Link | Destination |
|------|-------------|
| Home | `/` |
| Shop | `/products` |
| Shop > All Candles | `/products` |
| Shop > Dessert Candles | `/products?category=dessert` |
| Shop > Luxury Jars | `/products?category=luxury` |
| Shop > Gift Sets | `/products?category=gift` |
| Shop > Seasonal | `/products?category=seasonal` |
| Candle Care | `/candle-care` (static page) |
| FAQ | `/faq` (static page) |
| Contact | `/contact` (form page) |
| Account | `/account` (order history, or login prompt) |

## Key UI Components

| Component | Variants |
|-----------|----------|
| Button | primary (muted-gold bg), secondary (outlined), ghost (text-only) |
| Product Card | standard, featured (larger), mini (cart/recommendations) |
| Input | text, email, textarea — with label, placeholder, error state |
| Badge | cart count (muted-gold circle), category pill |
| Accordion | for product details (description, ingredients, care) |
| Skeleton | loading placeholder for images and text |

## Mobile-Specific

- Hamburger menu → slide-in drawer from left
- Cart accessible via sticky bottom bar or header icon
- Product images swipeable (touch gesture)
- "Add to cart" button always visible (no hover-only states)
- Checkout form: single column, large inputs, auto-zoom prevention
