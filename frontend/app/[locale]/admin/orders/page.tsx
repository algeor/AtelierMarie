"use client";

import { useEffect, useState, useRef } from "react";
import { useLocale, useTranslations } from "next-intl";
import { getAdminOrders, updateOrderStatus } from "@/lib/api";
import { ApiError } from "@/lib/api-client";
import { useLocalizedError } from "@/lib/useLocalizedError";
import { cn, formatPrice } from "@/lib/utils";
import { Skeleton } from "@/components/ui/Skeleton";
import type { OrderResponse, OrderStatus } from "@/lib/types";

const STATUS_FILTERS: (OrderStatus | "")[] = [
  "",
  "pending",
  "confirmed",
  "shipped",
  "delivered",
  "cancelled",
];

const STATUS_COLORS: Record<OrderStatus, string> = {
  pending: "bg-amber-100 text-amber-800",
  confirmed: "bg-blue-100 text-blue-800",
  shipped: "bg-purple-100 text-purple-800",
  delivered: "bg-green-100 text-green-800",
  cancelled: "bg-red-100 text-red-800",
};

const VALID_TRANSITIONS: Record<OrderStatus, OrderStatus[]> = {
  pending: ["confirmed", "cancelled"],
  confirmed: ["shipped", "cancelled"],
  shipped: ["delivered"],
  delivered: [],
  cancelled: [],
};

function formatDate(iso: string, locale: string): string {
  return new Date(iso).toLocaleDateString(locale === "bg" ? "bg-BG" : "en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function maskEmail(email: string): string {
  const [local, domain] = email.split("@");
  if (!domain || !local) return email;
  const visible = local.slice(0, 1);
  return `${visible}***@${domain}`;
}

export default function AdminOrdersPage() {
  const t = useTranslations("admin");
  const tStatus = useTranslations("orders.status");
  const locale = useLocale();
  const getLocalizedError = useLocalizedError();
  const [orders, setOrders] = useState<OrderResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const isInitialLoad = useRef(true);

  useEffect(() => {
    async function loadOrders() {
      try {
        if (isInitialLoad.current) {
          setIsLoading(true);
        } else {
          setIsRefreshing(true);
        }
        setError(null);
        const data = await getAdminOrders(1, 100, statusFilter || undefined);
        setOrders(data.orders);
      } catch (err) {
        setError(err instanceof ApiError ? getLocalizedError(err.code) : t("errors.loadOrders"));
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
        isInitialLoad.current = false;
      }
    }
    loadOrders();
  }, [statusFilter, getLocalizedError, t]);

  async function handleStatusChange(order: OrderResponse, newStatus: OrderStatus) {
    const previousStatus = order.status;
    setUpdatingId(order.id);
    setError(null);

    // Optimistic update
    setOrders((prev) =>
      prev.map((o) =>
        o.id === order.id ? { ...o, status: newStatus } : o
      )
    );

    try {
      await updateOrderStatus(order.id, newStatus);
      // Remove order from view if it no longer matches the active filter
      if (statusFilter && newStatus !== statusFilter) {
        setOrders((prev) => prev.filter((o) => o.id !== order.id));
      }
    } catch (err) {
      // Rollback
      setOrders((prev) =>
        prev.map((o) =>
          o.id === order.id ? { ...o, status: previousStatus } : o
        )
      );
      setError(
        err instanceof ApiError ? getLocalizedError(err.code) : t("errors.updateOrderStatus")
      );
    } finally {
      setUpdatingId(null);
    }
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="font-heading text-2xl font-semibold text-charcoal">
          {t("orders")}
        </h1>
        <p className="mt-1 text-sm text-soft-brown">
          {t("manageOrders")}
        </p>
      </div>

      {/* Status Filter Pills */}
      <div className="mb-6 flex flex-wrap gap-2">
        {STATUS_FILTERS.map((filter) => (
          <button
            key={filter}
            onClick={() => setStatusFilter(filter)}
            className={cn(
              "rounded-pill px-4 py-1.5 text-sm font-medium transition-colors duration-fast",
              statusFilter === filter
                ? "bg-muted-gold text-charcoal"
                : "bg-champagne-beige/50 text-soft-brown hover:bg-champagne-beige"
            )}
            aria-pressed={statusFilter === filter}
          >
            {filter ? tStatus(filter) : t("all")}
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-6 rounded-brand border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Orders Table */}
      <div className="relative overflow-x-auto rounded-brand border border-champagne-beige bg-cream">
        {isRefreshing && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-cream/50">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-muted-gold border-t-transparent" />
          </div>
        )}
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-champagne-beige bg-champagne-beige/30">
              <th className="px-4 py-3 font-medium text-charcoal">{t("orderId")}</th>
              <th className="px-4 py-3 font-medium text-charcoal">{t("customer")}</th>
              <th className="px-4 py-3 font-medium text-charcoal">{t("total")}</th>
              <th className="px-4 py-3 font-medium text-charcoal">{t("status")}</th>
              <th className="px-4 py-3 font-medium text-charcoal">{t("date")}</th>
              <th className="px-4 py-3 font-medium text-charcoal">{t("actions")}</th>
            </tr>
          </thead>
          <tbody className={cn(isRefreshing && "opacity-50 pointer-events-none")}>
            {isLoading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <tr key={i} className="border-b border-champagne-beige/50">
                  <td className="px-4 py-3"><Skeleton className="h-4 w-20" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-32" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-16" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-5 w-20" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-24" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-8 w-28" /></td>
                </tr>
              ))
            ) : orders.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-soft-brown">
                  {t("noOrders")}
                </td>
              </tr>
            ) : (
              orders.map((order) => (
                <tr
                  key={order.id}
                  className="border-b border-champagne-beige/50 last:border-0"
                >
                  <td className="px-4 py-3 font-mono text-xs text-soft-brown">
                    {order.id.slice(0, 8)}…
                  </td>
                  <td className="px-4 py-3 text-charcoal">
                    <span title={order.customer_email}>
                      {maskEmail(order.customer_email)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-soft-brown">
                    {formatPrice(order.total_cents)}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        "inline-flex items-center rounded-pill px-2.5 py-0.5 text-xs font-medium capitalize",
                        STATUS_COLORS[order.status]
                      )}
                    >
                      {tStatus(order.status)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-soft-brown">
                    {formatDate(order.created_at, locale)}
                  </td>
                  <td className="px-4 py-3">
                    {VALID_TRANSITIONS[order.status].length > 0 ? (
                      <select
                        value=""
                        disabled={updatingId === order.id}
                        aria-label={t("updateStatusForOrder", { id: order.id.slice(0, 8) })}
                        onChange={(e) => {
                          if (e.target.value) {
                            handleStatusChange(
                              order,
                              e.target.value as OrderStatus
                            );
                          }
                        }}
                        className="h-8 rounded-brand border border-champagne-beige bg-cream px-2 text-xs text-soft-brown focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown disabled:opacity-50"
                      >
                        <option value="">{t("updateStatus")}</option>
                        {VALID_TRANSITIONS[order.status].map((s) => (
                          <option key={s} value={s}>
                            {tStatus(s)}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <span className="text-xs text-soft-brown/50">
                        {t("noActions")}
                      </span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
