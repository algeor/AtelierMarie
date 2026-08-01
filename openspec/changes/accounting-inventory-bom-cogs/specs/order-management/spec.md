## ADDED Requirements

### Requirement: Ledger-managed order stock movements
When ledger-managed inventory is enabled for a product, order stock effects SHALL create inventory movement references inside the same transactional boundary as the order operation. Sale/fulfillment movements SHALL decrease finished-goods stock, and the product stock cache SHALL be updated from the movement result.

#### Scenario: Order creates finished goods issue movement
- **WHEN** checkout or order confirmation reserves or issues a ledger-managed product according to configured order stock timing
- **THEN** the system creates a negative finished-goods inventory movement linked to the order item and updates product display stock atomically

#### Scenario: Movement failure rolls back order stock update
- **WHEN** inventory movement creation fails during an order stock operation
- **THEN** the system rolls back the order stock update and returns an error rather than leaving order and stock state inconsistent

### Requirement: Cancellation stock reversal movements
When a ledger-managed product order is cancelled after stock was issued, cancellation SHALL create a reversal inventory movement linked to the original order movement instead of silently incrementing product stock only.

#### Scenario: Cancelled order reverses inventory movement
- **WHEN** an admin cancels an order containing a ledger-managed product whose stock was already issued
- **THEN** the system creates a positive reversal movement linked to the original issue movement and updates display stock atomically

#### Scenario: Cancellation remains safe for legacy products
- **WHEN** an order contains a product not yet ledger-managed
- **THEN** the existing stock restoration behavior applies

### Requirement: Return and restock inventory movements
Return inspection SHALL create inventory movement references for ledger-managed products based on the restock decision. Restocked quantities SHALL create positive finished-goods movements, while do-not-restock and partial-restock decisions SHALL create write-off or adjustment movements for non-restocked quantities when configured.

#### Scenario: Returned item is restocked through movement
- **WHEN** an admin inspects a return and chooses to restock a ledger-managed product
- **THEN** the system creates a positive restock movement linked to the order return and updates display stock atomically

#### Scenario: Returned item not restocked creates write-off evidence
- **WHEN** an admin marks a returned ledger-managed item as do not restock
- **THEN** the system records inventory review evidence or a write-off movement according to inventory settings

### Requirement: Inventory movement fallback mode
The system SHALL support a setup state where legacy product stock behavior continues while inventory movements are being bootstrapped and reviewed. Official valuation and COGS SHALL remain disabled for products or periods still in fallback mode.

#### Scenario: Fallback mode blocks official valuation
- **WHEN** a product still relies on legacy stock behavior without reviewed opening movements
- **THEN** the system excludes it from official valuation and creates a setup exception if official COGS is required
