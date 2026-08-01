## ADDED Requirements

### Requirement: Production batch records
The system SHALL provide admin-only production batch records for one-step manufacturing. A production batch SHALL store batch number, product id, recipe/BOM version id, planned output quantity, actual output quantity, status (`draft`, `produced`, `cancelled`), production date, ready date when provided, notes, actor, and audit timestamps.

#### Scenario: Admin creates draft production batch
- **WHEN** an admin creates a batch for 24 lavender candles from an active recipe
- **THEN** the system stores the batch as `draft` with planned output and expected component consumption

#### Scenario: Batch number is unique
- **WHEN** an admin attempts to create a production batch using an existing batch number
- **THEN** the system rejects the duplicate batch number

### Requirement: Batch material consumption
The system SHALL record actual material consumption for each production batch. Consumption lines SHALL store material id, optional supplier lot id, expected quantity, actual quantity, unit of measure, unit cost snapshot, waste quantity when provided, source recipe component id, and review status. Producing a batch SHALL create negative material inventory movements for actual consumption.

#### Scenario: Producing batch consumes materials
- **WHEN** an admin marks a batch as produced with actual wax, fragrance, wick, jar, and label quantities
- **THEN** the system creates negative material consumption movements linked to the batch

#### Scenario: Actual usage above tolerance creates warning
- **WHEN** actual fragrance usage exceeds expected recipe usage beyond the configured tolerance
- **THEN** the system records the usage and creates a batch variance warning for review

### Requirement: Finished goods receipt from production
The system SHALL create finished-goods inventory movement rows when a production batch is produced. Each finished output movement SHALL link product id, batch number, actual quantity produced, unit cost estimate or reviewed cost, production date, source production batch id, and valuation review state.

#### Scenario: Produced candles increase finished stock
- **WHEN** a batch for 24 candles is marked produced
- **THEN** the system creates a positive finished-goods movement and updates the product's display stock/cache by 24

#### Scenario: Produced quantity differs from plan
- **WHEN** planned output is 24 but actual output is 22
- **THEN** the system records 22 finished units, keeps the planned quantity for variance reporting, and creates a production variance warning

### Requirement: Production traceability
The system SHALL preserve traceability from finished product batch to source material movements, supplier lots when known, recipe version, production date, and sold order lines when assigned. Admins SHALL be able to inspect a finished batch and see source materials and related orders.

#### Scenario: Admin traces sold candle batch
- **WHEN** an admin opens a finished candle batch that has been sold in orders
- **THEN** the system shows the recipe version, materials consumed, supplier lots when known, finished quantity, remaining quantity, and linked order lines

#### Scenario: Supplier lot trace shows affected batches
- **WHEN** an admin opens a supplier fragrance lot
- **THEN** the system lists production batches that consumed that lot and any orders linked to those finished batches

### Requirement: Batch cancellation and correction
The system SHALL prevent silent mutation of produced batches. A produced batch can be corrected only through reversal or adjustment movements with actor, reason, and audit metadata. Draft batches MAY be edited until produced or cancelled.

#### Scenario: Draft batch can be edited
- **WHEN** a batch is still `draft`
- **THEN** an admin can update planned output and component actuals before production is posted

#### Scenario: Produced batch requires correction movement
- **WHEN** an admin discovers that a produced batch used two extra jars
- **THEN** the system requires a correction movement linked to the batch instead of editing the original produced movement silently
