## ADDED Requirements

### Requirement: Site-wide cookie consent popup
The system SHALL show a site-wide cookie consent popup when a visitor has no current consent choice for the active consent version. The popup SHALL explain necessary cookies and optional analytics cookies/storage, link to the Cookie Policy, and provide controls for accepting analytics, using necessary cookies only, and managing preferences.

#### Scenario: First visit shows popup
- **WHEN** a visitor opens any localized storefront page without a consent cookie
- **THEN** the cookie consent popup is visible
- **AND** it offers accepting analytics, necessary-only choice, and preference management

#### Scenario: Existing choice hides popup
- **WHEN** a visitor has a valid consent cookie for the current consent version
- **THEN** the cookie consent popup is not shown automatically

### Requirement: Consent preference cookie
The system SHALL persist the visitor's consent choice in a first-party preference cookie named `atelier_cookie_consent` or another documented project-specific name. The value SHALL include consent version, analytics consent boolean, timestamp, and locale. The cookie SHALL NOT contain a unique tracking identifier beyond the consent state.

#### Scenario: Necessary-only choice persisted
- **WHEN** a visitor chooses necessary cookies only
- **THEN** the consent cookie records analytics consent as false
- **AND** behavioral analytics remains disabled

#### Scenario: Analytics acceptance persisted
- **WHEN** a visitor accepts analytics
- **THEN** the consent cookie records analytics consent as true
- **AND** behavioral analytics is enabled for future eligible events

### Requirement: Consent can be changed later
The system SHALL provide a persistent way to reopen cookie settings from the Cookie Policy and global footer. Changing consent from accepted analytics to necessary-only SHALL immediately stop future behavioral analytics events and clear any unsent analytics queue.

#### Scenario: User withdraws analytics consent
- **WHEN** a visitor opens cookie settings and changes from analytics accepted to necessary only
- **THEN** no future behavioral analytics events are sent
- **AND** any queued analytics events are discarded

### Requirement: Consent version changes resurface popup
The system SHALL compare stored consent version against the current consent version. If the current version is newer, the visitor SHALL be asked for consent again.

#### Scenario: Consent version outdated
- **WHEN** a visitor has a consent cookie from an older consent version
- **THEN** the cookie consent popup is shown again

### Requirement: Consent popup accessibility
The consent popup SHALL be keyboard accessible, screen-reader understandable, and non-overlapping on mobile and desktop. It SHALL not prevent use of necessary storefront features after the visitor makes a choice.

#### Scenario: Keyboard user can choose consent
- **WHEN** a keyboard-only visitor opens the consent popup
- **THEN** focus moves through the popup controls in a logical order
- **AND** the visitor can save a choice without using a mouse

#### Scenario: Popup fits mobile viewport
- **WHEN** the popup is rendered on a mobile viewport
- **THEN** text and controls remain readable and do not overlap header, cart, or checkout controls
