## 1. Schema And Settings

- [ ] 1.1 Add inventory settings table for ledger mode, valuation enabled state, method, COGS date basis, rounding policy, missing-cost behavior, review metadata, and timestamps.
- [ ] 1.2 Add materials table with SKU/name/category, stock UOM, purchase UOM, conversion factor, supplier metadata, reorder threshold, active state, lot/expiry flags, and audit timestamps.
- [ ] 1.3 Add material lots/receipts tables with supplier lot, expiry/use-by date, received quantity, unit cost, currency, supplier, expense/document references, review state, and audit fields.
- [ ] 1.4 Add immutable inventory movement table with item type/id, movement type, quantity delta, UOM, source type/id, actor, reason, notes, reversal link, and timestamp.
- [ ] 1.5 Add recipe/BOM version and component tables with product id, version status, effective date, output quantity, component quantities, UOM, wastage percent, substitute group, and review state.
- [ ] 1.6 Add recipe cost snapshot table with material cost, packaging cost, optional labour/overhead estimates, unit cost, currency, source references, estimate/review labels, and timestamps.
- [ ] 1.7 Add production batch, batch consumption, and finished output tables with batch number, product id, recipe version, planned/actual quantities, material lots, actual usage, waste, cost snapshots, and status.
- [ ] 1.8 Add valuation layer, COGS ledger, inventory close, stock count, and inventory exception tables with review/audit metadata.
- [ ] 1.9 Add indexes for movement item/date/source/type, material/category/active, recipe product/effective/status, batch product/status/date, valuation item/date, and COGS order/product/date.
- [ ] 1.10 Add additive bootstrap migration that seeds valuation disabled and ledger mode setup state without changing existing checkout behavior.

## 2. Material Inventory Backend

- [ ] 2.1 Implement material catalog CRUD service with validation for UOMs, conversion factors, active state, lot/expiry flags, and admin audit metadata.
- [ ] 2.2 Implement material list/detail queries with on-hand quantity derived from inventory movements and reorder status.
- [ ] 2.3 Implement material receipt service that creates positive receipt movements and stores supplier, unit cost, lot, expiry, and expense/document links.
- [ ] 2.4 Implement material adjustment, spoilage, write-off, and stock count correction services using immutable correction/reversal movements.
- [ ] 2.5 Implement material lot lookup and expired/near-expiry diagnostics for production batch consumption.
- [ ] 2.6 Implement review exceptions for missing receipt evidence, missing supplier lot, missing expiry metadata, missing unit cost, and inactive material use.
- [ ] 2.7 Add admin API endpoints for material list/detail/create/update, receipts, lots, movements, adjustments, write-offs, and reorder view.
- [ ] 2.8 Ensure all material APIs require admin authentication and return no-store cache headers for sensitive inventory views.

## 3. Recipe BOM Backend

- [ ] 3.1 Implement recipe/BOM version CRUD service with draft, active, archived lifecycle and effective-date conflict validation.
- [ ] 3.2 Implement recipe component validation for material existence, active state, UOM conversion, wastage percent, quantity basis, and required/substitute groups.
- [ ] 3.3 Implement active recipe lookup by product id and date with deterministic tie-breaking and missing-recipe diagnostics.
- [ ] 3.4 Implement expected cost snapshot calculation from component quantities, wastage, output quantity, and current material costs.
- [ ] 3.5 Implement recipe review state transitions with accountant-reviewed metadata and audit events.
- [ ] 3.6 Implement recipe diagnostics for missing costs, invalid units, inactive materials, excessive wastage, and no active recipe.
- [ ] 3.7 Add admin API endpoints for recipe list/detail/create/update/activate/archive, component editing, cost snapshot generation, review actions, and diagnostics.
- [ ] 3.8 Link recipe/BOM status into existing product admin response models without changing public product payloads.

## 4. Production Batches Backend

- [ ] 4.1 Implement production batch CRUD service for draft batches with unique batch numbers, product links, recipe version links, planned output, production date, ready date, and notes.
- [ ] 4.2 Implement expected material consumption generation from selected recipe/BOM version and planned output quantity.
- [ ] 4.3 Implement produced-batch posting that validates material availability, lot/expiry rules, actual quantities, and variance tolerances.
- [ ] 4.4 Create negative material consumption movements when a batch is posted as produced.
- [ ] 4.5 Create positive finished-goods output movements and update product stock cache when a batch is posted as produced.
- [ ] 4.6 Implement batch variance exceptions for actual usage over tolerance, produced quantity mismatch, expired material use, missing cost, and insufficient materials.
- [ ] 4.7 Implement produced-batch correction flow using reversal/correction movements instead of editing original posted movements.
- [ ] 4.8 Implement traceability queries from finished batch to recipe version, source material movements/lots, remaining quantity, and linked order lines.
- [ ] 4.9 Add admin API endpoints for batch list/detail/create/update/post/cancel/correct, expected consumption, actual consumption, and traceability.

## 5. Inventory Valuation And COGS Backend

- [ ] 5.1 Implement valuation settings service with versioning, accountant review metadata, effective dates, method validation, and audit events.
- [ ] 5.2 Implement reviewed opening-balance workflow for existing product stock and optional material balances.
- [ ] 5.3 Implement valuation layer creation for reviewed material receipts, material consumption, finished production output, sale issues, returns, adjustments, write-offs, and revaluations.
- [ ] 5.4 Implement weighted-average cost calculation for materials and finished goods with quantity/value safeguards and rounding policy.
- [ ] 5.5 Add FIFO scaffolding and validation warnings without enabling FIFO official output unless settings require lot-layer discipline.
- [ ] 5.6 Implement period inventory close calculation for opening value, receipts, production in/out, sales/COGS, returns, adjustments/write-offs, ending value, and policy snapshot.
- [ ] 5.7 Implement COGS ledger generation for sold order lines with valuation source references, date basis, review state, and reversal links.
- [ ] 5.8 Implement valuation exceptions for unreviewed settings, unreviewed opening balances, missing source costs, negative on-hand, missing recipe, missing batch, and fallback-mode products.
- [ ] 5.9 Add admin API endpoints for valuation settings, opening balance review, valuation layers, COGS rows, inventory close preview, and exception details.

## 6. Order And Product Integration

- [ ] 6.1 Add inventory mode checks to order stock operations so legacy products keep current stock behavior until migrated.
- [ ] 6.2 Record finished-goods issue movements for ledger-managed products during configured order stock timing inside the existing checkout/order transaction.
- [ ] 6.3 Record cancellation reversal movements for ledger-managed products and keep product stock cache synchronized atomically.
- [ ] 6.4 Extend return inspection/restock flow to create ledger-managed restock/write-off movements for returned products.
- [ ] 6.5 Add order item inventory movement references or lookup mapping needed for traceability and COGS generation.
- [ ] 6.6 Add admin order response fields for finished batch, movement references, COGS readiness, valuation method, and inventory exceptions.
- [ ] 6.7 Add admin product response fields for active recipe, latest batch, ledger-managed state, stock source, valuation readiness, and inventory exceptions.
- [ ] 6.8 Block silent direct stock edits for ledger-managed products and route changes through adjustment or stock count endpoints.

## 7. Accounting Hub And Export Integration

- [ ] 7.1 Add inventory readiness checks to Accounting & Finance Hub period exceptions.
- [ ] 7.2 Extend finance summary totals with material on-hand value, finished goods on-hand value, COGS, write-offs, and inventory exception count when valuation is enabled.
- [ ] 7.3 Add inventory movement ledger adapter for accountant export packages.
- [ ] 7.4 Add material on-hand and finished-goods on-hand export sheets with quantities, values, UOMs, review state, and source metadata.
- [ ] 7.5 Add valuation summary and COGS export sheets with method, date basis, row counts, totals, and policy snapshot.
- [ ] 7.6 Add write-off/adjustment export sheet for spoilage, failed batches, stock count corrections, and manual inventory adjustments.
- [ ] 7.7 Ensure export manifest includes inventory sheet row counts, totals, schema version, and SHA-256 hashes.
- [ ] 7.8 Ensure unreviewed valuation output is labeled as estimate-only and official inventory/COGS export is blocked until settings and opening balances are reviewed.

## 8. Admin Frontend

- [ ] 8.1 Add admin navigation entries for Inventory, Materials, Recipes/BOM, Production Batches, and Valuation under the existing admin layout.
- [ ] 8.2 Build material list/detail/forms with stock UOM, supplier metadata, reorder status, lot/expiry flags, receipt actions, adjustment/write-off actions, and movement history.
- [ ] 8.3 Build recipe/BOM list/detail/forms with version lifecycle, component editor, UOM validation errors, wastage fields, cost snapshot preview, diagnostics, and review state.
- [ ] 8.4 Build production batch list/detail/forms with expected consumption, actual consumption editing, material lot selection, variance warnings, post/cancel/correct actions, and traceability view.
- [ ] 8.5 Build valuation settings and opening balance review screens with accountant-reviewed controls and policy warnings.
- [ ] 8.6 Add inventory movement, valuation layer, COGS ledger, and inventory close preview tables with filters and pagination.
- [ ] 8.7 Extend product admin screens with recipe status, latest batch, stock source, ledger-managed stock edit blocking, and inventory links.
- [ ] 8.8 Extend admin order screens with batch, movement, COGS readiness, valuation links, and inventory filters.
- [ ] 8.9 Add English and Bulgarian admin strings for inventory, recipe, batch, valuation, COGS, and exception labels.

## 9. Backend Tests

- [ ] 9.1 Add migration/schema tests for all new inventory, recipe, production, valuation, COGS, and exception tables.
- [ ] 9.2 Add material service tests for CRUD, receipts, lots, UOM conversion, movements, write-offs, stock counts, reorder status, and admin access.
- [ ] 9.3 Add recipe/BOM tests for version lifecycle, component validation, cost snapshots, review state, diagnostics, and inactive material warnings.
- [ ] 9.4 Add production batch tests for draft creation, expected consumption, posting, material movement creation, finished stock movement creation, variances, corrections, and traceability.
- [ ] 9.5 Add valuation tests for settings review, opening balances, weighted average calculation, valuation layer creation, period close, and missing-cost exceptions.
- [ ] 9.6 Add COGS tests for order sale rows, date basis, source movement references, returns/restock reversals, and estimate-vs-official labeling.
- [ ] 9.7 Add order integration tests for ledger-managed sale issue movements, cancellation reversals, return/restock movements, and legacy fallback behavior.
- [ ] 9.8 Add accounting export tests for inventory movement, on-hand, valuation summary, COGS, write-off sheets, manifest totals, hashes, and review gating.
- [ ] 9.9 Add API access-control tests for all inventory, recipe, production, valuation, and COGS endpoints.

## 10. Frontend Tests And Verification

- [ ] 10.1 Add frontend tests for material list/detail/forms, receipt recording, adjustment/write-off actions, lot/expiry warnings, and reorder states.
- [ ] 10.2 Add frontend tests for recipe/BOM component editing, UOM errors, cost snapshot preview, activation/archive flow, and missing-cost diagnostics.
- [ ] 10.3 Add frontend tests for production batch creation, expected/actual consumption, posting, variance warnings, correction flow, and traceability links.
- [ ] 10.4 Add frontend tests for valuation settings review, opening balance review, valuation close preview, and estimate/official labels.
- [ ] 10.5 Add frontend tests for product admin inventory context and direct stock edit blocking for ledger-managed products.
- [ ] 10.6 Add frontend tests for admin order inventory context, missing COGS filters, return inventory review filters, and movement links.
- [ ] 10.7 Run backend tests for inventory/accounting/order integration suites.
- [ ] 10.8 Run frontend tests and typecheck.
- [ ] 10.9 Manually verify a seeded candle workflow: receive wax/fragrance/jars, create recipe, produce batch, sell item, cancel/return one item, run valuation preview, and generate an export package.

## 11. Documentation And Operations

- [ ] 11.1 Document inventory setup order: materials, opening balances, recipes, batches, ledger mode, valuation settings, accountant review.
- [ ] 11.2 Document recommended candle material categories, UOM conventions, wastage handling, and supplier lot/expiry practices.
- [ ] 11.3 Document valuation limitations: no automated journal entries, no tax advice, no official output before accountant review.
- [ ] 11.4 Document rollback/fallback behavior for disabling ledger-managed inventory and preserving legacy product stock behavior.
- [ ] 11.5 Update admin/operator docs for month-end inventory close, exception resolution, and accountant export interpretation.
