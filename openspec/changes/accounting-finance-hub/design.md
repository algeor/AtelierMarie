## Context

Atelier Marie is a FastAPI + SQLite backend with a Next.js admin frontend. Recent
payment, courier, return, refund, and COD settlement work already separates order,
payment, courier, stock, and accounting evidence. The current accounting surface is
narrow: admin CSV endpoints export Stripe refunds, COD settlements, courier claims,
return reasons, and return inventory adjustments.

Research for this change is captured in `docs/accounting-finance-hub-research.md`.
The important accounting conclusions are:

- Sales revenue, payments, processor/courier payouts, and bank deposits are
  different accounting views and occur on different dates.
- EU VAT invoices need stable issue dates, sequential numbers, seller/customer
  fields, line details, VAT rates/amounts, and references for credit notes when
  the app issues invoice-like documents.
- Bulgaria's e-shop fiscalization rules around VAT Act Art. 118 and Ordinance
  N-18 are payment-method-sensitive and can require fiscal receipts, e-receipts,
  or standardized monthly audit files in specific setups.
- Supplier purchases, materials, packaging, tools, ads, subscriptions, and other
  expenses are accounting evidence too. Capturing them in the same hub gives the
  accountant a fuller monthly handoff and gives the owner useful margin signals.
- The website should preserve fiscal/accounting evidence and export it clearly,
  but should not claim to be a certified fiscal device, legal tax engine, or
  official inventory valuation system.

Stakeholders are the owner/admin, the accountant, and future implementers. The
primary workflow is month end: resolve review items, close a period, generate a
versioned export package, and give the accountant all source data needed to book
the month.

## Goals / Non-Goals

**Goals:**

- Provide a single admin Accounting & Finance Hub for monthly review and export.
- Keep sales, payments, payouts, refunds, COD/courier settlements, fees, tax, and
  fiscal-document evidence as separate ledgers.
- Reuse existing return/refund/COD/courier CSV report logic inside the broader
  export package.
- Add accountant-reviewed settings for seller legal profile, VAT/fiscal mode,
  document references, and export category mappings.
- Add a document registry for invoices, credit notes, fiscal receipt references,
  and external accountant/fiscal-system document numbers.
- Add Stripe payout reconciliation so payment processor fees and payouts are not
  confused with order revenue.
- Add an expense evidence register for supplier invoices/receipts, materials,
  packaging, tools, subscriptions, ads, payment status, attachment references,
  and accountant category mappings.
- Add optional product-cost estimate support for practical margin reporting using
  reviewed cost snapshots or recipe/BOM-style inputs, without treating it as
  official COGS or inventory valuation.
- Make exports repeatable, versioned, auditable, and human-friendly.

**Non-Goals:**

- No full double-entry general ledger in Atelier Marie.
- No certified fiscal-device behavior, NRA filing, or automatic N-18 monthly audit
  file submission in this change.
- No automated tax/legal advice. The app stores configured treatment and flags
  uncertain cases; the accountant remains final reviewer.
- No direct QuickBooks/Xero API integration in MVP.
- No official inventory valuation, stock capitalization, or accounting-grade COGS
  postings in MVP. Product-cost output is management reporting unless the
  accountant explicitly reviews and accepts the costing method.

## Decisions

### 1. Build an evidence and reconciliation layer, not accounting software

The app will produce ledgers, review exceptions, and export packages. It will not
post journal entries, maintain a chart of accounts as the accounting source of
truth, or calculate official tax filings.

Rationale: Atelier Marie already owns operational truth: orders, payments,
refunds, courier evidence, and stock events. The accountant owns final accounting
treatment. A clean evidence layer gives the accountant better input without
creating legal or maintenance risk.

Alternative considered: add a full general ledger. Rejected because it would
duplicate accounting software and require country-specific bookkeeping policy.

### 2. Use immutable period exports with reopen/version history

Create `finance_periods`, `finance_export_packages`, and `finance_audit_events`.
Periods move through `open`, `review`, `closed`, `exported`, `accepted`, and
`reopened`. A reopen never mutates an old export package; it creates a new version
with a reason and audit trail.

Rationale: accountants need to know exactly which data was handed over. Immutable
exports prevent silent month-end drift.

Alternative considered: regenerate ad hoc CSVs on demand. Rejected because totals
can change after refunds, courier settlement, manual corrections, or late Stripe
payout data.

### 3. Generate accounting ledgers from authoritative operational tables

Ledger services will read from `orders`, `order_items`, payments/refunds,
`payment_events`, return/refund tables, courier events, COD settlement records,
and document references. Where source data can later change, the ledger row must
include the checkout-time snapshot or export-time snapshot needed for audit.

Rationale: operational tables remain the source of truth, while ledger rows become
repeatable reporting views. This avoids introducing a second mutable source of
truth.

Alternative considered: persist every ledger row eagerly on every event. Rejected
for MVP because it increases race and migration complexity. Persist export
snapshots instead.

### 4. Separate sales, payment, payout, and document dates

Every ledger row must expose the date that defines it: order date, payment capture
date, refund date, payout effective/arrival date, delivery date, fiscal document
date, or export period date. Reports must not rely on one universal `created_at`.

Rationale: Shopify and Stripe documentation both distinguish order revenue from
payment activity and payout/bank timing. This is essential for reconciliation.

Alternative considered: group everything by order date. Rejected because Stripe
payouts, refunds, and COD settlements will not match bank deposits by order date.

### 5. Treat fiscal/tax documents as references unless the app is the issuer

Add `accounting_documents` to store document type, external/source system,
document number, issue date, linked order/refund/period, currency, totals, VAT
summary, file reference if available, status, and notes. If the app later issues
invoices itself, numbering must be sequential, locked, and audited; MVP supports
external references first.

Rationale: Bulgaria N-18 and VAT invoicing rules are strict. Capturing references
and evidence is useful now; claiming fiscal issuance requires a separate approved
implementation.

Alternative considered: generate invoices/fiscal receipts immediately. Rejected
until the accountant confirms legal settings, numbering, fiscal-device/e-shop
requirements, and document wording.

### 6. Add accountant-reviewed configuration with audit history

Use settings tables rather than environment variables for business/accounting
configuration that the owner/accountant must review: seller legal profile, VAT
registration mode, OSS mode, fiscal document mode, export default period, category
mappings, and close tolerances. Every change writes an audit event.

Rationale: these values affect exports and must be visible in admin history. They
are not secrets.

Alternative considered: hard-code Bulgarian values and thresholds. Rejected
because legal thresholds and registration status can change and depend on the
seller's facts.

### 7. Model Stripe payouts as imported provider activity

Use Stripe balance/reporting APIs where possible to import balance transactions,
payouts, fees, refunds, disputes, currency conversion, and trace IDs. Store raw
provider IDs, major/minor-unit amounts, currency, reporting category, payout ID,
and match status. Keep manual CSV import as fallback.

Rationale: Stripe fees and payouts are provider-side facts. They should reconcile
against payments and bank deposits, not be derived from order totals.

Alternative considered: estimate fees from payment amount. Rejected because real
fees include adjustments, FX, refunds, disputes, holds, and payout failures.

### 8. Use XLSX as the primary handoff format, with CSV and JSON manifest

Add `openpyxl` for server-side workbook generation. Each export package contains
an XLSX workbook, component CSV files, and a JSON manifest with schema version,
filters, row counts, totals, generated-by metadata, and SHA-256 hashes.

Rationale: accountants can inspect XLSX easily, while CSV and JSON support import
and reproducibility. Hashes make it clear if a file changed after export.

Alternative considered: CSV only. Rejected because multi-tab XLSX is a better
human handoff for a monthly finance pack.

### 9. Exceptions block close unless explicitly waived

Generate exceptions for missing VAT/fiscal classification, missing document
reference, paid order without payment record, provider payment without order,
Stripe payout not matched, COD delivered but unsettled, settlement mismatch,
refund without credit/document reference, duplicate provider ID, missing seller
profile, or negative/rounding totals over tolerance. A waiver requires a role,
reason, and audit event.

Rationale: the owner needs a practical month-end checklist. Blocking close on
high-risk gaps prevents bad exports while still allowing business judgment.

Alternative considered: show warnings only. Rejected because warnings are easy to
ignore at month end.

### 10. Minimize PII in exports and logs

Exports include customer data only where accounting requires it: order number,
invoice/business fields, VAT ID, country, payment references, and contact email if
needed for accountant matching. Logs and audit events use IDs and redacted values.

Rationale: finance exports need enough evidence, but privacy exposure should not
grow without a clear accounting reason.

Alternative considered: dump full order JSON. Rejected because it would include
unnecessary addresses, notes, and phone data.

### 11. Add expense evidence now, and product costing as estimates

Add expense records for supplier invoices/receipts, material purchases,
packaging, tools/equipment, subscriptions, ads, courier/provider charges, and
owner reimbursements. Each expense stores supplier, document number/date,
purchase date, payment date/status, category mapping, currency, net/tax/gross
amounts, file reference, notes, and audit metadata.

For product costing, support simple cost snapshots and optional recipe/BOM-style
inputs: material quantity, unit cost, packaging cost, optional labor estimate,
optional overhead estimate, effective date, source expense/material link, and
review status. Sales exports can include estimated unit cost and estimated gross
margin when costing is enabled, but this must be labeled as estimate data.

Rationale: the accountant needs purchase evidence, and the owner needs to know
whether products are profitable. A lightweight evidence register solves both
without introducing a full inventory accounting system.

Alternative considered: defer all expense tracking. Rejected because sales-only
exports do not tell the accountant or owner enough about the month. Alternative
considered: implement full inventory costing. Rejected because weighted-average,
FIFO, waste, labor capitalization, and stock valuation require accountant policy
and a separate inventory design.

## Risks / Trade-offs

- Legal/fiscal misconfiguration -> require accountant-reviewed settings and keep
  fiscal-device/NRA filing out of scope.
- Export totals differ from bank deposits -> expose separate sales, payment, and
  payout ledgers with explicit dates and reconciliation status.
- Late refunds or payouts after period close -> reopen period and create a new
  export version; never overwrite old packages.
- Stripe API/reporting availability -> support manual CSV import and review
  exceptions when provider data is missing.
- Dirty operational data from old orders -> include backfill defaults and mark
  legacy rows as `legacy_incomplete` exceptions instead of silently guessing.
- Missing supplier documents -> allow draft expense records, but flag missing
  invoice/receipt references before close when the category requires evidence.
- Misleading margin data -> label product-cost outputs as estimates, store
  costing basis/effective date, and require review before including them as
  accountant-facing cost fields.
- Large export packages -> build ledgers with paginated queries and stream ZIP
  output where practical; enforce date range limits if needed.
- PII leakage -> redact audit logs and limit export fields to accountant-useful
  columns.

## Migration Plan

1. Add finance settings, document registry, expense, product-cost snapshot,
   payout/import, period, export package, and audit tables with additive
   migrations.
2. Backfill seller settings as incomplete defaults and create a setup-required
   exception until reviewed.
3. Add ledger services and tests over existing orders/payments/refunds/COD data.
4. Add Stripe payout import/sync and manual import fallback.
5. Add expense evidence and product-cost estimate services, ledgers, and review
   exceptions.
6. Add finance hub APIs and admin UI for periods, exceptions, ledgers, expenses,
   product-cost settings, and exports.
7. Add export package generation using XLSX/CSV/JSON and archive file storage.
8. Add checkout/admin order extensions for optional business invoice fields,
   document references, and accounting readiness.

Rollback: all schema changes are additive. If the UI is disabled, existing orders,
payments, returns, and current CSV report endpoints continue to work. Export files
already generated remain static artifacts.

## Open Questions

- Which accountant import format is preferred after XLSX/CSV: Bulgarian accounting
  software template, QuickBooks/Xero import, or custom CSV mapping?
- Will Atelier Marie issue invoices inside this app, through the accountant, or
  through separate fiscal/accounting software?
- What exact fiscal-document mode applies to the production payment setup under
  Ordinance N-18?
- Should customer invoice requests be collected during checkout immediately, or
  only by admin after order placement in the first implementation?
- Should historic BGN-era orders be migrated with dual currency display, or are
  all production accounting periods EUR-only?
- Which expense categories should require an attached invoice/receipt before
  period close?
- Should product-cost estimates include labor and overhead now, or only direct
  materials and packaging for the first implementation?
