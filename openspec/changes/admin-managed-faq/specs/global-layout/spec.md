## ADDED Requirements

### Requirement: Footer includes FAQ link

The footer SHALL include a link to the FAQ page (`/[locale]/faq`), localized. The FAQ SHALL be discoverable from the footer and SHALL NOT be added to the main/header navigation.

#### Scenario: FAQ reachable from footer
- **WHEN** a visitor views the footer on any page
- **THEN** a localized "FAQ" (or equivalent) link is present and navigates to `/[locale]/faq`

#### Scenario: FAQ absent from main navigation
- **WHEN** a visitor views the header main navigation
- **THEN** no FAQ link is present there
