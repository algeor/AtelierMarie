import React from "react";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithIntl } from "../test-utils";
import { ApiError } from "@/lib/api-client";
import type { AccountingDocumentResponse, AccountingLedgerName, AdminOrderDetailResponse, OrderResponse } from "@/lib/types";

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href, className }: { children: React.ReactNode; href: string; className?: string }) => (
    <a href={href} className={className}>{children}</a>
  ),
  usePathname: () => "/admin/orders",
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "order-blocked" }),
}));

const period = {
  id: "period-2026-08",
  period_start: "2026-08-01",
  period_end: "2026-08-31",
  currency: "EUR",
  status: "review",
  summary_totals: {
    gross_sales_cents: 10000,
    net_sales_cents: 9000,
    total_customer_payments_cents: 9000,
    stripe_fees_cents: 300,
    cod_receivable_cents: 2500,
    recorded_expenses_cents: 2000,
    estimated_product_cost_cents: 4000,
    estimated_gross_margin_cents: 5000,
    review_required_item_count: 2,
  },
  open_exception_count: 1,
  blocking_exception_count: 1,
  created_at: "2026-08-01T10:00:00Z",
  updated_at: "2026-08-01T10:00:00Z",
};

const accountingConfig = {
  seller_profile: {
    id: 1,
    effective_date: "2026-08-01",
    reviewed: true,
    company_display_name: "Atelier Marie",
    legal_name: "Atelier Marie OOD",
    default_currency: "EUR",
    bank_details_configured: true,
    created_at: "2026-08-01T10:00:00Z",
  },
  vat_fiscal_settings: {
    id: 1,
    effective_date: "2026-08-01",
    reviewed: true,
    vat_mode: "not_registered",
    oss_mode: "not_applicable",
    fiscal_document_mode: "external_reference",
    tolerance_cents: 1,
    created_at: "2026-08-01T10:00:00Z",
  },
  category_mappings: [],
  export_schema: {
    id: "default",
    workbook_language: "en",
    date_format: "yyyy-mm-dd",
    decimal_separator: ".",
    default_period_range: "monthly",
    included_tabs: ["summary", "sales", "payments"],
    reviewed: true,
    updated_at: "2026-08-01T10:00:00Z",
  },
  expense_settings: {
    id: "default",
    required_document_categories: ["materials"],
    allowed_payment_statuses: ["unpaid", "paid"],
    default_category_mappings: {},
    close_behavior: "block",
    reviewed: true,
    updated_at: "2026-08-01T10:00:00Z",
  },
  product_cost_settings: {
    id: "default",
    enabled: true,
    costing_basis: "recipe_bom",
    include_labor: true,
    include_overhead: false,
    missing_cost_policy: "warning",
    reviewed: false,
    estimate_label: "management_estimate",
    updated_at: "2026-08-01T10:00:00Z",
  },
  setup_exceptions: [],
};

const ledgerRows: Record<AccountingLedgerName, Record<string, unknown>[]> = {
  sales: [{ order_number: "AM-1001", gross_amount_cents: 9000 }],
  payments: [{ order_number: "AM-1001", gross_amount_cents: 9000 }],
  stripe_payouts: [{ payout_id: "po_123", match_status: "mismatch" }],
  cod_settlements: [],
  expenses: [],
  product_costs: [],
  documents: [],
  refunds: [],
  courier_claims: [],
  return_reasons: [],
  inventory_adjustments: [],
  inventory_movements: [],
};

const blockedOrder: OrderResponse = {
  id: "order-blocked",
  status: "delivered",
  payment_method: "cod",
  payment_status: "paid",
  stripe_checkout_url: null,
  items_total_cents: 9000,
  shipping_cents: 0,
  shipping_price_source: "live",
  shipping_is_fallback: false,
  total_cents: 9000,
  customer_email: "buyer@example.com",
  customer_name: "Buyer",
  delivery_method: "office",
  delivery_courier: "econt",
  delivery_details: null,
  notes: null,
  items: [{ product_id: "candle", product_name: "Candle", price_cents: 9000, quantity: 1 }],
  tracking_number: null,
  tracking_carrier: null,
  tracking_url: null,
  courier_status: null,
  label_url: null,
  accounting_readiness_status: "blocked",
  document_reference_status: "missing",
  blocking_exception_count: 1,
  finance_period_id: "period-2026-08",
  finance_hub_links: { period_href: "/admin/accounting?period=period-2026-08" },
  created_at: "2026-08-01T10:00:00Z",
  updated_at: "2026-08-01T10:00:00Z",
};

const blockedOrderDetail: AdminOrderDetailResponse = {
  ...blockedOrder,
  order_number: "AM-1001",
  payment_events: [],
  return_cases: [],
  return_events: [],
  refund_records: [],
  cod_settlement: null,
  cod_settlement_required: true,
  econt_cod_evidence: null,
  payment_reconciliation_status: "pending",
  payout_reconciliation_status: "not_applicable",
  cod_settlement_status: "pending",
};

const invoiceDocument: AccountingDocumentResponse = {
  id: "doc-1",
  document_type: "invoice",
  source_system: "external_accountant",
  document_number: "INV-001",
  issue_date: "2026-08-01",
  order_id: "order-blocked",
  period_id: "period-2026-08",
  currency: "EUR",
  gross_amount_cents: 9000,
  status: "recorded",
  created_at: "2026-08-01T10:00:00Z",
  updated_at: "2026-08-01T10:00:00Z",
};

const api = vi.hoisted(() => ({
  getAccountingConfig: vi.fn(),
  listFinancePeriods: vi.fn(),
  getStripePayoutImportStatus: vi.fn(),
  listFinanceExceptions: vi.fn(),
  getAccountingLedger: vi.fn(),
  listAccountingExports: vi.fn(),
  listAccountingDocuments: vi.fn(),
  listExpenseEvidence: vi.fn(),
  listProductCosts: vi.fn(),
  getMissingProductCosts: vi.fn(),
  reviewFinancePeriod: vi.fn(),
  closeFinancePeriod: vi.fn(),
  reopenFinancePeriod: vi.fn(),
  acceptFinancePeriod: vi.fn(),
  createFinancePeriod: vi.fn(),
  resolveFinanceException: vi.fn(),
  waiveFinanceException: vi.fn(),
  generateAccountingExport: vi.fn(),
  acceptAccountingExport: vi.fn(),
  syncStripeBalanceTransactions: vi.fn(),
  createSellerLegalProfile: vi.fn(),
  createVatFiscalSettings: vi.fn(),
  upsertAccountingCategoryMapping: vi.fn(),
  updateAccountingExportSchema: vi.fn(),
  updateExpenseEvidenceSettings: vi.fn(),
  updateProductCostSettings: vi.fn(),
  createExpenseEvidence: vi.fn(),
  createProductCost: vi.fn(),
  getAccountingExportDownloadUrl: vi.fn((id: string, file = "xlsx") => `/download/${id}/${file}`),
  getAdminOrders: vi.fn(),
  getAdminOrder: vi.fn(),
  listOrderAccountingDocuments: vi.fn(),
  createAccountingDocument: vi.fn(),
  updateAccountingDocument: vi.fn(),
  applyManualPaymentAction: vi.fn(),
  createReturnCase: vi.fn(),
  receiveReturnCase: vi.fn(),
  inspectReturnCase: vi.fn(),
  closeReturnCase: vi.fn(),
  updateReturnAccounting: vi.fn(),
  createStripeRefund: vi.fn(),
  recordCodSettlement: vi.fn(),
  updateOrderStatus: vi.fn(),
  createAndShipEcontOrder: vi.fn(),
}));

vi.mock("@/lib/api", () => api);

vi.mock("@/components/admin/ShipOrderModal", () => ({
  ShipOrderModal: () => <div data-testid="ship-modal" />,
}));

vi.mock("@/components/admin/EcontFulfillmentPanel", () => ({
  EcontFulfillmentPanel: () => <div data-testid="econt-panel" />,
}));

import AdminAccountingPage from "@/app/[locale]/admin/accounting/page";
import AdminOrderDetailPage from "@/app/[locale]/admin/orders/[id]/page";
import AdminOrdersPage from "@/app/[locale]/admin/orders/page";

describe("Admin accounting frontend", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getAccountingConfig.mockResolvedValue(accountingConfig);
    api.listFinancePeriods.mockResolvedValue({ items: [period], total: 1 });
    api.getStripePayoutImportStatus.mockResolvedValue({ total_rows: 3, matched: 1, unmatched: 1, mismatched: 1, duplicate: 0, ignored: 0 });
    api.listFinanceExceptions.mockResolvedValue({
      items: [{ id: "ex-1", period_id: period.id, exception_type: "missing_document_reference", severity: "blocking", target_type: "order", target_id: "order-blocked", status: "open", message: "Missing document", created_at: "2026-08-01T10:00:00Z", updated_at: "2026-08-01T10:00:00Z" }],
      total: 1,
    });
    api.getAccountingLedger.mockImplementation((_periodId: string, ledger: AccountingLedgerName, options: { dateBasis?: string; page?: number; limit?: number } = {}) => {
      const page = options.page ?? 1;
      const limit = options.limit ?? 50;
      const rows = ledgerRows[ledger];
      return Promise.resolve({
        period_id: period.id,
        ledger,
        date_basis: options.dateBasis ?? "default",
        rows,
        totals: {},
        total: ledger === "sales" ? 75 : rows.length,
        page,
        limit,
      });
    });
    api.listAccountingExports.mockResolvedValue({ items: [{ id: "export-1", period_id: period.id, version: 1, schema_version: "v1", manifest: { row_counts: { sales: 1 } }, generated_at: "2026-08-01T10:00:00Z", current_final: true }], total: 1 });
    api.listAccountingDocuments.mockResolvedValue({ items: [], total: 0 });
    api.listExpenseEvidence.mockResolvedValue({ items: [{ id: "expense-1", supplier_name: "Wax Supplier", purchase_date: "2026-08-01", payment_status: "unpaid", gross_amount_cents: 2000, tax_amount_cents: 0, currency: "EUR", review_status: "missing_document", created_at: "2026-08-01T10:00:00Z", updated_at: "2026-08-01T10:00:00Z" }], total: 1 });
    api.listProductCosts.mockResolvedValue({ items: [{ id: "cost-1", product_name: "Candle", effective_date: "2026-08-01", costing_basis: "recipe_bom", material_cost_cents: 400, packaging_cost_cents: 100, labor_cost_cents: 0, overhead_cost_cents: 0, estimated_unit_cost_cents: 500, currency: "EUR", reviewed: true, accountant_reviewed: false, review_status: "reviewed", source_expense_ids: [], components: [], created_at: "2026-08-01T10:00:00Z", updated_at: "2026-08-01T10:00:00Z" }], total: 1 });
    api.getMissingProductCosts.mockResolvedValue({ items: [{ order_id: "order-blocked", order_date: "2026-08-01", product_id: "missing", product_name: "Missing Candle" }], total: 1 });
    api.reviewFinancePeriod.mockResolvedValue(period);
    api.closeFinancePeriod.mockResolvedValue({ ...period, status: "closed" });
    api.reopenFinancePeriod.mockResolvedValue({ ...period, status: "reopened" });
    api.resolveFinanceException.mockResolvedValue({ id: "ex-1", status: "resolved" });
    api.waiveFinanceException.mockResolvedValue({ id: "ex-1", status: "waived" });
    api.createExpenseEvidence.mockResolvedValue({});
    api.createProductCost.mockResolvedValue({});
    api.getAdminOrders.mockResolvedValue({ items: [blockedOrder], total: 1, page: 1, limit: 100 });
    api.getAdminOrder.mockResolvedValue(blockedOrderDetail);
    api.listOrderAccountingDocuments.mockResolvedValue({ items: [invoiceDocument], total: 1 });
    api.createAccountingDocument.mockResolvedValue({ ...invoiceDocument, id: "doc-new", document_number: "FR-100" });
    api.updateAccountingDocument.mockResolvedValue(invoiceDocument);
  });

  it("renders the finance hub overview and requires a reopen reason", async () => {
    renderWithIntl(<AdminAccountingPage />);

    expect(await screen.findByText("Accounting & Finance Hub")).toBeInTheDocument();
    expect(screen.getByText("Net sales")).toBeInTheDocument();
    api.closeFinancePeriod.mockRejectedValueOnce(new ApiError({ error: { code: "BLOCKING_EXCEPTIONS", message: "Blocking exceptions remain", details: null } }));
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(await screen.findByText("Blocking exceptions remain")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Reopen" }));

    expect(await screen.findByText("Reason required")).toBeInTheDocument();
  });

  it("supports exception actions, ledgers, exports, settings, expenses, and product costs", async () => {
    renderWithIntl(<AdminAccountingPage />);
    await screen.findByText("Accounting & Finance Hub");

    fireEvent.click(screen.getByRole("button", { name: "Exceptions" }));
    expect(await screen.findByText("Missing document")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Waive" }));
    expect(await screen.findByText("Reason required")).toBeInTheDocument();
    expect(api.waiveFinanceException).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("Reason ex-1"), { target: { value: "Accountant confirmed" } });
    fireEvent.click(screen.getByRole("button", { name: "Resolve" }));
    await waitFor(() => expect(api.resolveFinanceException).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: "Ledgers" }));
    expect(await screen.findByText("AM-1001")).toBeInTheDocument();
    expect(screen.getByText("Page 1 of 2")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Date basis"), { target: { value: "payment_date" } });
    await waitFor(() => expect(api.getAccountingLedger).toHaveBeenLastCalledWith(period.id, "sales", { dateBasis: "payment_date", page: 1, limit: 50 }));
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    await waitFor(() => expect(api.getAccountingLedger).toHaveBeenLastCalledWith(period.id, "sales", { dateBasis: "payment_date", page: 2, limit: 50 }));
    fireEvent.click(screen.getByRole("button", { name: "COD/courier" }));
    expect(await screen.findByText("No ledger rows.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Exports" }));
    expect(await screen.findByRole("link", { name: "Download XLSX" })).toHaveAttribute("href", "/download/export-1/xlsx");

    fireEvent.click(screen.getByRole("button", { name: "Settings" }));
    expect(await screen.findByText("Bank details redacted in hub view")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Expenses" }));
    expect(await screen.findByText("Wax Supplier")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Product costs" }));
    expect(await screen.findByText("Missing Candle")).toBeInTheDocument();
  });

  it("shows accounting flags and filter controls in admin orders", async () => {
    renderWithIntl(<AdminOrdersPage />);

    expect(await screen.findByText("blocked")).toBeInTheDocument();
    expect(screen.getByText("missing")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Finance hub" })).toHaveAttribute("href", "/admin/accounting?period=period-2026-08");

    fireEvent.click(screen.getByRole("button", { name: "Missing document" }));
    await waitFor(() => expect(api.getAdminOrders).toHaveBeenLastCalledWith(1, 100, undefined, undefined, undefined, "missing_document_reference"));
  });

  it("shows order detail accounting documents and finance hub links", async () => {
    renderWithIntl(<AdminOrderDetailPage />);

    expect(await screen.findByText("Accounting references")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Finance hub" })).toHaveAttribute("href", "/admin/accounting?period=period-2026-08");
    expect(screen.getByText("Readiness")).toBeInTheDocument();
    expect(screen.getByText("blocked")).toBeInTheDocument();
    expect(screen.getByText("INV-001")).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("Document number"), { target: { value: "FR-100" } });
    fireEvent.change(screen.getByPlaceholderText("Gross cents"), { target: { value: "9000" } });
    fireEvent.click(screen.getByRole("button", { name: "Add document" }));

    await waitFor(() => expect(api.createAccountingDocument).toHaveBeenCalledWith(expect.objectContaining({
      document_number: "FR-100",
      order_id: "order-blocked",
      gross_amount_cents: 9000,
    })));
  });
});
