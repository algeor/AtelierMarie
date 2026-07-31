## ADDED Requirements

### Requirement: Cookie inventory includes consent and analytics use
The Cookie Policy SHALL list all cookies and similar storage used after this change, including necessary session/auth/locale cookies, the new consent preference cookie, and the analytics use of the existing session cookie when analytics consent is granted.

#### Scenario: Cookie policy lists consent cookie
- **WHEN** a visitor opens the Cookie Policy
- **THEN** the cookie inventory includes the consent preference cookie name, purpose, type, and retention

#### Scenario: Cookie policy explains analytics session use
- **WHEN** analytics consent is enabled in the app
- **THEN** the Cookie Policy explains that accepted first-party analytics events are linked to the existing session cookie as a pseudonymous session key

### Requirement: No-tracking copy replaced before launch
The Privacy Policy and Cookie Policy SHALL no longer claim that the current app has no analytics once analytics collection is enabled. The policies SHALL instead state that optional first-party analytics is used only after consent and does not include advertising pixels, cross-site tracking, session replay, heatmaps, or profiling.

#### Scenario: Analytics enabled policy copy is accurate
- **WHEN** analytics collection is enabled in production
- **THEN** the privacy and cookie policy pages describe first-party analytics and consent controls instead of saying no analytics exists

### Requirement: Analytics purpose and retention disclosed
The Privacy Policy and Cookie Policy SHALL disclose the purpose, categories of data, retention period, legal basis/consent dependency, and withdrawal mechanism for analytics events.

#### Scenario: Visitor can understand analytics data use
- **WHEN** a visitor reads the analytics section of the Privacy Policy
- **THEN** the page explains the analytics purpose, event categories, retention period, and how to withdraw consent

### Requirement: Localized policy text
The analytics, consent, and cookie inventory policy copy SHALL be available in both supported locales.

#### Scenario: English policy updated
- **WHEN** a visitor opens `/en/cookies` or `/en/privacy`
- **THEN** the analytics and consent copy appears in English

#### Scenario: Bulgarian policy updated
- **WHEN** a visitor opens `/bg/cookies` or `/bg/privacy`
- **THEN** the analytics and consent copy appears in Bulgarian through the translation files
