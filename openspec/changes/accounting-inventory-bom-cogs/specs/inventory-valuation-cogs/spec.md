## ADDED Requirements

### Requirement: Inventory valuation settings
The system SHALL provide accountant-reviewed inventory valuation settings with method (`weighted_average` or `fifo`), effective date, included cost components, currency, rounding policy, COGS recognition date basis, missing-cost behavior, write-off mapping, reviewed state, reviewer metadata, and audit history. Official valuation and COGS SHALL remain disabled until settings are reviewed.

#### Scenario: Unreviewed valuation settings block official output
- **WHEN** valuation settings exist but are not marked accountant-reviewed
- **THEN** the system labels inventory cost output as estimates and blocks official valuation/COGS export sheets

#### Scenario: Accountant reviews weighted average method
- **WHEN** an admin records accountant review for `weighted_average` valuation settings with an effective date
- **THEN** the system allows periods on or after that date to run official valuation checks if opening balances are also reviewed

### Requirement: Valuation layers
The system SHALL derive valuation layers from inventory movements. Valuation layers SHALL store movement id, item type, item id, quantity, unit value, total value, currency, valuation method, source type/id, valuation date, review state, and method-specific metadata. Layers SHALL be append-only except through explicit reversal or revaluation layers.

#### Scenario: Material receipt creates valuation layer
- **WHEN** a reviewed material receipt with unit cost is posted under weighted-average valuation
- **THEN** the system creates an incoming valuation layer that updates the material's weighted average cost

#### Scenario: Production output creates finished valuation layer
- **WHEN** a production batch is produced from reviewed material consumption costs
- **THEN** the system creates a finished-goods valuation layer with unit cost derived from actual batch cost divided by actual output quantity

### Requirement: Weighted average costing
The system SHALL calculate weighted average unit cost from reviewed incoming value and quantity for each valued material or finished good. Negative movements SHALL consume the current weighted average cost at the valuation date unless a reviewed correction/revaluation layer applies.

#### Scenario: New material purchase updates weighted average
- **WHEN** a material has 1000 g on hand at EUR 0.02/g and a reviewed receipt adds 1000 g at EUR 0.03/g
- **THEN** the material weighted average cost becomes EUR 0.025/g before later consumption

#### Scenario: Consumption uses current average cost
- **WHEN** a production batch consumes 500 g of a weighted-average material
- **THEN** the valuation layer uses the current weighted average unit cost for that consumption

### Requirement: Period inventory close
The system SHALL provide period inventory close calculations for reviewed periods. A close SHALL compute opening quantity/value, receipts, production consumption, finished output, sales/COGS, returns/restocks, adjustments/write-offs, ending quantity/value, missing-cost exceptions, and valuation policy snapshot.

#### Scenario: Inventory close calculates ending value
- **WHEN** an admin runs inventory close for a month with reviewed movements and valuation settings
- **THEN** the system calculates ending material and finished-goods quantities and values for the period

#### Scenario: Missing opening balance blocks official close
- **WHEN** a valued product has opening quantity but no reviewed opening value
- **THEN** the system creates a blocking inventory valuation exception before official close

### Requirement: COGS ledger
The system SHALL generate COGS ledger rows for sold order lines when official valuation is enabled and reviewed. Each row SHALL include order id, order number, order line/product id, quantity sold, COGS recognition date, unit cost, total cost, valuation method, source finished batch or valuation layer when available, currency, review state, and reversal link for returns/refunds.

#### Scenario: Sold candle receives COGS row
- **WHEN** a candle order line is recognized for COGS under reviewed settings
- **THEN** the system creates a COGS ledger row with quantity, unit cost, total cost, valuation method, and source movement reference

#### Scenario: Returned item reverses COGS when restocked
- **WHEN** a sold item is returned and restocked through a reviewed inventory movement
- **THEN** the system creates an appropriate COGS reversal or restock valuation row linked to the original sale

### Requirement: Inventory valuation export sheets
The system SHALL extend accountant export packages with inventory movement, material on-hand, finished goods on-hand, valuation summary, COGS, write-off/adjustment, and valuation policy sheets when valuation is enabled. Sheets SHALL clearly label rows as official only when valuation settings, opening balances, and source movements are reviewed.

#### Scenario: Official valuation sheets included
- **WHEN** a closed finance period has reviewed inventory valuation enabled
- **THEN** the export package includes inventory and COGS sheets with row counts, totals, method, and policy snapshot in the manifest

#### Scenario: Estimate-only costs remain labeled
- **WHEN** valuation is not reviewed but management cost snapshots exist
- **THEN** export package cost sheets are labeled as estimates and are not presented as official COGS or inventory valuation
