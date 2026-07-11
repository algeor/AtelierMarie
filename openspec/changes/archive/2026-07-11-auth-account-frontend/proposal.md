## Why

The storefront has a working cart and checkout flow, but the user has no way to log in, view their account, or browse past orders. The backend auth routes are stubs, the header has no login/account UI, and there are no `/account` or `/orders` pages. Without this, customers cannot see their order history after placing a purchase, and the identity system stays incomplete — orders are session-only with no way to link them to a persistent account.

## What Changes

- Add `AuthContext` provider (mirrors `CartContext` pattern): manages user state, provides `login`/`logout` actions, hydrates on mount via `GET /v1/auth/me`
- Add login/account button to the Header component (shows "Sign In" or user avatar+name based on auth state)
- Create OAuth callback page (`/auth/callback`) that exchanges the code, stores the JWT, and redirects home
- Create Account page (`/account`): displays user info for authenticated users, login prompt for anonymous
- Create My Orders page (`/orders`): paginated list of past orders with status badges
- Create Order Detail page (`/orders/[id]`): items, total, status timeline visualization
- Enhance the API client to detect `X-Session-Rotated` response header and trigger cart/auth state refresh on session rotation
- Add `logout` function to API layer (`POST /v1/auth/logout`) that clears auth state and refreshes cart
- Add mock implementations for all new auth/order-history flows

## Capabilities

### New Capabilities
- `auth-ui`: Login button, OAuth callback handler, AuthContext provider, logout flow, session rotation handling
- `account-page`: User account page showing profile info or login prompt
- `order-history`: My Orders listing with status badges, order detail page with status timeline

### Modified Capabilities

## Impact

- **New files:** `frontend/contexts/AuthContext.tsx`, `frontend/app/auth/callback/page.tsx`, `frontend/app/account/page.tsx`, `frontend/app/orders/page.tsx`, `frontend/app/orders/[id]/page.tsx`, `frontend/components/auth/LoginButton.tsx`, `frontend/components/auth/UserMenu.tsx`, `frontend/components/orders/OrderStatusBadge.tsx`, `frontend/components/orders/StatusTimeline.tsx`
- **Modified:** `frontend/components/layout/Header.tsx` (add login/account button), `frontend/app/layout.tsx` (wrap with AuthProvider), `frontend/lib/api-client.ts` (X-Session-Rotated detection), `frontend/lib/api.ts` (add logout function), `frontend/lib/mock-api.ts` (add mock auth state), `frontend/lib/types.ts` (no new types needed — UserResponse, AuthTokenResponse already defined)
- **No new npm dependencies** — uses existing fetch-based API client, no external auth library needed
- **Backend dependency:** Requires auth routes to be implemented (Day 5 backend), but frontend can develop against mock API independently
