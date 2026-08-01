"use client";

import { type FormEvent, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import {
  applyManualPaymentAction,
  closeReturnCase,
  createAccountingDocument,
  createReturnCase,
  createStripeRefund,
  getAdminOrder,
  inspectReturnCase,
  listOrderAccountingDocuments,
  receiveReturnCase,
  recordCodSettlement,
  updateAccountingDocument,
  updateReturnAccounting,
} from "@/lib/api";
import { ApiError } from "@/lib/api-client";
import { useLocalizedError } from "@/lib/useLocalizedError";
import { cn, formatPrice } from "@/lib/utils";
import { DeliveryDetails } from "@/components/checkout/DeliveryDetails";
import { AdminInfoPopover } from "@/components/admin/AdminInfoPopover";
import { EcontFulfillmentPanel } from "@/components/admin/EcontFulfillmentPanel";
import { OrderStatusBadge } from "@/components/orders/OrderStatusBadge";
import { StatusTimeline } from "@/components/orders/StatusTimeline";
import { Skeleton } from "@/components/ui/Skeleton";
import { Button } from "@/components/ui/Button";
import { SaveConfirmation } from "@/components/admin/SaveConfirmation";
import type {
  AdminOrderDetailResponse,
  AccountingDocumentResponse,
  AccountingDocumentStatus,
  AccountingDocumentType,
  CallbackOutcome,
  CourierClaimStatus,
  CreateReturnCaseRequest,
  ManualPaymentAction,
  PaymentEventResponse,
  PaymentStatus,
  RestockDecision,
  ReturnReason,
} from "@/lib/types";

type PageState = "loading" | "success" | "not_found" | "error";

const PAYMENT_STATUS_COLORS: Record<PaymentStatus, string> = {
  pending: "bg-amber-100 text-amber-800",
  paid: "bg-green-100 text-green-800",
  cod_pending: "bg-gray-100 text-gray-700",
  failed: "bg-red-100 text-red-800",
  review_required: "bg-amber-100 text-amber-800",
  refund_pending: "bg-blue-100 text-blue-800",
  partially_refunded: "bg-blue-100 text-blue-800",
  refunded: "bg-blue-100 text-blue-800",
  dispute_open: "bg-red-100 text-red-800",
  dispute_won: "bg-green-100 text-green-800",
  dispute_lost: "bg-red-100 text-red-800",
};

const PAYMENT_ACTIONS: ManualPaymentAction[] = [
  "mark_paid",
  "mark_collected",
  "mark_refunded",
  "mark_failed",
  "mark_review",
  "cancel",
];

const RETURN_REASONS: ReturnReason[] = [
  "not_picked_up",
  "refused_delivery",
  "customer_return",
  "wrong_address",
  "unreachable_customer",
  "damaged_by_courier",
  "lost_by_courier",
  "merchant_error",
  "other",
];

const RESTOCK_DECISIONS: RestockDecision[] = ["restock", "do_not_restock", "partial"];
const COURIER_CLAIM_STATUSES: CourierClaimStatus[] = [
  "none",
  "filed",
  "approved",
  "rejected",
  "paid",
];
const CALLBACK_OUTCOMES: CallbackOutcome[] = [
  "confirmed",
  "declined",
  "unreachable",
  "needs_follow_up",
];

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function formatDateTime(iso: string, locale: string): string {
  return new Date(iso).toLocaleString(locale === "bg" ? "bg-BG" : "en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function formatOptionalDateTime(iso: string | null | undefined, locale: string): string | null {
  return iso ? formatDateTime(iso, locale) : null;
}

function formatEvidenceAmount(value: number | null | undefined): string | null {
  return typeof value === "number" ? value.toFixed(2) : null;
}

function formatEventName(event: PaymentEventResponse): string {
  const base = event.event_type || event.stripe_event_type || event.source;
  return base.replaceAll("_", " ").replaceAll(".", " ");
}

function formText(formData: FormData, key: string): string {
  const value = formData.get(key);
  return typeof value === "string" ? value.trim() : "";
}

function optionalFormText(formData: FormData, key: string): string | null {
  const value = formText(formData, key);
  return value || null;
}

function parseOptionalCents(value: string, errorMessage: string): number | null {
  if (!value.trim()) return null;
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 0) throw new Error(errorMessage);
  return parsed;
}

function parseRequiredCents(value: string, errorMessage: string): number {
  const parsed = parseOptionalCents(value, errorMessage);
  if (parsed === null) throw new Error(errorMessage);
  return parsed;
}

function parseRefundAmountCents(
  value: string,
  refundableCents: number,
  errorMessage: string,
): number | null {
  const parsed = parseOptionalCents(value, errorMessage);
  if (parsed === null) return null;
  if (parsed < 1 || parsed > refundableCents) throw new Error(errorMessage);
  return parsed;
}

function parseRestockQuantities(value: string, errorMessage: string): Record<string, number> | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const quantities: Record<string, number> = {};
  for (const part of trimmed.split(",")) {
    const [productId, rawQuantity] = part.split(":").map((item) => item.trim());
    const quantity = Number(rawQuantity);
    if (!productId || !Number.isInteger(quantity) || quantity < 1) {
      throw new Error(errorMessage);
    }
    quantities[productId] = quantity;
  }
  return quantities;
}

function refundIdempotencyKey(orderId: string): string {
  return `admin-refund-${orderId}-${Date.now()}`;
}

function hasPersonalizedItem(order: AdminOrderDetailResponse): boolean {
  return order.items.some((item) => {
    const searchable = `${item.product_id} ${item.product_name}`.toLowerCase();
    return ["custom", "personal", "bespoke", "made-to-order", "персон", "индивидуал"].some(
      (needle) => searchable.includes(needle),
    );
  });
}

function availablePaymentActions(order: AdminOrderDetailResponse): ManualPaymentAction[] {
  return PAYMENT_ACTIONS.filter((action) => {
    if (action === "mark_collected") {
      return order.payment_method === "cod" && !["paid", "refunded"].includes(order.payment_status);
    }
    if (action === "mark_paid") {
      return order.payment_method !== "cod" && !["paid", "refunded"].includes(order.payment_status);
    }
    if (action === "mark_refunded") return order.payment_status === "paid";
    if (action === "mark_failed") {
      return !["paid", "refunded", "failed"].includes(order.payment_status);
    }
    if (action === "mark_review") return !["paid", "refunded"].includes(order.payment_status);
    if (action === "cancel") return ["pending", "confirmed"].includes(order.status);
    return false;
  });
}

export default function AdminOrderDetailPage() {
  const tAdmin = useTranslations("admin");
  const tOrders = useTranslations("orders");
  const tPayment = useTranslations("orders.payment");
  const locale = useLocale();
  const params = useParams();
  const orderId = params.id as string;
  const getLocalizedError = useLocalizedError();
  const [order, setOrder] = useState<AdminOrderDetailResponse | null>(null);
  const [state, setState] = useState<PageState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [manualAction, setManualAction] = useState<ManualPaymentAction | null>(null);
  const [manualNote, setManualNote] = useState("");
  const [manualError, setManualError] = useState<string | null>(null);
  const [isManualSaving, setIsManualSaving] = useState(false);
  const [workflowError, setWorkflowError] = useState<string | null>(null);
  const [isWorkflowSaving, setIsWorkflowSaving] = useState(false);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);
  const [accountingDocuments, setAccountingDocuments] = useState<AccountingDocumentResponse[]>([]);
  const [documentForm, setDocumentForm] = useState<{
    document_type: AccountingDocumentType;
    source_system: string;
    document_number: string;
    issue_date: string;
    gross_amount_cents: string;
    status: AccountingDocumentStatus;
    notes: string;
  }>({
    document_type: "invoice",
    source_system: "external",
    document_number: "",
    issue_date: new Date().toISOString().slice(0, 10),
    gross_amount_cents: "",
    status: "recorded",
    notes: "",
  });

  useEffect(() => {
    let cancelled = false;

    async function fetchOrder() {
      try {
        setState("loading");
        setError(null);
        const [data, documentData] = await Promise.all([
          getAdminOrder(orderId),
          listOrderAccountingDocuments(orderId),
        ]);
        if (!cancelled) {
          setOrder(data);
          setAccountingDocuments(documentData.items);
          setDocumentForm((prev) => ({
            ...prev,
            gross_amount_cents: prev.gross_amount_cents || String(data.total_cents),
          }));
          setState("success");
        }
      } catch (err) {
        if (cancelled) return;
        if (
          err instanceof ApiError &&
          (err.code === "NOT_FOUND" || err.code === "ORDER_NOT_FOUND")
        ) {
          setState("not_found");
          return;
        }
        setError(
          err instanceof ApiError
            ? getLocalizedError(err.code)
            : tAdmin("errors.loadOrders")
        );
        setState("error");
      }
    }

    fetchOrder();
    return () => {
      cancelled = true;
    };
  }, [getLocalizedError, orderId, tAdmin]);

  async function handleManualActionSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!order || !manualAction) return;

    const note = manualNote.trim();
    if (!note) {
      setManualError(tAdmin("manualPayment.noteRequired"));
      return;
    }

    setIsManualSaving(true);
    setManualError(null);
    setSavedMessage(null);
    try {
      await applyManualPaymentAction(order.id, manualAction, note);
      const refreshed = await getAdminOrder(order.id);
      setOrder(refreshed);
      setManualAction(null);
      setManualNote("");
      setSavedMessage(tAdmin("manualPayment.saved"));
    } catch (err) {
      setManualError(
        err instanceof ApiError ? err.message : tAdmin("manualPayment.actionError")
      );
    } finally {
      setIsManualSaving(false);
    }
  }

  async function refreshOrder() {
    const [refreshed, documentData] = await Promise.all([
      getAdminOrder(orderId),
      listOrderAccountingDocuments(orderId),
    ]);
    setOrder(refreshed);
    setAccountingDocuments(documentData.items);
  }

  async function runWorkflowAction(
    action: () => Promise<void>,
    successMessage: string,
    form?: HTMLFormElement,
  ) {
    setWorkflowError(null);
    setSavedMessage(null);
    setIsWorkflowSaving(true);
    try {
      await action();
      await refreshOrder();
      form?.reset();
      setSavedMessage(successMessage);
    } catch (err) {
      setWorkflowError(
        err instanceof ApiError || err instanceof Error
          ? err.message
          : tAdmin("returnWorkflow.actionError"),
      );
    } finally {
      setIsWorkflowSaving(false);
    }
  }

  async function handleAccountingDocumentSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!order) return;
    const number = documentForm.document_number.trim();
    if (!number) {
      setWorkflowError(tAdmin("accountingPanel.documentNumberRequired"));
      return;
    }
    await runWorkflowAction(
      async () => {
        await createAccountingDocument({
          document_type: documentForm.document_type,
          source_system: documentForm.source_system.trim() || "external",
          document_number: number,
          issue_date: documentForm.issue_date,
          order_id: order.id,
          period_id: order.finance_period_id ?? null,
          currency: order.accounting_currency ?? "EUR",
          gross_amount_cents: Number.parseInt(documentForm.gross_amount_cents || "0", 10),
          status: documentForm.status,
          notes: documentForm.notes.trim() || null,
        });
      },
      tAdmin("accountingPanel.documentSaved"),
      event.currentTarget,
    );
    setDocumentForm((prev) => ({ ...prev, document_number: "", notes: "" }));
  }

  async function handleAccountingDocumentStatus(
    document: AccountingDocumentResponse,
    status: AccountingDocumentStatus,
  ) {
    await runWorkflowAction(
      async () => {
        await updateAccountingDocument(document.id, {
          document_type: document.document_type,
          source_system: document.source_system ?? "external",
          document_number: document.document_number ?? null,
          issue_date: document.issue_date,
          order_id: document.order_id ?? order?.id ?? null,
          refund_id: document.refund_id ?? null,
          period_id: document.period_id ?? order?.finance_period_id ?? null,
          currency: document.currency ?? order?.accounting_currency ?? "EUR",
          net_amount_cents: document.net_amount_cents ?? null,
          tax_amount_cents: document.tax_amount_cents ?? null,
          gross_amount_cents: document.gross_amount_cents ?? null,
          vat_summary: document.vat_summary ?? null,
          original_document_id: document.original_document_id ?? null,
          file_reference: document.file_reference ?? null,
          status,
          notes: document.notes ?? null,
        });
      },
      tAdmin("accountingPanel.documentSaved"),
    );
  }

  async function handleCreateReturnCase(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!order) return;
    const form = event.currentTarget;
    const formData = new FormData(form);
    const reason = formText(formData, "reason") as ReturnReason;
    const status = formText(formData, "status") as CreateReturnCaseRequest["status"];
    await runWorkflowAction(
      () =>
        createReturnCase(order.id, {
          reason,
          status,
          source: "admin",
          notes: optionalFormText(formData, "notes"),
        }).then(() => undefined),
      tAdmin("returnWorkflow.saved.returnCreated"),
      form,
    );
  }

  async function handleQuickReturn(reason: ReturnReason) {
    if (!order) return;
    await runWorkflowAction(
      () =>
        createReturnCase(order.id, {
          reason,
          status: "return_in_transit",
          source: "admin",
        }).then(() => undefined),
      tAdmin("returnWorkflow.saved.returnCreated"),
    );
  }

  async function handleReceiveReturn(returnId: string) {
    if (!order) return;
    await runWorkflowAction(
      () => receiveReturnCase(order.id, returnId).then(() => undefined),
      tAdmin("returnWorkflow.saved.returnReceived"),
    );
  }

  async function handleInspectReturn(event: FormEvent<HTMLFormElement>, returnId: string) {
    event.preventDefault();
    if (!order) return;
    const form = event.currentTarget;
    const formData = new FormData(form);
    await runWorkflowAction(
      () => {
        const decision = formText(formData, "restock_decision") as RestockDecision;
        const restockQuantities =
          decision === "partial"
            ? parseRestockQuantities(
                formText(formData, "restock_quantities"),
                tAdmin("returnWorkflow.validation.quantities"),
              )
            : null;
        return inspectReturnCase(order.id, returnId, {
          restock_decision: decision,
          restock_quantities: restockQuantities,
          notes: optionalFormText(formData, "notes"),
        }).then(() => undefined);
      },
      tAdmin("returnWorkflow.saved.returnInspected"),
      form,
    );
  }

  async function handleCloseReturn(returnId: string) {
    if (!order) return;
    await runWorkflowAction(
      () => closeReturnCase(order.id, returnId).then(() => undefined),
      tAdmin("returnWorkflow.saved.returnClosed"),
    );
  }

  async function handleReturnAccounting(event: FormEvent<HTMLFormElement>, returnId: string) {
    event.preventDefault();
    if (!order) return;
    const form = event.currentTarget;
    const formData = new FormData(form);
    await runWorkflowAction(
      () =>
        updateReturnAccounting(order.id, returnId, {
          courier_return_fee_cents: parseOptionalCents(
            formText(formData, "courier_return_fee_cents"),
            tAdmin("returnWorkflow.validation.cents"),
          ),
          courier_claim_id: optionalFormText(formData, "courier_claim_id"),
          courier_claim_status: formText(formData, "courier_claim_status") as CourierClaimStatus,
          courier_claim_amount_cents: parseOptionalCents(
            formText(formData, "courier_claim_amount_cents"),
            tAdmin("returnWorkflow.validation.cents"),
          ),
          notes: optionalFormText(formData, "notes"),
        }).then(() => undefined),
      tAdmin("returnWorkflow.saved.accountingUpdated"),
      form,
    );
  }

  async function handleStripeRefund(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!order) return;
    const form = event.currentTarget;
    const formData = new FormData(form);
    await runWorkflowAction(
      () =>
        createStripeRefund(order.id, {
          amount_cents: parseRefundAmountCents(
            formText(formData, "amount_cents"),
            refundableCents,
            tAdmin("returnWorkflow.validation.refundAmount"),
          ),
          reason: optionalFormText(formData, "reason"),
          idempotency_key: refundIdempotencyKey(order.id),
        }).then(() => undefined),
      tAdmin("returnWorkflow.saved.refundCreated"),
      form,
    );
  }

  async function handleCallbackReview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!order) return;
    const form = event.currentTarget;
    const formData = new FormData(form);
    const submitter = (event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null;
    const action = submitter?.value === "convert_to_cod" ? "convert_to_cod" : "record_callback";
    const outcome =
      action === "convert_to_cod" ? "confirmed" : (formText(formData, "callback_outcome") as CallbackOutcome);
    await runWorkflowAction(
      () => applyManualPaymentAction(order.id, action, formText(formData, "note"), outcome).then(() => undefined),
      action === "convert_to_cod"
        ? tAdmin("returnWorkflow.saved.convertedToCod")
        : tAdmin("returnWorkflow.saved.callbackRecorded"),
      form,
    );
  }

  async function handleCodSettlement(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!order) return;
    const form = event.currentTarget;
    const formData = new FormData(form);
    await runWorkflowAction(
      () =>
        recordCodSettlement(order.id, {
          amount_cents: parseRequiredCents(
            formText(formData, "amount_cents"),
            tAdmin("returnWorkflow.validation.cents"),
          ),
          settlement_date: formText(formData, "settlement_date"),
          courier_reference: optionalFormText(formData, "courier_reference"),
          notes: optionalFormText(formData, "notes"),
        }).then(() => undefined),
      tAdmin("returnWorkflow.saved.codSettlementRecorded"),
      form,
    );
  }

  if (state === "loading") {
    return (
      <div className="space-y-6">
        <Skeleton className="h-5 w-32" />
        <div className="rounded-brand border border-champagne-beige bg-cream p-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-2">
              <Skeleton className="h-8 w-48" />
              <Skeleton className="h-4 w-56" />
            </div>
            <Skeleton className="h-6 w-24" />
          </div>
          <div className="mt-8 grid gap-4 md:grid-cols-2">
            <Skeleton className="h-28 w-full" />
            <Skeleton className="h-28 w-full" />
          </div>
        </div>
      </div>
    );
  }

  if (state === "not_found") {
    return (
      <div className="rounded-brand border border-champagne-beige bg-cream p-8 text-center">
        <h1 className="mb-3 font-heading text-2xl text-charcoal">
          {tOrders("notFound")}
        </h1>
        <p className="mb-6 text-sm text-soft-brown">
          {tOrders("notFoundDescription")}
        </p>
        <Link
          href="/admin/orders"
          className="inline-flex items-center justify-center rounded-brand bg-charcoal px-5 py-2.5 text-sm font-medium text-warm-ivory transition-colors duration-fast hover:bg-soft-brown focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2"
        >
          {tAdmin("backToAdminOrders")}
        </Link>
      </div>
    );
  }

  if (state === "error") {
    return (
      <div className="rounded-brand border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        {error}
      </div>
    );
  }

  if (!order) return null;

  const isSpeedyOrder = order.delivery_courier === "speedy" || order.tracking_carrier === "speedy";
  const canMoveReturnInTransit = ["shipped", "delivered"].includes(order.status);
  const canCreateReturnCase = ["shipped", "delivered", "return_in_transit", "returned"].includes(
    order.status,
  );
  const refundableCents = Math.max(
    0,
    order.total_cents -
      order.refund_records
        .filter((refund) => ["pending", "succeeded"].includes(refund.status))
        .reduce((total, refund) => total + refund.amount_cents, 0),
  );
  const canCreateStripeRefund =
    order.payment_method === "card" &&
    ["paid", "partially_refunded", "refund_pending"].includes(order.payment_status) &&
    refundableCents > 0;
  const showCallbackReview =
    order.payment_method === "card" &&
    order.payment_status === "review_required" &&
    ["pending", "confirmed"].includes(order.status);
  const showCodSettlement =
    order.payment_method === "cod" && (order.status === "delivered" || order.cod_settlement !== null);
  const personalizedRefundWarning = hasPersonalizedItem(order);
  const today = new Date().toISOString().slice(0, 10);

  return (
    <div className="space-y-6">
      <Link
        href="/admin/orders"
        className="inline-block text-sm text-soft-brown transition-colors duration-fast hover:text-charcoal"
      >
        {tAdmin("backToAdminOrders")}
      </Link>

      <div className="rounded-brand border border-champagne-beige bg-cream p-6">
        <div className="flex flex-col gap-4 border-b border-champagne-beige pb-6 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h1 className="font-heading text-2xl font-semibold text-charcoal">
              {tAdmin("orderDetail", { id: order.id.slice(0, 8) })}
            </h1>
            <p className="mt-1 font-mono text-xs text-soft-brown">{order.id}</p>
          </div>
          <OrderStatusBadge status={order.status} />
        </div>

        <div className="grid gap-8 py-6 lg:grid-cols-[1.2fr_0.8fr]">
          <section>
            <h2 className="mb-4 text-sm font-medium text-charcoal">
              {tOrders("items")}
            </h2>
            <div className="divide-y divide-champagne-beige rounded-brand border border-champagne-beige bg-white">
              {order.items.map((item) => (
                <div
                  key={`${item.product_id}-${item.product_name}`}
                  className="flex items-start justify-between gap-4 p-4"
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium text-charcoal">
                      {item.product_name}
                    </p>
                    <p className="mt-1 text-sm text-soft-brown">
                      {formatPrice(item.price_cents)} x {item.quantity}
                    </p>
                    {(item.ledger_managed || item.inventory_mode === "ledger_managed") && (
                      <div className="mt-3 flex flex-wrap gap-2 text-xs text-soft-brown">
                        <span className="rounded-pill bg-champagne-beige/60 px-2 py-0.5 capitalize">
                          {tAdmin("stockIssueStatus")}: {(item.stock_issue_status ?? "missing").replaceAll("_", " ")}
                        </span>
                        <span className="rounded-pill bg-champagne-beige/60 px-2 py-0.5 capitalize">
                          {tAdmin("cogsReadiness")}: {(item.cogs_readiness ?? "not_required").replaceAll("_", " ")}
                        </span>
                        {item.valuation_method && (
                          <span className="rounded-pill bg-champagne-beige/60 px-2 py-0.5 capitalize">
                            {item.valuation_method.replaceAll("_", " ")}
                          </span>
                        )}
                        {item.finished_batch_id && (
                          <Link href={`/admin/inventory/batches?product_id=${item.product_id}`} className="font-medium text-charcoal underline-offset-2 hover:underline">
                            {item.finished_batch_number ?? item.finished_batch_id}
                          </Link>
                        )}
                        {item.source_movement_id && (
                          <Link href={`/admin/inventory/movements?item_type=finished_good&item_id=${item.product_id}&source_id=${order.id}`} className="font-medium text-charcoal underline-offset-2 hover:underline">
                            {tAdmin("inventoryMovement")}
                          </Link>
                        )}
                        {item.cogs_row_id && (
                          <Link href={`/admin/inventory/valuation/cogs?product_id=${item.product_id}`} className="font-medium text-charcoal underline-offset-2 hover:underline">
                            {tAdmin("cogsRow")}
                          </Link>
                        )}
                        {Boolean(item.inventory_exception_count) && (
                          <Link href={`/admin/inventory/valuation/exceptions?target_type=product&target_id=${item.product_id}`} className="font-medium text-amber-800 underline-offset-2 hover:underline">
                            {tAdmin("inventoryExceptions", { count: item.inventory_exception_count ?? 0 })}
                          </Link>
                        )}
                      </div>
                    )}
                  </div>
                  <span className="whitespace-nowrap font-medium text-charcoal">
                    {formatPrice(item.price_cents * item.quantity)}
                  </span>
                </div>
              ))}
            </div>
          </section>

          <aside className="space-y-5">
            <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-2 text-sm">
              <dt className="text-soft-brown">{tAdmin("placed")}</dt>
              <dd className="text-charcoal">{formatDateTime(order.created_at, locale)}</dd>
              <dt className="text-soft-brown">{tAdmin("updated")}</dt>
              <dd className="text-charcoal">{formatDateTime(order.updated_at, locale)}</dd>
              <dt className="text-soft-brown">{tAdmin("customer")}</dt>
              <dd className="text-charcoal">{order.customer_email}</dd>
              <dt className="text-soft-brown">{tAdmin("customerName")}</dt>
              <dd className="text-charcoal">
                {order.customer_name || tAdmin("notProvided")}
              </dd>
            </dl>

            <div className="border-t border-champagne-beige pt-5">
              <dl className="space-y-2 text-sm">
                <div className="flex items-center justify-between">
                  <dt className="text-soft-brown">{tAdmin("subtotal")}</dt>
                  <dd className="text-charcoal">
                    {formatPrice(order.items_total_cents)}
                  </dd>
                </div>
                <div className="flex items-center justify-between">
                  <dt className="text-soft-brown">{tAdmin("shipping")}</dt>
                  <dd className="flex items-center gap-2 text-charcoal">
                    {order.shipping_is_fallback && (
                      <span
                        className="rounded-pill bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800"
                        title={tOrders("shippingFallbackHint")}
                      >
                        {tOrders("shippingFallbackBadge")}
                      </span>
                    )}
                    {formatPrice(order.shipping_cents)}
                  </dd>
                </div>
                <div className="flex items-center justify-between border-t border-champagne-beige pt-2 font-medium">
                  <dt className="text-charcoal">{tAdmin("total")}</dt>
                  <dd className="text-charcoal">{formatPrice(order.total_cents)}</dd>
                </div>
              </dl>
            </div>

            <div className="border-t border-champagne-beige pt-5">
              <h2 className="mb-3 text-sm font-medium text-charcoal">
                {tPayment("sectionTitle")}
              </h2>
              <dl className="space-y-2 text-sm">
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-soft-brown">{tAdmin("paymentMethod")}</dt>
                  <dd className="text-charcoal">
                    {tPayment(`method.${order.payment_method}` as Parameters<typeof tPayment>[0])}
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-soft-brown">{tAdmin("paymentStatus")}</dt>
                  <dd>
                    <span
                      className={cn(
                        "inline-flex items-center rounded-pill px-2.5 py-0.5 text-xs font-medium",
                        PAYMENT_STATUS_COLORS[order.payment_status]
                      )}
                    >
                      {tPayment(`status.${order.payment_status}` as Parameters<typeof tPayment>[0])}
                    </span>
                  </dd>
                </div>
                {order.order_number && (
                  <div className="flex items-center justify-between gap-4">
                    <dt className="text-soft-brown">{tAdmin("orderNumber")}</dt>
                    <dd className="font-mono text-xs text-charcoal">{order.order_number}</dd>
                  </div>
                )}
                {order.reserved_until && (
                  <div className="flex items-center justify-between gap-4">
                    <dt className="text-soft-brown">{tAdmin("reservedUntil")}</dt>
                    <dd className="text-charcoal">{formatDateTime(order.reserved_until, locale)}</dd>
                  </div>
                )}
                {order.paid_at && (
                  <div className="flex items-center justify-between gap-4">
                    <dt className="text-soft-brown">{tAdmin("paidAt")}</dt>
                    <dd className="text-charcoal">{formatDateTime(order.paid_at, locale)}</dd>
                  </div>
                )}
                {order.collected_at && (
                  <div className="flex items-center justify-between gap-4">
                    <dt className="text-soft-brown">{tAdmin("collectedAt")}</dt>
                    <dd className="text-charcoal">{formatDateTime(order.collected_at, locale)}</dd>
                  </div>
                )}
                {order.stripe_checkout_session_id && (
                  <div className="flex items-center justify-between gap-4">
                    <dt className="text-soft-brown">{tAdmin("checkoutSession")}</dt>
                    <dd className="font-mono text-xs text-charcoal">
                      {order.stripe_checkout_session_id}
                    </dd>
                  </div>
                )}
              </dl>
            </div>
          </aside>
        </div>

        <section className="border-t border-champagne-beige py-6">
          <h2 className="mb-4 text-sm font-medium text-charcoal">
            {tOrders("progress")}
          </h2>
          <StatusTimeline
            currentStatus={order.status}
            trackingNumber={order.tracking_number}
            trackingCarrier={order.tracking_carrier}
            trackingUrl={order.tracking_url}
          />
        </section>

        <section className="border-t border-champagne-beige py-6">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-medium text-charcoal">
                {tAdmin("manualPayment.title")}
              </h2>
              <AdminInfoPopover content={tAdmin("manualPayment.subtitle")} />
            </div>
            <div className="flex flex-wrap gap-2">
              {availablePaymentActions(order).map((action) => (
                <Button
                  key={action}
                  type="button"
                  size="sm"
                  variant="secondary"
                  onClick={() => {
                    setManualAction(action);
                    setManualNote("");
                    setManualError(null);
                  }}
                >
                  {tAdmin(`manualPayment.actions.${action}` as Parameters<typeof tAdmin>[0])}
                </Button>
              ))}
            </div>
          </div>
        </section>

        <section className="border-t border-champagne-beige py-6">
          <h2 className="mb-4 text-sm font-medium text-charcoal">
            {tAdmin("paymentTimeline")}
          </h2>
          {order.payment_events.length === 0 ? (
            <p className="text-sm text-soft-brown">{tAdmin("noPaymentEvents")}</p>
          ) : (
            <ol className="space-y-3">
              {order.payment_events.map((event) => (
                <li
                  key={event.id}
                  className="rounded-brand border border-champagne-beige bg-white px-4 py-3"
                >
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <p className="text-sm font-semibold capitalize text-charcoal">
                        {formatEventName(event)}
                      </p>
                      <p className="mt-1 text-xs text-soft-brown">
                        {formatDateTime(event.created_at, locale)} · {event.source}
                      </p>
                    </div>
                    <span className="rounded-pill bg-champagne-beige/60 px-2.5 py-0.5 text-xs font-medium text-soft-brown">
                      {event.processing_status}
                    </span>
                  </div>
                  <dl className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
                    {event.provider_status && (
                      <div>
                        <dt className="text-soft-brown">{tAdmin("providerStatus")}</dt>
                        <dd className="font-medium text-charcoal">{event.provider_status}</dd>
                      </div>
                    )}
                    {event.provider && (
                      <div>
                        <dt className="text-soft-brown">{tAdmin("provider")}</dt>
                        <dd className="font-medium text-charcoal">{event.provider}</dd>
                      </div>
                    )}
                    {event.stripe_event_id && (
                      <div>
                        <dt className="text-soft-brown">{tAdmin("stripeEventId")}</dt>
                        <dd className="font-mono text-charcoal">{event.stripe_event_id}</dd>
                      </div>
                    )}
                    {event.stripe_event_type && (
                      <div>
                        <dt className="text-soft-brown">{tAdmin("stripeEventType")}</dt>
                        <dd className="font-mono text-charcoal">{event.stripe_event_type}</dd>
                      </div>
                    )}
                    {event.admin_email && (
                      <div>
                        <dt className="text-soft-brown">{tAdmin("adminEmail")}</dt>
                        <dd className="text-charcoal">{event.admin_email}</dd>
                      </div>
                    )}
                    {event.request_id && (
                      <div>
                        <dt className="text-soft-brown">{tAdmin("requestId")}</dt>
                        <dd className="font-mono text-charcoal">{event.request_id}</dd>
                      </div>
                    )}
                  </dl>
                  {event.admin_note && (
                    <p className="mt-3 rounded-brand bg-cream px-3 py-2 text-sm text-soft-brown">
                      {event.admin_note}
                    </p>
                  )}
                </li>
              ))}
            </ol>
          )}
        </section>

        <section className="border-t border-champagne-beige py-6">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-medium text-charcoal">
                {tAdmin("accountingPanel.title")}
              </h2>
              <AdminInfoPopover content={tAdmin("accountingPanel.subtitle")} />
            </div>
            {order.finance_hub_links?.period_href && (
              <Link
                href={order.finance_hub_links.period_href}
                className="inline-flex h-9 items-center justify-center rounded-brand border border-champagne-beige px-3 text-sm font-medium text-charcoal hover:bg-champagne-beige/40"
              >
                {tAdmin("openFinanceHub")}
              </Link>
            )}
          </div>

          <dl className="mb-4 grid gap-3 text-sm md:grid-cols-4">
            <div className="rounded-brand border border-champagne-beige bg-white p-3">
              <dt className="text-soft-brown">{tAdmin("accountingPanel.readiness")}</dt>
              <dd className="mt-1 text-charcoal">{order.accounting_readiness_status ?? "unreviewed"}</dd>
            </div>
            <div className="rounded-brand border border-champagne-beige bg-white p-3">
              <dt className="text-soft-brown">{tAdmin("accountingPanel.documentStatus")}</dt>
              <dd className="mt-1 text-charcoal">{order.document_reference_status ?? "not_required"}</dd>
            </div>
            <div className="rounded-brand border border-champagne-beige bg-white p-3">
              <dt className="text-soft-brown">{tAdmin("accountingPanel.payoutStatus")}</dt>
              <dd className="mt-1 text-charcoal">{order.payout_reconciliation_status ?? "not_applicable"}</dd>
            </div>
            <div className="rounded-brand border border-champagne-beige bg-white p-3">
              <dt className="text-soft-brown">{tAdmin("accountingPanel.codStatus")}</dt>
              <dd className="mt-1 text-charcoal">{order.cod_settlement_status ?? "not_applicable"}</dd>
            </div>
          </dl>

          <form onSubmit={handleAccountingDocumentSubmit} className="rounded-brand border border-champagne-beige bg-white p-4">
            <div className="grid gap-3 md:grid-cols-3 lg:grid-cols-6">
              <select
                value={documentForm.document_type}
                onChange={(event) => setDocumentForm((prev) => ({ ...prev, document_type: event.target.value as AccountingDocumentType }))}
                className="h-10 rounded-brand border border-champagne-beige bg-cream px-3 text-sm text-charcoal"
                aria-label={tAdmin("accountingPanel.documentType")}
              >
                <option value="invoice">invoice</option>
                <option value="credit_note">credit note</option>
                <option value="fiscal_receipt">fiscal receipt</option>
                <option value="alternative_sales_document">alternative document</option>
                <option value="external_document">external document</option>
              </select>
              <input
                value={documentForm.document_number}
                onChange={(event) => setDocumentForm((prev) => ({ ...prev, document_number: event.target.value }))}
                className="h-10 rounded-brand border border-champagne-beige bg-cream px-3 text-sm text-charcoal"
                placeholder={tAdmin("accountingPanel.documentNumber")}
              />
              <input
                value={documentForm.source_system}
                onChange={(event) => setDocumentForm((prev) => ({ ...prev, source_system: event.target.value }))}
                className="h-10 rounded-brand border border-champagne-beige bg-cream px-3 text-sm text-charcoal"
                placeholder={tAdmin("accountingPanel.sourceSystem")}
              />
              <input
                type="date"
                value={documentForm.issue_date}
                onChange={(event) => setDocumentForm((prev) => ({ ...prev, issue_date: event.target.value }))}
                className="h-10 rounded-brand border border-champagne-beige bg-cream px-3 text-sm text-charcoal"
                aria-label={tAdmin("accountingPanel.issueDate")}
              />
              <input
                value={documentForm.gross_amount_cents}
                onChange={(event) => setDocumentForm((prev) => ({ ...prev, gross_amount_cents: event.target.value }))}
                className="h-10 rounded-brand border border-champagne-beige bg-cream px-3 text-sm text-charcoal"
                placeholder={tAdmin("accountingPanel.grossCents")}
              />
              <button
                type="submit"
                disabled={isWorkflowSaving}
                className="rounded-brand bg-muted-gold px-3 py-2 text-sm font-medium text-charcoal disabled:opacity-50"
              >
                {tAdmin("accountingPanel.addDocument")}
              </button>
            </div>
          </form>

          <div className="mt-4 overflow-x-auto rounded-brand border border-champagne-beige bg-white">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-champagne-beige bg-champagne-beige/30">
                  <th className="px-4 py-3 font-medium text-charcoal">{tAdmin("accountingPanel.documentType")}</th>
                  <th className="px-4 py-3 font-medium text-charcoal">{tAdmin("accountingPanel.documentNumber")}</th>
                  <th className="px-4 py-3 font-medium text-charcoal">{tAdmin("accountingPanel.issueDate")}</th>
                  <th className="px-4 py-3 font-medium text-charcoal">{tAdmin("status")}</th>
                  <th className="px-4 py-3 font-medium text-charcoal">{tAdmin("actions")}</th>
                </tr>
              </thead>
              <tbody>
                {accountingDocuments.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-soft-brown">
                      {tAdmin("accountingPanel.noDocuments")}
                    </td>
                  </tr>
                ) : accountingDocuments.map((document) => (
                  <tr key={document.id} className="border-b border-champagne-beige/50 last:border-0">
                    <td className="px-4 py-3 text-soft-brown">{document.document_type}</td>
                    <td className="px-4 py-3 font-mono text-xs text-charcoal">{document.document_number ?? tAdmin("notProvided")}</td>
                    <td className="px-4 py-3 text-soft-brown">{formatDateTime(document.issue_date, locale)}</td>
                    <td className="px-4 py-3 text-soft-brown">{document.status}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => handleAccountingDocumentStatus(document, "recorded")}
                          className="rounded-brand border border-champagne-beige px-3 py-1.5 text-xs font-medium text-charcoal hover:bg-champagne-beige/40"
                        >
                          {tAdmin("accountingPanel.markRecorded")}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleAccountingDocumentStatus(document, "review_required")}
                          className="rounded-brand border border-champagne-beige px-3 py-1.5 text-xs font-medium text-charcoal hover:bg-champagne-beige/40"
                        >
                          {tAdmin("accountingPanel.markReview")}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <DeliveryDetails order={order} />

        <EcontFulfillmentPanel order={order} onRefreshOrder={refreshOrder} />

        {order.econt_cod_evidence && (
          <section className="mt-8 border-t border-champagne-beige pt-6">
            <div className="mb-4 flex items-center gap-2">
              <h2 className="text-sm font-medium text-charcoal">
                {tAdmin("econtCodEvidence.title")}
              </h2>
              <AdminInfoPopover content={tAdmin("econtCodEvidence.subtitle")} />
            </div>
            <dl className="grid gap-3 text-sm md:grid-cols-2">
              <div className="rounded-brand border border-champagne-beige bg-white p-3">
                <dt className="text-soft-brown">{tAdmin("econtCodEvidence.collectedAmount")}</dt>
                <dd className="mt-1 text-charcoal">
                  {formatEvidenceAmount(order.econt_cod_evidence.collected_amount) ??
                    tAdmin("notProvided")}
                </dd>
              </div>
              <div className="rounded-brand border border-champagne-beige bg-white p-3">
                <dt className="text-soft-brown">{tAdmin("econtCodEvidence.collectedTime")}</dt>
                <dd className="mt-1 text-charcoal">
                  {formatOptionalDateTime(order.econt_cod_evidence.collected_time, locale) ??
                    tAdmin("notProvided")}
                </dd>
              </div>
              <div className="rounded-brand border border-champagne-beige bg-white p-3">
                <dt className="text-soft-brown">{tAdmin("econtCodEvidence.paidAmount")}</dt>
                <dd className="mt-1 text-charcoal">
                  {formatEvidenceAmount(order.econt_cod_evidence.paid_amount) ??
                    tAdmin("notProvided")}
                </dd>
              </div>
              <div className="rounded-brand border border-champagne-beige bg-white p-3">
                <dt className="text-soft-brown">{tAdmin("econtCodEvidence.paidTime")}</dt>
                <dd className="mt-1 text-charcoal">
                  {formatOptionalDateTime(order.econt_cod_evidence.paid_time, locale) ??
                    tAdmin("notProvided")}
                </dd>
              </div>
            </dl>
          </section>
        )}

        {isSpeedyOrder && (
          <section className="mt-8 border-t border-champagne-beige pt-6">
            <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-medium text-charcoal">
                  {tAdmin("speedyFulfillment.title")}
                </h2>
                <AdminInfoPopover content={tAdmin("speedyFulfillment.subtitle")} />
              </div>
              <Link
                href={`/admin/speedy?order_id=${order.id}`}
                className="inline-flex h-9 items-center justify-center rounded-brand border border-champagne-beige px-3 text-sm font-medium text-charcoal hover:bg-champagne-beige/40"
              >
                {tAdmin("speedyDiagnostics")}
              </Link>
            </div>
            <dl className="grid gap-3 text-sm md:grid-cols-2">
              <div className="rounded-brand border border-champagne-beige bg-white p-3">
                <dt className="text-soft-brown">{tAdmin("speedyFulfillment.shipmentNumber")}</dt>
                <dd className="mt-1 font-mono text-charcoal">
                  {order.tracking_number || order.courier_shipment_number || tAdmin("notProvided")}
                </dd>
              </div>
              <div className="rounded-brand border border-champagne-beige bg-white p-3">
                <dt className="text-soft-brown">{tAdmin("speedyFulfillment.courierStatus")}</dt>
                <dd className="mt-1 text-charcoal">{order.courier_status || tAdmin("notProvided")}</dd>
              </div>
              <div className="rounded-brand border border-champagne-beige bg-white p-3">
                <dt className="text-soft-brown">{tAdmin("speedyFulfillment.syncStatus")}</dt>
                <dd className="mt-1 text-charcoal">{order.courier_sync_status || tAdmin("notProvided")}</dd>
              </div>
              <div className="rounded-brand border border-champagne-beige bg-white p-3">
                <dt className="text-soft-brown">{tAdmin("speedyFulfillment.lastSync")}</dt>
                <dd className="mt-1 text-charcoal">
                  {order.courier_last_synced_at ? formatDateTime(order.courier_last_synced_at, locale) : tAdmin("notProvided")}
                </dd>
              </div>
            </dl>
            {order.courier_last_error && (
              <p className="mt-3 rounded-brand border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {order.courier_last_error}
              </p>
            )}
            <div className="mt-4 flex flex-wrap gap-2">
              {order.tracking_url && (
                <a
                  href={order.tracking_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex h-9 items-center justify-center rounded-brand border border-champagne-beige px-3 text-sm font-medium text-charcoal hover:bg-champagne-beige/40"
                >
                  {tAdmin("speedyFulfillment.openTracking")}
                </a>
              )}
              {(order.tracking_number || order.courier_shipment_number) && (
                <a
                  href={`${API_BASE_URL}/v1/admin/speedy/orders/${order.id}/label`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex h-9 items-center justify-center rounded-brand bg-charcoal px-3 text-sm font-medium text-warm-ivory hover:bg-soft-brown"
                >
                  {tAdmin("speedyFulfillment.printLabel")}
                </a>
              )}
            </div>
          </section>
        )}

        <section className="mt-8 border-t border-champagne-beige pt-6">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-medium text-charcoal">
                {tAdmin("returnWorkflow.title")}
              </h2>
              <AdminInfoPopover content={tAdmin("returnWorkflow.subtitle")} />
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                size="sm"
                variant="secondary"
                disabled={!canMoveReturnInTransit || isWorkflowSaving}
                onClick={() => void handleQuickReturn("not_picked_up")}
              >
                {tAdmin("returnWorkflow.actions.markUncollected")}
              </Button>
              <Button
                type="button"
                size="sm"
                variant="secondary"
                disabled={!canMoveReturnInTransit || isWorkflowSaving}
                onClick={() => void handleQuickReturn("refused_delivery")}
              >
                {tAdmin("returnWorkflow.actions.markRefused")}
              </Button>
              <Button
                type="button"
                size="sm"
                variant="secondary"
                disabled={!canMoveReturnInTransit || isWorkflowSaving}
                onClick={() => void handleQuickReturn("customer_return")}
              >
                {tAdmin("returnWorkflow.actions.markReturnInTransit")}
              </Button>
            </div>
          </div>

          {workflowError && (
            <div className="mb-4 rounded-brand border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {workflowError}
            </div>
          )}

          {showCallbackReview && (
            <form
              onSubmit={handleCallbackReview}
              className="mb-5 rounded-brand border border-amber-200 bg-amber-50 p-4"
            >
              <h3 className="text-sm font-semibold text-charcoal">
                {tAdmin("returnWorkflow.callback.title")}
              </h3>
              <div className="mt-3 grid gap-3 md:grid-cols-[0.6fr_1fr]">
                <label className="text-sm font-medium text-charcoal" htmlFor="callback-outcome">
                  {tAdmin("returnWorkflow.callback.outcome")}
                  <select
                    id="callback-outcome"
                    name="callback_outcome"
                    defaultValue="needs_follow_up"
                    className="mt-1 block w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm"
                  >
                    {CALLBACK_OUTCOMES.map((outcome) => (
                      <option key={outcome} value={outcome}>
                        {tAdmin(`returnWorkflow.callback.outcomes.${outcome}` as Parameters<typeof tAdmin>[0])}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="text-sm font-medium text-charcoal" htmlFor="callback-note">
                  {tAdmin("manualPayment.noteLabel")}
                  <input
                    id="callback-note"
                    name="note"
                    required
                    className="mt-1 block w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm"
                    placeholder={tAdmin("returnWorkflow.callback.notePlaceholder")}
                  />
                </label>
              </div>
              <div className="mt-3 flex flex-wrap justify-end gap-2">
                <Button type="submit" size="sm" variant="secondary" isLoading={isWorkflowSaving} value="record_callback">
                  {tAdmin("returnWorkflow.callback.record")}
                </Button>
                <Button type="submit" size="sm" isLoading={isWorkflowSaving} value="convert_to_cod">
                  {tAdmin("returnWorkflow.callback.convert")}
                </Button>
              </div>
            </form>
          )}

          <form
            onSubmit={handleCreateReturnCase}
            className="grid gap-3 rounded-brand border border-champagne-beige bg-white p-4 md:grid-cols-[0.7fr_0.7fr_1fr_auto] md:items-end"
          >
            <label className="text-sm font-medium text-charcoal" htmlFor="return-reason">
              {tAdmin("returnWorkflow.reason")}
              <select
                id="return-reason"
                name="reason"
                defaultValue="customer_return"
                className="mt-1 block w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm"
              >
                {RETURN_REASONS.map((reason) => (
                  <option key={reason} value={reason}>
                    {tAdmin(`returnWorkflow.reasons.${reason}` as Parameters<typeof tAdmin>[0])}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm font-medium text-charcoal" htmlFor="return-status">
              {tAdmin("returnWorkflow.initialStatus")}
              <select
                id="return-status"
                name="status"
                defaultValue="requested"
                className="mt-1 block w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm"
              >
                <option value="requested">{tAdmin("returnWorkflow.status.requested")}</option>
                <option value="return_in_transit">
                  {tAdmin("returnWorkflow.status.return_in_transit")}
                </option>
              </select>
            </label>
            <label className="text-sm font-medium text-charcoal" htmlFor="return-notes">
              {tAdmin("notes")}
              <input
                id="return-notes"
                name="notes"
                className="mt-1 block w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm"
                placeholder={tAdmin("returnWorkflow.notesPlaceholder")}
              />
            </label>
            <Button type="submit" size="sm" disabled={!canCreateReturnCase} isLoading={isWorkflowSaving}>
              {tAdmin("returnWorkflow.actions.createReturn")}
            </Button>
          </form>

          <div className="mt-5 space-y-4">
            {order.return_cases.length === 0 ? (
              <p className="text-sm text-soft-brown">{tAdmin("returnWorkflow.noReturnCases")}</p>
            ) : (
              order.return_cases.map((returnCase) => (
                <div key={returnCase.id} className="rounded-brand border border-champagne-beige bg-white p-4">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <p className="text-sm font-semibold text-charcoal">
                        {tAdmin(`returnWorkflow.reasons.${returnCase.reason}` as Parameters<typeof tAdmin>[0])}
                      </p>
                      <p className="mt-1 font-mono text-xs text-soft-brown">{returnCase.id}</p>
                    </div>
                    <span className="rounded-pill bg-champagne-beige/60 px-2.5 py-0.5 text-xs font-medium text-soft-brown">
                      {tAdmin(`returnWorkflow.status.${returnCase.status}` as Parameters<typeof tAdmin>[0])}
                    </span>
                  </div>
                  <dl className="mt-3 grid gap-2 text-xs md:grid-cols-3">
                    <div>
                      <dt className="text-soft-brown">{tAdmin("returnWorkflow.source")}</dt>
                      <dd className="text-charcoal">{returnCase.source}</dd>
                    </div>
                    <div>
                      <dt className="text-soft-brown">{tAdmin("returnWorkflow.restockDecision")}</dt>
                      <dd className="text-charcoal">
                        {tAdmin(`returnWorkflow.restock.${returnCase.restock_decision}` as Parameters<typeof tAdmin>[0])}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-soft-brown">{tAdmin("returnWorkflow.courierFee")}</dt>
                      <dd className="text-charcoal">{formatPrice(returnCase.courier_return_fee_cents)}</dd>
                    </div>
                    {returnCase.courier_claim_id && (
                      <div>
                        <dt className="text-soft-brown">{tAdmin("returnWorkflow.claimId")}</dt>
                        <dd className="text-charcoal">{returnCase.courier_claim_id}</dd>
                      </div>
                    )}
                    {returnCase.notes && (
                      <div className="md:col-span-2">
                        <dt className="text-soft-brown">{tAdmin("notes")}</dt>
                        <dd className="text-charcoal">{returnCase.notes}</dd>
                      </div>
                    )}
                  </dl>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      disabled={!["requested", "return_in_transit"].includes(returnCase.status) || isWorkflowSaving}
                      onClick={() => void handleReceiveReturn(returnCase.id)}
                    >
                      {tAdmin("returnWorkflow.actions.receive")}
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      disabled={!["inspected", "rejected"].includes(returnCase.status) || isWorkflowSaving}
                      onClick={() => void handleCloseReturn(returnCase.id)}
                    >
                      {tAdmin("returnWorkflow.actions.close")}
                    </Button>
                  </div>

                  {returnCase.status === "received" && (
                    <form
                      onSubmit={(event) => void handleInspectReturn(event, returnCase.id)}
                      className="mt-4 grid gap-3 rounded-brand bg-cream p-3 md:grid-cols-[0.7fr_1fr_1fr_auto] md:items-end"
                    >
                      <label className="text-sm font-medium text-charcoal" htmlFor={`restock-${returnCase.id}`}>
                        {tAdmin("returnWorkflow.restockDecision")}
                        <select
                          id={`restock-${returnCase.id}`}
                          name="restock_decision"
                          defaultValue="restock"
                          className="mt-1 block w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm"
                        >
                          {RESTOCK_DECISIONS.map((decision) => (
                            <option key={decision} value={decision}>
                              {tAdmin(`returnWorkflow.restock.${decision}` as Parameters<typeof tAdmin>[0])}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="text-sm font-medium text-charcoal" htmlFor={`quantities-${returnCase.id}`}>
                        {tAdmin("returnWorkflow.partialQuantities")}
                        <input
                          id={`quantities-${returnCase.id}`}
                          name="restock_quantities"
                          className="mt-1 block w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm"
                          placeholder="product-id:1"
                        />
                      </label>
                      <label className="text-sm font-medium text-charcoal" htmlFor={`inspect-notes-${returnCase.id}`}>
                        {tAdmin("notes")}
                        <input
                          id={`inspect-notes-${returnCase.id}`}
                          name="notes"
                          className="mt-1 block w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm"
                        />
                      </label>
                      <Button type="submit" size="sm" isLoading={isWorkflowSaving}>
                        {tAdmin("returnWorkflow.actions.inspect")}
                      </Button>
                    </form>
                  )}

                  <form
                    onSubmit={(event) => void handleReturnAccounting(event, returnCase.id)}
                    className="mt-4 grid gap-3 rounded-brand bg-cream p-3 md:grid-cols-5 md:items-end"
                  >
                    <label className="text-sm font-medium text-charcoal" htmlFor={`fee-${returnCase.id}`}>
                      {tAdmin("returnWorkflow.courierFeeCents")}
                      <input
                        id={`fee-${returnCase.id}`}
                        name="courier_return_fee_cents"
                        inputMode="numeric"
                        defaultValue={returnCase.courier_return_fee_cents || ""}
                        className="mt-1 block w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm"
                      />
                    </label>
                    <label className="text-sm font-medium text-charcoal" htmlFor={`claim-id-${returnCase.id}`}>
                      {tAdmin("returnWorkflow.claimId")}
                      <input
                        id={`claim-id-${returnCase.id}`}
                        name="courier_claim_id"
                        defaultValue={returnCase.courier_claim_id ?? ""}
                        className="mt-1 block w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm"
                      />
                    </label>
                    <label className="text-sm font-medium text-charcoal" htmlFor={`claim-status-${returnCase.id}`}>
                      {tAdmin("returnWorkflow.claimStatus")}
                      <select
                        id={`claim-status-${returnCase.id}`}
                        name="courier_claim_status"
                        defaultValue={returnCase.courier_claim_status}
                        className="mt-1 block w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm"
                      >
                        {COURIER_CLAIM_STATUSES.map((status) => (
                          <option key={status} value={status}>
                            {tAdmin(`returnWorkflow.claimStatusValue.${status}` as Parameters<typeof tAdmin>[0])}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="text-sm font-medium text-charcoal" htmlFor={`claim-amount-${returnCase.id}`}>
                      {tAdmin("returnWorkflow.claimAmountCents")}
                      <input
                        id={`claim-amount-${returnCase.id}`}
                        name="courier_claim_amount_cents"
                        inputMode="numeric"
                        defaultValue={returnCase.courier_claim_amount_cents ?? ""}
                        className="mt-1 block w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm"
                      />
                    </label>
                    <Button type="submit" size="sm" variant="secondary" isLoading={isWorkflowSaving}>
                      {tAdmin("returnWorkflow.actions.saveAccounting")}
                    </Button>
                  </form>
                </div>
              ))
            )}
          </div>

          <div className="mt-5 grid gap-4 lg:grid-cols-2">
            {order.payment_method === "card" && (
              <form onSubmit={handleStripeRefund} className="rounded-brand border border-champagne-beige bg-white p-4">
                <h3 className="text-sm font-semibold text-charcoal">
                  {tAdmin("returnWorkflow.refund.title")}
                </h3>
                <p className="mt-1 text-sm text-soft-brown">
                  {tAdmin("returnWorkflow.refund.remaining", { amount: formatPrice(refundableCents) })}
                </p>
                {personalizedRefundWarning && (
                  <p className="mt-3 rounded-brand border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                    {tAdmin("returnWorkflow.refund.personalizedWarning")}
                  </p>
                )}
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <label className="text-sm font-medium text-charcoal" htmlFor="refund-amount">
                    {tAdmin("returnWorkflow.refund.amountCents")}
                    <input
                      id="refund-amount"
                      name="amount_cents"
                      inputMode="numeric"
                      className="mt-1 block w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm"
                      placeholder={String(refundableCents)}
                    />
                  </label>
                  <label className="text-sm font-medium text-charcoal" htmlFor="refund-reason">
                    {tAdmin("returnWorkflow.refund.reason")}
                    <input
                      id="refund-reason"
                      name="reason"
                      className="mt-1 block w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm"
                    />
                  </label>
                </div>
                <div className="mt-3 flex justify-end">
                  <Button type="submit" size="sm" disabled={!canCreateStripeRefund} isLoading={isWorkflowSaving}>
                    {tAdmin("returnWorkflow.refund.create")}
                  </Button>
                </div>
                {order.refund_records.length > 0 && (
                  <ul className="mt-3 space-y-2 text-xs text-soft-brown">
                    {order.refund_records.map((refund) => (
                      <li key={refund.id} className="rounded-brand bg-cream px-3 py-2">
                        {formatPrice(refund.amount_cents)} · {refund.status}
                        {refund.provider_refund_id ? ` · ${refund.provider_refund_id}` : ""}
                      </li>
                    ))}
                  </ul>
                )}
              </form>
            )}

            {showCodSettlement && (
              <form onSubmit={handleCodSettlement} className="rounded-brand border border-champagne-beige bg-white p-4">
                <h3 className="text-sm font-semibold text-charcoal">
                  {tAdmin("returnWorkflow.cod.title")}
                </h3>
                {order.cod_settlement && (
                  <p className="mt-1 text-sm text-soft-brown">
                    {tAdmin("returnWorkflow.cod.current", {
                      amount: formatPrice(order.cod_settlement.amount_cents),
                      date: order.cod_settlement.settlement_date,
                    })}
                  </p>
                )}
                {order.cod_settlement_required && (
                  <p className="mt-1 text-sm text-amber-800">{tAdmin("returnWorkflow.cod.required")}</p>
                )}
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <label className="text-sm font-medium text-charcoal" htmlFor="cod-amount">
                    {tAdmin("returnWorkflow.cod.amountCents")}
                    <input
                      id="cod-amount"
                      name="amount_cents"
                      inputMode="numeric"
                      required
                      defaultValue={order.cod_settlement?.amount_cents ?? order.total_cents}
                      className="mt-1 block w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm"
                    />
                  </label>
                  <label className="text-sm font-medium text-charcoal" htmlFor="cod-date">
                    {tAdmin("returnWorkflow.cod.date")}
                    <input
                      id="cod-date"
                      name="settlement_date"
                      type="date"
                      required
                      defaultValue={order.cod_settlement?.settlement_date ?? today}
                      className="mt-1 block w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm"
                    />
                  </label>
                  <label className="text-sm font-medium text-charcoal" htmlFor="cod-reference">
                    {tAdmin("returnWorkflow.cod.reference")}
                    <input
                      id="cod-reference"
                      name="courier_reference"
                      defaultValue={order.cod_settlement?.courier_reference ?? ""}
                      className="mt-1 block w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm"
                    />
                  </label>
                  <label className="text-sm font-medium text-charcoal" htmlFor="cod-notes">
                    {tAdmin("notes")}
                    <input
                      id="cod-notes"
                      name="notes"
                      defaultValue={order.cod_settlement?.notes ?? ""}
                      className="mt-1 block w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm"
                    />
                  </label>
                </div>
                <div className="mt-3 flex justify-end">
                  <Button type="submit" size="sm" isLoading={isWorkflowSaving}>
                    {tAdmin("returnWorkflow.cod.record")}
                  </Button>
                </div>
              </form>
            )}
          </div>
        </section>

        {order.notes && (
          <section className="mt-8 border-t border-champagne-beige pt-6">
            <h2 className="mb-2 text-sm font-medium text-charcoal">
              {tAdmin("notes")}
            </h2>
            <p className="whitespace-pre-wrap text-sm text-soft-brown">
              {order.notes}
            </p>
          </section>
        )}
      </div>

      {manualAction && (
        <div className="fixed inset-0 z-[90] flex items-center justify-center bg-charcoal/40 px-4">
          <form
            onSubmit={handleManualActionSubmit}
            className="w-full max-w-md rounded-brand border border-champagne-beige bg-cream p-5 shadow-xl"
          >
            <div className="mb-4 flex items-center gap-2">
              <h2 className="font-heading text-lg font-semibold text-charcoal">
                {tAdmin(`manualPayment.actions.${manualAction}` as Parameters<typeof tAdmin>[0])}
              </h2>
              <AdminInfoPopover content={tAdmin("manualPayment.noteHelp")} />
            </div>
            {manualError && (
              <div className="mb-4 rounded-brand border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {manualError}
              </div>
            )}
            <label className="block text-sm font-semibold text-charcoal" htmlFor="manual-payment-note">
              {tAdmin("manualPayment.noteLabel")}
            </label>
            <textarea
              id="manual-payment-note"
              value={manualNote}
              onChange={(event) => setManualNote(event.target.value)}
              rows={4}
              className="mt-2 w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown"
              placeholder={tAdmin("manualPayment.notePlaceholder")}
            />
            <div className="mt-5 flex justify-end gap-3">
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  setManualAction(null);
                  setManualNote("");
                  setManualError(null);
                }}
              >
                {tAdmin("manualPayment.cancel")}
              </Button>
              <Button type="submit" isLoading={isManualSaving}>
                {tAdmin("manualPayment.confirm")}
              </Button>
            </div>
          </form>
        </div>
      )}

      {savedMessage && (
        <SaveConfirmation
          message={savedMessage}
          onDismiss={() => setSavedMessage(null)}
        />
      )}
    </div>
  );
}
