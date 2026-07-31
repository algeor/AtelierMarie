## Purpose

Defines global storefront layout behavior shared across localized pages, including header, footer, language, fonts, and announcement surfaces.
## Requirements
### Requirement: Header includes language toggle
The global layout header SHALL include a language toggle button (flag icon) in the right-side utility area, positioned adjacent to the auth and cart controls. The toggle SHALL be visible on all viewport sizes (not collapsed into mobile menu).

#### Scenario: Header shows toggle on desktop
- **WHEN** a user views any page on a desktop viewport
- **THEN** the header displays a flag button (🇬🇧 when viewing BG, 🇧🇬 when viewing EN) in the right section

#### Scenario: Header shows toggle on mobile
- **WHEN** a user views any page on a mobile viewport
- **THEN** the flag toggle remains visible in the header (not inside hamburger menu)

### Requirement: HTML lang attribute set by locale
The root `<html>` element SHALL have its `lang` attribute set to the active locale (`bg` or `en`) determined by the `[locale]` route segment.

#### Scenario: Bulgarian locale sets lang
- **WHEN** a page is rendered under `/bg/...`
- **THEN** `<html lang="bg">` is rendered

#### Scenario: English locale sets lang
- **WHEN** a page is rendered under `/en/...`
- **THEN** `<html lang="en">` is rendered

### Requirement: Fonts include Cyrillic subset
The system SHALL load Playfair Display and Inter fonts with both `latin` and `cyrillic` subsets to support Bulgarian text rendering.

#### Scenario: Cyrillic text renders correctly
- **WHEN** a page displays Bulgarian text (e.g., "Лавандулов сън")
- **THEN** the text renders in the correct font (Playfair Display for headings, Inter for body) without fallback to system fonts

### Requirement: Footer with links and branding
The system SHALL render a footer on all localized storefront pages containing navigation links (including a link to the atelier story page), Atelier Marie social icon links, brand messaging, and copyright information.

#### Scenario: Footer renders on localized pages
- **WHEN** any localized storefront page loads
- **THEN** the footer is visible at the bottom of the page content with existing brand text and dynamic copyright year

#### Scenario: Footer Contact link is navigable
- **WHEN** the footer renders
- **THEN** the Contact navigation item links to `/contact` through the existing localized `Link` component
- **AND** activating it navigates to the localized contact page

#### Scenario: Footer includes Atelier story link
- **WHEN** the footer renders
- **THEN** it includes an "Atelier" link to `/[locale]/atelier` through the localized `Link` component

#### Scenario: Existing footer links remain unchanged unless in scope
- **WHEN** this change updates the footer
- **THEN** existing Home and Shop links keep their current localized destinations
- **AND** unrelated placeholder links are not changed unless covered by another change

#### Scenario: Footer includes social media section
- **WHEN** the footer renders
- **THEN** it includes Instagram and TikTok icon links that are visually grouped with or adjacent to footer navigation without disrupting the existing branding area

#### Scenario: Footer remains responsive
- **WHEN** the footer renders on mobile, tablet, or desktop widths
- **THEN** navigation links, social icons, brand text, and copyright text do not overlap and remain readable/clickable

### Requirement: Managed announcement bar
The global storefront layout SHALL render the existing top announcement bar from the managed site banner API instead of hardcoded static copy. The announcement bar SHALL appear above the header when the public banner endpoint returns an active banner, and SHALL be hidden when no banner is active. The bar SHALL display localized message text, optional link label and URL, and a dismiss control.

Dismissal SHALL be keyed by the banner's public dismiss key, not a single static storage key, so updated banner content or schedule can be shown even if a user dismissed an older banner. The banner SHALL remain responsive and SHALL NOT overlap header controls on mobile or desktop.

#### Scenario: Active managed banner renders above header
- **WHEN** the public banner endpoint returns an active banner
- **THEN** the announcement bar renders above the header with the localized message

#### Scenario: No active banner hides bar
- **WHEN** the public banner endpoint returns `banner = null`
- **THEN** no announcement bar is rendered

#### Scenario: Banner link renders when configured
- **WHEN** the active banner response includes `link_url` and `link_label`
- **THEN** the announcement bar renders a link using those values

#### Scenario: Dismissal is scoped to banner version
- **WHEN** a user dismisses banner version A and an admin later publishes banner version B
- **THEN** banner version B is shown to that user despite the prior dismissal

#### Scenario: Announcement bar remains responsive
- **WHEN** the banner renders on mobile, tablet, or desktop widths
- **THEN** message text, optional link, and dismiss control do not overlap and remain readable/clickable

### Requirement: Footer includes FAQ link

The footer SHALL include a link to the FAQ page (`/[locale]/faq`), localized. The FAQ SHALL be discoverable from the footer and SHALL NOT be added to the main/header navigation.

#### Scenario: FAQ reachable from footer
- **WHEN** a visitor views the footer on any page
- **THEN** a localized "FAQ" (or equivalent) link is present and navigates to `/[locale]/faq`

#### Scenario: FAQ absent from main navigation
- **WHEN** a visitor views the header main navigation
- **THEN** no FAQ link is present there

### Requirement: Main navigation includes Atelier link
The global header navigation SHALL include a link to the atelier story page at `/[locale]/atelier`, using the existing localized `Link` component, on all viewport sizes.

#### Scenario: Nav shows Atelier link
- **WHEN** a user views any localized storefront page
- **THEN** the header navigation includes an "Atelier" (story) link pointing to `/[locale]/atelier`

#### Scenario: Atelier link is localized
- **WHEN** the user is browsing under `/bg/...`
- **THEN** the Atelier nav link resolves to `/bg/atelier` and its label renders in Bulgarian

### Requirement: Footer includes legal policy links
The global storefront footer SHALL include localized links to Terms & Conditions, Privacy Policy, Cookie Policy, FAQ, Contact, and existing social links. The footer SHALL NOT add a standalone Returns link while returns are covered inside Terms & Conditions.

#### Scenario: Footer shows legal links
- **WHEN** the footer renders on a localized storefront page
- **THEN** Terms & Conditions, Privacy Policy, and Cookie Policy links are visible and navigable through localized routes

#### Scenario: Footer avoids obsolete returns and ODR links
- **WHEN** the footer renders
- **THEN** it does not show a standalone Returns link
- **AND** it does not include an outdated EU ODR platform link

### Requirement: Footer exposes quiet trader contact discoverability
The footer SHALL make legal/trader contact discoverable without turning the layout into a legal notice block.

#### Scenario: Trader contact remains discoverable
- **WHEN** a customer needs legal or order contact details
- **THEN** footer navigation provides access to Terms, Privacy, and Contact pages that contain the trader/contact information

### Requirement: Global layout hosts consent controls
The global storefront layout SHALL render the cookie consent popup and expose a persistent cookie settings entry point from global navigation or footer areas. Consent controls SHALL appear on localized storefront pages and SHALL NOT appear inside the admin layout.

#### Scenario: Consent popup available on storefront pages
- **WHEN** a visitor opens any localized storefront page without current consent
- **THEN** the global layout renders the cookie consent popup

#### Scenario: Admin layout excludes storefront consent popup
- **WHEN** an admin opens `/admin` or an admin subpage
- **THEN** the storefront consent popup is not rendered inside the admin layout

#### Scenario: Footer links to cookie settings
- **WHEN** a visitor views the footer
- **THEN** a cookie settings or Cookie Policy link is available so consent can be reviewed later

