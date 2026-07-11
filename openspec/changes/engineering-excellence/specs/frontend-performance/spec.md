## ADDED Requirements

### Requirement: Memoized AuthContext value
The `AuthProvider` SHALL wrap its context value object in `useMemo` with an explicit dependency array, so consumers only re-render when auth state actually changes.

#### Scenario: Unrelated state update in AuthProvider
- **WHEN** a timer or effect triggers a state update in AuthProvider that does not change user/loading/error values
- **THEN** `useAuth()` consumers SHALL NOT re-render (value reference remains stable)

#### Scenario: User logs in
- **WHEN** the user state changes from null to a user object
- **THEN** all `useAuth()` consumers SHALL re-render with the new user

### Requirement: Memoized CartContext value
The `CartProvider` SHALL wrap its context value object in `useMemo` with an explicit dependency array, so consumers only re-render when their consumed slice of cart state changes.

#### Scenario: Drawer open/close toggle
- **WHEN** `isDrawerOpen` changes but cart items remain the same
- **THEN** components consuming only `cart`/`addToCart`/`removeFromCart` SHALL NOT re-render

### Requirement: AdminProvider consumes AuthContext
The `AdminProvider` SHALL use `useAuth()` to obtain the current user instead of making its own `getCurrentUser()` API call.

#### Scenario: Admin page loads
- **WHEN** a user navigates to an admin page
- **THEN** only ONE `GET /v1/auth/me` request SHALL be made (by AuthProvider), not two

#### Scenario: Non-admin user visits admin page
- **WHEN** a non-admin user is returned by AuthContext
- **THEN** AdminProvider SHALL deny access based on the AuthContext user, without a separate fetch
