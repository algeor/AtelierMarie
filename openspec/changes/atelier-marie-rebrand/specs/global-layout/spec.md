## MODIFIED Requirements

### Requirement: Footer with links and branding
The system SHALL render an editorial Atelier Marie footer on all localized storefront pages containing grouped navigation links, Atelier Marie social icon links, existing account/auth entry points, legal/cookie links, brand messaging, and dynamic copyright information. The footer SHALL use a soft image-led or translucent-panel composition with a large decorative `ATELIER MARIE` wordmark where space allows. Link groups SHALL follow the note direction: Explore, Help, My Account, Legal, and Social.

#### Scenario: Footer renders on localized pages
- **WHEN** any localized storefront page loads
- **THEN** the footer is visible at the bottom of the page content with existing brand text and dynamic copyright year

#### Scenario: Footer Contact link is navigable
- **WHEN** the footer renders
- **THEN** the Contact navigation item links to `/contact` through the existing localized `Link` component
- **AND** activating it navigates to the localized contact page

#### Scenario: Footer includes Atelier story link
- **WHEN** the footer renders
- **THEN** it includes an `Atelier` link to `/[locale]/atelier` through the localized `Link` component

#### Scenario: Existing footer links remain available
- **WHEN** this change updates the footer
- **THEN** existing Home, Shop, Contact, FAQ, Terms, Privacy, Cookies, cookie settings, Instagram, and TikTok destinations remain available
- **AND** auth/account/order entry points remain available where the app already exposes them

#### Scenario: Footer links are grouped by purpose
- **WHEN** the editorial footer renders
- **THEN** Home, Shop, and Atelier are grouped under Explore
- **AND** Contact and FAQ are grouped under Help
- **AND** sign-in/login, My Account, and My Orders are grouped under My Account where those routes/actions exist
- **AND** Terms, Privacy, Cookies, and cookie settings are grouped under Legal
- **AND** Instagram and TikTok are grouped under Social

#### Scenario: Footer does not invent unavailable pages
- **WHEN** the editorial footer renders
- **THEN** it does not add reference-only links such as Order Tracking, Delivery, Return, Appointment, Find a Store, Sustainability, or Giving Back unless those routes/features exist

#### Scenario: Footer includes social media section
- **WHEN** the footer renders
- **THEN** it includes Instagram and TikTok icon links that are visually grouped with the footer content

#### Scenario: Footer remains responsive
- **WHEN** the footer renders on mobile, tablet, or desktop widths
- **THEN** navigation links, social icons, brand text, copyright text, and legal links do not overlap and remain readable/clickable

#### Scenario: Footer remains compact on mobile
- **WHEN** the footer renders on a narrow mobile viewport
- **THEN** footer groups stack or use a readable two-column grid with comfortable tap targets
- **AND** the large decorative wordmark does not block links or legal text

## ADDED Requirements

### Requirement: Global rebrand preserves exposed functionality
The storefront global shell SHALL preserve existing header, language, auth, cart, announcement, consent, footer, social, legal, and navigation functionality during the rebrand. Visual simplification SHALL NOT remove already exposed controls or routes.

#### Scenario: Header utility controls remain available
- **WHEN** any localized storefront page renders after the rebrand
- **THEN** the language toggle, auth/account control, cart control, and available navigation links remain reachable

#### Scenario: Cookie controls remain available
- **WHEN** a visitor views the storefront footer or consent surfaces
- **THEN** cookie policy/settings controls remain available through existing behavior

### Requirement: Newsletter space is not faked
The editorial footer SHALL NOT render a working newsletter signup unless a real subscription flow, validation, persistence/integration, and consent/privacy copy exist. If no real flow exists, the footer SHALL use that visual space for social/contact or brand copy instead.

#### Scenario: No fake newsletter form
- **WHEN** no newsletter subscription flow exists in the app
- **THEN** the footer does not show an input that appears to subscribe users
