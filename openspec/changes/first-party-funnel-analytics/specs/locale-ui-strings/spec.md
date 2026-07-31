## ADDED Requirements

### Requirement: Consent and analytics strings localized
The system SHALL add localized message strings for cookie consent popup text, consent actions, analytics settings, analytics-disabled notices, cookie inventory additions, privacy policy analytics copy, and admin analytics UI labels in `messages/en.json` and `messages/bg.json`.

#### Scenario: Consent popup localized in English
- **WHEN** a visitor opens an English localized page and the consent popup appears
- **THEN** all popup text and controls render from English message strings

#### Scenario: Consent popup localized in Bulgarian
- **WHEN** a visitor opens a Bulgarian localized page and the consent popup appears
- **THEN** all popup text and controls render from Bulgarian message strings

#### Scenario: Admin analytics localized
- **WHEN** an admin opens the analytics panel in either supported locale
- **THEN** headings, filters, metric labels, empty states, warnings, and export labels render through the translation system
