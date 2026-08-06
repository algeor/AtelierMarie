"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslations, useLocale } from "next-intl";
import { Link } from "@/i18n/navigation";
import { getOrders } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { OrderStatusBadge } from "@/components/orders/OrderStatusBadge";
import { Skeleton } from "@/components/ui/Skeleton";
import { formatPrice } from "@/lib/utils";
import type {
  CustomerOrderDateRange,
  CustomerOrderFilters,
  CustomerOrderSort,
  CustomerOrderView,
  OrderResponse,
  PaymentStatus,
} from "@/lib/types";

type PageState = "loading" | "success" | "error";

const DEFAULT_ORDER_FILTERS: Required<CustomerOrderFilters> = {
  q: "",
  view: "all",
  date_range: "all",
  sort: "newest",
};

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

export default function OrdersPage() {
  const t = useTranslations("orders");
  const tPayment = useTranslations("orders.payment");
  const tCommon = useTranslations("common");
  const tAuth = useTranslations("auth");
  const locale = useLocale();
  const { isAuthenticated } = useAuth();
  const [orders, setOrders] = useState<OrderResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<CustomerOrderFilters>(
    DEFAULT_ORDER_FILTERS,
  );
  const [state, setState] = useState<PageState>("loading");
  const limit = 20;

  const fetchOrders = useCallback(
    async (pageNum: number) => {
      setState((current) => (current === "success" ? "success" : "loading"));
      try {
        const data = await getOrders(pageNum, limit, filters);
        setOrders(data.items);
        setTotal(data.total);
        setPage(pageNum);
        setState("success");
      } catch {
        setState("error");
      }
    },
    [filters],
  );

  useEffect(() => {
    fetchOrders(1);
  }, [fetchOrders]);

  const totalPages = Math.max(1, Math.ceil(total / limit));
  const hasActiveFilters = useMemo(
    () =>
      Boolean(
        filters.q?.trim() ||
        (filters.view && filters.view !== "all") ||
        (filters.date_range && filters.date_range !== "all") ||
        (filters.sort && filters.sort !== "newest"),
      ),
    [filters],
  );

  function updateFilters(next: Partial<CustomerOrderFilters>) {
    setFilters((current) => ({ ...current, ...next }));
  }

  if (state === "loading") {
    return (
      <main className="bg-page px-4 py-12 text-text">
        <div className="mx-auto max-w-3xl">
          <h1 className="mb-8 font-heading text-4xl leading-tight text-text">
            {t("title")}
          </h1>
          <div className="space-y-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="editorial-paper-panel rounded-brand p-6">
                <div className="flex items-center justify-between">
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-32" />
                    <Skeleton className="h-4 w-24" />
                  </div>
                  <Skeleton className="h-6 w-20" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    );
  }

  if (state === "error") {
    return (
      <main className="bg-page px-4 py-12 text-text">
        <div className="mx-auto max-w-3xl">
          <h1 className="mb-8 font-heading text-4xl leading-tight text-text">
            {t("title")}
          </h1>
          <div className="editorial-soft-panel rounded-brand p-8 text-center">
            <p className="mb-4 text-muted">{t("loadingError")}</p>
            <button
              onClick={() => fetchOrders(page)}
              className="inline-flex items-center justify-center rounded-brand bg-primary px-6 py-3 font-medium text-primary-foreground transition-colors duration-fast hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page"
            >
              {tCommon("tryAgain")}
            </button>
          </div>
        </div>
      </main>
    );
  }

  if (orders.length === 0 && !hasActiveFilters) {
    return (
      <main className="bg-page px-4 py-12 text-text">
        <div className="mx-auto max-w-3xl">
          <h1 className="mb-8 font-heading text-4xl leading-tight text-text">
            {t("title")}
          </h1>
          <div className="editorial-soft-panel rounded-brand p-8 text-center">
            <p className="mb-2 font-medium text-text">{t("noOrders")}</p>
            <p className="mb-6 text-muted">{t("noOrdersDescription")}</p>
            <Link
              href="/products"
              className="inline-flex items-center justify-center rounded-brand bg-primary px-6 py-3 font-medium text-primary-foreground transition-colors duration-fast hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page"
            >
              {t("startShopping")}
            </Link>
            {!isAuthenticated && (
              <p className="mt-4 text-sm text-muted">
                {tAuth("signInToSeeOrders")}
              </p>
            )}
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="bg-page px-4 py-12 text-text">
      <div className="mx-auto max-w-3xl">
        <h1 className="mb-8 font-heading text-4xl leading-tight text-text">
          {t("title")}
        </h1>

        <section className="mb-8 border-y editorial-divider py-5">
          <div className="grid gap-5 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
            <div>
              <label
                htmlFor="order-search"
                className="mb-2 block text-xs font-medium uppercase text-muted"
              >
                {t("filters.searchLabel")}
              </label>
              <input
                id="order-search"
                type="search"
                value={filters.q ?? ""}
                onChange={(event) => updateFilters({ q: event.target.value })}
                placeholder={t("filters.searchPlaceholder")}
                className="h-11 w-full rounded-none border-0 border-b border-border/40 bg-transparent px-0 text-base text-text outline-none transition placeholder:text-muted/55 focus:border-focus focus:ring-0"
              />
            </div>

            <div className="flex items-center justify-between gap-4 text-sm text-muted sm:flex-col sm:items-end sm:justify-end sm:gap-1">
              <span>{t("filters.results", { count: total })}</span>
              {hasActiveFilters && (
                <button
                  type="button"
                  onClick={() => setFilters(DEFAULT_ORDER_FILTERS)}
                  className="font-medium text-text underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page"
                >
                  {t("filters.clear")}
                </button>
              )}
            </div>
          </div>

          <div
            className="mt-5 flex flex-wrap items-center gap-x-3 gap-y-2"
            aria-label={t("filters.viewLabel")}
          >
            {(
              [
                "all",
                "active",
                "needs_action",
                "delivered",
              ] as CustomerOrderView[]
            ).map((view) => (
              <button
                key={view}
                type="button"
                aria-pressed={(filters.view ?? "all") === view}
                onClick={() => updateFilters({ view })}
                className={`rounded-pill px-3.5 py-1.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page ${
                  (filters.view ?? "all") === view
                    ? "bg-text text-page shadow-sm shadow-text/10"
                    : "text-muted hover:bg-surface/55 hover:text-text"
                }`}
              >
                {t(`filters.views.${view}` as Parameters<typeof t>[0])}
              </button>
            ))}
          </div>

          <div className="mt-5 grid gap-4 border-t editorial-divider pt-4 sm:grid-cols-2">
            <div className="grid gap-2 sm:grid-cols-[auto_minmax(0,1fr)] sm:items-center sm:gap-4">
              <label
                htmlFor="order-date-range"
                className="text-xs font-medium uppercase text-muted"
              >
                {t("filters.dateLabel")}
              </label>
              <select
                id="order-date-range"
                value={filters.date_range ?? "all"}
                onChange={(event) =>
                  updateFilters({
                    date_range: event.target.value as CustomerOrderDateRange,
                  })
                }
                className="min-h-10 w-full rounded-none border-0 border-b border-border/35 bg-transparent px-0 py-2 text-sm font-medium text-text outline-none transition focus:border-focus focus:ring-0 sm:text-right"
              >
                <option value="all">{t("filters.dateRanges.all")}</option>
                <option value="last_30_days">
                  {t("filters.dateRanges.last_30_days")}
                </option>
                <option value="last_6_months">
                  {t("filters.dateRanges.last_6_months")}
                </option>
              </select>
            </div>

            <div className="grid gap-2 sm:grid-cols-[auto_minmax(0,1fr)] sm:items-center sm:gap-4">
              <label
                htmlFor="order-sort"
                className="text-xs font-medium uppercase text-muted"
              >
                {t("filters.sortLabel")}
              </label>
              <select
                id="order-sort"
                value={filters.sort ?? "newest"}
                onChange={(event) =>
                  updateFilters({
                    sort: event.target.value as CustomerOrderSort,
                  })
                }
                className="min-h-10 w-full rounded-none border-0 border-b border-border/35 bg-transparent px-0 py-2 text-sm font-medium text-text outline-none transition focus:border-focus focus:ring-0 sm:text-right"
              >
                <option value="newest">{t("filters.sorts.newest")}</option>
                <option value="oldest">{t("filters.sorts.oldest")}</option>
                <option value="highest">{t("filters.sorts.highest")}</option>
              </select>
            </div>
          </div>
        </section>

        {orders.length === 0 ? (
          <div className="editorial-soft-panel rounded-brand p-8 text-center">
            <p className="font-medium text-text">{t("filters.noMatch")}</p>
          </div>
        ) : (
          <div className="space-y-4">
            {orders.map((order) => {
              const itemCount = order.items.reduce(
                (sum, item) => sum + item.quantity,
                0,
              );
              const date = new Date(order.created_at).toLocaleDateString(
                locale === "bg" ? "bg-BG" : "en-US",
                { year: "numeric", month: "short", day: "numeric" },
              );

              return (
                <Link
                  key={order.id}
                  href={`/orders/${order.id}`}
                  className="editorial-paper-panel block rounded-brand p-6 transition-colors duration-fast hover:border-muted/45 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page"
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="min-w-0">
                      <div className="flex items-center gap-3 mb-1">
                        <span className="font-mono text-sm text-muted">
                          #{order.id.slice(0, 8)}
                        </span>
                        <OrderStatusBadge status={order.status} />
                      </div>
                      <p className="text-sm text-muted">
                        {date} · {t("item", { count: itemCount })}
                      </p>
                      <p className="mt-2">
                        <span
                          className={`inline-flex items-center rounded-pill px-2.5 py-0.5 text-xs font-medium ${PAYMENT_STATUS_COLORS[order.payment_status]}`}
                        >
                          {tPayment(
                            `method.${order.payment_method}` as Parameters<
                              typeof tPayment
                            >[0],
                          )}
                          {" · "}
                          {tPayment(
                            `status.${order.payment_status}` as Parameters<
                              typeof tPayment
                            >[0],
                          )}
                        </span>
                      </p>
                    </div>
                    <span className="whitespace-nowrap font-medium text-text">
                      {formatPrice(order.total_cents)}
                    </span>
                  </div>
                </Link>
              );
            })}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="mt-8 flex items-center justify-center gap-4">
            <button
              onClick={() => fetchOrders(page - 1)}
              disabled={page <= 1}
              className="rounded-brand border border-border px-4 py-2 text-sm font-medium text-text transition-colors duration-fast hover:bg-surface disabled:cursor-not-allowed disabled:opacity-50"
            >
              {tCommon("previous")}
            </button>
            <span className="text-sm text-muted">
              {tCommon("page", { current: page, total: totalPages })}
            </span>
            <button
              onClick={() => fetchOrders(page + 1)}
              disabled={page >= totalPages}
              className="rounded-brand border border-border px-4 py-2 text-sm font-medium text-text transition-colors duration-fast hover:bg-surface disabled:cursor-not-allowed disabled:opacity-50"
            >
              {tCommon("next")}
            </button>
          </div>
        )}
      </div>
    </main>
  );
}
