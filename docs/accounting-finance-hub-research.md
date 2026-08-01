# Accounting And Finance Hub Research

Date: 2026-08-01
Project: Atelier Marie e-commerce website

## Goal

Design a website/admin finance area that helps the owner track business money in
one place and export accountant-ready files. The feature should support practical
e-commerce operations first: orders, payments, refunds, courier cash collection,
fees, taxes, invoices/receipts, settlements, and monthly accounting handoff.

This document is a live research log. It separates broad "gold standard" ideas
from the stricter implementation proposal that should only include legally and
operationally relevant scope.

## Early Working Assumptions

- Atelier Marie is a small e-commerce seller for handcrafted candles.
- The app already has orders, payment states, Stripe card payments, pay on
  delivery, courier integrations, and admin order management in flight.
- The accountant needs reliable source data and exports, not a replacement for
  accounting software.
- Bulgaria/EU context matters. Current app docs use EUR; export design should
  still make currency explicit and preserve source amounts.

## Research Sources To Check

- EU VAT invoicing rules and invoice field expectations.
- Bulgaria/NRA requirements that affect fiscal receipts, invoices, online sales,
  VAT registration, and retention.
- Stripe reconciliation and balance transaction reports.
- Shopify finance/order/tax export patterns.
- Xero/QuickBooks accountant export and bank reconciliation patterns.
- Practical e-commerce scenarios: COD, courier payouts, card processor fees,
  refunds, returns, discounts, shipping, B2B invoice requests, VAT/non-VAT seller.

## Source-Backed Findings

### EU VAT invoicing baseline

Source: European Commission, VAT Invoicing
https://taxation-customs.ec.europa.eu/taxation/vat/vat-businesses/invoicing_en

- Electronic invoices are equivalent to paper invoices under EU VAT invoicing
  rules, subject to recipient acceptance. B2G has structured e-invoicing rules.
- VAT invoices are required for most B2B supplies and for some B2C transactions.
  Member States can have extra national requirements for private individuals.
- Full VAT invoice fields include issue date, unique sequential number, supplier
  name/address, customer name/address, customer VAT ID where relevant,
  description and quantity, unit price excluding tax/discounts unless included,
  transaction/payment date when different, VAT rate, VAT amount, and VAT
  breakdown by rate or exemption.
- Credit/debit notes or amended documents need an unambiguous reference to the
  initial invoice and details being amended.
- Special wording is needed for exemptions and reverse charge cases.

Implementation implication: store invoice-ready snapshots at order time. Do not
derive invoice lines later from mutable product/customer data. Invoice numbering
must be sequential and auditable if the app issues invoice documents.

### EU cross-border VAT and OSS

Sources:
- Your Europe, Cross-border VAT:
  https://europa.eu/youreurope/business/taxation/vat/cross-border-vat/index_en.htm
- European Commission, One Stop Shop:
  https://vat-one-stop-shop.ec.europa.eu/one-stop-shop_en

- For B2B goods sent to another EU country, VAT is generally not charged if the
  customer has a valid EU VAT number; VIES validation matters.
- For final consumers in another EU country, the EU distance-sales threshold is
  EUR 10,000. Below it, sales may remain taxable in the supplier's country. Once
  exceeded, customer-country VAT rules apply unless another valid treatment is
  used.
- OSS lets a seller register in one Member State, declare eligible cross-border
  B2C VAT, and pay VAT due in Member States of consumption through that portal.
- OSS returns are additional; they do not replace domestic VAT obligations.

Implementation implication: even if Atelier Marie starts domestic-only, the data
model should capture customer country, B2B/B2C status, VAT ID validation status,
destination country, VAT treatment, and source evidence. Hard-coding a single VAT
rule would create future accounting risk.

### Bulgaria currency context

Source: European Central Bank press release, 2025-07-08
https://www.ecb.europa.eu/press/pr/date/2025/html/ecb.pr250708~b9676a9fa8.en.html

- The Council approved Bulgaria's accession to the euro area on 2026-01-01.
- The lev conversion rate was fixed at BGN 1.95583 = EUR 1.

Implementation implication: EUR can be the primary 2026 currency, but exports
should always include ISO currency code. If historic BGN orders exist or dual
display/support is needed, store original currency and conversion metadata.

### Bulgaria e-shop fiscalization risk area

Sources:
- NRA attachment found from `nra.bg` search result:
  https://nraapp02.nra.bg/cms5/apps/wqreg/get/7a96aae05e565a87f603d54c308e7d8e
- The attachment discusses application of VAT Act, Corporate Income Tax Act,
  Accounting Act principles, and Ordinance N-18/2006 for sales through e-shops.

Key extracted points from the NRA attachment, translated/summarized:

- An "electronic shop" is software accessed through a browser/mobile app where
  goods/services are sold by distance contract, including product selection,
  buyer contact, delivery address, and payment method.
- Under Ordinance N-18, a person selling through an e-shop may need to submit
  e-shop information to the NRA portal before starting sales, depending on the
  organization of sales, payment methods, and whether fiscal receipt issuance is
  required.
- Fiscal receipt requirements are tied to the payment method. The NRA text lists
  exceptions such as cash deposit to a payment account, credit transfer, direct
  debit, some payment-service-provider cash transfer cases, and postal money
  transfer cases.
- For online card-not-present credit/debit card payments through an e-shop,
  Ordinance N-18 contains an alternative option to report sales with a sales
  registration document instead of a fiscal/system receipt when conditions are
  met. Sellers using that option must submit a standardized monthly audit file
  to NRA by the 15th day of the following month.
- For e-commerce, the NRA notes that normal accounting and tax rules still apply
  like traditional trade: transactions should be identified by substance and
  economic reality, and profits are taxed under the corporate income tax rules.
- The NRA attachment still references the historic VAT-registration threshold of
  BGN 100,000 in 12 months. Because Bulgaria adopted EUR in 2026, the website
  should not hard-code threshold values without accountant confirmation.

Implementation implication: the website should not pretend to be a certified
fiscal device or legal fiscalization engine unless that is intentionally built
and certified. The safer MVP is to preserve fiscal evidence, record fiscal
document references, and export the data an accountant/fiscal device provider
needs. Any N-18 automated file generation should be a later accountant-approved
subproject.

### Stripe / payment processor reconciliation

Sources:
- Stripe Balance report:
  https://docs.stripe.com/reports/report-types/balance
- Stripe Balance transaction types:
  https://docs.stripe.com/reports/balance-transaction-types

- Stripe's Balance report returns complete transaction history for
  reconciliation and can be downloaded as CSV.
- Reconciliation-critical fields include balance transaction ID, created date,
  available-on date, gross, fee, net, currency, payment intent ID, charge ID,
  refund metadata, payment method, payout ID, payout effective/arrival dates,
  payout status, reporting category, and trace ID.
- Stripe balance transaction types include adjustments, disputes, payout,
  payout failures/cancellations, currency conversion, Stripe fees, FX fees, tax
  fees, refunds, reserves, and holds.

Implementation implication: order revenue and bank deposits are different views.
The app must model gross customer payment, processor fees, net payout, payout
timing, and unmatched/review-required items separately.

### Shopify-style finance reporting as e-commerce gold standard

Sources:
- Shopify finance reports:
  https://help.shopify.com/en/manual/reports-and-analytics/shopify-reports/report-types/finances-report
- Shopify payout reconciliation report:
  https://help.shopify.com/en/manual/payments/shopify-payments/payouts/payout-reconciliation-report

- Finance Summary separates sales, payments, taxes, shipping, discounts,
  returns, and gross profit.
- Shopify's total sales formula is: gross sales - discounts - sales reversals +
  taxes + shipping + fees.
- Payments reports are grouped by payment method/gateway.
- Payout reconciliation separates balance activity, fees, refunds, chargebacks,
  adjustments, holds/reserves, and payouts to bank.
- Shopify explicitly states payout reconciliation reflects funds received and
  balance timing, not revenue for accounting purposes. Sales/order reports and
  payout reports may differ due to timing, currency, fees, holds, and payout
  schedules.

Implementation implication: Atelier Marie should expose at least four separate
accounting views: sales ledger, payment ledger, payout/cash ledger, and tax/fiscal
document ledger. One "revenue" table is not enough.

### Accounting software patterns

Sources from vendor search snippets and official docs surfaced by search:
- QuickBooks reconciliation: matching transactions entered in QuickBooks with
  bank/credit card statements.
- Xero reconciliation: matching each bank statement line to an existing
  transaction or creating one during reconciliation.
- Xero/QuickBooks audit trail: date-stamped user and transaction changes.
- Xero chart of accounts: categories such as assets, liabilities, equity,
  revenue, and expenses form the backbone of bookkeeping and reporting.

Implementation implication: this website should not become a full accounting
system, but it should produce accountant-ready data mapped to simple accounting
categories: sales revenue, shipping revenue, discounts/contra-revenue, refunds,
VAT payable, processor fees, courier fees, COD receivable, Stripe clearing,
bank deposits, and unresolved differences.

## Gold-Standard Functionality Ideas

### Core finance dashboard

- Monthly finance close screen with a clear state: open, draft export, exported,
  accountant accepted, reopened.
- Top-line cards: gross sales, discounts, returns, net sales, shipping charged,
  VAT collected, total customer payments, processor/courier fees, net bank/cash
  received, open COD receivable, refunds pending, and review-required items.
- Filters by accounting period, order date, payment date, payout date, invoice
  date, delivery date, customer country, payment method, courier, VAT treatment,
  and document status.

### Sales ledger

- One immutable row per order line and adjustment event.
- Captures product title/SKU snapshot, quantity, unit gross/net price, discount,
  tax/VAT rate, VAT amount, line gross, shipping allocation, refund/reversal link,
  order number, invoice/receipt number, customer country, and delivery country.
- Separates order date from payment/capture date and delivery/fulfillment date.

### Payment ledger

- One row per payment/refund/chargeback/manual collection event.
- Captures payment method, provider, provider IDs, gross amount, currency, status,
  captured/paid/failed/refunded timestamps, related order, and reconciliation
  status.
- COD/pay-on-delivery requires a receivable state: expected from customer/courier,
  collected by courier, paid out by courier, fee deducted, discrepancy.

### Payout / bank reconciliation ledger

- Stripe payout import or sync with payout ID, arrival date, gross, fees, net,
  trace ID, and settlement currency.
- Courier payout import/manual entry with shipment/order references, COD amounts,
  courier fees, returned shipment fees, and actual bank deposit.
- Bank statement upload/import later, with match suggestions by amount, date,
  provider reference, payout ID, courier report number, and order number.

### Tax and fiscal document registry

- Document registry for invoices, credit notes, fiscal receipt references,
  alternative sales-registration documents, and accountant-uploaded final docs.
- Sequential numbering only if the app is the issuer. Otherwise store external
  fiscal/invoice numbers from the fiscal device, invoice system, or accountant.
- Track VAT registration mode: not VAT registered, domestic VAT registered,
  OSS registered, reverse-charge relevant, export/outside-EU treatment.
- Store seller legal profile with versioning: company name, UIC/EIK, VAT ID,
  address, bank details, invoice language/template settings.

### Accountant export package

- Export formats: XLSX workbook as the human-friendly main package, CSV files for
  import, and JSON manifest for audit/reproducibility.
- Include separate tabs/files: summary, sales lines, orders, payments, payouts,
  refunds/returns, fees, taxes/VAT, invoices/documents, COD/courier settlements,
  review exceptions, and source metadata.
- Each export should include period, generation timestamp, app version/schema
  version, filters, row counts, totals, and SHA-256 hashes of the component files.
- Export should be repeatable and immutable once closed. If reopened, create a
  new export version with a change log rather than overwriting the old package.

### Review and controls

- Exceptions queue: missing VAT treatment, missing invoice/fiscal document,
  payment without order, paid order without payout, payout unmatched to bank,
  refund without credit note/reference, COD collected but not paid out, negative
  totals, rounding differences over tolerance, duplicate provider IDs, changed
  seller legal profile mid-period.
- Audit log for every manual edit/export/reopen action with user, timestamp,
  before/after, reason, and request ID.
- Role-based access: admin can view, finance manager/accountant can export/close,
  owner can approve reopening.

## Strict Accounting Filter

Keep for implementation proposal:

- Accountant handoff package with summary + structured ledgers.
- Finance dashboard focused on monthly close and review exceptions.
- Sales/payment/payout separation.
- VAT/fiscal document registry and explicit VAT treatment metadata.
- COD/courier settlement tracking because Atelier Marie uses pay on delivery and
  courier integrations.
- Stripe fee/payout reconciliation because card payments are in scope.
- Immutable export versions, audit trail, and manual notes.
- Configurable legal/tax settings reviewed by accountant; no hard-coded legal
  thresholds beyond stable constants such as ISO currency codes.

Defer or avoid:

- Full double-entry general ledger inside Atelier Marie.
- Certified fiscal-device behavior or automated N-18 audit-file filing until an
  accountant/fiscalization provider signs off exact requirements.
- Automatic VAT advice. The app can classify based on configured rules and flag
  uncertain cases, but accountant remains final reviewer.
- Direct QuickBooks/Xero API integration in MVP. Export files are more reliable
  and cheaper to validate first.
- Inventory valuation/COGS unless product cost snapshots already exist and the
  accountant asks for it. Keep hooks for later.

## Current Atelier Marie Fit

Existing/recently changed code already contains a narrow accounting report base:

- `app/services/accounting_report_service.py` produces CSV rows for Stripe refund
  reconciliation, COD settlement reconciliation, courier fee/claim records,
  return reason summaries, and return inventory adjustments.
- `app/routes/admin.py` exposes admin CSV routes under `/v1/admin/reports/*` for
  those five reports.
- `tests/realapp/test_accounting_reports.py` verifies those CSV exports.
- `openspec/changes/manage-order-returns-refunds` explicitly keeps order,
  payment, courier, stock, and accounting state separate and defers full ledger,
  invoicing, VAT engine, and payout import.

Proposal implication: the new change should not replace these report endpoints.
It should turn them into part of a broader finance close/export system:

- Add missing ledgers: sales lines, payments, Stripe payouts/fees, tax/fiscal
  documents, export packages, and exceptions.
- Keep the existing return/refund/COD/courier reports as package tabs/files.
- Add period close/export metadata and immutable export versions.
- Add UI workflow for owner/accountant handoff instead of only ad hoc CSV links.

## Proposed Website Prompt / Product Brief

Build an admin-only Accounting & Finance Hub for Atelier Marie that turns order,
payment, courier, refund, return, and document data into a monthly
accountant-ready export package. The feature must keep sales, payments, payouts,
tax/fiscal documents, and operational exceptions separate, because revenue,
cash received, and processor/courier settlements happen on different timelines.

The first version should not be a full accounting system and should not provide
legal/tax advice. It should be a reliable source-data and reconciliation layer:
capture immutable order/payment snapshots, classify rows using accountant-reviewed
settings, flag missing or inconsistent evidence, and export XLSX/CSV/JSON packages
with totals, row counts, hashes, and change history. It should support domestic
Bulgarian e-commerce first, Stripe card payments, pay-on-delivery/COD courier
settlement, refunds/returns, courier fees/claims, and future EU cross-border VAT
data capture without hard-coding tax thresholds.

Primary user outcome: at month end, the owner opens one screen, resolves review
items, generates a versioned export, and sends the accountant a package that
contains all sales, VAT/fiscal document references, payments, payouts, fees,
refunds, COD/courier settlements, and exception notes needed to book the month.
