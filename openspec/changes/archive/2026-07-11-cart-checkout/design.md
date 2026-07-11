## Context

The frontend has a working product catalog (listing page, detail pages, product cards) built with Next.js 14 App Router, Tailwind CSS, and a mock/real API switcher. The backend cart and checkout APIs are fully specified and implemented. The existing `api.ts` facade already exposes `getCart`, `addToCart`, `updateCartItem`, `removeFromCart`, `createOrder`, and `getOrder` functions — they just aren't wired to any UI yet.

The header has a non-interactive cart icon placeholder with a comment indicating Day 4 will provide real functionality. Product cards are currently wrapped entirely in a `<Link>` with no add-to-cart button.

## Goals / Non-Goals

**Goals:**
- Provide a complete cart → checkout → confirmation flow in the frontend
- Use React Context for cart state with optimistic updates
- Maintain the luxury aesthetic (smooth animations, elegant typography)
- Work fully with mock API (no backend required during development)
- Mobile-first responsive design throughout

**Non-Goals:**
- Payment processing (out of scope — orders are placed directly)
- User authentication for checkout (anonymous-first per architecture)
- Shipping rate calculation (single flat rate or free shipping)
- Saved addresses or returning customer detection
- Cart persistence across sessions on the client side (backend session handles this)

## Decisions

### 1. React Context over Zustand/Redux for cart state

**Choice:** Plain React Context + useReducer

**Rationale:** The cart state is small (items array, count, total), has a single update pattern (API calls that return full cart state), and doesn't need middleware, devtools, or complex selectors. Adding a state management library for this would be over-engineering. The API always returns the full `CartResponse`, so we don't need partial updates or normalization.

**Alternative considered:** Zustand — lighter than Redux but still an extra dependency for state that fits naturally in Context.

### 2. Drawer over modal or dedicated page for cart

**Choice:** Slide-in drawer from the right with backdrop overlay

**Rationale:** Drawers keep the user on their current page (browsing flow intact), show cart contents quickly, and are the expected pattern for luxury e-commerce. A separate `/cart` page breaks browsing momentum. A modal feels more disruptive than a drawer and is less natural for a list of items.

**Alternative considered:** Dedicated `/cart` page — simpler to implement but worse UX for browse-and-add patterns.

### 3. Optimistic updates with server state as truth

**Choice:** Immediately update local UI state, then fire API call. On error, revert to previous state and show a toast/error message.

**Rationale:** Cart interactions (add, remove, quantity change) feel sluggish with a loading spinner. Optimistic updates make the UI feel instant. The backend always returns the full `CartResponse`, so on success we reconcile with server state. On error we revert.

**Alternative considered:** Loading states per action — simpler but feels slow for quantity +/- buttons.

### 4. Checkout as a single page with sections (not multi-step wizard)

**Choice:** Single `/checkout` page with contact form, shipping address, and order summary sidebar

**Rationale:** The form is short (email, name, address) — splitting across multiple steps adds unnecessary friction for a checkout that takes 30 seconds. A sidebar shows the cart contents for reassurance without navigating away.

**Alternative considered:** Multi-step wizard — better for complex checkouts with payment, but overkill here.

### 5. Animation approach — Tailwind transitions only

**Choice:** CSS transitions and Tailwind `animate-` utilities for all animations (drawer slide, checkmark, badge bounce)

**Rationale:** No runtime animation library needed. Tailwind's built-in transition utilities plus a few custom keyframes in `tailwind.config.ts` cover all needs: drawer translate-x, opacity fade, scale bounce for badge, and a brief checkmark SVG. Respects `prefers-reduced-motion` via `motion-safe:` prefix.

**Alternative considered:** Framer Motion — powerful but adds ~30KB for animations achievable with CSS.

### 6. Cart initialization — fetch on mount, not SSR

**Choice:** CartProvider fetches `GET /v1/cart` on client mount (useEffect). Cart starts empty, hydrates from API.

**Rationale:** Cart depends on the session cookie which is per-browser. Server Components can't reliably read session cookies for initial render in Next.js App Router (RSC doesn't forward browser cookies by default without explicit configuration). Client-side fetch after mount is the simplest correct approach. The brief empty-to-loaded flash is acceptable since the header badge is the only initially-visible cart element.

**Alternative considered:** Server-side cart fetch via cookies() in layout — adds complexity with cookie forwarding and breaks mock API mode.

## Risks / Trade-offs

- **[Flash of empty cart on page load]** → Mitigated by showing the badge only after first successful fetch (no "0" flash). Skeleton state not needed since only the badge is visible.
- **[Optimistic update divergence]** → Server response always replaces local state. If add-to-cart fails (stock issue), user sees item briefly appear then disappear with an error toast. Acceptable trade-off for perceived speed.
- **[No payment integration]** → Orders are placed directly. This is intentional per the architecture (payment is a future concern). The checkout form makes this clear with "Place Order" not "Pay Now".
- **[Cart drawer on mobile]** → Full-width drawer on small screens (no side peek). Close on outside tap and with explicit X button. Scroll locked on body when drawer open.
- **[Form validation client-only]** → Backend also validates, so worst case is a 422 response shown as a friendly error. Client validation provides instant feedback.
- **[Price staleness at checkout]** → If a product's price_cents changes between the last cart fetch and checkout submission, the backend charges the current price (order snapshot at transaction time). The user could see a different total on the confirmation page. Mitigated by re-fetching the cart on checkout page mount to show the freshest prices. The remaining window (mount → submit) is acceptably small for a single-developer low-traffic store.
