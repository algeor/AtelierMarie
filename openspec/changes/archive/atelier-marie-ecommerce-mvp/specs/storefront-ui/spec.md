## ADDED Requirements

### Requirement: Announcement bar displays rotating messages
The system SHALL render a top announcement bar with configurable messages including "Handcrafted candles for every occasion" and "Free delivery over [configurable amount]". The bar SHALL be dismissible and persist dismissal state in the session.

#### Scenario: Announcement bar renders on page load
- **WHEN** a user visits any page
- **THEN** the announcement bar is visible at the top with the configured message text

#### Scenario: Free delivery threshold is configurable
- **WHEN** the admin sets the free delivery threshold to €50
- **THEN** the announcement bar displays "Free delivery over €50"

### Requirement: Header with navigation and utility icons
The system SHALL render a sticky header with the Atelier Marie logo text, a navigation menu (Welcome, Shop with dropdown, Candle Care, FAQ, B2B / Private Label, Contact), and utility icons for search, account, and cart (with item count badge).

#### Scenario: Shop dropdown displays subcategories
- **WHEN** a user hovers over or taps "Shop" in the navigation
- **THEN** a dropdown displays: All candles, Dessert candles, Luxury jars, Gift sets, Seasonal collection, Custom orders

#### Scenario: Cart icon shows item count
- **WHEN** the user has 3 items in their cart
- **THEN** the cart icon displays a badge with "3"

#### Scenario: Mobile navigation collapses to hamburger menu
- **WHEN** the viewport width is below 768px
- **THEN** the navigation collapses into a hamburger menu icon that opens a slide-out drawer

### Requirement: Hero section with editorial imagery and CTAs
The system SHALL render a hero section with a large editorial candle image placeholder, headline "Handcrafted candles for beautiful moments", subtext "Quiet luxury, soft scents, and handmade details for spaces you love.", and two CTA buttons: "Explore collection" and "Custom order".

#### Scenario: Hero section renders on homepage
- **WHEN** a user visits the homepage
- **THEN** the hero section is displayed with image, headline, subtext, and both CTA buttons

#### Scenario: Explore collection CTA navigates to shop
- **WHEN** a user clicks "Explore collection"
- **THEN** the user is navigated to the /shop page showing all products

### Requirement: Product grid displays minimal luxury cards
The system SHALL render a responsive product grid with cards showing: product image, product name, price, quick-add button, choose-options button (when variants exist), and wishlist heart icon.

#### Scenario: Product cards render in responsive grid
- **WHEN** a user visits the shop page with 8 products available
- **THEN** 8 product cards are displayed in a responsive grid (4 columns desktop, 2 columns tablet, 1 column mobile)

#### Scenario: Quick add button adds default variant to cart
- **WHEN** a user clicks "Quick add" on a product without variants
- **THEN** 1 unit of that product is added to the cart and the cart count updates

#### Scenario: Choose options button appears for variant products
- **WHEN** a product has multiple size or scent variants
- **THEN** the card displays "Choose options" instead of "Quick add" which opens the PDP

### Requirement: Product detail page with full product information
The system SHALL render a PDP with image gallery, product title, price, scent selector, size selector, burn time display, wax type display, quantity selector, "Add to cart" button, "Buy now" button, candle care accordion, shipping/returns accordion, and recommended products section.

#### Scenario: PDP displays all product attributes
- **WHEN** a user navigates to /products/{slug}
- **THEN** the page displays the product's gallery, title, price, scent, size, burn time, wax type, and action buttons

#### Scenario: Quantity selector updates add-to-cart quantity
- **WHEN** a user sets quantity to 3 and clicks "Add to cart"
- **THEN** 3 units of the product are added to the cart

#### Scenario: Accordions expand and collapse
- **WHEN** a user clicks the "Candle Care" accordion header
- **THEN** the candle care content expands; clicking again collapses it

### Requirement: Cart drawer slides in from right
The system SHALL render a slide-in cart drawer from the right side showing cart items with quantity controls, remove button, estimated total, and checkout button. An empty state message SHALL display when the cart is empty.

#### Scenario: Cart drawer opens on cart icon click
- **WHEN** a user clicks the cart icon in the header
- **THEN** a drawer slides in from the right showing cart contents

#### Scenario: Empty cart shows message
- **WHEN** the cart has no items and the drawer is opened
- **THEN** the drawer displays an empty state with message and "Continue shopping" link

#### Scenario: Quantity controls update totals
- **WHEN** a user increases quantity of an item from 1 to 2
- **THEN** the line item subtotal and estimated total update immediately

### Requirement: Search overlay with suggestions
The system SHALL render a full-screen or modal search overlay with an input field, live product suggestions as the user types, and a trending products section when the input is empty.

#### Scenario: Search overlay opens on search icon click
- **WHEN** a user clicks the search icon
- **THEN** a search overlay appears with focus on the input field

#### Scenario: Product suggestions appear while typing
- **WHEN** a user types "vanilla" in the search input
- **THEN** matching products are displayed below the input within 300ms of keystroke debounce

#### Scenario: Trending products shown on empty input
- **WHEN** the search overlay is open with an empty input
- **THEN** trending products are displayed as suggestions

### Requirement: Contact form with validation
The system SHALL render a contact section with name, email, phone (optional), and message fields, plus a submit button. Client-side validation SHALL enforce required fields and email format.

#### Scenario: Valid contact form submission
- **WHEN** a user fills in name, valid email, and message, then clicks submit
- **THEN** the form submits successfully and displays a confirmation message

#### Scenario: Invalid email shows error
- **WHEN** a user enters "notanemail" in the email field and attempts to submit
- **THEN** an inline error message appears indicating invalid email format

### Requirement: Newsletter signup section
The system SHALL render a newsletter signup section with email input and copy text "Join Atelier Marie for new releases, gift ideas, seasonal collections and special offers."

#### Scenario: Newsletter signup submits email
- **WHEN** a user enters a valid email and clicks subscribe
- **THEN** the email is recorded and a success confirmation appears

### Requirement: Footer with links and social icons
The system SHALL render a footer with links to About, Candle Care, Shipping, Returns, Privacy Policy, Contact; social media icons for Instagram and TikTok; and payment method icon placeholders.

#### Scenario: Footer renders on all pages
- **WHEN** a user scrolls to the bottom of any page
- **THEN** the footer is visible with all specified links, social icons, and payment icons

### Requirement: Responsive mobile-first design
The system SHALL be fully responsive with mobile-first breakpoints. All interactive elements SHALL have minimum 44px touch targets on mobile. Typography, spacing, and grid SHALL adapt gracefully across mobile (< 768px), tablet (768–1024px), and desktop (> 1024px).

#### Scenario: Mobile layout adapts correctly
- **WHEN** the viewport is 375px wide
- **THEN** the product grid shows 1 column, navigation is hamburger menu, hero text is stacked, and all touch targets are >= 44px

### Requirement: Luxury visual design system
The system SHALL use a soft luxury palette (warm ivory, cream, champagne beige, dusty pink, soft brown, muted gold accents), elegant serif for headings, clean sans-serif for body, large whitespace, soft rounded image cards, minimal borders, and smooth hover animations.

#### Scenario: Design tokens applied consistently
- **WHEN** any page is rendered
- **THEN** colors, typography, spacing, and border-radius conform to the defined luxury design tokens

#### Scenario: Hover animations are smooth
- **WHEN** a user hovers over a product card or button
- **THEN** a smooth transition (200–300ms ease) is applied for scale, shadow, or color changes
