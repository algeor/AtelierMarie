# Footer — Spec

## ADDED Requirements

### Requirement: Footer Navigation Links

The footer provides secondary navigation to important pages, ensuring discoverability of content not prominent in the header.

#### Scenario: Footer displays all required links

WHEN any page renders in the storefront
THEN the footer is visible at the bottom of the page content
AND it displays navigation links: About, Candle Care, Shipping, Returns, Privacy Policy, Contact
AND each link navigates to the corresponding page
AND links use soft brown (#8B7355) text color with muted gold (#C9A96E) hover state

#### Scenario: Footer links are organized in columns on desktop

WHEN the footer renders on a desktop viewport (>1024px)
THEN links are organized in logical columns (e.g., "Shop", "Help", "Company")
AND columns are evenly spaced within the footer container
AND the layout uses generous padding (48–64px vertical)

#### Scenario: Footer links stack on mobile

WHEN the footer renders on a mobile viewport (<768px)
THEN link groups stack vertically
AND each link has a minimum 44px touch target height
AND spacing between groups provides clear visual separation

### Requirement: Social Media Icons

The footer includes social media links connecting customers to the brand's social presence.

#### Scenario: Social media icons are displayed

WHEN the footer renders
THEN Instagram and TikTok icons are displayed
AND each icon links to the respective brand profile (opens in new tab with rel="noopener noreferrer")
AND icons use soft brown color with muted gold hover state
AND icons have a minimum 44px touch target size

#### Scenario: Social icons have accessible labels

WHEN a screen reader encounters the social icons
THEN each icon has an aria-label describing the destination (e.g., "Follow us on Instagram", "Follow us on TikTok")

#### Scenario: Social icons hover animation

WHEN a user hovers over a social media icon
THEN the icon transitions to muted gold color with a 200ms ease transition
AND optionally a subtle scale transform (1.05x) for tactile feedback

### Requirement: Payment Method Placeholders

The footer displays payment method icons to build trust and indicate accepted payment options.

#### Scenario: Payment icons are displayed

WHEN the footer renders
THEN payment method icon placeholders are displayed (Visa, Mastercard, and optionally iDEAL, PayPal, or others relevant to the market)
AND icons are displayed in a horizontal row
AND icons are appropriately sized (small, ~32px height) and use muted/grayscale styling to avoid visual clutter

#### Scenario: Payment icons are non-interactive

WHEN a user views the payment method icons
THEN the icons are purely decorative (not clickable)
AND they have role="img" and appropriate alt text for accessibility (e.g., "Accepted payment methods: Visa, Mastercard")

### Requirement: Footer Renders on All Pages

The footer is a consistent presence across the entire storefront.

#### Scenario: Footer is present on homepage

WHEN a user is on the homepage
THEN the footer is rendered below all page content

#### Scenario: Footer is present on product pages

WHEN a user is on a product listing or product detail page
THEN the footer is rendered below all page content

#### Scenario: Footer is present on content pages

WHEN a user is on Contact, FAQ, Candle Care, or any other content page
THEN the footer is rendered below all page content
AND the footer content and layout is identical across all pages
