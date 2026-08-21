## ADDED Requirements

### Requirement: Product detail shows suggested products
The storefront SHALL render a localized "Suggested for you" section on product detail pages when recommended products are available.

#### Scenario: Suggested products render below detail content
- **WHEN** a product detail page receives one or more recommended products
- **THEN** it displays them in a responsive product card layout below the main product detail content

#### Scenario: Suggested section omitted when empty
- **WHEN** the recommendations API returns no products
- **THEN** the product detail page omits the suggested products section without leaving an empty heading or placeholder

#### Scenario: Suggested section tolerates recommendation failure
- **WHEN** the selected product loads successfully but recommendation loading fails
- **THEN** the product detail page still renders the selected product and omits the suggested products section

#### Scenario: Suggested product card navigates to detail
- **WHEN** a shopper selects a suggested product card
- **THEN** they navigate to that suggested product's localized detail page

#### Scenario: Suggested section is localized
- **WHEN** the product detail page renders in English or Bulgarian
- **THEN** the suggested products section heading and any supporting labels use the active locale

### Requirement: Frontend API client supports recommendations
The frontend SHALL provide a typed API helper for product recommendations and matching mock API behavior for local development.

#### Scenario: API helper requests recommendations
- **WHEN** the product detail page needs suggested products
- **THEN** it calls a frontend API helper with product ID, locale, and limit

#### Scenario: Mock API supports recommendations
- **WHEN** mock API mode is enabled
- **THEN** the recommendations helper returns deterministic mock recommended products

#### Scenario: Product type remains shared
- **WHEN** frontend recommendation data is consumed
- **THEN** recommended products use the existing public product response type rather than a separate card-only shape

### Requirement: Frontend recommendation tests cover UI states
The frontend SHALL include focused tests for the recommendations UI states.

#### Scenario: Recommendations visible test
- **WHEN** recommended products are returned in a test
- **THEN** the product detail page test verifies the localized heading and product cards render

#### Scenario: Empty recommendations test
- **WHEN** no recommended products are returned in a test
- **THEN** the product detail page test verifies the section is omitted

#### Scenario: Recommendation failure test
- **WHEN** recommendation loading fails in a test
- **THEN** the selected product detail still renders
