## ADDED Requirements

### Requirement: Admin layout with sidebar navigation
The system SHALL render an admin-specific layout at `/admin` and all sub-paths with a sidebar navigation containing links to Dashboard, Products, and Orders. The layout SHALL NOT include the storefront header, footer, or announcement bar.

#### Scenario: Admin layout renders sidebar
- **WHEN** an admin user navigates to `/admin`
- **THEN** the page displays a sidebar with navigation links: "Dashboard", "Products", "Orders"
- **AND** the active link is visually highlighted
- **AND** the storefront header/footer are not visible

#### Scenario: Sidebar navigation links work
- **WHEN** admin clicks "Products" in the sidebar
- **THEN** the browser navigates to `/admin/products`
- **AND** the "Products" link becomes the active/highlighted link

### Requirement: Admin route protection
The system SHALL check if the current user is an admin before rendering admin pages. If the user is not an admin or not authenticated, the system SHALL redirect to the home page.

#### Scenario: Non-admin user redirected
- **WHEN** a non-admin user navigates to `/admin`
- **THEN** the user is redirected to `/`

#### Scenario: Unauthenticated user redirected
- **WHEN** an unauthenticated user navigates to `/admin/products`
- **THEN** the user is redirected to `/`

#### Scenario: Admin user sees admin layout
- **WHEN** an authenticated admin user navigates to `/admin`
- **THEN** the admin layout renders with the dashboard content

### Requirement: Responsive admin layout
The system SHALL provide a responsive admin layout that works on desktop and tablet. On smaller screens, the sidebar SHALL collapse to an icon-only or hamburger-triggered navigation.

#### Scenario: Desktop sidebar expanded
- **WHEN** viewport width is >= 1024px
- **THEN** sidebar shows full navigation labels and icons

#### Scenario: Tablet sidebar collapsed
- **WHEN** viewport width is < 1024px
- **THEN** sidebar collapses to icons only or is hidden behind a toggle button
