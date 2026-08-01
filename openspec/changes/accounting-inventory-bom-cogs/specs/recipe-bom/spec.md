## ADDED Requirements

### Requirement: Recipe BOM versions
The system SHALL provide versioned recipe/BOM records for sellable products and DIY kits. Each version SHALL store product id, version label, status (`draft`, `active`, `archived`), effective date, expected output quantity, output unit, notes, review state, and audit metadata. Only one active recipe version SHALL apply to a product for a given effective date.

#### Scenario: Admin activates new candle recipe
- **WHEN** an admin activates a recipe version for a candle product effective on 2026-09-01
- **THEN** the system archives or supersedes conflicting active versions for the same product/effective range and uses the new version for later cost lookups

#### Scenario: Draft recipe does not affect production
- **WHEN** a recipe version is still `draft`
- **THEN** production batch creation does not select it as the active recipe unless the admin explicitly chooses draft planning mode

### Requirement: Recipe component lines
The system SHALL let admins define recipe/BOM component lines with material id, quantity, unit of measure, quantity basis (`per_unit` or `per_batch`), wastage percentage, required flag, optional substitute group, and sort order. The system SHALL validate unit conversions against the material's stock unit before costing or production.

#### Scenario: Candle recipe includes wax and packaging
- **WHEN** an admin adds soy wax, fragrance oil, wick, jar, warning label, front label, and box components to a candle recipe
- **THEN** the recipe stores each component with quantity, unit, wastage, and required status

#### Scenario: Incompatible unit conversion is rejected
- **WHEN** an admin enters a recipe component unit that cannot convert to the material stock unit
- **THEN** the system rejects the component or marks the recipe invalid until a conversion is provided

### Requirement: Expected cost snapshots
The system SHALL calculate expected cost snapshots for recipe versions from current material costs, component quantities, wastage percentages, packaging components, and output quantity. A cost snapshot SHALL store currency, material cost, packaging cost, optional labour estimate, optional overhead estimate, total expected unit cost, calculation timestamp, source cost references, and estimate/review label.

#### Scenario: Recipe cost snapshot calculated
- **WHEN** an admin requests a cost snapshot for a recipe producing 24 candles
- **THEN** the system calculates expected batch cost and expected unit cost from the component quantities and current material costs

#### Scenario: Missing material cost creates warning
- **WHEN** a recipe component has no current material unit cost
- **THEN** the snapshot marks the cost incomplete and creates a missing-cost warning for review

### Requirement: Recipe review state
The system SHALL distinguish management-estimate recipes from accountant-reviewed costing recipes. Official valuation and COGS SHALL NOT use a recipe cost component as reviewed unless the recipe version and relevant costing settings are marked reviewed.

#### Scenario: Unreviewed recipe remains estimate-only
- **WHEN** a recipe version has expected costs but is not accountant-reviewed
- **THEN** exports and ledgers label its costs as management estimates

#### Scenario: Reviewed recipe can feed valuation prerequisites
- **WHEN** a recipe version and valuation settings are accountant-reviewed
- **THEN** production batches using that recipe can contribute to official valuation calculations according to the selected valuation method

### Requirement: Recipe diagnostics
The system SHALL provide diagnostics for products missing active recipes, invalid component units, inactive materials, missing material costs, and excessive configured wastage. Diagnostics SHALL be visible in recipe admin views and inventory/accounting exception views.

#### Scenario: Product missing recipe is flagged
- **WHEN** product-cost or production settings require recipes and a sellable candle has no active recipe
- **THEN** the system creates a missing-recipe warning linked to the product

#### Scenario: Inactive material on active recipe is flagged
- **WHEN** an active recipe references a material that has since been deactivated
- **THEN** the system keeps the recipe for historical use and flags it for admin review before new production
