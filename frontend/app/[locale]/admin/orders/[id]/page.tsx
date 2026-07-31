"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { getAdminOrder } from "@/lib/api";
import { ApiError } from "@/lib/api-client";
import { useLocalizedError } from "@/lib/useLocalizedError";
import { formatPrice } from "@/lib/utils";
import { DeliveryDetails } from "@/components/checkout/DeliveryDetails";
import { OrderStatusBadge } from "@/components/orders/OrderStatusBadge";
import { StatusTimeline } from "@/components/orders/StatusTimeline";
import { Skeleton } from "@/components/ui/Skeleton";
import type { OrderResponse } from "@/lib/types";

type PageState = "loading" | "success" | "not_found" | "error";
type AdminOrderResponse = OrderResponse & {
  tracking_number?: string | null;
  tracking_carrier?: string | null;
  tracking_url?: string | null;
};

function formatDateTime(iso: string, locale: string): string {
  return new Date(iso).toLocaleString(locale === "bg" ? "bg-BG" : "en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export default function AdminOrderDetailPage() {
  const tAdmin = useTranslations("admin");
  const tOrders = useTranslations("orders");
  const locale = useLocale();
  const params = useParams();
  const orderId = params.id as string;
  const getLocalizedError = useLocalizedError();
  const [order, setOrder] = useState<AdminOrderResponse | null>(null);
  const [state, setState] = useState<PageState>("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchOrder() {
      try {
        setState("loading");
        setError(null);
        const data = (await getAdminOrder(orderId)) as AdminOrderResponse;
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

        <DeliveryDetails order={order} />

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
    </div>
  );
}
