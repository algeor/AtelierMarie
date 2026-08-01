## 1. Dependencies And Schema

- [ ] 1.1 Add XLSX generation dependency (`openpyxl`) to backend project dependencies.
- [ ] 1.2 Add finance period table with period dates, currency, status, snapshot totals, actor fields, and timestamps.
- [ ] 1.3 Add finance audit event table with actor, action, target, request id, redacted before/after payload, reason, and timestamp.
- [ ] 1.4 Add seller legal profile version table with effective date, reviewed flag, company identifiers, address, contact, bank details, and default currency.
- [ ] 1.5 Add VAT/fiscal settings version table with reviewed flag, VAT mode, OSS mode, document reference requirements, thresholds, tolerances, and warning metadata.
- [ ] 1.6 Add accounting category mapping and export schema settings tables.
- [ ] 1.7 Add accounting document registry table for invoice, credit note, fiscal receipt, alternative document, and external accountant/fiscal-system references.
- [ ] 1.8 Add Stripe payout/balance transaction tables with provider ids, reporting category, dates, gross/fee/net amounts, currency, payout id, trace id, status, and match status.
- [ ] 1.9 Add export package table with period id, version, file paths, manifest metadata, acceptance metadata, actor fields, and timestamps.
- [ ] 1.10 Add order/accounting snapshot fields needed for invoice profile, settings version references, accounting classification, and readiness status.

## 2. Configuration Services

- [ ] 2.1 Implement seller legal profile service with versioning, reviewed state, redaction helpers, and audit writes.
- [ ] 2.2 Implement VAT/fiscal settings service with reviewed state, configurable thresholds/tolerances, document rules, and audit writes.
- [ ] 2.3 Implement accounting category mapping service for ledger/export category assignment.
- [ ] 2.4 Implement export schema settings service for workbook language, date format, decimal separator, included tabs, and custom column names.
- [ ] 2.5 Add admin API endpoints for accounting configuration read/update/review actions.
- [ ] 2.6 Add setup-required exceptions when seller profile or VAT/fiscal settings are missing or unreviewed.

## 3. Checkout And Order Accounting Capture

- [ ] 3.1 Extend checkout request models with optional `invoice_profile` fields and validation.
- [ ] 3.2 Persist invoice profile snapshot on created orders without requiring it for normal checkout.
- [ ] 3.3 Capture accounting snapshot fields at checkout: currency, seller settings version, VAT/fiscal settings version, payment method, delivery/customer country, discounts, shipping, and line data.
- [ ] 3.4 Add initial VAT/accounting classification state for domestic default, business VAT ID provided, cross-border candidate, manual review, and unreviewed orders.
- [ ] 3.5 Ensure missing accounting settings do not block customer checkout and instead create later accounting exceptions.
- [ ] 3.6 Update order response/admin response models and frontend types for invoice profile and accounting snapshot fields.

## 4. Finance Period And Exception Engine

- [ ] 4.1 Implement finance period CRUD and lifecycle transitions: open, review, closed, exported, accepted, reopened.
- [ ] 4.2 Implement finance audit event writer and integrate it with period actions.
- [ ] 4.3 Implement exception engine for missing settings, missing document reference, payment/order mismatch, payout mismatch, COD settlement gaps, refund document gaps, duplicate provider ids, and rounding differences.
- [ ] 4.4 Add exception resolution and waiver actions requiring admin actor and reason.
- [ ] 4.5 Block period close when blocking exceptions are unresolved or unwaived.
- [ ] 4.6 Snapshot summary totals when a period closes.
- [ ] 4.7 Implement period reopen behavior that preserves prior exports and requires a reason.

## 5. Ledger Services

- [ ] 5.1 Implement sales ledger query/service with order line, shipping, discount, tax, return/reversal, and adjustment rows.
- [ ] 5.2 Implement payment/refund ledger service for Stripe payments, COD/manual collections, failed/review payments, refunds, and disputes.
- [ ] 5.3 Implement Stripe payout/fee ledger service using stored provider balance transaction data.
- [ ] 5.4 Implement COD/courier settlement ledger service reusing current COD settlement and Econt COD evidence report logic.
- [ ] 5.5 Implement refund/return/courier claim/inventory adjustment ledger adapters reusing existing accounting report service rows.
- [ ] 5.6 Implement accounting document ledger service for invoices, credit notes, fiscal receipt references, and external documents.
- [ ] 5.7 Add date-basis filtering for sales/order date, payment date, payout date, settlement date, and document issue date.
- [ ] 5.8 Add admin ledger API endpoints with pagination, totals, filters, and no-store cache headers.

## 6. Stripe Payout Reconciliation

- [ ] 6.1 Implement Stripe balance transaction import/sync using Stripe report/balance data where available.
- [ ] 6.2 Add manual Stripe CSV import fallback with validation and provider-id deduplication.
- [ ] 6.3 Match Stripe balance transactions to local payments, refunds, disputes, and payout ids.
- [ ] 6.4 Compute Stripe payout mismatch status using configured tolerance.
- [ ] 6.5 Create accounting exceptions for unmatched Stripe provider rows, duplicate provider ids, and payout mismatches.
- [ ] 6.6 Add admin API endpoints for payout import status, sync trigger, manual import, and payout match review.

## 7. Accounting Document Registry

- [ ] 7.1 Implement accounting document create/update/list service with linked order/refund/period support.
- [ ] 7.2 Validate credit notes require an original document reference.
- [ ] 7.3 Enforce document type/source/status enums and amount/currency validation.
- [ ] 7.4 Write finance audit events for every document reference create/update.
- [ ] 7.5 Add admin API endpoints for order document references and document ledger operations.
- [ ] 7.6 Add missing-document exceptions based on configured payment method and fiscal mode rules.

## 8. Export Package Builder

- [ ] 8.1 Implement XLSX workbook builder with summary, ledgers, existing reports, exceptions, settings snapshot, and source metadata sheets.
- [ ] 8.2 Implement component CSV generation for every export workbook tab.
- [ ] 8.3 Implement JSON manifest generation with schema version, filters, row counts, totals, file list, and SHA-256 hashes.
- [ ] 8.4 Store export package files in a deterministic private exports directory outside public static assets.
- [ ] 8.5 Enforce final export generation only for closed periods.
- [ ] 8.6 Preserve immutable package versions and create new versions after reopen/reclose.
- [ ] 8.7 Add admin package download endpoint with no-store cache headers and admin authentication.
- [ ] 8.8 Add accountant acceptance action that records acceptance metadata and moves current period to accepted.

## 9. Admin Finance Hub Frontend

- [ ] 9.1 Add `/admin/accounting` route with period selector, status banner, summary cards, exception count, and export status.
- [ ] 9.2 Add finance period create/review/close/reopen/accept controls with required reason fields where applicable.
- [ ] 9.3 Add exception queue UI with filters, linked order/document/payout context, resolve, and waive actions.
- [ ] 9.4 Add ledger tabs or subpages for sales, payments/refunds, Stripe payouts/fees, COD/courier settlements, documents, and existing return/refund reports.
- [ ] 9.5 Add export history UI with package versions, manifest summary, download actions, and acceptance metadata.
- [ ] 9.6 Add accounting settings UI for seller profile, VAT/fiscal mode, category mappings, export schema, reviewed state, and redacted bank details.
- [ ] 9.7 Add i18n strings for English and Bulgarian admin accounting UI.
- [ ] 9.8 Add Accounting sidebar/navigation entry consistent with the existing admin layout.

## 10. Admin Orders Integration

- [ ] 10.1 Add accounting readiness fields to admin order list and detail API responses.
- [ ] 10.2 Add admin order filters for missing document reference, unresolved exception, payout mismatch, COD settlement pending, refund document missing, VAT review required, and finance period id.
- [ ] 10.3 Add order detail document reference panel for invoice, credit note, fiscal receipt, and external document references.
- [ ] 10.4 Add order detail links into the finance hub for related period, ledger rows, document rows, and exceptions.
- [ ] 10.5 Update frontend admin order list/detail components to display accounting flags without disrupting fulfillment actions.

## 11. Security, Privacy, And Operations

- [ ] 11.1 Ensure all finance APIs require admin authentication and return no-store cache headers for exports and sensitive ledger views.
- [ ] 11.2 Redact customer notes, full addresses, phone numbers, bank details, and raw provider payloads from logs and audit events unless explicitly required in export rows.
- [ ] 11.3 Add role/actor checks for close, reopen, waive exception, export, and acceptance actions using existing admin identity.
- [ ] 11.4 Add operational documentation for accountant validation of VAT/fiscal settings and export workflow.
- [ ] 11.5 Document that certified fiscal-device behavior, NRA filing, and official tax advice are out of scope for this change.

## 12. Backend Tests

- [ ] 12.1 Add migration/schema tests for new finance, settings, document, payout, export, and audit tables.
- [ ] 12.2 Add configuration service tests for versioning, reviewed state, redaction, and audit events.
- [ ] 12.3 Add checkout route tests for valid/invalid invoice profile and accounting snapshot capture.
- [ ] 12.4 Add finance period lifecycle tests for create, review, close blocking, close success, export, accept, reopen, and audit events.
- [ ] 12.5 Add exception engine tests for missing settings, missing documents, COD unsettled, Stripe mismatch, duplicate provider id, refund document missing, and waiver behavior.
- [ ] 12.6 Add ledger service tests for sales, payments/refunds, payouts/fees, COD/courier, document, and date-basis filtering.
- [ ] 12.7 Add Stripe payout import/sync tests with matched, unmatched, duplicate, fee, refund, dispute, and payout failure rows.
- [ ] 12.8 Add document registry tests for invoice/fiscal reference CRUD, credit note original-reference validation, and audit events.
- [ ] 12.9 Add export builder tests for XLSX tabs, CSV components, JSON manifest, hashes, immutable versions, and no overwrite after reopen.
- [ ] 12.10 Add admin API access-control tests for finance hub, ledgers, settings, export download, and package generation endpoints.

## 13. Frontend Tests And Verification

- [ ] 13.1 Add frontend tests for Accounting & Finance Hub access, period selector, summary cards, and status banners.
- [ ] 13.2 Add frontend tests for period actions, required reopen/waiver reasons, and blocked close behavior.
- [ ] 13.3 Add frontend tests for exception queue filters, linked context, resolve, and waiver actions.
- [ ] 13.4 Add frontend tests for ledger table rendering, empty states, pagination, and date-basis filters.
- [ ] 13.5 Add frontend tests for accounting settings forms, reviewed state, validation errors, and bank-detail redaction.
- [ ] 13.6 Add frontend tests for export history, package download action, and accountant acceptance state.
- [ ] 13.7 Add frontend tests for admin order accounting flags, filters, document reference panel, and finance hub links.
- [ ] 13.8 Run backend tests for accounting-related suites.
- [ ] 13.9 Run frontend tests and typecheck.
- [ ] 13.10 Manually inspect a generated XLSX/CSV/JSON export package for one seeded period with card, COD, refund, return, courier fee, and document-reference examples.
