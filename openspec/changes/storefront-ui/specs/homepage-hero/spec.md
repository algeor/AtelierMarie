# Homepage & Hero — Spec

## ADDED Requirements

### Requirement: Editorial Hero Section

The homepage hero section communicates the brand essence with a large editorial visual, compelling headline, descriptive subtext, and two clear calls to action.

#### Scenario: Hero section renders with full content on desktop

WHEN a user visits the homepage on a desktop viewport
THEN a large hero section is displayed spanning the full viewport width
AND it contains a prominent image placeholder (gradient or editorial photo area)
AND the headline reads "Handcrafted candles for beautiful moments"
AND the subtext reads "Quiet luxury, soft scents, and handmade details for spaces you love."
AND two CTA buttons are displayed: "Explore collection" (primary) and "Custom order" (secondary)
AND the layout uses generous vertical padding (80–120px)

#### Scenario: Hero CTAs navigate correctly

WHEN a user clicks the "Explore collection" CTA button
THEN they are navigated to /shop
WHEN a user clicks the "Custom order" CTA button
THEN they are navigated to the custom order page or contact page with custom order context

#### Scenario: Hero section adapts to mobile

WHEN a user views the homepage on a mobile viewport (<768px)
THEN the hero section stacks content vertically
AND the headline font size reduces while remaining prominent
AND CTAs stack vertically or remain side-by-side if space permits (minimum 44px height each)
AND vertical padding reduces proportionally (48–64px)
AND the image placeholder adapts to a portrait or square aspect ratio

#### Scenario: Hero image placeholder maintains visual quality

WHEN the hero section renders without a real product photograph (MVP state)
THEN a gradient placeholder using brand colors (warm ivory to cream to champagne beige) is displayed
AND the placeholder feels intentional and premium, not broken or incomplete
AND the gradient or pattern complements the text overlay readability

### Requirement: Featured Products Section

Below the hero, a curated selection of featured products encourages browsing.

#### Scenario: Featured products display on homepage

WHEN the homepage loads below the hero section
THEN a "Featured" or "Our Favorites" section is displayed
AND it shows a curated grid of product cards (4 on desktop, 2 on tablet, 1 on mobile)
AND each product card follows the standard product card design (image, name, price, action)
AND the section includes a "View all" link to /shop

#### Scenario: Featured products handle loading state

WHEN featured products are being fetched from the API
THEN skeleton loading placeholders are displayed in the grid positions
AND the skeletons match the card dimensions and layout

### Requirement: Homepage Newsletter CTA

A newsletter signup prompt on the homepage captures visitor emails.

#### Scenario: Newsletter section displays on homepage

WHEN a user scrolls to the newsletter section on the homepage
THEN a visually distinct section is displayed with a warm background
AND copy reads "Join Atelier Marie for new releases, gift ideas, seasonal collections and special offers."
AND an email input field and subscribe button are present
AND the section uses generous padding and centered layout

#### Scenario: Newsletter signup succeeds from homepage

WHEN a user enters a valid email address and clicks subscribe
THEN a success message is displayed (e.g., "Welcome to Atelier Marie!")
AND the input field and button are replaced by the confirmation
AND a newsletter_signup event is emitted
