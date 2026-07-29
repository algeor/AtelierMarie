## MODIFIED Requirements

### Requirement: Footer with links and branding
The system SHALL render a footer on all localized storefront pages containing navigation links, a Terms & Conditions link, Atelier Marie social icon links, brand messaging, and copyright information. The footer SHALL NOT add a standalone promotional Returns link; returns information is discoverable through Terms & Conditions.

#### Scenario: Footer renders on localized pages
- **WHEN** any localized storefront page loads
- **THEN** the footer is visible at the bottom of the page content with existing brand text and dynamic copyright year

#### Scenario: Footer Contact link is navigable
- **WHEN** the footer renders
- **THEN** the Contact navigation item links to `/contact` through the existing localized `Link` component
- **AND** activating it navigates to the localized contact page

#### Scenario: Footer Terms link is navigable
- **WHEN** the footer renders
- **THEN** the Terms & Conditions navigation item links to `/terms` through the existing localized `Link` component
- **AND** activating it navigates to the localized Terms & Conditions page

#### Scenario: Footer does not promote returns separately
- **WHEN** the footer renders
- **THEN** it does not include a separate Returns or Free Returns navigation item
- **AND** returns information remains available through Terms & Conditions

#### Scenario: Existing footer links remain unchanged unless in scope
- **WHEN** this change updates the footer
- **THEN** existing Home and Shop links keep their current localized destinations
- **AND** unrelated placeholder links, such as About, are not changed unless covered by another change

#### Scenario: Footer includes social media section
- **WHEN** the footer renders
- **THEN** it includes Instagram and TikTok icon links that are visually grouped with or adjacent to footer navigation without disrupting the existing branding area

#### Scenario: Footer remains responsive
- **WHEN** the footer renders on mobile, tablet, or desktop widths
- **THEN** navigation links, social icons, brand text, and copyright text do not overlap and remain readable/clickable
