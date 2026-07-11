"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { getOrder } from "@/lib/api";
import { OrderStatusBadge } from "@/components/orders/OrderStatusBadge";
import { StatusTimeline } from "@/components/orders/StatusTimeline";
import { Skeleton } from "@/components/ui/Skeleton";
import { formatPrice } from "@/lib/utils";
import type { OrderResponse } from "@/lib/types";

type PageState = "loading" | "success" | "not_found";

export default function OrderDetailPage() {
  const t = useTranslations("orders");
  const locale = useLocale();
  const params = useParams();
  const orderId = params.id as string;
  const [order, setOrder] = useState<OrderResponse | null>(null);
  const [state, setState] = useState<PageState>("loading");

  useEffect(() => {
    let cancelled = false;

    async function fetchOrder() {
      try {
        const data = await getOrder(orderId);
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
  }, [orderId]);

  if (state === "loading") {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12">
        <Skeleton className="h-8 w-48 mb-8" />
        <div className="bg-white rounded-brand p-8 shadow-sm border border-champagne-beige space-y-6">
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
    );
  }

  if (state === "not_found") {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12">
        <div className="bg-white rounded-brand p-8 shadow-sm border border-champagne-beige text-center">
          <h1 className="font-heading text-2xl text-charcoal mb-4">
            {t("notFound")}
          </h1>
          <p className="text-soft-brown mb-6">
            {t("notFoundDescription")}
          </p>
          <Link
            href="/orders"
            className="inline-flex items-center justify-center px-6 py-3 bg-charcoal text-warm-ivory font-medium rounded-brand hover:bg-soft-brown transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2"
          >
            {t("backToOrders")}
          </Link>
        </div>
      </div>
    );
  }

  if (!order) return null;

  const date = new Date(order.created_at).toLocaleDateString(locale === "bg" ? "bg-BG" : "en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <Link
        href="/orders"
        className="text-soft-brown hover:text-charcoal text-sm mb-6 inline-block transition-colors duration-fast"
      >
        {t("backToOrders")}
      </Link>

      <div className="bg-white rounded-brand p-8 shadow-sm border border-champagne-beige">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <div>
            <h1 className="font-heading text-2xl text-charcoal mb-1">
              {t("orderNumber", { id: order.id.slice(0, 8) })}
            </h1>
            <p className="text-sm text-soft-brown">{date}</p>
          </div>
          <OrderStatusBadge status={order.status} />
        </div>

        {/* Status Timeline */}
        <div className="mb-8 pb-8 border-b border-champagne-beige">
          <h2 className="text-sm font-medium text-charcoal mb-4">
            {t("progress")}
          </h2>
          <StatusTimeline currentStatus={order.status} />
        </div>

        {/* Items Table */}
        <div className="mb-8">
          <h2 className="text-sm font-medium text-charcoal mb-4">{t("items")}</h2>
          <div className="space-y-3">
            {order.items.map((item) => (
              <div
                key={item.product_id}
                className="flex items-center justify-between py-2 border-b border-champagne-beige last:border-0"
              >
                <div className="min-w-0">
                  <p className="text-charcoal font-medium truncate">
                    {item.product_name}
                  </p>
                  <p className="text-sm text-soft-brown">
                    {formatPrice(item.price_cents)} × {item.quantity}
                  </p>
                </div>
                <span className="text-charcoal font-medium whitespace-nowrap ml-4">
                  {formatPrice(item.price_cents * item.quantity)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Total */}
        <div className="flex items-center justify-between pt-4 border-t border-champagne-beige">
          <span className="text-charcoal font-medium">{t("total")}</span>
          <span className="text-lg font-heading text-charcoal">
            {formatPrice(order.total_cents)}
          </span>
        </div>

        {/* Customer Info */}
        <div className="mt-8 pt-6 border-t border-champagne-beige">
          <h2 className="text-sm font-medium text-charcoal mb-2">
            {t("contact")}
          </h2>
          <p className="text-sm text-soft-brown">{order.customer_email}</p>
        </div>
      </div>
    </div>
  );
}
