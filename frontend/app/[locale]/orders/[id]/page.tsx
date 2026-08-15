"use client";

import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { getOrder } from "@/lib/api";
import { OrderStatusBadge } from "@/components/orders/OrderStatusBadge";
import { StatusTimeline } from "@/components/orders/StatusTimeline";
import { CourierTrackingSummary } from "@/components/orders/CourierTrackingSummary";
import { DeliveryDetails } from "@/components/checkout/DeliveryDetails";
import { Skeleton } from "@/components/ui/Skeleton";
import { formatPrice } from "@/lib/utils";
import type { OrderResponse, PaymentStatus } from "@/lib/types";

const BANK_IBAN = process.env.NEXT_PUBLIC_BANK_IBAN ?? "";
const BANK_BIC = process.env.NEXT_PUBLIC_BANK_BIC ?? "";
const BANK_NAME = process.env.NEXT_PUBLIC_BANK_NAME ?? "";

const PAYMENT_STATUS_COLORS: Record<PaymentStatus, string> = {
  pending: "bg-warning/10 text-warning",
  paid: "bg-success/10 text-success",
  cod_pending: "bg-secondary text-secondary-foreground",
  failed: "bg-error/10 text-error",
  review_required: "bg-warning/10 text-warning",
  refund_pending: "bg-accent-soft/40 text-accent",
  partially_refunded: "bg-accent-soft/40 text-accent",
  refunded: "bg-accent-soft/40 text-accent",
  dispute_open: "bg-error/10 text-error",
  dispute_won: "bg-success/10 text-success",
  dispute_lost: "bg-error/10 text-error",
};

type PageState = "loading" | "success" | "not_found";

export default function OrderDetailPage() {
  const t = useTranslations("orders");
  const tPayment = useTranslations("orders.payment");
  const locale = useLocale();
  const params = useParams();
  const searchParams = useSearchParams();
  const orderId = params.id as string;
  const paymentReturnToken =
    searchParams.get("payment_return_token") ?? searchParams.get("token");
  const [order, setOrder] = useState<OrderResponse | null>(null);
  const [state, setState] = useState<PageState>("loading");

  useEffect(() => {
    let cancelled = false;

    async function fetchOrder() {
      try {
        const data = await getOrder(orderId, paymentReturnToken);
        if (!cancelled) {
          setOrder(data);
          setState("success");
        }
      } catch {
        if (!cancelled) {
          setState("not_found");
        }
      }
    }

    fetchOrder();
    return () => {
      cancelled = true;
    };
  }, [orderId, paymentReturnToken]);

  if (state === "loading") {
    return (
      <main className="bg-page px-4 py-12 text-text">
        <div className="mx-auto max-w-3xl">
          <Skeleton className="mb-8 h-8 w-48" />
          <div className="editorial-soft-panel space-y-6 rounded-brand p-8">
            <div className="flex items-center gap-4">
              <Skeleton className="h-6 w-32" />
              <Skeleton className="h-6 w-20" />
            </div>
            <div className="space-y-3">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
            </div>
            <div className="space-y-4">
              <Skeleton className="h-3 w-3" />
              <Skeleton className="h-3 w-3" />
              <Skeleton className="h-3 w-3" />
              <Skeleton className="h-3 w-3" />
            </div>
          </div>
        </div>
      </main>
    );
  }

  if (state === "not_found") {
    return (
      <main className="bg-page px-4 py-12 text-text">
        <div className="mx-auto max-w-3xl">
          <div className="editorial-soft-panel rounded-brand p-8 text-center">
            <h1 className="mb-4 font-heading text-2xl text-text">
              {t("notFound")}
            </h1>
            <p className="mb-6 text-muted">{t("notFoundDescription")}</p>
            <Link
              href="/orders"
              className="inline-flex items-center justify-center rounded-brand bg-primary px-6 py-3 font-medium text-primary-foreground transition-colors duration-fast hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page"
            >
              {t("backToOrders")}
            </Link>
          </div>
        </div>
      </main>
    );
  }

  if (!order) return null;

  const date = new Date(order.created_at).toLocaleDateString(
    locale === "bg" ? "bg-BG" : "en-US",
    {
      year: "numeric",
      month: "long",
      day: "numeric",
    },
  );
  const paymentStatusMessage =
    order.payment_method === "card"
      ? order.payment_status === "paid"
        ? tPayment("returnPaid")
        : order.payment_status === "failed"
          ? tPayment("returnFailed")
          : tPayment("returnPending")
      : order.payment_method === "cod"
        ? tPayment("codConfirmation")
        : order.payment_method === "bank_transfer" &&
            order.payment_status === "pending"
          ? tPayment("bankInstructions")
          : null;

  return (
    <main className="bg-page px-4 py-12 text-text">
      <div className="mx-auto max-w-3xl">
        <Link
          href="/orders"
          className="mb-6 inline-block rounded-brand text-sm text-muted transition-colors duration-fast hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page"
        >
          {t("backToOrders")}
        </Link>

        <div className="editorial-soft-panel rounded-brand p-8">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
            <div>
              <h1 className="mb-1 font-heading text-2xl text-text">
                {t("orderNumber", { id: order.id.slice(0, 8) })}
              </h1>
              <p className="text-sm text-muted">{date}</p>
            </div>
            <OrderStatusBadge status={order.status} />
          </div>

          {order.fulfillment_status === "awaiting_production" && (
            <div className="mb-8 rounded-brand border border-warning/25 bg-warning/10 px-4 py-3 text-sm leading-6 text-warning">
              <p>{t("craftedLaterNotice")}</p>
              <p>{t("shipsWhenCompleteNotice")}</p>
            </div>
          )}

          {/* Status Timeline */}
          <div className="mb-8 border-b editorial-divider pb-8">
            <h2 className="mb-4 text-sm font-medium text-text">
              {t("progress")}
            </h2>
            <StatusTimeline
              currentStatus={order.status}
              trackingNumber={order.tracking_number}
              trackingCarrier={order.tracking_carrier}
              trackingUrl={order.tracking_url}
            />
          </div>

          {/* Items Table */}
          <div className="mb-8">
            <h2 className="mb-4 text-sm font-medium text-text">{t("items")}</h2>
            <div className="space-y-3">
              {order.items.map((item) => (
                <div
                  key={item.product_id}
                  className="flex items-center justify-between border-b editorial-divider py-2 last:border-0"
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium text-text">
                      {item.product_name}
                    </p>
                    <p className="text-sm text-muted">
                      {formatPrice(item.price_cents)} × {item.quantity}
                    </p>
                  </div>
                  <span className="ml-4 whitespace-nowrap font-medium text-text">
                    {formatPrice(item.price_cents * item.quantity)}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Total */}
          <div className="flex items-center justify-between border-t editorial-divider pt-4">
            <span className="font-medium text-text">{t("total")}</span>
            <span className="font-heading text-lg text-text">
              {formatPrice(order.total_cents)}
            </span>
          </div>

          {/* Customer Info */}
          <div className="mt-8 border-t editorial-divider pt-6">
            <h2 className="mb-2 text-sm font-medium text-text">
              {t("contact")}
            </h2>
            <p className="text-sm text-muted">{order.customer_email}</p>
          </div>

          {/* Payment status block */}
          <div className="mt-6 border-t editorial-divider pt-6">
            <h2 className="mb-3 text-sm font-medium text-text">
              {tPayment("sectionTitle")}
            </h2>
            <div className="flex flex-wrap items-center gap-3 mb-3">
              <span className="text-sm text-muted">
                {tPayment(
                  `method.${order.payment_method}` as Parameters<
                    typeof tPayment
                  >[0],
                )}
              </span>
              <span
                className={`inline-flex items-center rounded-pill px-2.5 py-0.5 text-xs font-medium ${PAYMENT_STATUS_COLORS[order.payment_status]}`}
              >
                {tPayment(
                  `status.${order.payment_status}` as Parameters<
                    typeof tPayment
                  >[0],
                )}
              </span>
            </div>
            {paymentStatusMessage && (
              <p className="mb-3 text-sm leading-6 text-muted">
                {paymentStatusMessage}
              </p>
            )}

            {/* Retry payment link for card orders with pending/failed payment */}
            {order.payment_method === "card" &&
              (order.payment_status === "pending" ||
                order.payment_status === "failed") &&
              paymentReturnToken && (
                <Link
                  href={`/orders/${order.id}/retry-payment?token=${encodeURIComponent(paymentReturnToken)}`}
                  className="inline-flex items-center text-sm font-medium text-accent underline underline-offset-2 transition-colors duration-fast hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                >
                  {tPayment("retryPayment")}
                </Link>
              )}

            {/* IBAN instructions for bank transfer orders awaiting payment */}
            {order.payment_method === "bank_transfer" &&
              order.payment_status === "pending" &&
              BANK_IBAN && (
                <div className="editorial-note-panel mt-3 space-y-1.5 rounded-brand p-4 text-sm">
                  <p className="mb-2 font-medium text-text">
                    {tPayment("bankInstructions")}
                  </p>
                  <p className="text-muted">
                    <span className="font-medium text-text">
                      {tPayment("bankName")}:
                    </span>{" "}
                    {BANK_NAME}
                  </p>
                  <p className="font-mono text-muted">
                    <span className="font-sans font-medium text-text">
                      {tPayment("bankIban")}:
                    </span>{" "}
                    {BANK_IBAN}
                  </p>
                  <p className="text-muted">
                    <span className="font-medium text-text">
                      {tPayment("bankBic")}:
                    </span>{" "}
                    {BANK_BIC}
                  </p>
                  <p className="text-muted">
                    <span className="font-medium text-text">
                      {tPayment("bankAmount")}:
                    </span>{" "}
                    {formatPrice(order.total_cents)}
                  </p>
                  <p className="text-muted">
                    <span className="font-medium text-text">
                      {tPayment("bankReference")}:
                    </span>{" "}
                    {order.id.slice(0, 8)}
                  </p>
                  <p className="mt-2 text-xs text-muted/70">
                    {tPayment("bankNote")}
                  </p>
                </div>
              )}
          </div>

          {/* Delivery details */}
          <CourierTrackingSummary order={order} />
          <DeliveryDetails order={order} />
        </div>
      </div>
    </main>
  );
}
