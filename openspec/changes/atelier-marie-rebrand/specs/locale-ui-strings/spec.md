## MODIFIED Requirements

### Requirement: All user-facing surfaces use translation system
The system SHALL use the translation system for ALL user-facing text including: announcement bar, header, footer, product UI, cart, checkout, orders, admin panel, auth pages, account pages, rebrand homepage copy, landing category labels, trust recap copy, FAQ category/accordion labels, branded error pages, footer group headings, and rebrand-specific admin labels. No hardcoded user-facing strings outside of translation files.

#### Scenario: Announcement bar translated
- **WHEN** a user views any page under `/bg/...`
- **THEN** the announcement bar content renders in Bulgarian

#### Scenario: Footer translated
- **WHEN** a user views any page under `/en/...`
- **THEN** the footer content renders in English

#### Scenario: Rebrand homepage strings translated
- **WHEN** a user views the rebranded homepage under `/bg/...`
- **THEN** hero copy, category labels, trust recap text, CTAs, and featured-section labels render in Bulgarian from message files

#### Scenario: Error page strings translated
- **WHEN** a user views a branded 404 or generic error page under `/bg/...`
- **THEN** recovery copy and actions render in Bulgarian from message files

#### Scenario: Admin rebrand strings translated
- **WHEN** an admin views rebranded admin navigation, filters, actions, empty states, or save/error feedback in either supported locale
- **THEN** the strings render through the translation system for the active locale
