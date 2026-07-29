## ADDED Requirements

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
