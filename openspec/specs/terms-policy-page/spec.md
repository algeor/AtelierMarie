# terms-policy-page Specification

## Purpose
TBD - created by archiving change minimal-terms-returns-policy. Update Purpose after archive.
## Requirements
### Requirement: Public Terms and Conditions page
The system SHALL provide a localized public Terms & Conditions page at `/[locale]/terms`. The page SHALL use the existing locale routing, render as part of the storefront layout, and present legal content in a narrow readable column with restrained Atelier Marie styling.

#### Scenario: English terms page renders
- **WHEN** a visitor opens `/en/terms`
- **THEN** the page renders English Terms & Conditions content
- **AND** the page title communicates that it is the Terms & Conditions page

#### Scenario: Bulgarian terms page renders
- **WHEN** a visitor opens `/bg/terms`
- **THEN** the page renders Bulgarian Terms & Conditions content
- **AND** Bulgarian text renders in the existing site typography without layout overlap

### Requirement: Terms page section navigation
The Terms & Conditions page SHALL include a compact section navigation near the top. Each navigation item SHALL link to a visible section anchor on the same page, including a returns anchor at `#returns`.

#### Scenario: Returns anchor is available
- **WHEN** a visitor navigates to `/en/terms#returns`
- **THEN** the right of withdrawal and returns section is visible with its heading reachable by the anchor

#### Scenario: Section navigation works on mobile
- **WHEN** the page is viewed on a mobile viewport
- **THEN** section navigation remains readable and tappable without horizontal overflow

### Requirement: Terms page legal sections
The Terms & Conditions page SHALL include sections for seller information, products and handmade variations, orders and payment, delivery, right of withdrawal and returns, custom or personalized products, faulty or damaged items, refunds, and contact.

#### Scenario: Required sections are present
- **WHEN** a visitor opens the Terms & Conditions page
- **THEN** headings for seller information, orders and payment, delivery, right of withdrawal and returns, custom products, faulty or damaged items, refunds, and contact are present

### Requirement: Withdrawal and returns policy content
The `#returns` section SHALL describe the statutory 14-day withdrawal right for standard products, the customer's 14-day deadline to send goods back after withdrawal, the manual email/contact-form request process, and the model withdrawal form. It SHALL state that customers do not need to give a reason for ordinary withdrawal and that photos are not required for ordinary withdrawal.

#### Scenario: Standard withdrawal flow is clear
- **WHEN** a visitor reads the returns section
- **THEN** the page explains that standard products may be withdrawn from within 14 days after delivery without giving a reason
- **AND** the page explains that the customer should contact Atelier Marie by email or contact form before the deadline expires

#### Scenario: Model withdrawal form is available
- **WHEN** a visitor reads the returns section
- **THEN** a model withdrawal form text is available on the page
- **AND** the page explains that using the model form is optional if the customer makes another clear withdrawal statement

### Requirement: Return condition and return shipping disclosure
The returns section SHALL request original packaging where possible without making packaging an absolute condition of withdrawal. It SHALL state that the customer pays direct return shipping costs for change-of-mind withdrawal unless Atelier Marie agrees otherwise, and that the customer may be responsible for diminished value caused by handling beyond what is necessary to inspect the product, including lighting or using the candle.

#### Scenario: Packaging is requested but not absolute
- **WHEN** a visitor reads the returns section
- **THEN** the page asks customers to return items with original packaging where possible
- **AND** it does not say that original packaging is always required to exercise withdrawal

#### Scenario: Lit candles are handled as diminished value
- **WHEN** a visitor reads the returns section
- **THEN** the page explains that lighting, using, or over-handling a candle may reduce the refundable amount

### Requirement: Custom products exception
The Terms & Conditions page SHALL state that the statutory withdrawal right does not apply, where legally permitted, to products made to the customer's specifications or clearly personalized. Examples SHALL include custom names, messages, logos, photos, bespoke colors, fragrances, and made-to-order designs requested by the customer.

#### Scenario: Personalized products are excluded narrowly
- **WHEN** a visitor reads the custom products section
- **THEN** it explains that clearly personalized or customer-specified products are excluded from withdrawal
- **AND** the examples are specific to customer-requested customization rather than ordinary product choices

### Requirement: Faulty, damaged, or incorrect item handling
The Terms & Conditions page SHALL distinguish ordinary withdrawal from faulty, damaged, or incorrect items. It SHALL state that statutory rights for non-conforming goods remain unaffected, and that photos are requested for damaged, faulty, or incorrect items to help resolve the issue.

#### Scenario: Photos requested only for problem items
- **WHEN** a visitor reads the faulty or damaged items section
- **THEN** the page asks for clear photos of the item and packaging for damaged, faulty, or incorrect items
- **AND** ordinary withdrawal does not require photos

#### Scenario: Statutory rights remain unaffected
- **WHEN** a visitor reads the faulty or damaged items section
- **THEN** the page states that statutory rights for faulty or non-conforming goods remain unaffected by the 14-day withdrawal information

### Requirement: Terms page metadata
The Terms & Conditions page SHALL define localized metadata and localized alternate links using the existing SEO utilities.

#### Scenario: Metadata is localized
- **WHEN** `/bg/terms` is rendered
- **THEN** the page metadata title and description are Bulgarian

