## MODIFIED Requirements

### Requirement: Session stores preferred locale
The sessions table SHALL include a `preferred_locale` column (TEXT, values: `bg` or `en`, default `en`). The locale preference SHALL be persisted when detected or manually changed by the user.

#### Scenario: New session gets default locale
- **WHEN** a new session is created for a user with no cookie
- **THEN** `preferred_locale` is set based on `Accept-Language` detection (or `en` if no `bg` detected)

#### Scenario: Locale preference updated on toggle
- **WHEN** a user switches language via the toggle and the frontend sends a preference update
- **THEN** the session's `preferred_locale` is updated to the new locale

#### Scenario: Locale persisted for order context
- **WHEN** an order is placed
- **THEN** the order can reference the session's `preferred_locale` for future email localization
