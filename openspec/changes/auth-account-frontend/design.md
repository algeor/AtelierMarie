## Context

The AtelierMarie frontend has a working product browsing, cart, and checkout flow. Users can place orders anonymously via session cookies. However:

- The header shows no login/account controls (only logo, nav links, and cart icon)
- There is no AuthContext — user identity state isn't tracked client-side
- The backend auth routes (`/v1/auth/login`, `/v1/auth/callback`, `/v1/auth/me`, `/v1/auth/logout`) are stubs returning 501
- There is no `/account` page or `/orders` list page
- The only order visibility is the confirmation page immediately after checkout
- The API client does not detect the `X-Session-Rotated` header (needed for session rotation on logout/login)

The identity model is anonymous-first: full functionality works without login. Login is an overlay that links sessions to a persistent user, enabling cross-session order visibility. The frontend develops against mock API independently of the backend auth implementation.

## Goals / Non-Goals

**Goals:**
- Add AuthContext that mirrors the CartContext pattern (provider, reducer, hook)
- Show auth state in the header (login button vs. user menu with account/orders/logout)
- Handle the full OAuth redirect flow (click login → redirect to backend → callback page exchanges code → redirect home)
- Create account page (shows user info or login prompt)
- Create My Orders page (paginated list with status badges)
- Create Order Detail page (items, total, status timeline)
- Handle X-Session-Rotated response header in the API client (refresh cart+auth state when the backend rotates the session)
- Maintain full mock API coverage so development works without backend

**Non-Goals:**
- Backend auth implementation (separate spec — this is frontend only)
- Admin UI (Day 6 spec)
- User registration/signup (Google OAuth only)
- Profile editing (name, avatar — read-only from Google)
- Email notification preferences
- Password reset / credentials management (no passwords — OAuth only)
- Mobile-specific auth patterns (responsive design is Day 8)

## Decisions

### 1. AuthContext as a React Context + useReducer (same pattern as CartContext)

**Decision:** Create `frontend/contexts/AuthContext.tsx` with the same architecture as `CartContext`:
- `useReducer` for state management
- Hydrate on mount by calling `GET /v1/auth/me` (returns user or null)
- Expose `user`, `isLoading`, `isAuthenticated`, `login()`, `logout()` via context hook

```typescript
interface AuthState {
  user: UserResponse | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}
```

**Alternatives considered:**
- *Zustand or Jotai:* Adds a dependency for minimal gain. CartContext already established the useReducer pattern. Consistency > library overhead.
- *Server Component with cookies:* Could check auth server-side in layout, but auth state changes on client actions (login/logout) — need client state anyway for immediate reactivity.
- *NextAuth.js:* Overkill for single-provider (Google only), introduces significant complexity, and tightly couples frontend auth to Next.js internals.

**Rationale:** Consistency with CartContext. No new dependencies. The pattern is proven in this codebase.

### 2. OAuth flow via redirect (not popup)

**Decision:** Login button navigates to `{API_URL}/v1/auth/login` which redirects to Google. After Google consent, the backend redirects back to `/auth/callback?code=...&state=...`. The callback page:
1. Extracts `code` and `state` from URL params
2. Calls `POST /v1/auth/google` with the code
3. Backend sets JWT as HttpOnly cookie in the response
4. Frontend receives the user object in the response body
5. Updates AuthContext state
6. Redirects to the page the user was on before login (stored in `state` param or localStorage)

**Alternatives considered:**
- *Popup window:* Blocked by many browsers, worse mobile UX. Rejected.
- *Client-side token storage (localStorage):* Less secure than HttpOnly cookie. Rejected — backend owns token storage.

**Rationale:** Standard OAuth redirect flow. The backend handles the security-sensitive parts (token storage, cookie flags). Frontend only exchanges the code and receives the user object.

### 3. JWT stored as HttpOnly cookie (backend-managed)

**Decision:** The frontend never sees or stores the JWT directly. The backend sets it as an HttpOnly, Secure, SameSite=Lax cookie. The API client sends `credentials: "include"` (already implemented) which attaches cookies automatically.

`GET /v1/auth/me` returns the user object if the JWT cookie is valid, 401 otherwise. The frontend treats 401 as "not logged in" (already handled in `getCurrentUser()` in `api.ts`).

**Rationale:** More secure than localStorage — not accessible to XSS. Consistent with session cookie pattern. The API client already uses `credentials: "include"`.

### 4. X-Session-Rotated header detection in API client

**Decision:** When the backend rotates the session (on logout, or login replacing anonymous session), it includes `X-Session-Rotated: true` in the response. The API client's `handleResponse` function checks for this header and triggers:
1. Cart state refresh (`refreshCart()` from CartContext)
2. Auth state refresh (re-call `GET /v1/auth/me`)

Implementation: the API client emits a custom event (`session-rotated`) that both CartContext and AuthContext listen for.

```typescript
// In handleResponse:
if (res.headers.get("X-Session-Rotated") === "true") {
  window.dispatchEvent(new Event("session-rotated"));
}
```

**Alternatives considered:**
- *Direct context refresh call from api-client:* Creates circular dependency (api-client would need to import context). Rejected.
- *Polling /auth/me periodically:* Wasteful, slow. Rejected.
- *Require manual refresh after logout:* Poor UX — stale data visible. Rejected.

**Rationale:** Event-based decoupling avoids circular imports. Both contexts independently listen and refresh. Clean separation.

### 5. Login redirect URL preservation

**Decision:** Before redirecting to `/v1/auth/login`, store the current path in `sessionStorage` under key `auth_redirect_to`. The callback page reads this after successful auth and redirects there. Falls back to `/` if no stored path.

The backend's `/v1/auth/login` endpoint accepts a `?redirect_to=` query parameter that it passes through the OAuth `state` parameter. The callback page reads from the `state` param first (preferred — survives session storage clearing), falling back to sessionStorage.

**Rationale:** Users should land back where they were. sessionStorage is tab-scoped so doesn't leak across tabs. State param is the OAuth-standard mechanism.

### 6. Order status badge component with color mapping

**Decision:** Create `OrderStatusBadge` using the existing `Badge` component with status-to-color mapping:

| Status | Color | Label |
|--------|-------|-------|
| pending | amber/yellow | Pending |
| confirmed | blue | Confirmed |
| shipped | indigo | Shipped |
| delivered | green | Delivered |
| cancelled | red | Cancelled |

**Rationale:** Visual distinction helps users scan order lists quickly. Colors follow conventional meaning (green=good, red=bad, amber=waiting).

### 7. Status timeline as vertical stepper

**Decision:** Order detail page shows a vertical timeline/stepper with all states in sequence. Current and past states are filled/colored. Future states are gray/empty. Cancelled orders show a strike-through on skipped states.

States in order: Pending → Confirmed → Shipped → Delivered
Cancelled is shown as a branch from wherever it happened.

**Rationale:** Gives users a clear sense of progress. Common e-commerce pattern (Amazon, Shopify). Better than just a badge for the detail page.

### 8. Layout: AuthProvider wraps CartProvider

**Decision:** In `layout.tsx`, AuthProvider wraps CartProvider (outermost context wins):

```tsx
<AuthProvider>
  <CartProvider>
    ...
  </CartProvider>
</AuthProvider>
```

**Rationale:** Auth state determines whether to show authenticated order lists. Cart state may need to refresh based on auth events. Auth is the outermost concern.

### 9. User menu as dropdown (not separate page navigation)

**Decision:** When authenticated, the header shows a user avatar/initial + chevron. Clicking opens a dropdown with: "My Account", "My Orders", "Sign Out". On mobile, these are full-width links in the future mobile menu (Day 8).

**Alternatives considered:**
- *Always navigate to /account:* Extra click to reach orders. Rejected.
- *Sidebar:* Over-engineered for 3 links. Rejected.

**Rationale:** Fast access to common actions. Standard e-commerce pattern.

### 10. Mock auth state toggle for development

**Decision:** The mock API `getCurrentUser()` returns the mock user by default (simulating logged-in state). Add a `mockAuthState` module variable that can be toggled via `mockLogout()` / `mockLogin()` to test both states during development.

**Rationale:** Developers need to test both anonymous and authenticated flows without a backend.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| **OAuth callback race with session cookie** | Callback page shows loading state while exchanging code. If exchange fails, show error with retry link. Never leave user on blank page. |
| **X-Session-Rotated missed on non-JSON responses** | The header is checked in `handleResponse` which runs on all fetch calls. Even failed responses are checked. Edge case: if the browser follows a redirect (302 from /v1/auth/login), the header on the redirect response is lost — but that's expected (redirect is pre-auth). |
| **JWT cookie expiry while user is active** | `GET /v1/auth/me` returns 401 → AuthContext sets user to null → UI reverts to anonymous state. No jarring error — just seamless degradation. Cart persists (session-keyed, not user-keyed). |
| **Cart state stale after login (new session may have different cart)** | session-rotated event triggers cart refresh. If the backend merges carts on login (future feature), the refreshed cart reflects the merge. |
| **Order list empty for anonymous users** | Show a friendly message: "Sign in to see your order history" with login CTA. Orders placed in this session still visible via the session-keyed endpoint. |
| **Multiple tabs open during logout** | session-rotated is a window event, scoped to the tab that made the request. Other tabs won't refresh until their next API call fails with 401, at which point their AuthContext resets. Acceptable for MVP. |
| **Google OAuth consent screen shows different redirect_uri than expected** | Backend configures allowed redirect URIs. Frontend must use the same callback URL consistently. Use `window.location.origin + "/auth/callback"` as the redirect_uri. |

## Open Questions

None — all decisions align with the established patterns (CartContext, api-client, mock-api) and the implementation plan Day 5 requirements.