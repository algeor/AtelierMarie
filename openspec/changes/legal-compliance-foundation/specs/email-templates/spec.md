## ADDED Requirements

### Requirement: Order emails include legal policy references
Order placed and payment-pending email templates SHALL include concise localized references to Terms & Conditions, withdrawal/returns information, trader contact details, and Privacy Policy links. The emails SHALL use stable public site URLs from template context instead of hardcoded localhost URLs.

#### Scenario: English order placed email includes legal references
- **WHEN** the English order placed email is rendered
- **THEN** it includes the order summary, total, Terms & Conditions link, Privacy Policy link, and trader contact email

#### Scenario: Bulgarian payment pending email includes legal references
- **WHEN** the Bulgarian payment pending email is rendered
- **THEN** it includes localized legal/policy references and payment instructions without removing the existing order summary

### Requirement: Email template context includes legal URL values
The email rendering path SHALL provide templates with public URLs for Terms & Conditions, Privacy Policy, Cookie Policy, and Contact pages, plus trader identity/contact values from the centralized legal identity source.

#### Scenario: Template receives public policy URLs
- **WHEN** an order email is rendered in either locale
- **THEN** template context includes localized public URLs for Terms, Privacy, Cookies, and Contact pages
