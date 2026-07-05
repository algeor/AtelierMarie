# Navigation & Header — Spec

## ADDED Requirements

### Requirement: Announcement Bar

A dismissible announcement bar displays rotating promotional messages at the top of the page, persisting dismissal state within the session.

#### Scenario: Announcement bar displays rotating messages

WHEN a user loads any page and has not dismissed the announcement bar
THEN the announcement bar is visible at the top of the viewport
AND it displays one message at a time from a configured list (e.g., "Handcrafted candles for every occasion", "Free delivery over €50")
AND messages rotate automatically every 5 seconds
AND the bar uses a subtle background color (cream or champagne beige)

#### Scenario: User dismisses the announcement bar

WHEN a user clicks the dismiss (X) button on the announcement bar
THEN the announcement bar slides up and disappears
AND the dismissal state is stored in sessionStorage
WHEN the user navigates to another page within the same session
THEN the announcement bar remains hidden

#### Scenario: Announcement bar reappears in new session

WHEN a user opens the site in a new browser session (new tab after closing all tabs)
THEN the announcement bar is visible again with rotating messages

### Requirement: Sticky Header

A persistent header provides brand identity, primary navigation, and utility actions (search, account, cart) that remain accessible as the user scrolls.

#### Scenario: Header remains visible on scroll

WHEN a user scrolls down the page beyond the header's natural position
THEN the header becomes sticky (fixed to top of viewport)
AND it retains its full content (logo, nav, utility icons)
AND a subtle shadow appears to indicate elevation above content

#### Scenario: Header displays all navigation elements

WHEN the header is rendered on desktop (>768px)
THEN it displays the Atelier Marie logo (left)
AND navigation links: Welcome, Shop (with dropdown indicator), Candle Care, FAQ, B2B/Private Label, Contact
AND utility icons (right): search icon, account icon, cart icon with item count badge

#### Scenario: Cart badge reflects live item count

WHEN items are added to or removed from the cart
THEN the cart icon badge updates immediately to show the current total item count
WHEN the cart is empty
THEN no badge is displayed on the cart icon

### Requirement: Shop Mega-Dropdown

The Shop navigation item opens a dropdown revealing product subcategories for easy browsing.

#### Scenario: Shop dropdown opens on hover (desktop)

WHEN a user hovers over the "Shop" navigation link on desktop
THEN a dropdown panel appears below the header
AND it displays subcategories: All candles, Dessert candles, Luxury jars, Gift sets, Seasonal collection, Custom orders
AND each subcategory is a clickable link to the filtered shop page
AND the dropdown has a smooth fade-in transition (200ms)

#### Scenario: Shop dropdown closes appropriately

WHEN the user moves the cursor away from both the Shop link and the dropdown panel
THEN the dropdown closes after a brief delay (150ms) to prevent accidental close
WHEN the user clicks a subcategory link
THEN the dropdown closes and navigation occurs

#### Scenario: Shop dropdown keyboard accessibility

WHEN a user focuses the Shop link via keyboard (Tab) and presses Enter or Space
THEN the dropdown opens
AND focus moves to the first subcategory link
WHEN the user presses Escape
THEN the dropdown closes and focus returns to the Shop link

### Requirement: Mobile Navigation

On viewports below 768px, navigation collapses into a hamburger menu that opens a slide-out drawer.

#### Scenario: Hamburger icon replaces navigation on mobile

WHEN the viewport width is less than 768px
THEN the desktop navigation links are hidden
AND a hamburger menu icon (three horizontal lines) is displayed
AND utility icons (search, cart with badge) remain visible in the header

#### Scenario: Mobile drawer opens with full navigation

WHEN a user taps the hamburger menu icon
THEN a drawer slides in from the left
AND it contains all navigation links (Welcome, Shop with expandable subcategories, Candle Care, FAQ, B2B/Private Label, Contact)
AND a semi-transparent overlay covers the rest of the page
AND the body scroll is locked

#### Scenario: Mobile drawer closes

WHEN a user taps the overlay behind the drawer
THEN the drawer slides out and the overlay fades away
WHEN a user taps a navigation link inside the drawer
THEN the drawer closes and the user navigates to the selected page
WHEN a user taps the X close button inside the drawer
THEN the drawer closes
