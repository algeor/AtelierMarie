## MODIFIED Requirements

### Requirement: Footer with links and branding
The system SHALL render a footer on all pages containing navigation links (Home, Shop, Contact), social media icons (Instagram), brand messaging, and copyright information.

#### Scenario: Footer renders on all pages
- **WHEN** any page loads
- **THEN** the footer is visible at the bottom of the page content with navigation links (Home → /, Shop → /products, Contact → /contact), social media icons (Instagram), brand text ("Handcrafted with love"), and dynamic copyright year

#### Scenario: Footer links are navigable
- **WHEN** a user clicks a footer link (Home, Shop, or Contact)
- **THEN** they are navigated to the corresponding page (/, /products, or /contact)

#### Scenario: Footer includes social media section
- **WHEN** the footer renders
- **THEN** it includes a social media section with an Instagram icon link, visually separated from the navigation links
