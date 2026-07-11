## ADDED Requirements

### Requirement: Account page shows user profile when authenticated
The system SHALL have a page at `/account` that displays the authenticated user's profile information: name, email, and avatar image.

#### Scenario: Authenticated user views account page
- **WHEN** an authenticated user navigates to `/account`
- **THEN** the page SHALL display their name, email address, and avatar image (from Google). It SHALL also show links to "My Orders" and a "Sign Out" button.

#### Scenario: Account page layout
- **WHEN** an authenticated user views `/account`
- **THEN** the page SHALL show a heading "My Account", the user's avatar (large), their display name, and their email address in a clean card layout consistent with the site's luxury aesthetic

### Requirement: Account page shows login prompt when anonymous
The system SHALL display a login prompt on `/account` for anonymous users, encouraging them to sign in.

#### Scenario: Anonymous user views account page
- **WHEN** an anonymous (unauthenticated) user navigates to `/account`
- **THEN** the page SHALL display a friendly message (e.g., "Sign in to view your account and order history") with a prominent "Sign In with Google" button that triggers the OAuth flow

#### Scenario: Login prompt redirects back to account
- **WHEN** an anonymous user clicks the login button on `/account`
- **THEN** after successful OAuth, they SHALL be redirected back to `/account` (not to home)

### Requirement: Account page loading state
The system SHALL show a loading skeleton on the account page while auth state is hydrating.

#### Scenario: Auth state loading
- **WHEN** the account page renders while `isLoading` is true in AuthContext
- **THEN** the page SHALL display skeleton placeholders (not flash between anonymous prompt and profile)
