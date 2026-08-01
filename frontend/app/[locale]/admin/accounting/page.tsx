"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import {
  acceptAccountingExport,
  acceptFinancePeriod,
  closeFinancePeriod,
  createExpenseEvidence,
  createFinancePeriod,
  createProductCost,
  createSellerLegalProfile,
  createVatFiscalSettings,
  generateAccountingExport,
  getAccountingConfig,
  getAccountingExportDownloadUrl,
  getAccountingLedger,
  getMissingProductCosts,
  getStripePayoutImportStatus,
  listAccountingDocuments,
  listAccountingExports,
  listExpenseEvidence,
  listFinanceExceptions,
  listFinancePeriods,
  listProductCosts,
  reopenFinancePeriod,
  resolveFinanceException,
  reviewFinancePeriod,
  syncStripeBalanceTransactions,
  updateAccountingExportSchema,
  updateExpenseEvidenceSettings,
  updateProductCostSettings,
  upsertAccountingCategoryMapping,
  waiveFinanceException,
} from "@/lib/api";
import { ApiError } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/Skeleton";
import type {
  AccountingConfigurationResponse,
  AccountingDocumentResponse,
  AccountingLedgerName,
  AccountingLedgerResponse,
  ExpenseEvidenceResponse,
  ExpensePaymentStatus,
  ExpenseReviewStatus,
  FinanceExceptionResponse,
  FinanceExceptionStatus,
  FinanceExportPackageResponse,
  FinancePeriodResponse,
  FiscalDocumentMode,
  MissingCostPolicy,
  MissingProductCostDiagnostic,
  ProductCostVersionResponse,
  VatMode,
} from "@/lib/types";

type TabKey = "overview" | "exceptions" | "ledgers" | "exports" | "settings" | "expenses" | "productCosts";

const TABS: TabKey[] = ["overview", "exceptions", "ledgers", "exports", "settings", "expenses", "productCosts"];

const LEDGERS: AccountingLedgerName[] = [
  "sales",
  "payments",
  "stripe_payouts",
  "cod_settlements",
  "expenses",
  "product_costs",
  "documents",
  "refunds",
  "courier_claims",
  "return_reasons",
  "inventory_adjustments",
  "inventory_movements",
];

const LEDGER_PAGE_SIZE = 50;

const LEDGER_DATE_BASIS_OPTIONS = [
  "",
  "order_date",
  "payment_date",
  "payout_date",
  "settlement_date",
  "purchase_date",
  "document_date",
  "effective_date",
  "issue_date",
] as const;

const SUMMARY_KEYS = [
  "gross_sales_cents",
  "net_sales_cents",
  "total_customer_payments_cents",
  "stripe_fees_cents",
  "cod_receivable_cents",
  "recorded_expenses_cents",
  "estimated_product_cost_cents",
  "estimated_gross_margin_cents",
  "material_on_hand_value_cents",
  "finished_goods_on_hand_value_cents",
  "inventory_cogs_cents",
  "inventory_writeoffs_cents",
  "inventory_exception_count",
  "review_required_item_count",
];

const STATUS_STYLES: Record<string, string> = {
  open: "bg-blue-100 text-blue-800",
  review: "bg-amber-100 text-amber-800",
  closed: "bg-slate-100 text-slate-700",
  exported: "bg-purple-100 text-purple-800",
  accepted: "bg-green-100 text-green-800",
  reopened: "bg-orange-100 text-orange-800",
  blocking: "bg-red-100 text-red-800",
  warning: "bg-amber-100 text-amber-800",
  resolved: "bg-green-100 text-green-800",
  waived: "bg-slate-100 text-slate-700",
  missing_document: "bg-red-100 text-red-800",
  reviewed: "bg-green-100 text-green-800",
  unreviewed: "bg-amber-100 text-amber-800",
  estimate: "bg-amber-100 text-amber-800",
  accountant_reviewed: "bg-green-100 text-green-800",
};

function todayDate(): string {
  return new Date().toISOString().slice(0, 10);
}

function monthStart(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
}

function formatDate(iso: string | null | undefined, locale: string): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleDateString(locale === "bg" ? "bg-BG" : "en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatMoneyCents(value: unknown): string {
  const cents = typeof value === "number" ? value : Number(value ?? 0);
  if (!Number.isFinite(cents)) return "-";
  const sign = cents < 0 ? "-" : "";
  return `${sign}EUR ${Math.abs(cents / 100).toFixed(2)}`;
}

function asCents(value: string): number {
  const parsed = Number.parseInt(value || "0", 10);
  return Number.isFinite(parsed) ? parsed : 0;
}

function splitCsv(value: string): string[] {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

function statusLabel(value: string): string {
  return value.replaceAll("_", " ");
}

function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) return error.message;
  return fallback;
}

function Pill({ value }: { value: string }) {
  return (
    <span className={cn("inline-flex rounded-pill px-2.5 py-0.5 text-xs font-medium capitalize", STATUS_STYLES[value] ?? "bg-champagne-beige/60 text-soft-brown")}>
      {statusLabel(value)}
    </span>
  );
}

function FieldValue({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase text-soft-brown">{label}</dt>
      <dd className="mt-1 text-sm text-charcoal">{value}</dd>
    </div>
  );
}

function GenericTable({ rows, emptyLabel }: { rows: Record<string, unknown>[]; emptyLabel: string }) {
  const columns = useMemo(() => {
    const first = rows[0];
    return first ? Object.keys(first).slice(0, 8) : [];
  }, [rows]);

  if (rows.length === 0) {
    return <div className="rounded-brand border border-champagne-beige bg-cream p-6 text-sm text-soft-brown">{emptyLabel}</div>;
  }

  return (
    <div className="overflow-x-auto rounded-brand border border-champagne-beige bg-cream">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-champagne-beige bg-champagne-beige/30">
            {columns.map((column) => (
              <th key={column} className="px-4 py-3 font-medium text-charcoal">
                {statusLabel(column)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index} className="border-b border-champagne-beige/50 last:border-0">
              {columns.map((column) => {
                const value = row[column];
                const text = column.includes("cents") ? formatMoneyCents(value) : String(value ?? "-");
                return <td key={column} className="max-w-[18rem] truncate px-4 py-3 text-soft-brown" title={text}>{text}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function AdminAccountingPage() {
  const t = useTranslations("admin.accounting");
  const common = useTranslations("common");
  const locale = useLocale();
  const [activeTab, setActiveTab] = useState<TabKey>("overview");
  const [activeLedger, setActiveLedger] = useState<AccountingLedgerName>("sales");
  const [ledgerDateBasis, setLedgerDateBasis] = useState("");
  const [ledgerPage, setLedgerPage] = useState(1);
  const [periods, setPeriods] = useState<FinancePeriodResponse[]>([]);
  const [selectedPeriodId, setSelectedPeriodId] = useState<string>("");
  const [config, setConfig] = useState<AccountingConfigurationResponse | null>(null);
  const [exceptions, setExceptions] = useState<FinanceExceptionResponse[]>([]);
  const [ledger, setLedger] = useState<AccountingLedgerResponse | null>(null);
  const [exportsList, setExportsList] = useState<FinanceExportPackageResponse[]>([]);
  const [documents, setDocuments] = useState<AccountingDocumentResponse[]>([]);
  const [expenses, setExpenses] = useState<ExpenseEvidenceResponse[]>([]);
  const [productCosts, setProductCosts] = useState<ProductCostVersionResponse[]>([]);
  const [missingCosts, setMissingCosts] = useState<MissingProductCostDiagnostic[]>([]);
  const [stripeStatus, setStripeStatus] = useState<{ matched: number; unmatched: number; mismatched: number; total_rows: number } | null>(null);
  const [exceptionFilter, setExceptionFilter] = useState<FinanceExceptionStatus | "">("open");
  const [expenseCategoryFilter, setExpenseCategoryFilter] = useState("");
  const [expenseReviewFilter, setExpenseReviewFilter] = useState<ExpenseReviewStatus | "">("");
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [accountantName, setAccountantName] = useState("");
  const [accountantReference, setAccountantReference] = useState("");
  const [acceptanceNote, setAcceptanceNote] = useState("");
  const [exceptionReasons, setExceptionReasons] = useState<Record<string, string>>({});
  const [periodForm, setPeriodForm] = useState({ period_start: monthStart(), period_end: todayDate(), currency: "EUR" });
  const [sellerForm, setSellerForm] = useState({ company_display_name: "", legal_name: "", default_currency: "EUR", reviewed: false });
  const [vatForm, setVatForm] = useState<{ vat_mode: VatMode; fiscal_document_mode: FiscalDocumentMode; tolerance_cents: string; reviewed: boolean }>({
    vat_mode: "unknown",
    fiscal_document_mode: "external_reference",
    tolerance_cents: "1",
    reviewed: false,
  });
  const [categoryForm, setCategoryForm] = useState({ mapping_key: "materials", category_code: "", category_label: "Materials", reviewed: false });
  const [exportSchemaForm, setExportSchemaForm] = useState({ workbook_language: "en", included_tabs: "summary,sales,payments,expenses,exceptions", reviewed: false });
  const [expenseSettingsForm, setExpenseSettingsForm] = useState({ required_document_categories: "materials,packaging", close_behavior: "block", reviewed: false });
  const [productCostSettingsForm, setProductCostSettingsForm] = useState<{ enabled: boolean; costing_basis: "manual_snapshot" | "recipe_bom" | "imported_estimate"; missing_cost_policy: MissingCostPolicy; reviewed: boolean }>({
    enabled: true,
    costing_basis: "recipe_bom",
    missing_cost_policy: "warning",
    reviewed: false,
  });
  const [expenseForm, setExpenseForm] = useState({
    supplier_name: "",
    document_number: "",
    purchase_date: todayDate(),
    gross_amount_cents: "0",
    tax_amount_cents: "0",
    category_key: "materials",
    attachment_reference: "",
    payment_status: "unpaid" as ExpensePaymentStatus,
    review_status: "unreviewed" as ExpenseReviewStatus,
  });
  const [productCostForm, setProductCostForm] = useState({
    product_id: "",
    product_name: "",
    effective_date: todayDate(),
    material_cost_cents: "0",
    packaging_cost_cents: "0",
    labor_cost_cents: "0",
    overhead_cost_cents: "0",
    reviewed: false,
    accountant_reviewed: false,
  });

  const selectedPeriod = periods.find((period) => period.id === selectedPeriodId) ?? periods[0] ?? null;
  const currentExport = exportsList.find((item) => item.current_final) ?? exportsList[0] ?? null;
  const ledgerTotalPages = Math.max(1, Math.ceil((ledger?.total ?? 0) / (ledger?.limit ?? LEDGER_PAGE_SIZE)));
  const currentLedgerPage = ledger?.page ?? ledgerPage;

  const loadPeriodData = useCallback(async (periodId: string, options: { soft?: boolean } = {}) => {
    if (!periodId) return;
    if (options.soft) setIsRefreshing(true);
    try {
      const [exceptionData, ledgerData, exportData, documentData, expenseData, costData, missingData] = await Promise.all([
        listFinanceExceptions(periodId, exceptionFilter),
        getAccountingLedger(periodId, activeLedger, { dateBasis: ledgerDateBasis || undefined, page: ledgerPage, limit: LEDGER_PAGE_SIZE }),
        listAccountingExports(periodId),
        listAccountingDocuments({ periodId }),
        listExpenseEvidence({ categoryKey: expenseCategoryFilter || undefined, reviewStatus: expenseReviewFilter || undefined }),
        listProductCosts(),
        getMissingProductCosts(periodId),
      ]);
      setExceptions(exceptionData.items);
      setLedger(ledgerData);
      setExportsList(exportData.items);
      setDocuments(documentData.items);
      setExpenses(expenseData.items);
      setProductCosts(costData.items);
      setMissingCosts(missingData.items);
    } catch (error) {
      setActionError(errorMessage(error, t("loadError")));
    } finally {
      setIsRefreshing(false);
    }
  }, [activeLedger, exceptionFilter, expenseCategoryFilter, expenseReviewFilter, ledgerDateBasis, ledgerPage, t]);

  const loadWorkspace = useCallback(async (preferredPeriodId?: string) => {
    setIsLoading(true);
    setActionError(null);
    try {
      const [configData, periodData, stripeData] = await Promise.all([
        getAccountingConfig(),
        listFinancePeriods(),
        getStripePayoutImportStatus(),
      ]);
      setConfig(configData);
      setPeriods(periodData.items);
      setStripeStatus(stripeData);
      const nextPeriodId = preferredPeriodId || selectedPeriodId || periodData.items[0]?.id || "";
      setSelectedPeriodId(nextPeriodId);
      if (configData.seller_profile) {
        setSellerForm({
          company_display_name: configData.seller_profile.company_display_name ?? "",
          legal_name: configData.seller_profile.legal_name ?? "",
          default_currency: configData.seller_profile.default_currency,
          reviewed: configData.seller_profile.reviewed,
        });
      }
      if (configData.vat_fiscal_settings) {
        setVatForm({
          vat_mode: configData.vat_fiscal_settings.vat_mode,
          fiscal_document_mode: configData.vat_fiscal_settings.fiscal_document_mode,
          tolerance_cents: String(configData.vat_fiscal_settings.tolerance_cents),
          reviewed: configData.vat_fiscal_settings.reviewed,
        });
      }
      setExportSchemaForm({
        workbook_language: configData.export_schema.workbook_language,
        included_tabs: configData.export_schema.included_tabs.join(","),
        reviewed: configData.export_schema.reviewed,
      });
      setExpenseSettingsForm({
        required_document_categories: configData.expense_settings.required_document_categories.join(","),
        close_behavior: configData.expense_settings.close_behavior,
        reviewed: configData.expense_settings.reviewed,
      });
      setProductCostSettingsForm({
        enabled: configData.product_cost_settings.enabled,
        costing_basis: configData.product_cost_settings.costing_basis,
        missing_cost_policy: configData.product_cost_settings.missing_cost_policy,
        reviewed: configData.product_cost_settings.reviewed,
      });
      if (nextPeriodId) await loadPeriodData(nextPeriodId);
    } catch (error) {
      setActionError(errorMessage(error, t("loadError")));
    } finally {
      setIsLoading(false);
    }
  }, [loadPeriodData, selectedPeriodId, t]);

  useEffect(() => {
    loadWorkspace();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!selectedPeriodId || isLoading) return;
    loadPeriodData(selectedPeriodId, { soft: true });
  }, [selectedPeriodId, activeLedger, exceptionFilter, expenseCategoryFilter, expenseReviewFilter, ledgerDateBasis, ledgerPage]); // eslint-disable-line react-hooks/exhaustive-deps

  async function runAction(label: string, action: () => Promise<unknown>, reloadPeriodId = selectedPeriodId) {
    setBusyAction(label);
    setActionError(null);
    setSuccess(null);
    try {
      await action();
      setSuccess(t("saved"));
      await loadWorkspace(reloadPeriodId);
    } catch (error) {
      setActionError(errorMessage(error, t("saveError")));
    } finally {
      setBusyAction(null);
    }
  }

  function requireReason(): boolean {
    if (!reason.trim()) {
      setActionError(t("reasonRequired"));
      return false;
    }
    return true;
  }

  function requireExceptionReason(exceptionId: string): boolean {
    if (!(exceptionReasons[exceptionId] ?? "").trim()) {
      setActionError(t("reasonRequired"));
      return false;
    }
    return true;
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-72" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-72 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex items-center gap-2">
          <h1 className="font-heading text-2xl font-semibold text-charcoal">{t("title")}</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <select
            value={selectedPeriodId}
            onChange={(event) => { setSelectedPeriodId(event.target.value); setLedgerPage(1); }}
            className="h-10 rounded-brand border border-champagne-beige bg-cream px-3 text-sm text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown"
            aria-label={t("selectPeriod")}
          >
            {periods.length === 0 && <option value="">{t("empty.periods")}</option>}
            {periods.map((period) => (
              <option key={period.id} value={period.id}>
                {period.period_start} - {period.period_end} ({period.status})
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => runAction("stripe", () => syncStripeBalanceTransactions())}
            disabled={busyAction !== null}
            className="rounded-brand border border-champagne-beige bg-cream px-3 py-2 text-sm font-medium text-charcoal hover:bg-champagne-beige/50 disabled:opacity-50"
          >
            {t("syncStripe")}
          </button>
        </div>
      </div>

      {actionError && <div className="rounded-brand border border-red-200 bg-red-50 p-4 text-sm text-red-700">{actionError}</div>}
      {success && <div className="rounded-brand border border-green-200 bg-green-50 p-4 text-sm text-green-700">{success}</div>}

      <section className="rounded-brand border border-champagne-beige bg-cream p-4">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-sm font-semibold text-charcoal">{t("period")}</span>
            {selectedPeriod ? (
              <>
                <span className="text-sm text-soft-brown">{selectedPeriod.period_start} - {selectedPeriod.period_end}</span>
                <Pill value={selectedPeriod.status} />
                <span className="text-sm text-soft-brown">{t("exceptions")}: {selectedPeriod.open_exception_count}</span>
                <span className="text-sm text-soft-brown">{t("blocking")}: {selectedPeriod.blocking_exception_count}</span>
                <span className="text-sm text-soft-brown">{t("exportStatus")}: {currentExport ? `v${currentExport.version}` : t("none")}</span>
              </>
            ) : (
              <span className="text-sm text-soft-brown">{t("empty.periods")}</span>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" disabled={!selectedPeriod || busyAction !== null} onClick={() => selectedPeriod && runAction("review", () => reviewFinancePeriod(selectedPeriod.id))} className="rounded-brand bg-muted-gold px-3 py-2 text-sm font-medium text-charcoal disabled:opacity-50">{t("review")}</button>
            <button type="button" disabled={!selectedPeriod || busyAction !== null} onClick={() => selectedPeriod && runAction("close", () => closeFinancePeriod(selectedPeriod.id))} className="rounded-brand bg-charcoal px-3 py-2 text-sm font-medium text-cream disabled:opacity-50">{t("close")}</button>
            <button type="button" disabled={!selectedPeriod || busyAction !== null} onClick={() => selectedPeriod && requireReason() && runAction("reopen", () => reopenFinancePeriod(selectedPeriod.id, { reason }))} className="rounded-brand border border-champagne-beige px-3 py-2 text-sm font-medium text-charcoal disabled:opacity-50">{t("reopen")}</button>
            <button type="button" disabled={!selectedPeriod || busyAction !== null} onClick={() => selectedPeriod && runAction("accept-period", () => acceptFinancePeriod(selectedPeriod.id, { reason, accountant_name: accountantName, accountant_reference: accountantReference }))} className="rounded-brand border border-champagne-beige px-3 py-2 text-sm font-medium text-charcoal disabled:opacity-50">{t("accept")}</button>
          </div>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <label className="text-sm text-soft-brown">
            {t("reason")}
            <input value={reason} onChange={(event) => setReason(event.target.value)} className="mt-1 h-10 w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-charcoal" />
          </label>
          <label className="text-sm text-soft-brown">
            {t("accountantName")}
            <input value={accountantName} onChange={(event) => setAccountantName(event.target.value)} className="mt-1 h-10 w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-charcoal" />
          </label>
          <label className="text-sm text-soft-brown">
            {t("accountantReference")}
            <input value={accountantReference} onChange={(event) => setAccountantReference(event.target.value)} className="mt-1 h-10 w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-charcoal" />
          </label>
        </div>
      </section>

      <div className="flex flex-wrap gap-2">
        {TABS.map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setActiveTab(tab)}
            className={cn("rounded-pill px-4 py-2 text-sm font-medium transition-colors", activeTab === tab ? "bg-muted-gold text-charcoal" : "bg-champagne-beige/50 text-soft-brown hover:bg-champagne-beige")}
          >
            {t(`tabs.${tab}`)}
          </button>
        ))}
      </div>

      {isRefreshing && <div className="h-1 rounded-full bg-muted-gold/40" />}

      {activeTab === "overview" && selectedPeriod && (
        <div className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {SUMMARY_KEYS.map((key) => {
              const value = selectedPeriod.summary_totals?.[key];
              return (
                <div key={key} className="rounded-brand border border-champagne-beige bg-cream p-4">
                  <p className="text-xs font-semibold uppercase text-soft-brown">{t(`summary.${key}`)}</p>
                  <p className="mt-2 text-xl font-semibold text-charcoal">{key.includes("cents") ? formatMoneyCents(value) : String(value ?? 0)}</p>
                </div>
              );
            })}
          </div>
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="rounded-brand border border-champagne-beige bg-cream p-4">
              <h2 className="font-heading text-lg font-semibold text-charcoal">Stripe</h2>
              <dl className="mt-4 grid grid-cols-2 gap-3">
                <FieldValue label="Rows" value={stripeStatus?.total_rows ?? 0} />
                <FieldValue label="Matched" value={stripeStatus?.matched ?? 0} />
                <FieldValue label="Unmatched" value={stripeStatus?.unmatched ?? 0} />
                <FieldValue label="Mismatched" value={stripeStatus?.mismatched ?? 0} />
              </dl>
            </div>
            <div className="rounded-brand border border-champagne-beige bg-cream p-4 lg:col-span-2">
              <h2 className="font-heading text-lg font-semibold text-charcoal">{t("createPeriod")}</h2>
              <div className="mt-4 grid gap-3 md:grid-cols-4">
                <input type="date" value={periodForm.period_start} onChange={(event) => setPeriodForm((prev) => ({ ...prev, period_start: event.target.value }))} className="h-10 rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm" aria-label={t("startDate")} />
                <input type="date" value={periodForm.period_end} onChange={(event) => setPeriodForm((prev) => ({ ...prev, period_end: event.target.value }))} className="h-10 rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm" aria-label={t("endDate")} />
                <input value={periodForm.currency} onChange={(event) => setPeriodForm((prev) => ({ ...prev, currency: event.target.value.toUpperCase() }))} className="h-10 rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm" aria-label={t("currency")} />
                <button type="button" onClick={() => runAction("create-period", () => createFinancePeriod(periodForm))} className="rounded-brand bg-muted-gold px-3 py-2 text-sm font-medium text-charcoal">{t("create")}</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === "exceptions" && (
        <div className="space-y-4">
          <select value={exceptionFilter} onChange={(event) => setExceptionFilter(event.target.value as FinanceExceptionStatus | "")} className="h-10 rounded-brand border border-champagne-beige bg-cream px-3 text-sm text-charcoal">
            <option value="open">Open</option>
            <option value="resolved">Resolved</option>
            <option value="waived">Waived</option>
            <option value="">{common("all")}</option>
          </select>
          <div className="overflow-x-auto rounded-brand border border-champagne-beige bg-cream">
            <table className="w-full text-left text-sm">
              <thead><tr className="border-b border-champagne-beige bg-champagne-beige/30"><th className="px-4 py-3">Type</th><th className="px-4 py-3">Context</th><th className="px-4 py-3">Message</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">{t("reason")}</th><th className="px-4 py-3">{t("actions")}</th></tr></thead>
              <tbody>
                {exceptions.length === 0 ? (
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-soft-brown">{t("empty.exceptions")}</td></tr>
                ) : exceptions.map((exception) => (
                  <tr key={exception.id} className="border-b border-champagne-beige/50 last:border-0">
                    <td className="px-4 py-3"><Pill value={exception.severity} /><div className="mt-1 text-xs text-soft-brown">{statusLabel(exception.exception_type)}</div></td>
                    <td className="px-4 py-3 text-soft-brown">
                      {exception.target_type === "order" && exception.target_id ? <Link href={`/admin/orders/${exception.target_id}`} className="text-charcoal underline-offset-2 hover:underline">{exception.target_type}: {exception.target_id.slice(0, 8)}</Link> : `${exception.target_type ?? "-"}: ${exception.target_id ?? "-"}`}
                    </td>
                    <td className="max-w-[24rem] px-4 py-3 text-soft-brown">{exception.message}</td>
                    <td className="px-4 py-3"><Pill value={exception.status} /></td>
                    <td className="px-4 py-3"><input aria-label={`${t("reason")} ${exception.id}`} value={exceptionReasons[exception.id] ?? ""} onChange={(event) => setExceptionReasons((prev) => ({ ...prev, [exception.id]: event.target.value }))} className="h-9 w-44 rounded-brand border border-champagne-beige bg-warm-ivory px-2 text-sm" /></td>
                    <td className="px-4 py-3"><div className="flex gap-2"><button type="button" onClick={() => requireExceptionReason(exception.id) && runAction(`resolve-${exception.id}`, () => resolveFinanceException(exception.id, { reason: exceptionReasons[exception.id] ?? "" }))} className="rounded-brand bg-muted-gold px-3 py-1.5 text-xs font-medium text-charcoal">{t("resolve")}</button><button type="button" onClick={() => requireExceptionReason(exception.id) && runAction(`waive-${exception.id}`, () => waiveFinanceException(exception.id, { reason: exceptionReasons[exception.id] ?? "" }))} className="rounded-brand border border-champagne-beige px-3 py-1.5 text-xs font-medium text-charcoal">{t("waive")}</button></div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === "ledgers" && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {LEDGERS.map((item) => (
              <button key={item} type="button" onClick={() => { setActiveLedger(item); setLedgerPage(1); }} className={cn("rounded-pill px-3 py-1.5 text-sm font-medium", activeLedger === item ? "bg-muted-gold text-charcoal" : "bg-champagne-beige/50 text-soft-brown")}>{t(`ledgers.${item}`)}</button>
            ))}
          </div>
          <div className="flex flex-wrap items-end gap-3 rounded-brand border border-champagne-beige bg-cream p-3">
            <label className="text-xs font-semibold uppercase text-soft-brown">
              {t("dateBasis")}
              <select
                value={ledgerDateBasis}
                onChange={(event) => { setLedgerDateBasis(event.target.value); setLedgerPage(1); }}
                className="mt-1 h-10 rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm font-normal normal-case text-charcoal"
                aria-label={t("dateBasis")}
              >
                {LEDGER_DATE_BASIS_OPTIONS.map((basis) => (
                  <option key={basis || "default"} value={basis}>{t(`dateBases.${basis || "default"}`)}</option>
                ))}
              </select>
            </label>
            <div className="flex items-center gap-2 text-sm text-soft-brown">
              <button type="button" disabled={currentLedgerPage <= 1 || isRefreshing} onClick={() => setLedgerPage((page) => Math.max(1, page - 1))} className="rounded-brand border border-champagne-beige px-3 py-2 font-medium text-charcoal disabled:opacity-50">{common("previous")}</button>
              <span>{common("page", { current: currentLedgerPage, total: ledgerTotalPages })}</span>
              <button type="button" disabled={currentLedgerPage >= ledgerTotalPages || isRefreshing} onClick={() => setLedgerPage((page) => page + 1)} className="rounded-brand border border-champagne-beige px-3 py-2 font-medium text-charcoal disabled:opacity-50">{common("next")}</button>
            </div>
          </div>
          <GenericTable rows={ledger?.rows ?? []} emptyLabel={t("empty.ledger")} />
        </div>
      )}

      {activeTab === "exports" && selectedPeriod && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={() => runAction("generate-export", () => generateAccountingExport(selectedPeriod.id))} className="rounded-brand bg-muted-gold px-3 py-2 text-sm font-medium text-charcoal">{t("generateExport")}</button>
            {currentExport && <button type="button" onClick={() => runAction("accept-export", () => acceptAccountingExport(currentExport.id, { accountant_name: accountantName, accountant_reference: accountantReference, note: acceptanceNote }))} className="rounded-brand border border-champagne-beige px-3 py-2 text-sm font-medium text-charcoal">{t("acceptExport")}</button>}
          </div>
          <textarea value={acceptanceNote} onChange={(event) => setAcceptanceNote(event.target.value)} className="min-h-20 w-full rounded-brand border border-champagne-beige bg-cream p-3 text-sm text-charcoal" placeholder={t("acceptanceNote")} />
          <div className="overflow-x-auto rounded-brand border border-champagne-beige bg-cream">
            <table className="w-full text-left text-sm"><thead><tr className="border-b border-champagne-beige bg-champagne-beige/30"><th className="px-4 py-3">Version</th><th className="px-4 py-3">Generated</th><th className="px-4 py-3">Manifest</th><th className="px-4 py-3">Accepted</th><th className="px-4 py-3">{t("actions")}</th></tr></thead><tbody>{exportsList.length === 0 ? <tr><td colSpan={5} className="px-4 py-8 text-center text-soft-brown">{t("empty.exports")}</td></tr> : exportsList.map((item) => <tr key={item.id} className="border-b border-champagne-beige/50 last:border-0"><td className="px-4 py-3 text-charcoal">v{item.version}{item.current_final ? " current" : ""}</td><td className="px-4 py-3 text-soft-brown">{formatDate(item.generated_at, locale)}</td><td className="px-4 py-3 text-soft-brown">{Object.entries((item.manifest?.row_counts ?? {}) as Record<string, unknown>).map(([key, value]) => `${key}: ${value}`).join(", ") || "-"}</td><td className="px-4 py-3 text-soft-brown">{item.accepted_at ? formatDate(item.accepted_at, locale) : "-"}</td><td className="px-4 py-3"><div className="flex gap-2"><a href={getAccountingExportDownloadUrl(item.id, "xlsx")} className="rounded-brand bg-muted-gold px-3 py-1.5 text-xs font-medium text-charcoal">{t("downloadXlsx")}</a><a href={getAccountingExportDownloadUrl(item.id, "manifest")} className="rounded-brand border border-champagne-beige px-3 py-1.5 text-xs font-medium text-charcoal">{t("downloadManifest")}</a></div></td></tr>)}</tbody></table>
          </div>
        </div>
      )}

      {activeTab === "settings" && config && (
        <div className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-2">
            <section className="rounded-brand border border-champagne-beige bg-cream p-4"><h2 className="font-heading text-lg font-semibold text-charcoal">{t("settings.seller")}</h2><p className="mt-1 text-xs text-soft-brown">{t("settings.bankRedacted")}</p><div className="mt-4 grid gap-3 md:grid-cols-2"><input value={sellerForm.company_display_name} onChange={(event) => setSellerForm((prev) => ({ ...prev, company_display_name: event.target.value }))} className="h-10 rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm" placeholder="Atelier Marie" /><input value={sellerForm.legal_name} onChange={(event) => setSellerForm((prev) => ({ ...prev, legal_name: event.target.value }))} className="h-10 rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm" placeholder="Legal name" /><label className="flex items-center gap-2 text-sm text-soft-brown"><input type="checkbox" checked={sellerForm.reviewed} onChange={(event) => setSellerForm((prev) => ({ ...prev, reviewed: event.target.checked }))} /> {t("settings.reviewed")}</label><button type="button" onClick={() => runAction("seller", () => createSellerLegalProfile({ ...sellerForm, effective_date: todayDate(), bank_details: null }))} className="rounded-brand bg-muted-gold px-3 py-2 text-sm font-medium text-charcoal">{common("save")}</button></div></section>
            <section className="rounded-brand border border-champagne-beige bg-cream p-4"><h2 className="font-heading text-lg font-semibold text-charcoal">{t("settings.vatFiscal")}</h2><p className="mt-1 text-xs text-soft-brown">{t("settings.vatWarning")}</p><div className="mt-4 grid gap-3 md:grid-cols-2"><select value={vatForm.vat_mode} onChange={(event) => setVatForm((prev) => ({ ...prev, vat_mode: event.target.value as VatMode }))} className="h-10 rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm"><option value="unknown">unknown</option><option value="not_registered">not registered</option><option value="registered">registered</option><option value="oss_registered">OSS registered</option></select><select value={vatForm.fiscal_document_mode} onChange={(event) => setVatForm((prev) => ({ ...prev, fiscal_document_mode: event.target.value as FiscalDocumentMode }))} className="h-10 rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm"><option value="external_reference">external reference</option><option value="app_invoice_reference">app invoice reference</option><option value="fiscal_device_reference">fiscal device reference</option><option value="alternative_sales_document">alternative sales document</option><option value="not_configured">not configured</option></select><input value={vatForm.tolerance_cents} onChange={(event) => setVatForm((prev) => ({ ...prev, tolerance_cents: event.target.value }))} className="h-10 rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm" /><label className="flex items-center gap-2 text-sm text-soft-brown"><input type="checkbox" checked={vatForm.reviewed} onChange={(event) => setVatForm((prev) => ({ ...prev, reviewed: event.target.checked }))} /> {t("settings.reviewed")}</label><button type="button" onClick={() => runAction("vat", () => createVatFiscalSettings({ ...vatForm, effective_date: todayDate(), tolerance_cents: asCents(vatForm.tolerance_cents) }))} className="rounded-brand bg-muted-gold px-3 py-2 text-sm font-medium text-charcoal">{common("save")}</button></div></section>
          </div>
          <div className="grid gap-4 lg:grid-cols-3">
            <section className="rounded-brand border border-champagne-beige bg-cream p-4"><h2 className="font-heading text-lg font-semibold text-charcoal">{t("settings.categories")}</h2><div className="mt-4 space-y-3"><input value={categoryForm.mapping_key} onChange={(event) => setCategoryForm((prev) => ({ ...prev, mapping_key: event.target.value }))} className="h-10 w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm" /><input value={categoryForm.category_label} onChange={(event) => setCategoryForm((prev) => ({ ...prev, category_label: event.target.value }))} className="h-10 w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm" /><input value={categoryForm.category_code} onChange={(event) => setCategoryForm((prev) => ({ ...prev, category_code: event.target.value }))} className="h-10 w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm" /><label className="flex items-center gap-2 text-sm text-soft-brown"><input type="checkbox" checked={categoryForm.reviewed} onChange={(event) => setCategoryForm((prev) => ({ ...prev, reviewed: event.target.checked }))} /> {t("settings.reviewed")}</label><button type="button" onClick={() => runAction("category", () => upsertAccountingCategoryMapping(categoryForm.mapping_key, categoryForm))} className="rounded-brand bg-muted-gold px-3 py-2 text-sm font-medium text-charcoal">{common("save")}</button></div></section>
            <section className="rounded-brand border border-champagne-beige bg-cream p-4"><h2 className="font-heading text-lg font-semibold text-charcoal">{t("settings.exportSchema")}</h2><div className="mt-4 space-y-3"><select value={exportSchemaForm.workbook_language} onChange={(event) => setExportSchemaForm((prev) => ({ ...prev, workbook_language: event.target.value }))} className="h-10 w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm"><option value="en">English</option><option value="bg">Bulgarian</option></select><input value={exportSchemaForm.included_tabs} onChange={(event) => setExportSchemaForm((prev) => ({ ...prev, included_tabs: event.target.value }))} className="h-10 w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm" /><label className="flex items-center gap-2 text-sm text-soft-brown"><input type="checkbox" checked={exportSchemaForm.reviewed} onChange={(event) => setExportSchemaForm((prev) => ({ ...prev, reviewed: event.target.checked }))} /> {t("settings.reviewed")}</label><button type="button" onClick={() => runAction("export-schema", () => updateAccountingExportSchema({ workbook_language: exportSchemaForm.workbook_language as "en" | "bg", included_tabs: splitCsv(exportSchemaForm.included_tabs), reviewed: exportSchemaForm.reviewed }))} className="rounded-brand bg-muted-gold px-3 py-2 text-sm font-medium text-charcoal">{common("save")}</button></div></section>
            <section className="rounded-brand border border-champagne-beige bg-cream p-4"><h2 className="font-heading text-lg font-semibold text-charcoal">{t("settings.expenseSettings")}</h2><div className="mt-4 space-y-3"><input value={expenseSettingsForm.required_document_categories} onChange={(event) => setExpenseSettingsForm((prev) => ({ ...prev, required_document_categories: event.target.value }))} className="h-10 w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm" /><select value={expenseSettingsForm.close_behavior} onChange={(event) => setExpenseSettingsForm((prev) => ({ ...prev, close_behavior: event.target.value }))} className="h-10 w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm"><option value="warn">warn</option><option value="block">block</option></select><label className="flex items-center gap-2 text-sm text-soft-brown"><input type="checkbox" checked={expenseSettingsForm.reviewed} onChange={(event) => setExpenseSettingsForm((prev) => ({ ...prev, reviewed: event.target.checked }))} /> {t("settings.reviewed")}</label><button type="button" onClick={() => runAction("expense-settings", () => updateExpenseEvidenceSettings({ required_document_categories: splitCsv(expenseSettingsForm.required_document_categories), close_behavior: expenseSettingsForm.close_behavior as "warn" | "block", reviewed: expenseSettingsForm.reviewed }))} className="rounded-brand bg-muted-gold px-3 py-2 text-sm font-medium text-charcoal">{common("save")}</button></div></section>
          </div>
          <section className="rounded-brand border border-champagne-beige bg-cream p-4"><h2 className="font-heading text-lg font-semibold text-charcoal">{t("settings.productCostSettings")}</h2><p className="mt-1 text-xs text-soft-brown">{t("settings.costingScope")}</p><div className="mt-4 grid gap-3 md:grid-cols-5"><label className="flex items-center gap-2 text-sm text-soft-brown"><input type="checkbox" checked={productCostSettingsForm.enabled} onChange={(event) => setProductCostSettingsForm((prev) => ({ ...prev, enabled: event.target.checked }))} /> enabled</label><select value={productCostSettingsForm.costing_basis} onChange={(event) => setProductCostSettingsForm((prev) => ({ ...prev, costing_basis: event.target.value as "manual_snapshot" | "recipe_bom" | "imported_estimate" }))} className="h-10 rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm"><option value="manual_snapshot">manual snapshot</option><option value="recipe_bom">recipe/BOM</option><option value="imported_estimate">imported estimate</option></select><select value={productCostSettingsForm.missing_cost_policy} onChange={(event) => setProductCostSettingsForm((prev) => ({ ...prev, missing_cost_policy: event.target.value as MissingCostPolicy }))} className="h-10 rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm"><option value="none">none</option><option value="warning">warning</option><option value="blocking">blocking</option></select><label className="flex items-center gap-2 text-sm text-soft-brown"><input type="checkbox" checked={productCostSettingsForm.reviewed} onChange={(event) => setProductCostSettingsForm((prev) => ({ ...prev, reviewed: event.target.checked }))} /> {t("settings.reviewed")}</label><button type="button" onClick={() => runAction("product-cost-settings", () => updateProductCostSettings(productCostSettingsForm))} className="rounded-brand bg-muted-gold px-3 py-2 text-sm font-medium text-charcoal">{common("save")}</button></div></section>
        </div>
      )}

      {activeTab === "expenses" && (
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-4"><input value={expenseCategoryFilter} onChange={(event) => setExpenseCategoryFilter(event.target.value)} className="h-10 rounded-brand border border-champagne-beige bg-cream px-3 text-sm" placeholder={t("forms.category")} /><select value={expenseReviewFilter} onChange={(event) => setExpenseReviewFilter(event.target.value as ExpenseReviewStatus | "")} className="h-10 rounded-brand border border-champagne-beige bg-cream px-3 text-sm"><option value="">{common("all")}</option><option value="unreviewed">unreviewed</option><option value="reviewed">reviewed</option><option value="missing_document">missing document</option><option value="waived">waived</option></select></div>
          <section className="rounded-brand border border-champagne-beige bg-cream p-4"><h2 className="font-heading text-lg font-semibold text-charcoal">{t("forms.addExpense")}</h2><div className="mt-4 grid gap-3 md:grid-cols-4"><input value={expenseForm.supplier_name} onChange={(event) => setExpenseForm((prev) => ({ ...prev, supplier_name: event.target.value }))} className="h-10 rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm" placeholder={t("forms.supplierName")} /><input value={expenseForm.document_number} onChange={(event) => setExpenseForm((prev) => ({ ...prev, document_number: event.target.value }))} className="h-10 rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm" placeholder={t("forms.documentNumber")} /><input type="date" value={expenseForm.purchase_date} onChange={(event) => setExpenseForm((prev) => ({ ...prev, purchase_date: event.target.value }))} className="h-10 rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm" /><input value={expenseForm.category_key} onChange={(event) => setExpenseForm((prev) => ({ ...prev, category_key: event.target.value }))} className="h-10 rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm" placeholder={t("forms.category")} /><input value={expenseForm.gross_amount_cents} onChange={(event) => setExpenseForm((prev) => ({ ...prev, gross_amount_cents: event.target.value }))} className="h-10 rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm" placeholder={t("forms.grossCents")} /><input value={expenseForm.tax_amount_cents} onChange={(event) => setExpenseForm((prev) => ({ ...prev, tax_amount_cents: event.target.value }))} className="h-10 rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm" placeholder={t("forms.taxCents")} /><input value={expenseForm.attachment_reference} onChange={(event) => setExpenseForm((prev) => ({ ...prev, attachment_reference: event.target.value }))} className="h-10 rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm" placeholder={t("forms.attachmentReference")} /><select value={expenseForm.payment_status} onChange={(event) => setExpenseForm((prev) => ({ ...prev, payment_status: event.target.value as ExpensePaymentStatus }))} className="h-10 rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm"><option value="unpaid">unpaid</option><option value="paid">paid</option><option value="partially_paid">partially paid</option><option value="reimbursed">reimbursed</option></select><button type="button" onClick={() => runAction("add-expense", () => createExpenseEvidence({ supplier_name: expenseForm.supplier_name, document_number: expenseForm.document_number || null, purchase_date: expenseForm.purchase_date, payment_status: expenseForm.payment_status, category_key: expenseForm.category_key || null, gross_amount_cents: asCents(expenseForm.gross_amount_cents), tax_amount_cents: asCents(expenseForm.tax_amount_cents), attachment_reference: expenseForm.attachment_reference || null, review_status: expenseForm.review_status }))} className="rounded-brand bg-muted-gold px-3 py-2 text-sm font-medium text-charcoal">{t("forms.addExpense")}</button></div></section>
          <GenericTable rows={expenses as unknown as Record<string, unknown>[]} emptyLabel={t("empty.expenses")} />
        </div>
      )}

      {activeTab === "productCosts" && (
        <div className="space-y-4">
          <section className="rounded-brand border border-champagne-beige bg-cream p-4"><h2 className="font-heading text-lg font-semibold text-charcoal">{t("forms.addProductCost")}</h2><div className="mt-4 grid gap-3 md:grid-cols-4"><input value={productCostForm.product_name} onChange={(event) => setProductCostForm((prev) => ({ ...prev, product_name: event.target.value }))} className="h-10 rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm" placeholder={t("forms.productName")} /><input value={productCostForm.product_id} onChange={(event) => setProductCostForm((prev) => ({ ...prev, product_id: event.target.value }))} className="h-10 rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm" placeholder={t("forms.productId")} /><input type="date" value={productCostForm.effective_date} onChange={(event) => setProductCostForm((prev) => ({ ...prev, effective_date: event.target.value }))} className="h-10 rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm" /><input value={productCostForm.material_cost_cents} onChange={(event) => setProductCostForm((prev) => ({ ...prev, material_cost_cents: event.target.value }))} className="h-10 rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm" placeholder={t("forms.materialCents")} /><input value={productCostForm.packaging_cost_cents} onChange={(event) => setProductCostForm((prev) => ({ ...prev, packaging_cost_cents: event.target.value }))} className="h-10 rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm" placeholder={t("forms.packagingCents")} /><input value={productCostForm.labor_cost_cents} onChange={(event) => setProductCostForm((prev) => ({ ...prev, labor_cost_cents: event.target.value }))} className="h-10 rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm" placeholder={t("forms.laborCents")} /><input value={productCostForm.overhead_cost_cents} onChange={(event) => setProductCostForm((prev) => ({ ...prev, overhead_cost_cents: event.target.value }))} className="h-10 rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm" placeholder={t("forms.overheadCents")} /><label className="flex items-center gap-2 text-sm text-soft-brown"><input type="checkbox" checked={productCostForm.reviewed} onChange={(event) => setProductCostForm((prev) => ({ ...prev, reviewed: event.target.checked }))} /> {t("settings.reviewed")}</label><button type="button" onClick={() => runAction("add-cost", () => createProductCost({ product_id: productCostForm.product_id || null, product_name: productCostForm.product_name, effective_date: productCostForm.effective_date, costing_basis: productCostSettingsForm.costing_basis, material_cost_cents: asCents(productCostForm.material_cost_cents), packaging_cost_cents: asCents(productCostForm.packaging_cost_cents), labor_cost_cents: asCents(productCostForm.labor_cost_cents), overhead_cost_cents: asCents(productCostForm.overhead_cost_cents), reviewed: productCostForm.reviewed, accountant_reviewed: productCostForm.accountant_reviewed, review_status: productCostForm.accountant_reviewed ? "accountant_reviewed" : productCostForm.reviewed ? "reviewed" : "estimate" }))} className="rounded-brand bg-muted-gold px-3 py-2 text-sm font-medium text-charcoal">{t("forms.addProductCost")}</button></div></section>
          <div className="rounded-brand border border-champagne-beige bg-cream p-4"><h2 className="font-heading text-lg font-semibold text-charcoal">Missing costs</h2><GenericTable rows={missingCosts as unknown as Record<string, unknown>[]} emptyLabel={t("empty.productCosts")} /></div>
          <GenericTable rows={productCosts as unknown as Record<string, unknown>[]} emptyLabel={t("empty.productCosts")} />
        </div>
      )}
    </div>
  );
}
