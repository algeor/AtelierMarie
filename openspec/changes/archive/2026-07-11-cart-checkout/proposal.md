## Why

The backend cart and checkout APIs are implemented (session-cart, orders-checkout changes), but there is no frontend UI for customers to interact with their cart or place an order. Without a cart drawer, checkout page, and order confirmation, customers cannot complete a purchase — the entire conversion funnel is broken on the frontend.

## What Changes

- **Cart Context (React Context):** Global client-side state managing cart items, total, and count. Syncs with backend API. Provides optimistic updates with rollback on error.
- **Cart drawer:** Slide-in panel from the right with overlay, showing item list with quantity controls, remove buttons, and subtotal. Opens on add-to-cart or cart icon click.
- **Cart badge in header:** Live item count badge on the existing cart icon in `Header.tsx`. Reads from CartContext.
- **Add-to-cart interaction:** Button on product cards and product detail pages triggers a brief checkmark animation, updates the badge, and optionally opens the cart drawer.
- **Checkout page:** Multi-section form with contact info (email, name), shipping address, and an order summary sidebar. Calls `POST /v1/orders` on submit.
- **Form validation:** Client-side required field and email format validation mirroring backend rules.
- **Order confirmation page:** Shows order ID, ordered items with quantities and prices, total, and a "thank you" message after successful checkout.

## Capabilities

### New Capabilities
- `cart-ui`: Cart state management (React Context), cart drawer component, add-to-cart interactions with animations, cart badge with live count
- `checkout-ui`: Checkout page with contact/shipping forms, order summary sidebar, client-side validation, order submission
- `order-confirmation-ui`: Post-checkout confirmation page displaying order details and thank-you message

### Modified Capabilities

## Impact

- **New files:** `frontend/contexts/CartContext.tsx`, `frontend/components/cart/CartDrawer.tsx`, `frontend/components/cart/CartItem.tsx`, `frontend/components/cart/CartBadge.tsx`, `frontend/app/checkout/page.tsx`, `frontend/app/orders/[id]/confirmation/page.tsx`
- **Modified files:** `frontend/components/layout/Header.tsx` (cart badge integration), `frontend/components/products/ProductCard.tsx` (add-to-cart button), `frontend/app/layout.tsx` (wrap with CartProvider)
- **Dependencies:** No new npm packages needed (React Context built-in, animations via Tailwind)
- **API integration:** Uses existing `POST /v1/cart`, `GET /v1/cart`, `PATCH /v1/cart/{product_id}`, `DELETE /v1/cart/{product_id}`, `POST /v1/orders` endpoints
- **Mock API:** Extend `mock-api.ts` with cart state management for development without backend
