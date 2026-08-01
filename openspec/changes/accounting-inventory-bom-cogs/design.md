## Context

Atelier Marie currently tracks finished-product stock as a mutable integer on
`products.stock`. Checkout decrements that value directly, cancellation restores
it directly, and returns can create `inventory_adjustments` for restock evidence.
That is enough for storefront availability, but it is not enough for accountant
inventory valuation, COGS, material traceability, or batch recall support.

The active `accounting-finance-hub` change correctly keeps product-cost output as
management estimates. This change adds the missing operational inventory layers
needed before official inventory valuation can be enabled: materials, recipes,
production batches, movement history, and accountant-reviewed valuation policy.

## Goals / Non-Goals

**Goals:**

- Track raw materials and packaging used by candle and DIY production.
- Version recipes/BOMs so product cost can be calculated from reviewed component
  quantities, units, wastage, and material costs.
- Record one-step production batches that consume materials and create finished
  goods with batch IDs.
- Introduce an immutable inventory movement ledger for all stock-changing events.
- Support accountant-reviewed inventory valuation and COGS exports after opening
  balances and cost policy are reviewed.
- Fit into the existing admin and Accounting & Finance Hub without replacing the
  accountant or creating a full general ledger.

**Non-Goals:**

- No multi-warehouse, routing, work centers, machine capacity planning, or full
  MRP forecasting.
- No automatic double-entry journal posting.
- No fiscal-device, NRA filing, or tax-advice behavior.
- No direct QuickBooks, Xero, or external accounting software sync.
- No mandatory lot tracking for every raw-material issue in the first release;
  supplier lots are supported where known.

## Decisions

### 1. Use an inventory movement ledger as the source of truth

Create `inventory_movements` for receipts, material adjustments, production
consumption, finished production output, order sale issues, cancellations,
returns/restocks, stock counts, spoilage, write-offs, and valuation adjustments.
Each movement stores item type, item id, quantity delta, unit of measure, source
type/id, actor, timestamp, notes, and immutable audit metadata.

`products.stock` remains as a denormalized cache/display value during migration.
New official valuation and COGS must derive from movement and valuation layers,
not from direct reads of the mutable stock column.

Alternative considered: calculate COGS from `products.stock` and order lines.
Rejected because it loses purchase cost, batch, adjustment, and waste history.

### 2. Separate materials from sellable products

Add a materials catalog rather than overloading `products` for raw materials.
Materials need units, suppliers, purchase documents, supplier lots, expiry/use-by
metadata, and stock movements that do not belong in the storefront catalog.

Finished goods stay linked to existing products. A production batch converts
material movements into finished-good receipt movements for product stock.

Alternative considered: add hidden products for wax, fragrance, and jars.
Rejected because storefront product constraints, media, price, and active flags do
not match raw-material behavior.

### 3. Treat recipes/BOMs as expected plans and batches as actuals

Recipe/BOM versions hold expected component quantities, UOM, wastage percentages,
effective date, output quantity, and expected cost snapshots. Production batches
copy the active recipe version, then record actual quantities consumed and actual
finished quantity produced.

This preserves planned-vs-actual comparison without requiring complex shop-floor
workflow. Actual batches become the basis for finished-good cost and traceability.

Alternative considered: use recipe snapshots only and skip batches. Rejected
because official COGS needs actual production and waste evidence.

### 4. Start with one-step manufacturing

The production workflow is one operation: consume materials, optionally record
waste, and receive finished goods. This matches a small candle workshop and avoids
ERP-sized routing complexity.

Operations, work centers, labour time, and overhead estimates can be stored as
optional management fields, but they are excluded from official inventory value
unless valuation settings explicitly include accountant-reviewed rules.

Alternative considered: model full work orders and operations now. Rejected as
too much process for the current shop size.

### 5. Use weighted average as the first valuation method candidate

Weighted average is the default recommended policy because candle materials are
often interchangeable, bought repeatedly at changing prices, and physically mixed
in normal workshop use. FIFO remains available as a future/accountant-selected
policy only when lot-layer discipline is truly required.

Valuation settings must be versioned, effective-dated, and marked
accountant-reviewed before official valuation/COGS export sheets are labeled as
official. Until then, cost outputs remain estimates.

Alternative considered: force FIFO for all materials. Rejected because it creates
high admin burden and can be less truthful if the workshop does not issue stock by
lot order.

### 6. Preserve supplier document and expense links

Material receipts should link to expense evidence/supplier documents from the
Accounting & Finance Hub where possible. A receipt can still be drafted without a
document, but period close should flag missing evidence when the material category
requires it.

Alternative considered: build a full purchasing/accounts-payable module. Rejected
because the existing expense evidence register is the right accounting boundary.

### 7. Bootstrap opening balances explicitly

Migration creates opening-balance movement rows for existing finished product
stock and optional material balances. Opening quantities and values are review
items until the owner/accountant confirms them.

Alternative considered: infer historical stock movements from old orders.
Rejected because prior direct stock edits and missing purchase history would make
the inferred ledger unreliable.

### 8. Integrate with orders through movement references

When ledger-managed inventory is enabled, checkout/order confirmation records
finished-good issue movements, cancellation records reversal movements, and return
inspection records restock/write-off movements. Existing order behavior should
remain transactionally safe and still update display stock from the ledger/cache.

Alternative considered: switch all order stock logic in one migration. Rejected
because checkout stock handling is high-risk and should be migrated behind a
feature flag or settings state.

### 9. Export valuation evidence, not journal entries

The Accounting & Finance Hub export adds inventory movement, valuation summary,
materials on hand, finished goods on hand, COGS, and write-off sheets. It does not
post accounting journal entries or claim to be the accounting system of record.

Alternative considered: generate debit/credit journal entries automatically.
Rejected until the accountant defines exact chart-of-accounts mappings and local
bookkeeping treatment.

## Risks / Trade-offs

- Dirty opening balances -> require opening-balance review exceptions and keep old
  export versions immutable.
- Owner edits product stock directly after ledger mode -> block silent edits and
  require stock-count or adjustment movements instead.
- Cost method chosen too early -> label outputs as estimates until accountant
  review is recorded.
- FIFO selected without lot discipline -> warn and require supplier/finished lot
  assignments for FIFO-valued items.
- Material UOM mistakes -> enforce canonical stock UOM, explicit conversion
  factors, and validation on recipe/batch entries.
- Production waste hidden in recipes -> support expected wastage percentages and
  explicit write-off/failed-batch adjustments.
- Checkout race conditions -> keep stock mutations inside existing transactions
  and update movement/cache rows atomically.
- Large movement history -> index by item, source, movement date, period, and
  movement type; paginate admin movement views.

## Migration Plan

1. Add additive tables for materials, material lots, inventory movements, recipes,
   recipe components, production batches, batch consumption, valuation settings,
   valuation layers, COGS rows, stock counts, and audit events.
2. Seed inventory settings with valuation disabled and ledger mode in setup state.
3. Create opening-balance movement rows from current `products.stock` with unknown
   value status and review exceptions.
4. Add material receipt and recipe/BOM services without changing checkout stock
   behavior.
5. Add production batches and movement-driven finished stock cache updates.
6. Enable order movement references behind reviewed ledger settings.
7. Add valuation/COGS calculation only after opening balances, method, and cost
   component settings are reviewed.
8. Extend exports and period close exceptions with inventory/COGS sheets.

Rollback: all schema changes are additive. If inventory ledger mode is disabled,
existing product stock and current accounting exports continue to work. Generated
export packages remain immutable historical artifacts.

## Open Questions

- Should the accountant prefer perpetual weighted average or month-end periodic
  weighted average for the first official valuation version?
- Should inbound shipping/landed cost be included in material unit cost?
- Should owner labour be capitalized, expensed separately, or tracked only as a
  management estimate?
- Which date triggers official COGS: order, payment, shipment, delivery, invoice,
  or accounting period close?
- Which material categories require supplier lot/expiry tracking from day one?
- How should sample candles, giveaways, testers, and failed batches map in the
  accountant export for Bulgarian bookkeeping?
