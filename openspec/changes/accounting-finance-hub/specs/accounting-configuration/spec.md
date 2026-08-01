## ADDED Requirements

### Requirement: Seller legal profile settings
The system SHALL provide admin-managed seller legal profile settings for accounting exports, including company display name, legal name, UIC/EIK, VAT identification number when applicable, registered address, contact email, bank details, default currency, and effective date. Changes SHALL be audited and versioned.

#### Scenario: Missing seller profile creates setup exception
- **WHEN** no reviewed seller legal profile exists
- **THEN** the Accounting & Finance Hub shows a setup-required exception and blocks period close

#### Scenario: Seller profile change is audited
- **WHEN** an admin updates the seller VAT identification number
- **THEN** the system stores a new effective settings version and records a finance audit event with old and new redacted values

### Requirement: VAT and fiscal mode configuration
The system SHALL provide accountant-reviewed VAT/fiscal settings, including VAT registration mode, OSS mode, default domestic VAT treatment, fiscal document mode, document reference requirements by payment method, and warning text that configuration is not tax/legal advice. Threshold amounts SHALL be configurable and SHALL NOT be hard-coded as legal truth.

#### Scenario: Accountant-reviewed settings required
- **WHEN** VAT/fiscal settings have not been marked reviewed
- **THEN** the system blocks final period close and shows the settings review exception

#### Scenario: Threshold value is configurable
- **WHEN** an admin changes a VAT threshold warning value after accountant confirmation
- **THEN** the system stores the configured value with effective date and audit event rather than relying on a hard-coded threshold

### Requirement: Accounting category mappings
The system SHALL provide configurable category mappings for export rows, including sales revenue, shipping revenue, discounts/contra-revenue, VAT payable, Stripe clearing, Stripe fees, courier fees, COD receivable, refunds, disputes, bank payouts, and unresolved differences.

#### Scenario: Missing mapping creates warning
- **WHEN** a ledger row has no configured accounting category mapping
- **THEN** the export package includes the row but the exception queue flags the missing mapping for accountant review

### Requirement: Export schema settings
The system SHALL provide export schema settings for workbook language, date format, decimal separator, default period range, included tabs/files, and optional accountant-specific column names. Changes SHALL apply only to new export packages.

#### Scenario: Existing export keeps old schema
- **WHEN** export schema settings are changed after a package was generated
- **THEN** the old package remains unchanged and only later packages use the new settings

### Requirement: Settings access control
Accounting configuration endpoints and UI SHALL require admin authentication. Settings responses SHALL redact sensitive bank details except where the admin is explicitly editing or exporting the settings snapshot.

#### Scenario: Settings redaction in hub summary
- **WHEN** the finance hub summary loads seller configuration status
- **THEN** bank account details are redacted while setup/review status remains visible
