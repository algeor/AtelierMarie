## ADDED Requirements

### Requirement: Material catalog
The system SHALL provide an admin-only material catalog for raw materials and packaging used in production. Each material SHALL store an id, display name, category, stock unit of measure, optional purchase unit of measure, optional conversion factor, preferred supplier metadata, reorder threshold, active state, lot-tracking flag, expiry-tracking flag, and audit timestamps.

#### Scenario: Admin creates candle material
- **WHEN** an admin creates a material for soy wax with stock unit `g`, purchase unit `kg`, and conversion factor `1000`
- **THEN** the system stores the material as active and makes it available for receipts, recipe components, and production batches

#### Scenario: Non-admin cannot manage materials
- **WHEN** a non-admin attempts to create or update a material
- **THEN** the system rejects the request using the existing admin access behavior

### Requirement: Material receipts
The system SHALL allow admins to record material receipts for purchased materials. A receipt SHALL create an immutable positive inventory movement and SHALL store quantity, unit of measure, unit cost when known, currency, supplier, receipt date, optional supplier lot, optional expiry/use-by date, optional expense evidence link, optional document reference, actor, and notes.

#### Scenario: Wax receipt increases material stock
- **WHEN** an admin records a receipt for `5000 g` of soy wax with a unit cost and supplier invoice reference
- **THEN** the system creates a positive inventory movement linked to the material and includes the receipt in material on-hand totals

#### Scenario: Receipt without required document is flagged
- **WHEN** a material category requires supplier evidence and an admin records a receipt without an expense or document reference
- **THEN** the material remains recorded and the system creates a review exception before official inventory close

### Requirement: Material lots and expiry metadata
The system SHALL support optional supplier lot and expiry/use-by metadata for material receipts. When a material is configured as lot-tracked or expiry-tracked, receipt and production consumption flows SHALL require the configured metadata before the row can be marked reviewed.

#### Scenario: Lot-tracked fragrance requires supplier lot
- **WHEN** an admin receives a fragrance oil material configured as lot-tracked without a supplier lot number
- **THEN** the system saves the draft receipt and marks it with a missing-lot review exception

#### Scenario: Expired material appears in warnings
- **WHEN** a material lot has an expiry date before the selected production date
- **THEN** the system warns that the material lot is expired before it can be consumed by a production batch

### Requirement: Material inventory movements
The system SHALL store all material stock changes as immutable inventory movement rows. Movement types SHALL include receipt, production_consumption, adjustment, spoilage, write_off, stock_count_correction, and opening_balance. A movement SHALL include quantity delta, unit of measure, source type/id, actor, reason when manual, timestamp, and audit metadata.

#### Scenario: Admin writes off spoiled fragrance
- **WHEN** an admin records spoiled fragrance oil with a reason and quantity
- **THEN** the system creates a negative write-off movement and does not mutate prior receipt rows

#### Scenario: Movement cannot be silently edited
- **WHEN** an admin needs to correct a posted material movement
- **THEN** the system requires a reversal or correction movement with actor and reason instead of editing the original row in place

### Requirement: Material on-hand and reorder status
The system SHALL calculate material on-hand quantity from inventory movements and SHALL expose reorder status based on each active material's threshold. On-hand views SHALL show stock unit, available quantity, reserved/expected consumption when available, review exceptions, and latest movement date.

#### Scenario: Material below reorder threshold is listed
- **WHEN** soy wax on-hand quantity is below its configured reorder threshold
- **THEN** the admin material list marks the material as needing reorder

#### Scenario: Inactive material excluded from new recipes
- **WHEN** a material is inactive
- **THEN** the system excludes it from new recipe component selectors while preserving historical movements and batches
