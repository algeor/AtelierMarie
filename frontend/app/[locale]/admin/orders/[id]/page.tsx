"use client";

import { type FormEvent, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { applyManualPaymentAction, getAdminOrder } from "@/lib/api";
import { ApiError } from "@/lib/api-client";
import { useLocalizedError } from "@/lib/useLocalizedError";
import { cn, formatPrice } from "@/lib/utils";
import { DeliveryDetails } from "@/components/checkout/DeliveryDetails";
import { EcontFulfillmentPanel } from "@/components/admin/EcontFulfillmentPanel";
import { OrderStatusBadge } from "@/components/orders/OrderStatusBadge";
import { StatusTimeline } from "@/components/orders/StatusTimeline";
import { Skeleton } from "@/components/ui/Skeleton";
import { Button } from "@/components/ui/Button";
import { SaveConfirmation } from "@/components/admin/SaveConfirmation";
import type {
  AdminOrderDetailResponse,
  ManualPaymentAction,
  PaymentEventResponse,
  PaymentStatus,
} from "@/lib/types";

type PageState = "loading" | "success" | "not_found" | "error";

const PAYMENT_STATUS_COLORS: Record<PaymentStatus, string> = {
  pending: "bg-amber-100 text-amber-800",
  paid: "bg-green-100 text-green-800",
  cod_pending: "bg-gray-100 text-gray-700",
  failed: "bg-red-100 text-red-800",
  refunded: "bg-blue-100 text-blue-800",
};

const PAYMENT_ACTIONS: ManualPaymentAction[] = [
  "mark_paid",
  "mark_collected",
  "mark_refunded",
  "mark_failed",
  "mark_review",
  "cancel",
];

function formatDateTime(iso: string, locale: string): string {
  return new Date(iso).toLocaleString(locale === "bg" ? "bg-BG" : "en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function formatEventName(event: PaymentEventResponse): string {
  const base = event.event_type || event.stripe_event_type || event.source;
  return base.replaceAll("_", " ").replaceAll(".", " ");
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
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function fetchOrder() {
      try {
        setState("loading");
        setError(null);
        const data = await getAdminOrder(orderId);
        if (!cancelled) {
          setOrder(data);
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
    setSaved(false);
    try {
      await applyManualPaymentAction(order.id, manualAction, note);
      const refreshed = await getAdminOrder(order.id);
      setOrder(refreshed);
      setManualAction(null);
      setManualNote("");
      setSaved(true);
    } catch (err) {
      setManualError(
        err instanceof ApiError ? err.message : tAdmin("manualPayment.actionError")
      );
    } finally {
      setIsManualSaving(false);
    }
  }

  async function refreshOrder() {
    const refreshed = await getAdminOrder(orderId);
    setOrder(refreshed);
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
            <div>
              <h2 className="text-sm font-medium text-charcoal">
                {tAdmin("manualPayment.title")}
              </h2>
              <p className="mt-1 text-sm text-soft-brown">
                {tAdmin("manualPayment.subtitle")}
              </p>
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

        <DeliveryDetails order={order} />

        <EcontFulfillmentPanel order={order} onRefreshOrder={refreshOrder} />

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
            <div className="mb-4">
              <h2 className="font-heading text-lg font-semibold text-charcoal">
                {tAdmin(`manualPayment.actions.${manualAction}` as Parameters<typeof tAdmin>[0])}
              </h2>
              <p className="mt-1 text-sm text-soft-brown">
                {tAdmin("manualPayment.noteHelp")}
              </p>
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

      {saved && (
        <SaveConfirmation
          message={tAdmin("manualPayment.saved")}
          onDismiss={() => setSaved(false)}
        />
      )}
    </div>
  );
}
