## 1. Cart Context & State Management

- [x] 1.1 Create `frontend/contexts/CartContext.tsx` with CartProvider, useCart hook, and reducer (items, total_cents, item_count, isLoading, error)
- [x] 1.2 Implement cart hydration on mount (fetch `GET /v1/cart` via api.ts, populate state)
- [x] 1.3 Implement `addToCart(productId, quantity?)` with optimistic update and rollback on error
- [x] 1.4 Implement `updateQuantity(productId, quantity)` with optimistic update and rollback
- [x] 1.5 Implement `removeItem(productId)` with optimistic update and rollback
- [x] 1.6 Add `openDrawer` / `closeDrawer` state and functions to context
- [x] 1.7 Add `refreshCart()` function that re-fetches `GET /v1/cart` to sync local state with server
- [x] 1.8 Wrap app in CartProvider (`frontend/app/layout.tsx`)
- [x] 1.9 Add inline error display: CartContext exposes `error` string that auto-clears after 5s; consuming components render it as a dismissible inline banner

## 2. Cart Drawer

- [x] 2.1 Create `frontend/components/cart/CartDrawer.tsx` — slide-in panel with backdrop, close on X / backdrop click / Escape key, focus trap (Tab cycles within drawer while open)
- [x] 2.2 Create `frontend/components/cart/CartItem.tsx` — single item row with name, price, quantity +/- buttons, remove button
- [x] 2.3 Add empty cart state ("Your cart is empty" + "Continue Shopping" link)
- [x] 2.4 Add subtotal display and "Proceed to Checkout" link at drawer bottom
- [x] 2.5 Implement body scroll lock when drawer is open
- [x] 2.6 Add slide-in/out animation with `motion-safe:` prefix (CSS transition on translate-x)

## 3. Cart Badge & Header Integration

- [x] 3.1 Create `frontend/components/cart/CartBadge.tsx` — badge showing item_count, hidden when 0, bounce animation on change
- [x] 3.2 Update `frontend/components/layout/Header.tsx` — replace static cart div with interactive button + CartBadge, wire to `openDrawer`
- [x] 3.3 Mount CartDrawer in layout (inside CartProvider)

## 4. Add-to-Cart Button

- [x] 4.1 Create `frontend/components/cart/AddToCartButton.tsx` — button with loading, success (checkmark), and disabled (out of stock) states
- [x] 4.2 Update `frontend/components/products/ProductCard.tsx` — add AddToCartButton below price (stop card being entirely a Link wrapper for the button area)
- [x] 4.3 Add AddToCartButton to product detail page (`frontend/app/products/[id]/page.tsx`)
- [x] 4.4 Add checkmark SVG animation keyframe to `tailwind.config.ts`

## 5. Checkout Page

- [x] 5.1 Create `frontend/app/checkout/page.tsx` — client component with two-column layout (form + sidebar), loading skeleton while cart fetches
- [x] 5.2 Re-fetch cart on mount for freshest prices, then implement empty-cart redirect (if cart empty after fetch, redirect to `/products`)
- [x] 5.3 Build contact form section (email required, name optional) with inline validation on blur
- [x] 5.4 Build shipping address section (optional textarea)
- [x] 5.5 Build order summary sidebar (item list from CartContext, subtotal, "Place Order" button)
- [x] 5.6 Implement form submission: validate → disable button → call `createOrder()` → redirect to confirmation or show error
- [x] 5.7 Handle error states (409 stock conflict, network errors) with user-friendly messages, preserve form input
- [x] 5.8 Add accessibility: aria-required, aria-live error region, focus management on validation failure

## 6. Order Confirmation Page

- [x] 6.1 Create `frontend/app/orders/[id]/confirmation/page.tsx` — fetch order via `getOrder(id)`, display details with loading skeleton
- [x] 6.2 Display order ID, item list (name, qty, price from snapshot), total, and thank-you heading
- [x] 6.3 Show "Continue Shopping" link and order status note
- [x] 6.4 Handle order-not-found / access-denied (friendly message + link to shop)
- [x] 6.5 Re-fetch cart on mount (backend already cleared it during checkout; re-fetch syncs local state without destructively clearing a legitimate cart on revisit)

## 7. Mock API Enhancements

- [x] 7.1 Add in-memory cart state to `frontend/lib/mock-api.ts` (add, update, remove, get with real state tracking)
- [x] 7.2 Add mock `createOrder` that returns a realistic OrderResponse and clears mock cart state
- [x] 7.3 Add mock `getOrder` that returns the last created order for confirmation page testing

## 8. Tests

- [x] 8.1 Create `frontend/__tests__/contexts/CartContext.test.tsx` — test hydration, addToCart, updateQuantity, removeItem, optimistic rollback on error
- [x] 8.2 Create `frontend/__tests__/components/cart/CartDrawer.test.tsx` — test open/close, empty state, Escape key, backdrop click
- [x] 8.3 Create `frontend/__tests__/components/cart/AddToCartButton.test.tsx` — test loading state, success checkmark, out-of-stock disabled
- [x] 8.4 Create `frontend/__tests__/app/checkout.test.tsx` — test form validation (email required, invalid format), empty-cart redirect, submission success/failure
- [x] 8.5 Create `frontend/__tests__/app/order-confirmation.test.tsx` — test order display, not-found handling, cart refresh on mount
