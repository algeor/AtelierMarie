## ADDED Requirements

### Requirement: Subdirectory-based locale routing
The system SHALL serve all user-facing pages under a locale prefix (`/bg/...` or `/en/...`). The `[locale]` segment SHALL be a dynamic route parameter that determines the active language for the page.

#### Scenario: Bulgarian product listing
- **WHEN** a user navigates to `/bg/products`
- **THEN** the products page renders with Bulgarian UI strings and product content

#### Scenario: English product listing
- **WHEN** a user navigates to `/en/products`
- **THEN** the products page renders with English UI strings and product content

#### Scenario: Invalid locale in URL
- **WHEN** a user navigates to `/de/products` (unsupported locale)
- **THEN** the system redirects to `/en/products`

### Requirement: Root URL redirect
The system SHALL redirect requests to the bare root URL (`/`) to the appropriate locale-prefixed path based on the detected locale.

#### Scenario: Bulgarian user visits root
- **WHEN** a Bulgarian-language browser requests `/`
- **THEN** the system responds with a 307 redirect to `/bg/`

#### Scenario: English user visits root
- **WHEN** a non-Bulgarian browser requests `/`
- **THEN** the system responds with a 307 redirect to `/en/`

#### Scenario: User with saved preference visits root
- **WHEN** a user with `NEXT_LOCALE=bg` cookie requests `/`
- **THEN** the system redirects to `/bg/` (cookie takes priority)

### Requirement: SEO alternate language tags
The system SHALL include `hreflang` link tags on every page, pointing to the alternate-language version of the same page.

#### Scenario: English page includes Bulgarian alternate
- **WHEN** a user views `/en/products/lavender-dream-300ml`
- **THEN** the page includes `<link rel="alternate" hreflang="bg" href="/bg/products/lavender-dream-300ml">`

#### Scenario: Bulgarian page includes English alternate
- **WHEN** a user views `/bg/products`
- **THEN** the page includes `<link rel="alternate" hreflang="en" href="/en/products">`

### Requirement: HTML lang attribute
The system SHALL set the `<html lang>` attribute to match the active locale.

#### Scenario: Bulgarian page lang attribute
- **WHEN** a user views any page under `/bg/...`
- **THEN** the HTML element has `lang="bg"`

#### Scenario: English page lang attribute
- **WHEN** a user views any page under `/en/...`
- **THEN** the HTML element has `lang="en"`
