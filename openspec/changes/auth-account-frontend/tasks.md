## 1. AuthContext Foundation

- [ ] 1.1 Create `frontend/contexts/AuthContext.tsx` — implement AuthState interface (user, isLoading, isAuthenticated, error: string | null), AuthAction union type with actions: HYDRATE_START, HYDRATE_SUCCESS, HYDRATE_FAILURE, LOGIN_COMPLETE, LOGOUT_START, LOGOUT_SUCCESS, LOGOUT_FAILURE, SESSION_REFRESH, CLEAR_ERROR. Implement authReducer, AuthProvider component with useReducer. Error state auto-clears after 5s timeout (matching CartContext pattern).
- [ ] 1.2 Implement hydration in AuthProvider — useEffect on mount calls `getCurrentUser()`, dispatches HYDRATE_SUCCESS or HYDRATE_FAILURE, sets isLoading=false. Must use `let cancelled = false` cleanup pattern (return cleanup function that sets `cancelled = true`) to prevent stale dispatches on unmount/re-mount in StrictMode.
- [ ] 1.3 Implement `login()` function in AuthContext — validates redirect path starts with `/` and does NOT start with `//` (rejects absolute URLs and protocol-relative URLs; falls back to `/` if invalid). Stores validated path in sessionStorage (`auth_redirect_to`). Navigates to `{API_URL}/v1/auth/login?redirect_to={currentPath}` using `window.location.href` (full-page navigation, not router.push — this exits the SPA to the backend OAuth flow).
- [ ] 1.4 Implement `logout()` function in AuthContext — dispatches LOGOUT_START, calls `POST /v1/auth/logout` via API layer (returns 200 JSON with `X-Session-Rotated: true` header), then proactively dispatches LOGOUT_SUCCESS (sets user=null, isAuthenticated=false, error=null). On failure, dispatches LOGOUT_FAILURE with error message. Does NOT rely solely on the session-rotated event for state clearing — the event is a secondary signal for other contexts (CartContext).
- [ ] 1.5 Export `useAuth()` hook that throws if used outside AuthProvider — exposes: `user`, `isLoading`, `isAuthenticated`, `error`, `login()`, `logout()`, `loginComplete(user: UserResponse)` (dispatches LOGIN_COMPLETE with the user object)
- [ ] 1.6 Update `frontend/app/layout.tsx` — wrap CartProvider with AuthProvider (AuthProvider outermost)

## 2. API Client Enhancements

- [ ] 2.1 Add `X-Session-Rotated` detection in `frontend/lib/api-client.ts` — in `handleResponse`, after response is parsed, check `res.headers.get("X-Session-Rotated") === "true"` and dispatch `window.dispatchEvent(new Event("session-rotated"))`
- [ ] 2.2 Add `logout()` function to `frontend/lib/api.ts` — calls `apiClient.post("/v1/auth/logout")` in real mode, toggles mock state in mock mode
- [ ] 2.3 Update `frontend/lib/mock-api.ts` — add mutable `isAuthenticated` state, make `getCurrentUser()` return null when not authenticated, add `mockLogout()` that sets state to anonymous
- [ ] 2.4 Add `session-rotated` event listener in CartContext — useEffect that listens for the event and calls `refreshCart()`
- [ ] 2.5 Add `session-rotated` event listener in AuthContext — useEffect that listens for the event and re-fetches `getCurrentUser()`

## 3. Header Auth UI

- [ ] 3.1 Create `frontend/components/auth/LoginButton.tsx` — renders "Sign In" link styled as the site's navigation links, onClick triggers AuthContext `login()`
- [ ] 3.2 Create `frontend/components/auth/UserMenu.tsx` — renders user avatar (or initial in a circle) with dropdown containing "My Account" (/account), "My Orders" (/orders), "Sign Out". Uses useState for open/close, click-outside to dismiss. Accessibility: trigger button has `aria-expanded`, `aria-haspopup="menu"`; dropdown has `role="menu"`; items have `role="menuitem"`; Escape key closes the dropdown and returns focus to trigger.
- [ ] 3.3 Update `frontend/components/layout/Header.tsx` — import useAuth, conditionally render LoginButton (when anonymous) or UserMenu (when authenticated). Show Skeleton circle while isLoading.

## 4. OAuth Callback Page

- [ ] 4.1 Create `frontend/app/auth/callback/page.tsx` — Client Component that reads `success`, `redirect_to`, and `error` query params from URL on mount via `useSearchParams()` (note: no `code` param — backend already exchanged it). If `error` param is present, immediately show error state without calling getCurrentUser().
- [ ] 4.2 Implement callback page logic — on mount, call `getCurrentUser()` via API layer. If user returned, call `loginComplete(user)` (exposed from AuthContext, dispatches LOGIN_COMPLETE). Then re-validate redirect_to path (same rules as login(): must start with `/`, must not start with `//`; use shared `lib/validateRedirectPath.ts` utility) and navigate via `router.replace()` (from query param, or sessionStorage `auth_redirect_to` fallback, or `/`). If getCurrentUser() returns null or throws, show error state.
- [ ] 4.3 Implement error state in callback page — if `error` query param is present or getCurrentUser() fails, show "Sign in failed. Please try again." with a link that triggers login() again
- [ ] 4.4 Implement loading state in callback page — show centered spinner/text "Signing you in..." while exchanging

## 5. Account Page

- [ ] 5.1 Create `frontend/app/account/page.tsx` — Client Component that uses `useAuth()` to determine state
- [ ] 5.2 Implement authenticated view — card layout showing large avatar image, display name, email, links to "My Orders", "Sign Out" button
- [ ] 5.3 Implement anonymous view — centered card with message "Sign in to view your account and order history" + prominent "Sign In with Google" button
- [ ] 5.4 Implement loading skeleton — show placeholder shapes while `isLoading` is true

## 6. Order History Page

- [ ] 6.1 Create `frontend/components/orders/OrderStatusBadge.tsx` — uses Badge component with `className` prop to apply custom Tailwind color classes per status (bypasses the limited variant enum). Color mapping: pending=`bg-amber-100 text-amber-800`, confirmed=`bg-blue-100 text-blue-800`, shipped=`bg-indigo-100 text-indigo-800`, delivered=`bg-green-100 text-green-800`, cancelled=`bg-red-100 text-red-800`. Badge `variant` left as default; colors are applied via className override.
- [ ] 6.2 Create `frontend/app/orders/page.tsx` — Client Component that fetches orders via `getOrders()` on mount, shows paginated list
- [ ] 6.3 Implement order list item — each order shows: formatted date, order ID (truncated to first 8 chars), status badge, item count summary, total price
- [ ] 6.4 Implement empty state — "No orders yet" with "Start Shopping" link to `/products`. For anonymous users, add "Sign in to see all your orders" CTA
- [ ] 6.5 Implement pagination — Previous/Next buttons, disable when at boundaries, show "Page X of Y"
- [ ] 6.6 Implement loading skeleton — show 3-4 order-card-shaped skeletons while fetching
- [ ] 6.7 Implement error state — "Something went wrong loading your orders" with "Try again" button that retries

## 7. Order Detail Page

- [ ] 7.1 Create `frontend/components/orders/StatusTimeline.tsx` — vertical stepper showing order progression. Props: `currentStatus: OrderStatus`. Renders Pending → Confirmed → Shipped → Delivered steps. Past/current steps filled and colored, future steps gray. For cancelled orders: show "Pending → Cancelled" sequence for MVP (the status field alone cannot determine the exact point of cancellation; the backend only stores final status, not transition history).
- [ ] 7.2 Create `frontend/app/orders/[id]/page.tsx` — Client Component that fetches single order via `getOrder(id)`, distinct from the existing `/orders/[id]/confirmation/page.tsx` (which is the post-checkout success page). Both routes coexist: `/orders/123` = detail view from order history, `/orders/123/confirmation` = post-checkout celebratory page. The detail page is a standard read-only view; the confirmation page has the confetti/success messaging.
- [ ] 7.3 Implement order detail layout — order ID, date, status badge, status timeline, items table (name, qty, unit price, line total), order total, customer email
- [ ] 7.4 Implement not-found state — if order fetch returns 404, show "Order not found" with link to `/orders`
- [ ] 7.5 Implement loading skeleton — skeleton placeholders for timeline, items list, and total

## 8. Tests

- [ ] 8.1 Create `frontend/__tests__/contexts/AuthContext.test.tsx` — test hydration (authenticated + anonymous), login triggers navigation, logout clears state, session-rotated event re-fetches
- [ ] 8.2 Create `frontend/__tests__/components/auth/UserMenu.test.tsx` — test dropdown opens/closes, contains expected links, sign out triggers logout
- [ ] 8.3 Create `frontend/__tests__/components/orders/OrderStatusBadge.test.tsx` — test each status renders correct color class and label
- [ ] 8.4 Create `frontend/__tests__/components/orders/StatusTimeline.test.tsx` — test each status shows correct completed/future steps, cancelled branch rendering
- [ ] 8.5 Create `frontend/__tests__/pages/orders.test.tsx` — test orders page renders list, handles empty state, handles error state, pagination controls
- [ ] 8.6 Create `frontend/__tests__/pages/account.test.tsx` — test authenticated view shows user info, anonymous view shows login prompt
- [ ] 8.7 Test X-Session-Rotated detection — verify api-client dispatches event, CartContext refreshes, AuthContext refreshes