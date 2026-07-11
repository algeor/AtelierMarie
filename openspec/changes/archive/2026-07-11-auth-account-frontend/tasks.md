## 1. AuthContext Foundation

- [ ] 1.1 Create `frontend/contexts/AuthContext.tsx` — implement AuthState interface (user, isLoading, error: string | null), AuthAction union type with actions: HYDRATE_START, HYDRATE_SUCCESS, HYDRATE_FAILURE, LOGIN_COMPLETE, LOGOUT_START, LOGOUT_SUCCESS, LOGOUT_FAILURE, SESSION_REFRESH, CLEAR_ERROR. Implement authReducer, AuthProvider component with useReducer. `isAuthenticated` is NOT stored in state — it is derived as `state.user !== null` in the context value object to prevent desync bugs. Error state auto-clears after 5s timeout using `errorTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)` pattern (matching CartContext lines 159-181).
- [ ] 1.2 Implement hydration in AuthProvider — useEffect on mount calls `getCurrentUser()`, dispatches HYDRATE_SUCCESS or HYDRATE_FAILURE, sets isLoading=false. Must use `let cancelled = false` cleanup pattern (return cleanup function that sets `cancelled = true`) to prevent stale dispatches on unmount/re-mount in StrictMode.
- [ ] 1.3 Create `frontend/lib/validateRedirectPath.ts` — exports `validateRedirectPath(path: string): string` that returns the path if it starts with `/` and does NOT start with `//` (rejects absolute URLs and protocol-relative URLs), otherwise returns `/`. Used by both login() and the callback page.
- [ ] 1.4 Implement `login()` function in AuthContext — calls `validateRedirectPath(currentPath)`, stores validated path in sessionStorage (`auth_redirect_to`). Navigates to `{API_URL}/v1/auth/login?redirect_to={validatedPath}` using `window.location.href` (full-page navigation, not router.push — this exits the SPA to the backend OAuth flow).
- [ ] 1.5 Implement `logout()` function in AuthContext — dispatches LOGOUT_START, calls `POST /v1/auth/logout` via API layer (returns 200 JSON with `X-Session-Rotated: true` header). On success, dispatches LOGOUT_SUCCESS (sets user=null, error=null). On failure (network error, 5xx), STILL dispatches LOGOUT_SUCCESS to clear local state (user intent is to log out regardless of server response); logs the error for monitoring. Shows brief non-blocking warning if API call failed. Does NOT rely solely on the session-rotated event for state clearing — the event is a secondary signal for other contexts (CartContext).
- [ ] 1.6 Export `useAuth()` hook that throws if used outside AuthProvider — exposes: `user`, `isLoading`, `isAuthenticated` (derived: `user !== null`), `error`, `login()`, `logout()`, `loginComplete(user: UserResponse)` (dispatches LOGIN_COMPLETE with the user object)
- [ ] 1.6 Update `frontend/app/layout.tsx` — wrap CartProvider with AuthProvider (AuthProvider outermost)

## 2. API Client Enhancements

- [ ] 2.1 Add `X-Session-Rotated` detection in `frontend/lib/api-client.ts` — as the FIRST line in `handleResponse` (before checking `res.ok`), check `res.headers.get("X-Session-Rotated") === "true"` and dispatch `window.dispatchEvent(new Event("session-rotated"))`. This ensures session rotation is detected even on error responses.
- [ ] 2.2 Add `logout()` function to `frontend/lib/api.ts` — calls `apiClient.post<void>("/v1/auth/logout")` in real mode, calls `mockApi.logout()` in mock mode. Returns `Promise<void>` (response body is informational only; the header is what matters).
- [ ] 2.3 Update `frontend/lib/mock-api.ts` — add mutable `isAuthenticated` state, make `getCurrentUser()` return null when not authenticated, add `mockLogout()` that sets state to anonymous and dispatches `window.dispatchEvent(new Event("session-rotated"))` to simulate the real API header behavior
- [ ] 2.4 Add `session-rotated` event listener in CartContext — useEffect that adds `window.addEventListener("session-rotated", refreshCart)` and returns cleanup: `return () => window.removeEventListener("session-rotated", refreshCart)`
- [ ] 2.5 Add `session-rotated` event listener in AuthContext — useEffect that adds `window.addEventListener("session-rotated", handler)` where handler re-fetches `getCurrentUser()`. Returns cleanup: `return () => window.removeEventListener("session-rotated", handler)`
- [ ] 2.6 Remove or deprecate the existing `login(code, redirectUri)` function from `frontend/lib/api.ts` — this function calls `POST /v1/auth/google` which is the old frontend-code-exchange pattern. Under the server-side callback design, the frontend never has the code. Remove the function and its mock counterpart.

## 3. Header Auth UI

- [ ] 3.1 Create `frontend/components/auth/LoginButton.tsx` — renders "Sign In" link styled as the site's navigation links, onClick triggers AuthContext `login()`
- [ ] 3.2 Create `frontend/components/auth/UserMenu.tsx` — renders user avatar (or initial in a circle) with dropdown containing "My Account" (/account), "My Orders" (/orders), "Sign Out". Uses useState for open/close, click-outside to dismiss. Accessibility: trigger button has `aria-expanded`, `aria-haspopup="menu"`; dropdown has `role="menu"`; items have `role="menuitem"`; Escape key closes the dropdown and returns focus to trigger.
- [ ] 3.3 Update `frontend/components/layout/Header.tsx` — import useAuth, conditionally render LoginButton (when anonymous) or UserMenu (when authenticated). Show Skeleton circle while isLoading.

## 4. OAuth Callback Page

- [ ] 4.1 Create `frontend/app/auth/callback/page.tsx` — export default a Server Component that wraps the callback Client Component in a `<Suspense fallback={<LoadingSpinner/>}>` boundary (required by Next.js 14 for useSearchParams). The Client Component reads `success`, `redirect_to`, and `error` query params from URL on mount via `useSearchParams()` (note: no `code` param — backend already exchanged it). If `error` param is present, immediately show error state without calling getCurrentUser().
- [ ] 4.2 Implement callback page logic — on mount, call `getCurrentUser()` via API layer. If user returned, call `loginComplete(user)` (exposed from AuthContext, dispatches LOGIN_COMPLETE). Then validate redirect_to path using `validateRedirectPath()` from `lib/validateRedirectPath.ts` (from query param first, or sessionStorage `auth_redirect_to` fallback, or `/`). Immediately clear sessionStorage: `sessionStorage.removeItem('auth_redirect_to')`. Navigate via `router.replace()`. If getCurrentUser() returns null or throws, show error state.
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

- [ ] 8.1 Create `frontend/__tests__/contexts/AuthContext.test.tsx` — test hydration (authenticated + anonymous + network failure), login validates redirect and triggers window.location.href navigation, logout clears state (even on API failure), session-rotated event re-fetches, loginComplete(user) updates state, useAuth() throws outside provider, error auto-clears after 5s (vi.useFakeTimers), isAuthenticated derived correctly from user state, `let cancelled = false` cleanup prevents stale dispatch
- [ ] 8.2 Create `frontend/__tests__/components/auth/UserMenu.test.tsx` — test dropdown opens/closes (click trigger toggles), click-outside closes, Escape closes and returns focus to trigger, contains expected links (href="/account", href="/orders"), sign out calls logout() from useAuth(), avatar displays when avatar_url present, initial circle when avatar_url null, aria-expanded/aria-haspopup/role="menu"/role="menuitem" attributes present
- [ ] 8.3 Create `frontend/__tests__/components/orders/OrderStatusBadge.test.tsx` — test each status renders correct color class via className prop and correct capitalized label
- [ ] 8.4 Create `frontend/__tests__/components/orders/StatusTimeline.test.tsx` — test each status shows correct completed/future steps (pending=1 filled, confirmed=2, shipped=3, delivered=4), cancelled shows "Pending → Cancelled" only (MVP limitation)
- [ ] 8.5 Create `frontend/__tests__/pages/orders.test.tsx` — test orders page renders list with correct fields (date, truncated ID, badge, item count, total), handles empty state, handles anonymous CTA, handles error state with retry button, pagination controls (Previous disabled on page 1, Next disabled on last page), loading skeleton
- [ ] 8.6 Create `frontend/__tests__/pages/account.test.tsx` — test authenticated view shows avatar/name/email/My Orders link/Sign Out button, anonymous view shows "Sign In with Google" button that passes /account as redirect_to, loading skeleton
- [ ] 8.7 Create `frontend/__tests__/lib/api-client.test.ts` — test handleResponse dispatches session-rotated event when X-Session-Rotated header present (case-insensitive), does not dispatch when absent. In CartContext tests: verify event triggers refreshCart(). In AuthContext tests: verify event triggers getCurrentUser() re-fetch.
- [ ] 8.8 Create `frontend/__tests__/app/auth/callback.test.tsx` — test successful flow (reads success=true, calls getCurrentUser, calls loginComplete, navigates to redirect_to), error param shows error immediately without API call, getCurrentUser failure shows error, redirect_to validation via validateRedirectPath, sessionStorage fallback and cleanup, loading state renders Suspense fallback
- [ ] 8.9 Create `frontend/__tests__/components/auth/LoginButton.test.tsx` — test renders "Sign In" text, onClick calls login() from useAuth()
- [ ] 8.10 Create `frontend/__tests__/components/layout/Header.test.tsx` — test shows LoginButton when not authenticated, shows UserMenu when authenticated, shows skeleton circle while isLoading
- [ ] 8.11 Create `frontend/__tests__/app/orders/[id].test.tsx` — test displays order details (ID, date, badge, timeline, items table, total, email), handles 404 (shows "Order not found"), loading skeleton
- [ ] 8.12 Create `frontend/__tests__/lib/validateRedirectPath.test.ts` — test accepts valid paths (/products, /account, /orders/123), rejects protocol-relative URLs (//evil.com), rejects absolute URLs (https://evil.com), rejects javascript: URIs, returns / as fallback for all invalid paths
- [ ] 8.13 Verify all existing CartContext tests pass after adding session-rotated listener (regression check)
