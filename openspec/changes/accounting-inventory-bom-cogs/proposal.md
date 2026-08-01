## Why

Atelier Marie needs to move beyond simple finished-product stock and estimated
product costs before the Accounting & Finance Hub can support accountant-ready
inventory valuation or COGS. Candle and DIY production depends on raw materials,
recipes, batch traceability, waste, and cost-method discipline, so those layers
must be introduced before any official valuation claim.

## What Changes

- Add a materials inventory layer for wax, fragrance oils, wicks, jars, labels,
  packaging, supplier lots, receipts, adjustments, spoilage, and reorder signals.
- Add recipe/BOM versioning for finished products and DIY kits, with component
  quantities, units of measure, wastage percentages, effective dates, and expected
  material/packaging cost snapshots.
- Add one-step production batches that consume materials, record actual usage and
  waste, create finished-goods batch stock, and preserve traceability from
  supplier lot to sold product.
- Add an immutable inventory movement ledger as the source of truth for receipts,
  production consumption, finished output, sales, cancellations, returns,
  adjustments, write-offs, and stock counts.
- Add accountant-reviewed inventory valuation and COGS support after the movement
  ledger is reliable, with weighted average as the first recommended method and
  FIFO deferred unless explicitly selected by the accountant.
- Extend admin review surfaces so owners can resolve inventory exceptions such as
  missing material cost, missing recipe, insufficient materials, expired material
  use, unmatched stock counts, and missing batch/COGS data.
- Extend accountant exports with inventory movement, material on-hand, finished
  goods on-hand, valuation summary, COGS, and write-off sheets when valuation is
  enabled and reviewed.
- Keep this out of full ERP scope: no multi-warehouse, work centers, routings,
  automated journal entries, fiscal-device behavior, or direct accounting sync.

## Capabilities

### New Capabilities

- `materials-inventory`: Raw material catalog, supplier lots, receipts, stock
  movements, adjustments, spoilage/write-offs, reorder status, and audit metadata.
- `recipe-bom`: Recipe/BOM versions for products and kits, component quantities,
  units, wastage, effective dates, expected cost snapshots, and review state.
- `production-batches`: Production batch records that consume materials, record
  actual usage/waste, create finished-goods batches, and support traceability.
- `inventory-valuation-cogs`: Accountant-reviewed inventory valuation settings,
  valuation layers, period inventory close, COGS ledger, and export data.

### Modified Capabilities

- `admin-products`: Surface recipe, material, batch, and inventory-ledger status
  for products, and prevent silent stock edits once ledger-managed stock is used.
- `admin-orders`: Surface finished batch, inventory movement, and COGS/valuation
  readiness links from order detail and order review views.
- `order-management`: Record sale, cancellation, return, and restock effects as
  inventory movement references when ledger-managed inventory is enabled.

## Impact

- Backend: additive SQLite tables for materials, material lots, inventory
  movements, recipe/BOM versions, production batches, valuation settings,
  valuation layers, COGS rows, stock counts, and audit events; new inventory,
  recipe, production, and valuation services.
- Frontend: admin inventory screens for materials, recipes, batches, stock
  movements, valuation review, exceptions, and product/order inventory context.
- Accounting Hub: adds inventory readiness and valuation/COGS exports without
  turning Atelier Marie into a full double-entry accounting system.
- Data migration: preserve current `products.stock` as a display/cache field while
  bootstrapping opening balances into inventory movements with review exceptions.
- Operations: accountant must review valuation method, COGS recognition date,
  labour/overhead treatment, VAT/input-cost treatment, waste/write-off mapping,
  and opening inventory values before official output is enabled.
