## ADDED Requirements

### Requirement: Accountant export package generation
The system SHALL generate accountant export packages for closed finance periods. Each package SHALL include an XLSX workbook, component CSV files, and a JSON manifest. The package SHALL include summary, sales ledger, payment ledger, payout/fee ledger, COD/courier settlement ledger, refunds/returns, courier claims, inventory adjustments, accounting documents, exceptions, settings snapshot, and source metadata.

#### Scenario: Admin generates package for closed period
- **WHEN** an admin generates an export package for a closed finance period
- **THEN** the system creates an export version containing XLSX, CSV components, and JSON manifest files for the period

#### Scenario: Open period cannot be exported as final
- **WHEN** an admin attempts to generate a final export for a period that is not closed
- **THEN** the system rejects the request and explains that the period must be closed first

### Requirement: Export manifest integrity
The JSON manifest SHALL include export id, period id, period date range, currency, schema version, generated timestamp, generated actor, app version when available, filters, row counts, summary totals, component file names, and SHA-256 hashes for every component file.

#### Scenario: Manifest contains component hashes
- **WHEN** an export package is generated
- **THEN** the manifest lists each component file with row count, total fields where applicable, and SHA-256 hash

### Requirement: Export package immutability and versions
The system SHALL treat export packages as immutable. Regenerating after a period is reopened SHALL create a new export version and SHALL NOT overwrite old package files or manifest metadata.

#### Scenario: Reopened period creates new export version
- **WHEN** an accepted period is reopened, corrected, closed, and exported again
- **THEN** the system creates a new export version while preserving the previous export version and its manifest

### Requirement: Existing reports included in package
The export package SHALL include the existing accounting report outputs for Stripe refund reconciliation, COD settlements, courier claims, return reasons, and return inventory adjustments as package tabs/files, preserving their current accounting fields and adding period metadata where needed.

#### Scenario: COD report included in export package
- **WHEN** a package is generated for a period containing COD orders
- **THEN** the package includes the COD settlement report data with unsettled, settled, mismatch, and Econt evidence fields

### Requirement: Export download security
Export package download endpoints SHALL require admin authentication, use no-store cache headers, and expose files only by export id. Download responses SHALL NOT log file contents or raw customer notes.

#### Scenario: Non-admin cannot download package
- **WHEN** a non-admin requests an export package download URL
- **THEN** the system returns the existing admin-auth failure response and does not reveal whether the export exists

### Requirement: Accountant acceptance note
The system SHALL let an admin mark an export package as accepted by the accountant with optional accountant name/reference and note. Acceptance SHALL record an audit event and move the finance period to `accepted` when the export is the current final version.

#### Scenario: Admin marks export accepted
- **WHEN** an admin records accountant acceptance for the current export package
- **THEN** the system stores the acceptance metadata, records an audit event, and marks the period `accepted`
