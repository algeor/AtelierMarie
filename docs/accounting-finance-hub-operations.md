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

If seller or VAT/fiscal settings are missing or unreviewed, the hub should create
setup exceptions and block final period close until resolved or explicitly waived.

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
7. Resolve or waive exceptions with reasons. Waivers should explain the accounting
   decision, not hide missing evidence.
8. Close the period only after blocking exceptions are resolved or waived.
9. Generate the accountant export package and send the XLSX/CSV/manifest package.
10. Record accountant acceptance or reopen the period with a reason if corrections
    are needed. Reopening must create a new export version; old packages remain
    immutable.

## Explicit Non-Goals

- The website does not issue certified fiscal receipts or act as a certified
  fiscal device.
- The website does not file NRA returns, OSS returns, VAT returns, or Ordinance
  N-18 monthly audit files.
- The website does not provide tax or legal advice. Configured VAT/fiscal modes
  are stored evidence and review state; the accountant remains final reviewer.
- The website does not maintain a full double-entry general ledger or official
  chart of accounts.
- Product-cost estimates are management reporting unless accountant-reviewed.
  Official inventory valuation, stock capitalization, FIFO/weighted-average
  valuation, and accounting-grade COGS postings are out of scope for this change.

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
