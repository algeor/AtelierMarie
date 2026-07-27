## ADDED Requirements

### Requirement: Stock restoration on return receipt
The product service SHALL provide a stock-restoration entry point used when a return is
received, mirroring the cancellation restore path. For each returned item it SHALL
execute a guarded `UPDATE products SET stock = stock + ? WHERE id = ?` and SHALL log a
warning (without failing the operation) when the product no longer exists
(`rowcount == 0`). Restoration SHALL run inside the caller's return-receipt
transaction.

#### Scenario: Returned units are added back to stock
- **WHEN** a return of 3 units of product X is received
- **THEN** product X stock increases by exactly 3

#### Scenario: Restoration tolerates a deleted product
- **WHEN** a returned item references a product that has been deleted
- **THEN** the restore logs a warning for that product and continues restoring the remaining items
