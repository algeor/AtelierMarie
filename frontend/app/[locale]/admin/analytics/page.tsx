"use client";

import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import {
  getAdminAnalyticsCheckout,
  getAdminAnalyticsExportUrl,
  getAdminAnalyticsFunnel,
  getAdminAnalyticsProducts,
  getAdminAnalyticsSummary,
} from "@/lib/api";
import { formatPrice } from "@/lib/utils";
import type {
  AnalyticsFunnelResponse,
  AnalyticsSummaryResponse,
  CheckoutAnalyticsResponse,
  ProductAnalyticsResponse,
} from "@/lib/types";

function isoDate(daysAgo: number) {
  const date = new Date();
  date.setDate(date.getDate() - daysAgo);
  return date.toISOString().slice(0, 10);
}

export default function AdminAnalyticsPage() {
  const t = useTranslations("admin.analytics");
  const [startDate, setStartDate] = useState(() => isoDate(30));
  const [endDate, setEndDate] = useState(() => isoDate(0));
  const [summary, setSummary] = useState<AnalyticsSummaryResponse | null>(null);
  const [funnel, setFunnel] = useState<AnalyticsFunnelResponse | null>(null);
  const [products, setProducts] = useState<ProductAnalyticsResponse | null>(null);
  const [checkout, setCheckout] = useState<CheckoutAnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [summaryData, funnelData, productData, checkoutData] = await Promise.all([
          getAdminAnalyticsSummary(startDate, endDate),
          getAdminAnalyticsFunnel(startDate, endDate),
          getAdminAnalyticsProducts(startDate, endDate),
          getAdminAnalyticsCheckout(startDate, endDate),
        ]);
        if (!cancelled) {
          setSummary(summaryData);
          setFunnel(funnelData);
          setProducts(productData);
          setCheckout(checkoutData);
        }
      } catch {
        if (!cancelled) setError(t("error"));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [endDate, startDate, t]);

  const exportUrl = useMemo(
    () => getAdminAnalyticsExportUrl(startDate, endDate),
    [endDate, startDate]
  );

  const metricCards = summary
    ? [
        { label: t("metrics.sessions"), value: summary.consented_sessions.toLocaleString() },
        { label: t("metrics.events"), value: summary.accepted_events.toLocaleString() },
        { label: t("metrics.conversion"), value: `${summary.conversion_rate}%` },
        { label: t("metrics.orders"), value: summary.backend_order_count.toLocaleString() },
        { label: t("metrics.revenue"), value: formatPrice(summary.backend_revenue_cents) },
        { label: t("metrics.health"), value: summary.health.duckdb_load_status },
      ]
    : [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="flex items-center gap-2">
          <h1 className="font-heading text-3xl text-charcoal">{t("title")}</h1>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <label className="text-sm text-soft-brown">
            {t("startDate")}
            <input
              type="date"
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
              className="mt-1 block rounded-brand border border-champagne-beige bg-cream px-3 py-2 text-charcoal"
            />
          </label>
          <label className="text-sm text-soft-brown">
            {t("endDate")}
            <input
              type="date"
              value={endDate}
              onChange={(event) => setEndDate(event.target.value)}
              className="mt-1 block rounded-brand border border-champagne-beige bg-cream px-3 py-2 text-charcoal"
            />
          </label>
          <a
            href={exportUrl}
            download
            className="inline-flex min-h-10 items-center justify-center rounded-brand bg-charcoal px-4 py-2 text-sm font-semibold text-cream hover:bg-soft-brown"
          >
            {t("exportCsv")}
          </a>
        </div>
      </div>

      {error && <div className="rounded-brand border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}

      {loading ? (
        <div className="rounded-brand border border-champagne-beige bg-cream p-6 text-sm text-soft-brown">
          {t("loading")}
        </div>
      ) : (
        <>
          <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6" aria-label={t("summary")}>
            {metricCards.map((metric) => (
              <div key={metric.label} className="rounded-brand border border-champagne-beige bg-cream p-4">
                <p className="text-xs uppercase tracking-wide text-soft-brown">{metric.label}</p>
                <p className="mt-2 break-words font-heading text-2xl text-charcoal">{metric.value}</p>
              </div>
            ))}
          </section>

          {summary?.delivery_warning && (
            <div className="rounded-brand border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
              {t("coverageWarning", {
                consented: summary.consented_order_count,
                purchases: summary.analytics_purchase_count,
              })}
            </div>
          )}

          <section className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-brand border border-champagne-beige bg-cream p-5">
              <h2 className="font-heading text-xl text-charcoal">{t("coverageTitle")}</h2>
              <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-soft-brown">{t("businessTruth")}</dt>
                  <dd className="font-semibold text-charcoal">
                    {summary?.backend_order_count ?? 0} / {formatPrice(summary?.backend_revenue_cents ?? 0)}
                  </dd>
                </div>
                <div>
                  <dt className="text-soft-brown">{t("measuredCoverage")}</dt>
                  <dd className="font-semibold text-charcoal">
                    {summary?.analytics_purchase_count ?? 0} / {formatPrice(summary?.analytics_purchase_revenue_cents ?? 0)}
                  </dd>
                </div>
                <div>
                  <dt className="text-soft-brown">{t("coveragePercent")}</dt>
                  <dd className="font-semibold text-charcoal">{summary?.coverage_percent ?? 0}%</dd>
                </div>
                <div>
                  <dt className="text-soft-brown">{t("consentedDelta")}</dt>
                  <dd className="font-semibold text-charcoal">{summary?.consented_order_delta ?? 0}</dd>
                </div>
              </dl>
            </div>

            <div className="rounded-brand border border-champagne-beige bg-cream p-5">
              <h2 className="font-heading text-xl text-charcoal">{t("healthTitle")}</h2>
              <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                <div><dt className="text-soft-brown">{t("accepted")}</dt><dd className="font-semibold text-charcoal">{summary?.health.accepted ?? 0}</dd></div>
                <div><dt className="text-soft-brown">{t("rejected")}</dt><dd className="font-semibold text-charcoal">{summary?.health.rejected ?? 0}</dd></div>
                <div><dt className="text-soft-brown">{t("duplicates")}</dt><dd className="font-semibold text-charcoal">{summary?.health.duplicate ?? 0}</dd></div>
                <div><dt className="text-soft-brown">{t("validationFailures")}</dt><dd className="font-semibold text-charcoal">{summary?.health.validation_failure ?? 0}</dd></div>
              </dl>
            </div>
          </section>

          <section className="rounded-brand border border-champagne-beige bg-cream p-5">
            <h2 className="font-heading text-xl text-charcoal">{t("funnelTitle")}</h2>
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="text-soft-brown">
                  <tr><th className="py-2 pr-4">{t("step")}</th><th className="py-2 pr-4">{t("count")}</th><th className="py-2">{t("conversionFromPrevious")}</th></tr>
                </thead>
                <tbody className="divide-y divide-champagne-beige">
                  {(funnel?.steps ?? []).map((step) => (
                    <tr key={step.event_type}>
                      <td className="py-2 pr-4 font-medium text-charcoal">{t(`events.${step.event_type}`)}</td>
                      <td className="py-2 pr-4 text-charcoal">{step.count}</td>
                      <td className="py-2 text-charcoal">{step.conversion_from_previous}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="rounded-brand border border-champagne-beige bg-cream p-5">
            <h2 className="font-heading text-xl text-charcoal">{t("productsTitle")}</h2>
            {(products?.products.length ?? 0) === 0 ? (
              <p className="mt-3 text-sm text-soft-brown">{t("empty")}</p>
            ) : (
              <div className="mt-4 overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="text-soft-brown">
                    <tr><th className="py-2 pr-4">{t("product")}</th><th className="py-2 pr-4">{t("impressions")}</th><th className="py-2 pr-4">{t("clicks")}</th><th className="py-2 pr-4">{t("ctr")}</th><th className="py-2 pr-4">{t("views")}</th><th className="py-2 pr-4">{t("adds")}</th><th className="py-2 pr-4">{t("purchases")}</th><th className="py-2 pr-4">{t("revenue")}</th><th className="py-2">{t("conversion")}</th></tr>
                  </thead>
                  <tbody className="divide-y divide-champagne-beige">
                    {(products?.products ?? []).map((product) => (
                      <tr key={product.product_id}>
                        <td className="py-2 pr-4 font-medium text-charcoal">{product.product_name || product.product_id}</td>
                        <td className="py-2 pr-4 text-charcoal">{product.impressions}</td>
                        <td className="py-2 pr-4 text-charcoal">{product.clicks}</td>
                        <td className="py-2 pr-4 text-charcoal">{product.click_through_rate}%</td>
                        <td className="py-2 pr-4 text-charcoal">{product.views}</td>
                        <td className="py-2 pr-4 text-charcoal">{product.add_to_cart}</td>
                        <td className="py-2 pr-4 text-charcoal">{product.purchases}</td>
                        <td className="py-2 pr-4 text-charcoal">{formatPrice(product.revenue_cents)}</td>
                        <td className="py-2 text-charcoal">{product.conversion_rate}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="rounded-brand border border-champagne-beige bg-cream p-5">
            <h2 className="font-heading text-xl text-charcoal">{t("checkoutTitle")}</h2>
            <div className="mt-4 grid gap-4 md:grid-cols-3">
              <MetricList title={t("checkoutSteps")} data={{ checkout_start: checkout?.checkout_starts ?? 0, order_submit: checkout?.order_submits ?? 0, payment_redirect: checkout?.payment_redirects ?? 0, purchase_confirmed: checkout?.purchase_confirmed ?? 0 }} />
              <MetricList title={t("deliveryMethods")} data={checkout?.delivery_methods ?? {}} />
              <MetricList title={t("paymentMethods")} data={checkout?.payment_methods ?? {}} />
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function MetricList({ title, data }: { title: string; data: Record<string, number> }) {
  const entries = Object.entries(data);
  return (
    <div className="rounded-brand border border-champagne-beige/70 p-4">
      <h3 className="text-sm font-semibold text-charcoal">{title}</h3>
      <dl className="mt-3 space-y-2 text-sm">
        {entries.length === 0 ? (
          <div className="text-soft-brown">0</div>
        ) : (
          entries.map(([key, value]) => (
            <div key={key} className="flex items-center justify-between gap-3">
              <dt className="break-words text-soft-brown">{key}</dt>
              <dd className="font-semibold text-charcoal">{value}</dd>
            </div>
          ))
        )}
      </dl>
    </div>
  );
}
