## ADDED Requirements

### Requirement: Language toggle displays opposite locale flag
The system SHALL display a flag icon representing the language NOT currently active. Clicking the flag SHALL switch to that language.

#### Scenario: Viewing in Bulgarian shows English flag
- **WHEN** a user is viewing a page under `/bg/...`
- **THEN** the header displays a 🇬🇧 (UK/English) flag button

#### Scenario: Viewing in English shows Bulgarian flag
- **WHEN** a user is viewing a page under `/en/...`
- **THEN** the header displays a 🇧🇬 (Bulgarian) flag button

### Requirement: Toggle switches locale and navigates
The system SHALL navigate the user to the equivalent page in the other locale when the toggle is clicked, preserving the current path.

#### Scenario: Switch from BG to EN on product page
- **WHEN** a user clicks the 🇬🇧 flag while on `/bg/products/lavender-dream-300ml`
- **THEN** the user is navigated to `/en/products/lavender-dream-300ml`

#### Scenario: Switch from EN to BG on checkout
- **WHEN** a user clicks the 🇧🇬 flag while on `/en/checkout`
- **THEN** the user is navigated to `/bg/checkout`

### Requirement: Toggle updates locale cookie
The system SHALL update the `NEXT_LOCALE` cookie when the user clicks the language toggle, so the preference persists on subsequent visits.

#### Scenario: Cookie updated on toggle click
- **WHEN** a user on `/en/...` clicks the 🇧🇬 flag
- **THEN** the `NEXT_LOCALE` cookie is set to `bg`

### Requirement: Toggle placement in header
The language toggle SHALL be placed in the header, on the right side, adjacent to the auth and cart controls. On mobile viewports, the flag SHALL remain visible (not hidden in a hamburger menu).

#### Scenario: Toggle visible on desktop
- **WHEN** a user views the site on a desktop viewport
- **THEN** the flag toggle is visible in the header right section, before or after the auth control

#### Scenario: Toggle visible on mobile
- **WHEN** a user views the site on a mobile viewport
- **THEN** the flag toggle is visible in the header (not collapsed into a menu)
