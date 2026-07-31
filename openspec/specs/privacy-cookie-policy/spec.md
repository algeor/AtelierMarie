# privacy-cookie-policy Specification

## Purpose
TBD - created by archiving change legal-compliance-foundation. Update Purpose after archive.
## Requirements
### Requirement: Localized privacy policy page
The system SHALL provide a public localized Privacy Policy page at `/[locale]/privacy`. The page SHALL define localized metadata and alternate links, identify the trader/controller, describe the personal data categories processed by the current app, explain high-level purposes and legal bases, list relevant recipients/processors, describe retention references, explain consumer data rights, and provide a contact method for privacy requests.

#### Scenario: English privacy policy renders
- **WHEN** `/en/privacy` is rendered
- **THEN** the page shows English privacy content covering orders, delivery data, contact messages, comments, account data, cookies, payment references, and transactional email delivery

#### Scenario: Bulgarian privacy policy renders
- **WHEN** `/bg/privacy` is rendered
- **THEN** the page shows Bulgarian privacy content with localized metadata and alternate links

#### Scenario: Privacy policy matches current integrations
- **WHEN** the Privacy Policy describes third-party recipients
- **THEN** it includes only current or configured processors such as Google OAuth, Stripe payment references, email delivery, hosting, and courier/order fulfillment where applicable
- **AND** it does not claim analytics, advertising pixels, newsletter marketing, or profiling unless those features exist in the app

### Requirement: Localized cookie policy page
The system SHALL provide a public localized Cookie Policy page at `/[locale]/cookies`. The page SHALL list current cookies by name or category, including the backend session cookie, auth cookie, and locale cookie, with purpose, type, and duration where known. The page SHALL state that non-essential analytics/advertising cookies are not used when the codebase contains no such tracking.

#### Scenario: Cookie inventory renders
- **WHEN** `/en/cookies` is rendered
- **THEN** the page lists the session, auth, and locale cookies with their purpose and necessity/preference classification

#### Scenario: No consent banner required for current cookie set
- **WHEN** the site only uses necessary/session/auth/locale cookies
- **THEN** the system does not render a marketing-style consent banner
- **AND** the Cookie Policy explains that a consent mechanism will be needed before non-essential tracking is added

### Requirement: Legal policy routes are discoverable
Privacy and Cookie Policy routes SHALL be included in localized navigation surfaces and sitemap entries where static public routes are listed.

#### Scenario: Sitemap includes legal routes
- **WHEN** the sitemap is generated
- **THEN** `/en/privacy`, `/bg/privacy`, `/en/cookies`, and `/bg/cookies` are included with localized alternates

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

