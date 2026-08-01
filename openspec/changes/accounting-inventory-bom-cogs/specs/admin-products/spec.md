## ADDED Requirements

### Requirement: Product inventory context
The admin product detail and edit views SHALL surface inventory context for each product, including display stock source, active recipe/BOM status, latest production batch, ledger-managed stock state, valuation readiness, and linked inventory exceptions.

#### Scenario: Admin sees product recipe and batch status
- **WHEN** an admin opens a candle product detail or edit view
- **THEN** the system shows whether the product has an active recipe, recent production batches, current finished stock, and inventory review warnings

#### Scenario: Product with missing recipe is highlighted
- **WHEN** a sellable product requires recipe costing but has no active recipe
- **THEN** the admin product view shows a missing-recipe warning with a link to create or review a recipe

### Requirement: Ledger-managed stock editing
When a product is configured for ledger-managed inventory, the admin product form SHALL NOT allow silent direct stock edits. Stock changes SHALL be recorded through stock count, production, receipt, sale, return, or adjustment movements with actor and reason. Products not yet migrated to ledger-managed stock MAY continue using the existing stock field behavior.

#### Scenario: Direct stock edit blocked for ledger-managed product
- **WHEN** an admin edits a ledger-managed product and attempts to change the stock number directly
- **THEN** the system blocks the direct stock edit and prompts the admin to create an inventory adjustment or stock count correction

#### Scenario: Legacy product stock edit still works before migration
- **WHEN** a product has not been migrated to ledger-managed inventory
- **THEN** the existing product stock edit behavior remains available

### Requirement: Product inventory links
The admin product views SHALL link to related material recipes, production batches, finished-goods movements, valuation layers, and COGS rows where available.

#### Scenario: Admin navigates from product to batch history
- **WHEN** an admin clicks the product's batch history link
- **THEN** the system opens the production batch list filtered to that product

#### Scenario: Admin navigates from product to valuation rows
- **WHEN** valuation rows exist for a product
- **THEN** the product inventory context links to the valuation ledger filtered to that product
