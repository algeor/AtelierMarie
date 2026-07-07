## ADDED Requirements

### Requirement: Global header with logo, navigation, and cart icon
The system SHALL render a sticky header on all pages containing the site logo (text "Atelier Marie" in Playfair Display), navigation links (Home, Shop), and a cart icon with item count badge.

#### Scenario: Header renders on all pages
- **WHEN** any page loads
- **THEN** the header is visible at the top of the viewport with logo, nav links, and cart icon

#### Scenario: Cart badge shows item count
- **WHEN** the cart contains items
- **THEN** the cart icon displays a Badge component with the current item count

#### Scenario: Cart badge hidden when empty
- **WHEN** the cart is empty (or cart state is not yet available)
- **THEN** the cart icon renders without a badge (no "0" shown)

#### Scenario: Cart badge data source (Day 3)
- **WHEN** Day 3 implementation (Add to Cart not connected to backend)
- **THEN** the cart badge displays 0 (hardcoded). Cart icon is non-interactive (`aria-disabled="true"`, no link, `cursor-default`). A CartContext provider will be introduced in Day 4 to enable reactive badge updates and link to /cart.

#### Scenario: Header is sticky on scroll
- **WHEN** the user scrolls down
- **THEN** the header remains fixed at the top of the viewport

#### Scenario: Navigation links are accessible
- **WHEN** a keyboard user tabs through the header
- **THEN** all navigation links and the cart icon are focusable with visible focus rings

### Requirement: Footer with links and branding
The system SHALL render a footer on all pages containing navigation links (Home, Shop), brand messaging, and copyright information.

#### Scenario: Footer renders on all pages
- **WHEN** any page loads
- **THEN** the footer is visible at the bottom of the page content with navigation links (Home → /, Shop → /products), brand text ("Handcrafted with love"), and dynamic copyright year

#### Scenario: Footer links are navigable
- **WHEN** a user clicks a footer link (Home or Shop)
- **THEN** they are navigated to the corresponding page (/ or /products)

#### Scenario: Footer includes placeholder links for future pages
- **WHEN** the footer renders
- **THEN** it includes placeholder links for About and Contact that link to "#" until those pages are built

### Requirement: Announcement bar with session-persistent dismissal
The system SHALL render a dismissible announcement bar above the header displaying the text "Free shipping on orders over €50 ✨". Once dismissed, it SHALL NOT reappear during the same browser session.

**SSR/Hydration pattern:** AnnouncementBar is a Client Component using `useState(false)` for `isDismissed` initial state, then checking sessionStorage in `useEffect`. SSR and initial client render both show the bar (avoiding hydration mismatch). After mount, useEffect hides it if previously dismissed (one-frame flash acceptable). Note: sessionStorage is per-tab — dismissal does not persist across tabs (intentional: per-tab is less aggressive).

#### Scenario: Announcement bar visible on first visit
- **WHEN** a user visits the site for the first time in a session
- **THEN** the announcement bar is visible above the header displaying "Free shipping on orders over €50 ✨" in a muted-gold background

#### Scenario: Announcement bar can be dismissed
- **WHEN** a user clicks the dismiss (×) button on the announcement bar
- **THEN** the bar disappears immediately and the layout shifts up

#### Scenario: Dismissal persists within session
- **WHEN** a user has dismissed the announcement bar and navigates to another page
- **THEN** the announcement bar does NOT reappear

#### Scenario: Announcement bar returns on new session
- **WHEN** a user opens a new browser session (closes and reopens browser)
- **THEN** the announcement bar is visible again

#### Scenario: Dismiss button meets touch target requirements
- **WHEN** the announcement bar renders
- **THEN** the dismiss button has a minimum touch target of 44×44px

### Requirement: Responsive layout adapts to viewport width
The system SHALL adapt the layout shell for mobile, tablet, and desktop viewports.

#### Scenario: Mobile header (below 768px)
- **WHEN** viewport width is below 768px
- **THEN** the header shows logo and cart icon only; navigation links are hidden (accessible via footer instead)

#### Scenario: Tablet header (768px–1024px)
- **WHEN** viewport width is between 768px and 1024px
- **THEN** the header shows full inline navigation (logo, nav links, cart icon) matching the desktop layout

#### Scenario: Desktop header (above 1024px)
- **WHEN** viewport width is above 1024px
- **THEN** the header shows full navigation inline with logo and cart icon
