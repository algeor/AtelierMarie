## Why

Atelier Marie now has real e-commerce operations: card payments, payment on
delivery, couriers, refunds, returns, COD settlement, and narrow accounting CSVs.
The owner needs one month-end finance workflow that turns those operational facts
into accountant-ready evidence without pretending the website is a full accounting
or fiscalization system.

## What Changes

- Add an admin-only Accounting & Finance Hub for monthly review, close, and
  accountant handoff.
- Add accounting-oriented ledgers for sales lines, orders, payments, refunds,
  Stripe payouts/fees, COD/courier settlements, fiscal document references, and
  review exceptions.
- Add accountant-reviewed finance settings: seller legal profile, VAT mode,
  document-numbering mode, fiscal-document mode, export schema settings, and
  account/category mappings.
- Add fiscal/tax document registry records for invoices, credit notes, fiscal
  receipt references, external accounting documents, and N-18-related evidence
  without making the app a certified fiscal device.
- Add Stripe payout reconciliation import/sync support so gross payments, fees,
  refunds, disputes, holds, and bank payouts are separated from order revenue.
- Extend the existing return/refund/COD/courier CSV reports into a versioned
  monthly export package with XLSX, CSV files, JSON manifest, totals, row counts,
  hashes, and export history.
- Add a review queue for missing or inconsistent accounting evidence before a
  period can be closed.
- Add immutable export versions and audit logs for close, export, reopen, manual
  edits, and accountant acceptance notes.
- Keep tax/legal values configurable and accountant-reviewed; do not hard-code VAT
  thresholds or automate official filings in this change.

## Capabilities

### New Capabilities

- `accounting-finance-hub`: Admin finance dashboard, monthly period close workflow,
  exception review, and accountant acceptance/reopen states.
- `accounting-ledgers`: Sales, payment, payout, COD/courier, refund/return, fee,
  and fiscal-document source ledgers used for accounting exports.
- `accountant-export-package`: Versioned accountant handoff packages in XLSX, CSV,
  and JSON manifest formats with totals, row counts, hashes, and audit metadata.
- `accounting-configuration`: Seller legal profile, VAT/fiscal mode, document
  reference behavior, export schema settings, and accountant-reviewed category
  mappings.

### Modified Capabilities

- `checkout-flow`: Capture optional invoice/business customer fields and immutable
  accounting snapshots needed for later invoices, VAT classification, and exports.
- `admin-orders`: Surface accounting readiness, document references, payout/COD
  reconciliation status, and links from orders into the Accounting & Finance Hub.

## Impact

- Backend: new accounting services, export package builder, period close records,
  document registry, settings/audit tables, Stripe payout import/sync, admin
  finance routes, and reuse of existing refund/COD/courier report services.
- Frontend: new `/admin/accounting` finance hub, period close/review screens,
  export history, settings page, exception queue, and order-detail finance links.
- Data: additive SQLite migrations for finance periods, ledger snapshots,
  document references, payout records, export manifests, category mappings, and
  audit events.
- Exports: XLSX workbook plus CSV files and JSON manifest; no direct QuickBooks,
  Xero, NRA filing, or fiscal-device integration in MVP.
- Operations: accountant validates VAT/fiscal settings before production use;
  unresolved exceptions block period close unless explicitly waived with a note.
