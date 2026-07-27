## ADDED Requirements

### Requirement: Main navigation includes Atelier link
The global header navigation SHALL include a link to the atelier story page at `/[locale]/atelier`, using the existing localized `Link` component, on all viewport sizes.

#### Scenario: Nav shows Atelier link
- **WHEN** a user views any localized storefront page
- **THEN** the header navigation includes an "Atelier" (story) link pointing to `/[locale]/atelier`

#### Scenario: Atelier link is localized
- **WHEN** the user is browsing under `/bg/...`
- **THEN** the Atelier nav link resolves to `/bg/atelier` and its label renders in Bulgarian

## MODIFIED Requirements

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
