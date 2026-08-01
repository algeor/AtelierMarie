## ADDED Requirements

### Requirement: Admin order inventory context
Admin order detail views SHALL surface inventory context for order items, including finished batch assignment when known, inventory movement references, stock issue status, COGS readiness, valuation method, and related inventory exceptions.

#### Scenario: Admin sees order item batch reference
- **WHEN** an admin opens an order whose item was fulfilled from a finished production batch
- **THEN** the order detail shows the batch number and links to the production batch traceability view

#### Scenario: Missing COGS readiness is visible
- **WHEN** an order line has no COGS row but valuation settings require official COGS
- **THEN** the admin order detail shows a COGS readiness warning linked to the inventory exception

### Requirement: Admin order inventory filters
The admin order list SHALL support inventory/accounting filters for missing batch assignment, missing inventory movement, missing COGS row, valuation exception, and returned item pending restock/write-off review.

#### Scenario: Admin filters orders missing COGS
- **WHEN** an admin applies the missing COGS filter on the order list
- **THEN** the system returns only orders with at least one order item missing a required COGS row

#### Scenario: Admin filters returns pending inventory review
- **WHEN** an admin filters for returned items pending inventory review
- **THEN** the system returns orders with returned items that have not been restocked, written off, or otherwise resolved in inventory movements

### Requirement: Order inventory links in accounting review
Admin order views SHALL link to related inventory movements, valuation layers, COGS ledger rows, production batches, and accounting period exceptions without exposing raw internal audit payloads unnecessarily.

#### Scenario: Admin opens inventory movement from order
- **WHEN** an admin selects an inventory movement reference from an order item
- **THEN** the system opens the inventory movement detail with order context and redacted audit metadata
