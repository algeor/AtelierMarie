## ADDED Requirements

### Requirement: Detect user locale from browser language
The system SHALL read the `Accept-Language` HTTP header on incoming requests and determine the user's preferred locale. If the header contains `bg` (in any priority position), the locale SHALL be set to `bg`. Otherwise, the locale SHALL default to `en`.

#### Scenario: Bulgarian browser visits site
- **WHEN** a request arrives with `Accept-Language: bg,en;q=0.9`
- **THEN** the detected locale is `bg`

#### Scenario: English browser visits site
- **WHEN** a request arrives with `Accept-Language: en-US,en;q=0.9`
- **THEN** the detected locale is `en`

#### Scenario: Non-Bulgarian, non-English browser visits site
- **WHEN** a request arrives with `Accept-Language: de,fr;q=0.8`
- **THEN** the detected locale is `en` (default)

#### Scenario: No Accept-Language header
- **WHEN** a request arrives without an `Accept-Language` header
- **THEN** the detected locale is `en` (default)

### Requirement: Persist locale preference in cookie
The system SHALL store the user's locale preference in a `NEXT_LOCALE` cookie. Once set, the cookie SHALL take precedence over `Accept-Language` detection on subsequent requests.

#### Scenario: Cookie overrides header detection
- **WHEN** a request has `NEXT_LOCALE=bg` cookie AND `Accept-Language: en`
- **THEN** the effective locale is `bg` (cookie wins)

#### Scenario: Cookie set on first visit
- **WHEN** middleware detects locale and redirects to `/bg/` or `/en/`
- **THEN** a `NEXT_LOCALE` cookie is set with the detected value

### Requirement: Store locale preference server-side
The system SHALL persist the user's preferred locale in the `sessions` table (`preferred_locale` column) for server-side use (emails, order records).

#### Scenario: Locale saved to session
- **WHEN** a user's locale is determined (detection or manual switch)
- **THEN** the backend stores `preferred_locale` = `bg` or `en` in the session row
