## ADDED Requirements

### Requirement: AuthContext provides user state to the application
The system SHALL provide an `AuthContext` React context that tracks the current user's authentication state. The context SHALL hydrate on mount by calling `GET /v1/auth/me`. It SHALL expose `user` (UserResponse | null), `isLoading` (boolean), `isAuthenticated` (boolean), `login()`, and `logout()` via a `useAuth()` hook.

#### Scenario: Initial hydration — authenticated user
- **WHEN** the app mounts and the session has a valid JWT cookie
- **THEN** AuthContext SHALL call `GET /v1/auth/me`, receive a UserResponse, and set `user` to that object, `isAuthenticated` to true, and `isLoading` to false

#### Scenario: Initial hydration — anonymous user
- **WHEN** the app mounts and there is no JWT cookie (or it's expired)
- **THEN** AuthContext SHALL call `GET /v1/auth/me`, receive a 401/null, and set `user` to null, `isAuthenticated` to false, and `isLoading` to false

#### Scenario: Hydration loading state
- **WHEN** AuthContext is hydrating (between mount and API response)
- **THEN** `isLoading` SHALL be true and components SHALL show appropriate loading states (not flash between anonymous/authenticated)

### Requirement: Login button redirects to OAuth
The system SHALL display a "Sign In" button in the header when the user is not authenticated. Clicking the button SHALL navigate to `{API_URL}/v1/auth/login?redirect_to={current_path}`.

#### Scenario: Anonymous user sees login button
- **WHEN** an anonymous user views any page
- **THEN** the header SHALL display a "Sign In" link/button (not a user menu)

#### Scenario: Login button stores redirect path
- **WHEN** user clicks "Sign In" on `/products/lavender-dreams-300ml`
- **THEN** the browser SHALL navigate to `{API_URL}/v1/auth/login?redirect_to=/products/lavender-dreams-300ml`

### Requirement: OAuth callback page detects login success (server-side code exchange)
The system SHALL have a page at `/auth/callback` that handles the post-OAuth redirect from the backend. The backend exchanges the authorization code server-side and redirects the browser to this page with `success=true` or `error=<code>` query params. The frontend NEVER sees the authorization code — it only detects the outcome and hydrates auth state.

#### Scenario: Successful callback
- **WHEN** the backend redirects to `/auth/callback?success=true&redirect_to=/products`
- **THEN** the page SHALL call `GET /v1/auth/me` to hydrate the user, call `loginComplete(user)` on AuthContext, and navigate to the `redirect_to` path (or `/` if none)

#### Scenario: OAuth error from backend
- **WHEN** the backend redirects to `/auth/callback?error=invalid_state` (or any error code)
- **THEN** the page SHALL immediately display "Sign in failed. Please try again." with a link to retry login, WITHOUT calling `GET /v1/auth/me`

#### Scenario: getCurrentUser failure after success
- **WHEN** the callback page receives `success=true` but `GET /v1/auth/me` fails (network error, 500)
- **THEN** the page SHALL display "Sign in failed. Please try again." with a link to retry login

#### Scenario: Callback loading state
- **WHEN** the callback page is hydrating auth state after a successful redirect
- **THEN** the page SHALL display a loading indicator (spinner or text "Signing you in...")

### Requirement: Authenticated user sees user menu in header
The system SHALL display a user menu in the header when the user is authenticated. The menu SHALL show the user's avatar (or first initial) and provide dropdown access to "My Account", "My Orders", and "Sign Out".

#### Scenario: Authenticated user sees avatar and menu
- **WHEN** an authenticated user views any page
- **THEN** the header SHALL display their avatar (from `avatar_url`) or a circle with their first initial, and clicking it SHALL open a dropdown menu

#### Scenario: User menu contains expected links
- **WHEN** the user opens the header menu
- **THEN** the menu SHALL contain links to "/account" (My Account), "/orders" (My Orders), and a "Sign Out" button

#### Scenario: Sign Out clears auth state
- **WHEN** user clicks "Sign Out" in the menu
- **THEN** the system SHALL call `POST /v1/auth/logout`, clear the user from AuthContext, and the header SHALL revert to showing the "Sign In" button

### Requirement: Session rotation triggers state refresh
The API client SHALL detect the `X-Session-Rotated: true` response header on any API response. When detected, it SHALL dispatch a `session-rotated` DOM event. Both AuthContext and CartContext SHALL listen for this event and refresh their state.

#### Scenario: Logout rotates session
- **WHEN** `POST /v1/auth/logout` response includes `X-Session-Rotated: true`
- **THEN** CartContext SHALL re-fetch the cart (new session has empty cart) and AuthContext SHALL re-fetch `/v1/auth/me` (now returns null)

#### Scenario: Login rotates session
- **WHEN** the OAuth callback response includes `X-Session-Rotated: true`
- **THEN** CartContext SHALL re-fetch the cart (may have merged or changed) and AuthContext state is already updated from the login response

### Requirement: Logout function in API layer
The API layer SHALL export a `logout()` function that calls `POST /v1/auth/logout`. It SHALL be available in both mock and real API modes.

#### Scenario: Real API logout
- **WHEN** `logout()` is called in real API mode
- **THEN** it SHALL POST to `/v1/auth/logout` with credentials included

#### Scenario: Mock API logout
- **WHEN** `logout()` is called in mock API mode
- **THEN** it SHALL toggle the mock auth state to anonymous and return successfully

### Requirement: AuthProvider wraps CartProvider in layout
The `AuthProvider` SHALL wrap `CartProvider` in the root layout, making auth state available to all components including those that depend on cart state.

#### Scenario: Provider hierarchy
- **WHEN** the app renders
- **THEN** the component tree SHALL be `AuthProvider > CartProvider > Header + Main + Footer`
