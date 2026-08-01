# Accounting & Finance Hub Operations

Date: 2026-08-01

This guide defines how Atelier Marie should use the Accounting & Finance Hub at
month end. The hub is an evidence, reconciliation, and export layer. It is not a
certified fiscal device, a tax filing tool, or a replacement for the accountant's
bookkeeping system.

## Accountant-Reviewed Setup

Before the first production close, the owner and accountant should review and
mark these settings as reviewed in `/admin/accounting`:

- Seller legal profile: legal name, display name, UIC/EIK, VAT ID when relevant,
  registered address, contact email, bank-details presence, and default currency.
- VAT/fiscal settings: VAT registration mode, OSS mode, domestic treatment,
  fiscal document mode, document-reference rules by payment method, tolerances,
  and any threshold warning values.
- Category mappings: sales revenue, shipping revenue, discounts, VAT/tax, Stripe
  clearing, Stripe fees, courier fees, COD receivable, refunds, expenses,
  product-cost estimates, and unresolved differences.
- Export schema: workbook language, date format, decimal separator, included tabs,
  and any accountant-specific column labels.
- Expense evidence settings: categories that require invoice/receipt evidence,
  allowed payment statuses, default mappings, and whether missing evidence blocks
  period close.
- Product-cost settings: enabled state, costing basis, labor/overhead inclusion,
  missing-cost policy, reviewed state, and estimate label.
- Inventory valuation settings: ledger mode, valuation enabled state, weighted
  average/FIFO method, COGS date basis, rounding policy, missing-cost behavior,
  included cost components, write-off mapping, effective date, and accountant
  review metadata.

If seller or VAT/fiscal settings are missing or unreviewed, the hub should create
setup exceptions and block final period close until resolved or explicitly waived.

## Inventory Setup Order

Set up inventory in this order. Do not label valuation or COGS as official until
the accountant has reviewed the policy and opening values.

1. Create material catalog rows for wax, fragrance oils, dyes, wicks, jars,
   lids, labels, boxes, bags, inserts, and DIY-kit components.
2. Record opening balances for existing materials and finished goods. Use the
   physical count quantity, stock UOM, unit value or total value, and mark rows
   reviewed only after owner/accountant confirmation.
3. Create recipe/BOM versions for sellable candles and DIY kits. Keep drafts out
   of production until component quantities, UOMs, wastage, and material costs are
   checked.
4. Create production batches from reviewed or intentionally selected recipe
   versions. Post a batch only when actual output and material usage are known.
5. Move products to ledger-managed inventory only after opening balance and batch
   workflows are ready. Legacy products may keep direct product-stock behavior.
6. Review valuation settings: method, effective date, COGS date basis, rounding,
   missing-cost behavior, included labour/overhead treatment, and write-off
   mapping.
7. Generate valuation layers and COGS rows. Resolve blocking inventory exceptions
   before month-end close or export acceptance.

## Candle Material Conventions

Recommended material categories:

- `wax`: soy wax, beeswax, coconut wax, wax blends.
- `fragrance`: fragrance oil and essential oil. Prefer lot tracking and use-by
  dates when supplied.
- `wick`: wick, sustainer tabs, wick stickers.
- `container`: jars, tins, lids, dust covers.
- `label`: front labels, warning labels, CLP/allergen inserts where relevant.
- `packaging`: boxes, tissue, bags, kraft paper, shipping inserts.
- `diy_component`: kit wax packs, fragrance vials, wick packs, tins, labels,
  instruction cards.
- `consumable`: glue dots, dye, cleaning consumables, test supplies.

Use small canonical stock units for recipe accuracy: `g` for wax/fragrance/dye,
`ml` only when the supplier and recipe both work by volume, and `piece` or `pcs`
for jars, wicks, labels, boxes, and inserts. Purchases can be recorded in larger
units such as `kg` with an explicit purchase-to-stock conversion factor of `1000`.

Wastage should be visible. Put normal expected loss in the recipe wastage percent
and record unusual loss, spills, failed batches, testers, samples, or giveaways as
write-off/adjustment movements with reasons. If fragrance oils, allergens, or
containers have supplier lot numbers or expiry/use-by dates, record them on
receipts so affected batches and orders can be traced later.

## Month-End Workflow

1. Create or select the monthly finance period.
2. Start review to assign orders and refresh exceptions.
3. Import or sync Stripe balance/payout rows; use manual CSV import when the API
   source is unavailable.
4. Record accounting document references for invoices, credit notes, fiscal
   receipts, alternative sales documents, or accountant/fiscal-system references.
5. Record expense evidence for supplier invoices/receipts, materials, packaging,
   tools, subscriptions, ads, courier/provider charges, and reimbursements.
6. Review product-cost estimates only as management reporting unless the
   accountant has reviewed the costing method and cost versions.
7. Run inventory close preview for the same period. Check opening value,
   material receipts, production consumption, finished output, COGS, returns,
   adjustments/write-offs, ending value, and inventory exceptions.
8. Generate valuation layers and COGS rows when valuation is enabled. Treat rows
   as estimate-only until valuation settings, opening balances, and source costs
   are reviewed.
9. Resolve or waive exceptions with reasons. Waivers should explain the accounting
   decision, not hide missing evidence.
10. Close the period only after blocking exceptions are resolved or waived.
11. Generate the accountant export package and send the XLSX/CSV/manifest package.
12. Record accountant acceptance or reopen the period with a reason if corrections
    are needed. Reopening must create a new export version; old packages remain
    immutable.

## Inventory Close Review

During month-end review, use `/admin/inventory/valuation` and the finance period
exceptions together:

- Review unreviewed inventory settings and opening balances first.
- Check materials below reorder threshold separately from accounting exceptions;
  reorder warnings are operational, not automatically blocking.
- Investigate missing receipt evidence, missing supplier lot, missing expiry
  metadata, missing unit cost, inactive material use, missing recipe, missing
  batch assignment, missing sale movement, and missing COGS rows.
- Compare valuation close preview totals to export sheets: inventory movements,
  material on hand, finished goods on hand, valuation summary, COGS, and
  write-offs/adjustments.
- Use the export manifest row counts, sheet totals, schema version, and SHA-256
  hashes to confirm the package given to the accountant is complete and unchanged.

## Explicit Non-Goals

- The website does not issue certified fiscal receipts or act as a certified
  fiscal device.
- The website does not file NRA returns, OSS returns, VAT returns, or Ordinance
  N-18 monthly audit files.
- The website does not provide tax or legal advice. Configured VAT/fiscal modes
  are stored evidence and review state; the accountant remains final reviewer.
- The website does not maintain a full double-entry general ledger or official
  chart of accounts.
- The website does not post automatic journal entries. Inventory valuation and
  COGS exports are evidence for the accountant's bookkeeping system, not a direct
  accounting system of record.
- Product-cost and recipe costs are management estimates unless the accountant has
  reviewed the recipe, valuation settings, opening balances, and source costs.
- Official inventory/COGS output is blocked or labeled estimate-only while
  valuation settings, opening balances, or source movement costs remain
  unreviewed.
- FIFO should not be used for official output unless the shop actually follows
  lot-layer discipline and the accountant selects it. Weighted average is the
  simpler first policy for a small candle workshop.

## Rollback And Fallback

All inventory schema additions are additive. If ledger-managed inventory is not
ready, keep products in legacy or setup mode. Legacy products continue using the
existing `products.stock` behavior for checkout, cancellation, and availability;
official valuation and COGS should exclude or flag those products as fallback
until reviewed opening movements exist.

If a ledger-managed product needs a stock change, do not edit product stock
directly. Use production batch output, sale/cancellation/return flows, material or
finished-good adjustment movements, or stock count correction movements with actor
and reason. To pause the new workflow, set inventory settings back to setup or
legacy mode and keep historical movements/export packages immutable.

## Privacy And Logging

- Finance APIs require admin authentication.
- Sensitive finance responses and export downloads use no-store cache headers.
- Audit events and logs should use IDs and redacted before/after payloads.
- Do not log customer notes, full addresses, phone numbers, supplier bank/payment
  details, raw provider payloads, or expense attachment contents.
- Export rows may include accountant-required evidence fields, but raw order JSON,
  attachment contents, and unnecessary PII should not be dumped into exports.
- Bank details are redacted in hub summaries. Full values should only appear in
  explicit edit/export contexts where the accountant requires them.
