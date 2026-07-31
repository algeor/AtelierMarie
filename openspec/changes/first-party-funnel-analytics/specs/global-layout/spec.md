## ADDED Requirements

### Requirement: Global layout hosts consent controls
The global storefront layout SHALL render the cookie consent popup and expose a persistent cookie settings entry point from global navigation or footer areas. Consent controls SHALL appear on localized storefront pages and SHALL NOT appear inside the admin layout.

#### Scenario: Consent popup available on storefront pages
- **WHEN** a visitor opens any localized storefront page without current consent
- **THEN** the global layout renders the cookie consent popup

#### Scenario: Admin layout excludes storefront consent popup
- **WHEN** an admin opens `/admin` or an admin subpage
- **THEN** the storefront consent popup is not rendered inside the admin layout

#### Scenario: Footer links to cookie settings
- **WHEN** a visitor views the footer
- **THEN** a cookie settings or Cookie Policy link is available so consent can be reviewed later
