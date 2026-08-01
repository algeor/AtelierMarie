## 1. Dependencies And Schema

- [x] 1.1 Add XLSX generation dependency (`openpyxl`) to backend project dependencies.
- [x] 1.2 Add finance period table with period dates, currency, status, snapshot totals, actor fields, and timestamps.
- [x] 1.3 Add finance audit event table with actor, action, target, request id, redacted before/after payload, reason, and timestamp.
- [x] 1.4 Add seller legal profile version table with effective date, reviewed flag, company identifiers, address, contact, bank details, and default currency.
- [x] 1.5 Add VAT/fiscal settings version table with reviewed flag, VAT mode, OSS mode, document reference requirements, thresholds, tolerances, and warning metadata.
- [x] 1.6 Add accounting category mapping and export schema settings tables.
- [x] 1.7 Add accounting document registry table for invoice, credit note, fiscal receipt, alternative document, and external accountant/fiscal-system references.
- [x] 1.8 Add Stripe payout/balance transaction tables with provider ids, reporting category, dates, gross/fee/net amounts, currency, payout id, trace id, status, and match status.
- [x] 1.9 Add export package table with period id, version, file paths, manifest metadata, acceptance metadata, actor fields, and timestamps.
- [x] 1.10 Add order/accounting snapshot fields needed for invoice profile, settings version references, accounting classification, and readiness status.
- [x] 1.11 Add expense evidence tables with supplier, document reference, dates, payment status, category mapping, net/tax/gross amounts, currency, attachment reference, review status, and audit fields.
- [x] 1.12 Add optional product-cost estimate tables for product cost versions, costing basis, material/packaging/labor/overhead components, effective dates, source expense/material links, reviewed state, and audit fields.

## 2. Configuration Services

- [x] 2.1 Implement seller legal profile service with versioning, reviewed state, redaction helpers, and audit writes.
- [x] 2.2 Implement VAT/fiscal settings service with reviewed state, configurable thresholds/tolerances, document rules, and audit writes.
- [x] 2.3 Implement accounting category mapping service for ledger/export category assignment.
- [x] 2.4 Implement export schema settings service for workbook language, date format, decimal separator, included tabs, and custom column names.
- [x] 2.5 Add admin API endpoints for accounting configuration read/update/review actions.
- [x] 2.6 Add setup-required exceptions when seller profile or VAT/fiscal settings are missing or unreviewed.
- [x] 2.7 Implement expense evidence settings for categories that require document evidence, allowed payment statuses, default mappings, and close behavior.
- [x] 2.8 Implement product-cost settings for enabled state, costing basis, labor/overhead inclusion, missing-cost policy, reviewed state, and estimate labeling.

## 3. Checkout And Order Accounting Capture

- [x] 3.1 Extend checkout request models with optional `invoice_profile` fields and validation.
- [x] 3.2 Persist invoice profile snapshot on created orders without requiring it for normal checkout.
- [x] 3.3 Capture accounting snapshot fields at checkout: currency, seller settings version, VAT/fiscal settings version, payment method, delivery/customer country, discounts, shipping, and line data.
- [x] 3.4 Add initial VAT/accounting classification state for domestic default, business VAT ID provided, cross-border candidate, manual review, and unreviewed orders.
- [x] 3.5 Ensure missing accounting settings do not block customer checkout and instead create later accounting exceptions.
- [x] 3.6 Update order response/admin response models and frontend types for invoice profile and accounting snapshot fields.

## 4. Finance Period And Exception Engine

- [x] 4.1 Implement finance period CRUD and lifecycle transitions: open, review, closed, exported, accepted, reopened.
- [x] 4.2 Implement finance audit event writer and integrate it with period actions.
- [x] 4.3 Implement exception engine for missing settings, missing document reference, payment/order mismatch, payout mismatch, COD settlement gaps, refund document gaps, expense document gaps, duplicate provider ids, missing product costs when configured, and rounding differences.
- [x] 4.4 Add exception resolution and waiver actions requiring admin actor and reason.
- [x] 4.5 Block period close when blocking exceptions are unresolved or unwaived.
- [x] 4.6 Snapshot summary totals when a period closes.
- [x] 4.7 Implement period reopen behavior that preserves prior exports and requires a reason.

## 5. Ledger Services

- [x] 5.1 Implement sales ledger query/service with order line, shipping, discount, tax, return/reversal, and adjustment rows.
- [x] 5.2 Implement payment/refund ledger service for Stripe payments, COD/manual collections, failed/review payments, refunds, and disputes.
- [x] 5.3 Implement Stripe payout/fee ledger service using stored provider balance transaction data.
- [x] 5.4 Implement COD/courier settlement ledger service reusing current COD settlement and Econt COD evidence report logic.
- [x] 5.5 Implement refund/return/courier claim/inventory adjustment ledger adapters reusing existing accounting report service rows.
- [x] 5.6 Implement accounting document ledger service for invoices, credit notes, fiscal receipt references, and external documents.
- [x] 5.7 Implement expense evidence ledger service for supplier invoices/receipts, materials, packaging, tools, subscriptions, ads, courier/provider charges, owner reimbursements, payment status, and attachment references.
- [x] 5.8 Implement optional product-cost estimate ledger service with effective cost versions, costing basis, estimated unit cost, estimated total cost, estimated gross margin, and missing-cost warnings.
- [x] 5.9 Add date-basis filtering for sales/order date, payment date, payout date, settlement date, expense purchase/document/payment date, product-cost effective date, and document issue date.
- [x] 5.10 Add admin ledger API endpoints with pagination, totals, filters, and no-store cache headers.

## 6. Stripe Payout Reconciliation

- [x] 6.1 Implement Stripe balance transaction import/sync using Stripe report/balance data where available.
- [x] 6.2 Add manual Stripe CSV import fallback with validation and provider-id deduplication.
- [x] 6.3 Match Stripe balance transactions to local payments, refunds, disputes, and payout ids.
- [x] 6.4 Compute Stripe payout mismatch status using configured tolerance.
- [x] 6.5 Create accounting exceptions for unmatched Stripe provider rows, duplicate provider ids, and payout mismatches.
- [x] 6.6 Add admin API endpoints for payout import status, sync trigger, manual import, and payout match review.

## 7. Accounting Document Registry

- [x] 7.1 Implement accounting document create/update/list service with linked order/refund/period support.
- [x] 7.2 Validate credit notes require an original document reference.
- [x] 7.3 Enforce document type/source/status enums and amount/currency validation.
- [x] 7.4 Write finance audit events for every document reference create/update.
- [x] 7.5 Add admin API endpoints for order document references and document ledger operations.
- [x] 7.6 Add missing-document exceptions based on configured payment method and fiscal mode rules.

## 7A. Expense Evidence And Product Costing

- [x] 7A.1 Implement expense evidence CRUD service with validation, attachment reference support, payment status changes, category mapping, redaction, and audit events.
- [x] 7A.2 Add admin API endpoints for expense list/create/update/review, attachment reference metadata, and payment status updates.
- [x] 7A.3 Implement product-cost version CRUD service with manual cost snapshots and recipe/BOM-style component inputs.
- [x] 7A.4 Add admin API endpoints for product-cost versions, review state, effective-date lookup, and missing-cost diagnostics.
- [x] 7A.5 Link product-cost estimates to sales ledger rows by product id/SKU and order date when costing is enabled.
- [x] 7A.6 Ensure product-cost outputs are labeled as estimates unless the costing settings and effective cost version are accountant-reviewed.

## 8. Export Package Builder

- [x] 8.1 Implement XLSX workbook builder with summary, ledgers, expense evidence, optional product-cost estimates, existing reports, exceptions, settings snapshot, and source metadata sheets.
- [x] 8.2 Implement component CSV generation for every export workbook tab.
- [x] 8.3 Implement JSON manifest generation with schema version, filters, row counts, totals, file list, and SHA-256 hashes.
- [x] 8.4 Store export package files in a deterministic private exports directory outside public static assets.
- [x] 8.5 Enforce final export generation only for closed periods.
- [x] 8.6 Preserve immutable package versions and create new versions after reopen/reclose.
- [x] 8.7 Add admin package download endpoint with no-store cache headers and admin authentication.
- [x] 8.8 Add accountant acceptance action that records acceptance metadata and moves current period to accepted.
- [x] 8.9 Include expense evidence CSV/XLSX tabs and optional product-cost estimate/margin CSV/XLSX tabs with estimate/review labels in export packages.

## 9. Admin Finance Hub Frontend

- [x] 9.1 Add `/admin/accounting` route with period selector, status banner, summary cards, exception count, and export status.
- [x] 9.2 Add finance period create/review/close/reopen/accept controls with required reason fields where applicable.
- [x] 9.3 Add exception queue UI with filters, linked order/document/payout context, resolve, and waive actions.
- [x] 9.4 Add ledger tabs or subpages for sales, payments/refunds, Stripe payouts/fees, COD/courier settlements, expenses, product-cost estimates, documents, and existing return/refund reports.
- [x] 9.5 Add export history UI with package versions, manifest summary, download actions, and acceptance metadata.
- [x] 9.6 Add accounting settings UI for seller profile, VAT/fiscal mode, category mappings, export schema, reviewed state, and redacted bank details.
- [x] 9.7 Add i18n strings for English and Bulgarian admin accounting UI.
- [x] 9.8 Add Accounting sidebar/navigation entry consistent with the existing admin layout.
- [x] 9.9 Add expense evidence UI for supplier invoice/receipt records, payment status, category mapping, attachment reference status, review state, and filters.
- [x] 9.10 Add product-cost estimate UI for manual cost snapshots or recipe/BOM-style inputs, effective dates, reviewed state, and missing-cost diagnostics.

## 10. Admin Orders Integration

- [x] 10.1 Add accounting readiness fields to admin order list and detail API responses.
- [x] 10.2 Add admin order filters for missing document reference, unresolved exception, payout mismatch, COD settlement pending, refund document missing, VAT review required, and finance period id.
- [x] 10.3 Add order detail document reference panel for invoice, credit note, fiscal receipt, and external document references.
- [x] 10.4 Add order detail links into the finance hub for related period, ledger rows, document rows, and exceptions.
- [x] 10.5 Update frontend admin order list/detail components to display accounting flags without disrupting fulfillment actions.

## 11. Security, Privacy, And Operations

- [x] 11.1 Ensure all finance APIs require admin authentication and return no-store cache headers for exports and sensitive ledger views.
- [x] 11.2 Redact customer notes, full addresses, phone numbers, bank details, and raw provider payloads from logs and audit events unless explicitly required in export rows.
- [x] 11.3 Add role/actor checks for close, reopen, waive exception, export, and acceptance actions using existing admin identity.
- [x] 11.4 Add operational documentation for accountant validation of VAT/fiscal settings and export workflow.
- [x] 11.5 Document that certified fiscal-device behavior, NRA filing, and official tax advice are out of scope for this change.
- [x] 11.6 Document that product-cost estimates are management reporting unless accountant-reviewed, and official inventory valuation/accounting-grade COGS postings are out of scope.
- [x] 11.7 Redact or avoid logging expense attachment contents and supplier bank/payment details unless explicitly included in export rows.

## 12. Backend Tests

- [x] 12.1 Add migration/schema tests for new finance, settings, document, payout, export, and audit tables.
- [x] 12.2 Add configuration service tests for versioning, reviewed state, redaction, and audit events.
- [x] 12.3 Add checkout route tests for valid/invalid invoice profile and accounting snapshot capture.
- [x] 12.4 Add finance period lifecycle tests for create, review, close blocking, close success, export, accept, reopen, and audit events.
- [x] 12.5 Add exception engine tests for missing settings, missing documents, COD unsettled, Stripe mismatch, duplicate provider id, refund document missing, and waiver behavior.
- [x] 12.6 Add ledger service tests for sales, payments/refunds, payouts/fees, COD/courier, document, and date-basis filtering.
- [x] 12.7 Add Stripe payout import/sync tests with matched, unmatched, duplicate, fee, refund, dispute, and payout failure rows.
- [x] 12.8 Add document registry tests for invoice/fiscal reference CRUD, credit note original-reference validation, and audit events.
- [x] 12.9 Add export builder tests for XLSX tabs, CSV components, JSON manifest, hashes, immutable versions, and no overwrite after reopen.
- [x] 12.10 Add admin API access-control tests for finance hub, ledgers, settings, export download, and package generation endpoints.
- [x] 12.11 Add expense evidence tests for CRUD, required document exceptions, payment status, category mapping, attachment references, redaction, and audit events.
- [x] 12.12 Add product-cost estimate tests for effective-date lookup, manual snapshots, recipe/BOM components, missing-cost warnings, estimate labeling, and reviewed state.

## 13. Frontend Tests And Verification

- [x] 13.1 Add frontend tests for Accounting & Finance Hub access, period selector, summary cards, and status banners.
- [x] 13.2 Add frontend tests for period actions, required reopen/waiver reasons, and blocked close behavior.
- [x] 13.3 Add frontend tests for exception queue filters, linked context, resolve, and waiver actions.
- [x] 13.4 Add frontend tests for ledger table rendering, empty states, pagination, and date-basis filters.
- [x] 13.5 Add frontend tests for accounting settings forms, reviewed state, validation errors, and bank-detail redaction.
- [x] 13.6 Add frontend tests for export history, package download action, and accountant acceptance state.
- [x] 13.7 Add frontend tests for admin order accounting flags, filters, document reference panel, and finance hub links.
- [x] 13.8 Run backend tests for accounting-related suites.
- [x] 13.9 Run frontend tests and typecheck.
- [x] 13.10 Manually inspect a generated XLSX/CSV/JSON export package for one seeded period with card, COD, refund, return, courier fee, and document-reference examples.
- [x] 13.11 Add frontend tests for expense evidence forms, filters, required-document warnings, payment status changes, and export visibility.
- [x] 13.12 Add frontend tests for product-cost estimate forms, missing-cost diagnostics, estimate labels, and margin summary visibility.
