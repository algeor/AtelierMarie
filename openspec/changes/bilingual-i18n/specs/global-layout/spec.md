## MODIFIED Requirements

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
