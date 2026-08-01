"use client";

import { type FormEvent, type ReactNode, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import {
  cancelSpeedyShipment,
  createSpeedyWaybill,
  getSpeedyAdminOverview,
  getSpeedyPickupTerms,
  getSpeedyShipmentInfo,
  refreshSpeedyTracking,
  requestSpeedyPickup,
  searchSpeedyShipments,
} from "@/lib/api";
import { ApiError } from "@/lib/api-client";
import { useLocalizedError } from "@/lib/useLocalizedError";
import { cn, formatPrice } from "@/lib/utils";
import { Skeleton } from "@/components/ui/Skeleton";
import type {
  SpeedyAdminOverviewResponse,
  SpeedyEventResponse,
  SpeedyOrderSummary,
} from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function formatDate(value: string | null | undefined): string {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

function statusTone(status: string): string {
  if (["healthy", "success", "created", "existing", "shipped"].includes(status)) {
    return "border-green-200 bg-green-50 text-green-800";
  }
  if (["warning", "blocked", "cancelled", "shipment_cancelled"].includes(status)) {
    return "border-amber-200 bg-amber-50 text-amber-800";
  }
  if (["failed", "unavailable"].includes(status)) {
    return "border-red-200 bg-red-50 text-red-700";
  }
  return "border-champagne-beige bg-warm-ivory text-soft-brown";
}

export default function AdminSpeedyPage() {
  const t = useTranslations("admin.speedy");
  const getLocalizedError = useLocalizedError();
  const searchParams = useSearchParams();
  const focusedOrderId = searchParams.get("order_id");
  const [overview, setOverview] = useState<SpeedyAdminOverviewResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [actionKey, setActionKey] = useState<string | null>(null);
  const [searchRef, setSearchRef] = useState(focusedOrderId ?? "");
  const [searchResult, setSearchResult] = useState<string[] | null>(null);
  const [infoShipmentId, setInfoShipmentId] = useState("");
  const [shipmentInfo, setShipmentInfo] = useState<Record<string, unknown>[] | null>(null);
  const [selectedShipments, setSelectedShipments] = useState<string[]>([]);
  const [cutoffs, setCutoffs] = useState<string[]>([]);
  const [pickupDateTime, setPickupDateTime] = useState("");
  const [visitEndTime, setVisitEndTime] = useState("");
  const [contactName, setContactName] = useState("");
  const [phone, setPhone] = useState("");
  const [pickupOrders, setPickupOrders] = useState<Record<string, unknown>[] | null>(null);

  async function loadOverview(background = false) {
    try {
      if (background) setIsRefreshing(true);
      else setIsLoading(true);
      setError(null);
      setOverview(await getSpeedyAdminOverview(focusedOrderId));
    } catch (err) {
      setError(err instanceof ApiError ? getLocalizedError(err.code) : t("loadError"));
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }

  useEffect(() => {
    loadOverview();
  }, [focusedOrderId]);

  const shippedShipments = useMemo(() => {
    return overview?.queues.shipped
      .map((order) => order.tracking_number)
      .filter((value): value is string => Boolean(value)) ?? [];
  }, [overview]);

  async function runAction(label: string, action: () => Promise<unknown>, successKey = "generic") {
    setActionKey(label);
    setError(null);
    setSuccess(null);
    try {
      await action();
      setSuccess(t(`success.${successKey}` as Parameters<typeof t>[0]));
      await loadOverview(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("actionError"));
    } finally {
      setActionKey(null);
    }
  }

  function toggleShipment(shipment: string) {
    setSelectedShipments((current) =>
      current.includes(shipment)
        ? current.filter((item) => item !== shipment)
        : [...current, shipment],
    );
  }

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await runAction("search", async () => {
      const result = await searchSpeedyShipments({ reference: searchRef, include_returns: true });
      setSearchResult(result.barcodes);
    }, "search");
  }

  async function handleInfo(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await runAction("info", async () => {
      const result = await getSpeedyShipmentInfo({ shipment_ids: [infoShipmentId] });
      setShipmentInfo(result.shipments);
    }, "info");
  }

  async function handlePickupTerms() {
    await runAction("pickupTerms", async () => {
      const result = await getSpeedyPickupTerms({ shipment_ids: selectedShipments });
      setCutoffs(result.cutoffs);
      if (!pickupDateTime && result.cutoffs[0]) setPickupDateTime(result.cutoffs[0]);
    }, "pickupTerms");
  }

  async function handlePickupRequest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await runAction("pickup", async () => {
      const result = await requestSpeedyPickup({
        shipment_ids: selectedShipments,
        pickup_datetime: pickupDateTime,
        visit_end_time: visitEndTime,
        contact_name: contactName,
        phone,
      });
      setPickupOrders(result.orders);
    }, "pickup");
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-52" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!overview) return null;

  return (
    <div className="max-w-7xl space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="font-heading text-2xl font-semibold text-charcoal">{t("title")}</h1>
          <p className="mt-1 text-sm text-soft-brown">{t("subtitle")}</p>
        </div>
        <button
          type="button"
          onClick={() => loadOverview(true)}
          disabled={isRefreshing}
          className="h-10 rounded-brand border border-champagne-beige bg-cream px-4 text-sm font-medium text-charcoal hover:bg-champagne-beige/40 disabled:opacity-50"
        >
          {isRefreshing ? t("refreshing") : t("refresh")}
        </button>
      </div>

      {(error || success) && (
        <div
          className={cn(
            "rounded-brand border p-4 text-sm",
            success ? "border-green-200 bg-green-50 text-green-800" : "border-red-200 bg-red-50 text-red-700",
          )}
          role="status"
        >
          {success ?? error}
        </div>
      )}

      <section className="rounded-brand border border-champagne-beige bg-cream p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h2 className="text-sm font-semibold uppercase text-soft-brown">{t("health.title")}</h2>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span className={cn("rounded-pill border px-3 py-1 text-xs font-semibold", statusTone(overview.health.status))}>
                {t(`health.status.${overview.health.status}` as Parameters<typeof t>[0])}
              </span>
              <span className="text-sm text-charcoal">{overview.health.message}</span>
            </div>
          </div>
          <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:min-w-[34rem]">
            <HealthItem label={t("health.username")} value={overview.health.username_configured ? t("yes") : t("no")} />
            <HealthItem label={t("health.password")} value={overview.health.password_configured ? t("yes") : t("no")} />
            <HealthItem label={t("health.configuredClient")} value={overview.health.configured_client_id ?? "-"} />
            <HealthItem label={t("health.verifiedClient")} value={overview.health.verified_client_id ?? "-"} />
            <HealthItem label={t("health.circuit")} value={overview.health.circuit.state} />
            <HealthItem label={t("health.lastCheck")} value={formatDate(overview.health.checked_at)} />
          </dl>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-4">
        <Metric label={t("metrics.successes")} value={overview.metrics.recent_successes} />
        <Metric label={t("metrics.failures")} value={overview.metrics.recent_failures} />
        <Metric label={t("metrics.cancellations")} value={overview.metrics.cancellation_count} />
        <Metric label={t("metrics.pickups")} value={overview.metrics.pickup_request_count} />
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <OrderQueue
          title={t("queues.ready")}
          orders={overview.queues.ready_to_ship}
          empty={t("queues.emptyReady")}
          actionKey={actionKey}
          actions={(order) => (
            <button
              type="button"
              disabled={actionKey === `ship:${order.order_id}`}
              onClick={() => runAction(`ship:${order.order_id}`, () => createSpeedyWaybill(order.order_id), "createWaybill")}
              className="rounded-brand bg-charcoal px-3 py-1.5 text-xs font-medium text-warm-ivory disabled:opacity-50"
            >
              {t("actions.createWaybill")}
            </button>
          )}
        />
        <OrderQueue
          title={t("queues.shipped")}
          orders={overview.queues.shipped}
          empty={t("queues.emptyShipped")}
          actionKey={actionKey}
          selectable
          selectedShipments={selectedShipments}
          onToggleShipment={toggleShipment}
          actions={(order) => (
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => window.open(`${API_BASE_URL}/v1/admin/speedy/orders/${order.order_id}/label`, "_blank", "noopener")}
                className="rounded-brand border border-champagne-beige px-3 py-1.5 text-xs font-medium text-charcoal hover:bg-champagne-beige/40"
              >
                {t("actions.print")}
              </button>
              <button
                type="button"
                disabled={actionKey === `track:${order.order_id}`}
                onClick={() => runAction(`track:${order.order_id}`, () => refreshSpeedyTracking(order.order_id), "track")}
                className="rounded-brand border border-champagne-beige px-3 py-1.5 text-xs font-medium text-charcoal hover:bg-champagne-beige/40 disabled:opacity-50"
              >
                {t("actions.track")}
              </button>
              <button
                type="button"
                disabled={actionKey === `cancel:${order.order_id}` || order.courier_sync_status === "shipment_cancelled"}
                onClick={() => runAction(`cancel:${order.order_id}`, () => cancelSpeedyShipment(order.order_id, { comment: "Cancelled from admin" }), "cancel")}
                className="rounded-brand border border-red-200 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
              >
                {t("actions.cancel")}
              </button>
            </div>
          )}
        />
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <div className="rounded-brand border border-champagne-beige bg-cream p-5">
          <h2 className="text-sm font-semibold uppercase text-soft-brown">{t("lookup.title")}</h2>
          <form onSubmit={handleSearch} className="mt-4 flex gap-2">
            <input
              value={searchRef}
              onChange={(event) => setSearchRef(event.target.value)}
              className="min-w-0 flex-1 rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm text-charcoal"
              placeholder={t("lookup.reference")}
            />
            <button type="submit" className="rounded-brand bg-charcoal px-4 py-2 text-sm font-medium text-warm-ivory">
              {t("actions.search")}
            </button>
          </form>
          {searchResult && <ResultList label={t("lookup.matches")} values={searchResult} />}

          <form onSubmit={handleInfo} className="mt-5 flex gap-2">
            <input
              value={infoShipmentId}
              onChange={(event) => setInfoShipmentId(event.target.value)}
              className="min-w-0 flex-1 rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm text-charcoal"
              placeholder={t("lookup.shipmentId")}
            />
            <button type="submit" className="rounded-brand border border-champagne-beige px-4 py-2 text-sm font-medium text-charcoal">
              {t("actions.info")}
            </button>
          </form>
          {shipmentInfo && (
            <pre className="mt-4 max-h-56 overflow-auto rounded-brand bg-warm-ivory p-3 text-xs text-charcoal">
              {JSON.stringify(shipmentInfo, null, 2)}
            </pre>
          )}
        </div>

        <div className="rounded-brand border border-champagne-beige bg-cream p-5">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <h2 className="text-sm font-semibold uppercase text-soft-brown">{t("pickup.title")}</h2>
            <span className="text-xs text-soft-brown">{t("pickup.selected", { count: selectedShipments.length })}</span>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setSelectedShipments(shippedShipments)}
              className="rounded-brand border border-champagne-beige px-3 py-1.5 text-xs text-charcoal"
            >
              {t("pickup.selectAll")}
            </button>
            <button
              type="button"
              onClick={handlePickupTerms}
              disabled={selectedShipments.length === 0 || actionKey === "pickupTerms"}
              className="rounded-brand border border-champagne-beige px-3 py-1.5 text-xs text-charcoal disabled:opacity-50"
            >
              {t("pickup.getTerms")}
            </button>
          </div>
          {cutoffs.length > 0 && <ResultList label={t("pickup.cutoffs")} values={cutoffs} />}
          <form onSubmit={handlePickupRequest} className="mt-5 grid gap-3 sm:grid-cols-2">
            <Input label={t("pickup.pickupDateTime")} value={pickupDateTime} onChange={setPickupDateTime} />
            <Input label={t("pickup.visitEndTime")} value={visitEndTime} onChange={setVisitEndTime} />
            <Input label={t("pickup.contactName")} value={contactName} onChange={setContactName} />
            <Input label={t("pickup.phone")} value={phone} onChange={setPhone} />
            <button
              type="submit"
              disabled={selectedShipments.length === 0 || actionKey === "pickup"}
              className="rounded-brand bg-charcoal px-4 py-2 text-sm font-medium text-warm-ivory disabled:opacity-50 sm:col-span-2"
            >
              {t("pickup.request")}
            </button>
          </form>
          {pickupOrders && (
            <pre className="mt-4 max-h-40 overflow-auto rounded-brand bg-warm-ivory p-3 text-xs text-charcoal">
              {JSON.stringify(pickupOrders, null, 2)}
            </pre>
          )}
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
        <div className="rounded-brand border border-champagne-beige bg-cream p-5">
          <h2 className="text-sm font-semibold uppercase text-soft-brown">{t("offices.title")}</h2>
          <dl className="mt-4 space-y-2 text-sm">
            <HealthItem label={t("offices.status")} value={overview.office_refresh.status ?? "-"} />
            <HealthItem label={t("offices.records")} value={overview.office_refresh.records?.toString() ?? "-"} />
            <HealthItem label={t("offices.refreshedAt")} value={formatDate(overview.office_refresh.refreshed_at)} />
            {overview.office_refresh.error && <HealthItem label={t("offices.error")} value={overview.office_refresh.error} />}
          </dl>
        </div>
        <div className="rounded-brand border border-champagne-beige bg-cream p-5">
          <h2 className="text-sm font-semibold uppercase text-soft-brown">{t("events.title")}</h2>
          <div className="mt-4 space-y-3">
            {overview.events.length === 0 ? (
              <p className="text-sm text-soft-brown">{t("events.empty")}</p>
            ) : (
              overview.events.map((event) => <EventRow key={event.id} event={event} />)
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

function HealthItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2">
      <dt className="text-soft-brown">{label}</dt>
      <dd className="text-right font-medium text-charcoal">{value}</dd>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-brand border border-champagne-beige bg-cream p-4">
      <p className="text-xs font-semibold uppercase text-soft-brown">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-charcoal">{value}</p>
    </div>
  );
}

function OrderQueue({
  title,
  orders,
  empty,
  actions,
  selectable = false,
  selectedShipments = [],
  onToggleShipment,
}: {
  title: string;
  orders: SpeedyOrderSummary[];
  empty: string;
  actionKey: string | null;
  actions: (order: SpeedyOrderSummary) => ReactNode;
  selectable?: boolean;
  selectedShipments?: string[];
  onToggleShipment?: (shipment: string) => void;
}) {
  return (
    <div className="rounded-brand border border-champagne-beige bg-cream p-5">
      <h2 className="text-sm font-semibold uppercase text-soft-brown">{title}</h2>
      <div className="mt-4 overflow-x-auto">
        {orders.length === 0 ? (
          <p className="py-8 text-center text-sm text-soft-brown">{empty}</p>
        ) : (
          <table className="w-full min-w-[42rem] text-left text-sm">
            <thead>
              <tr className="border-b border-champagne-beige text-xs uppercase text-soft-brown">
                {selectable && <th className="w-10 py-2" />}
                <th className="py-2">Order</th>
                <th className="py-2">Customer</th>
                <th className="py-2">Shipment</th>
                <th className="py-2">Status</th>
                <th className="py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.order_id} className="border-b border-champagne-beige/60 last:border-0">
                  {selectable && (
                    <td className="py-3">
                      {order.tracking_number && (
                        <input
                          type="checkbox"
                          checked={selectedShipments.includes(order.tracking_number)}
                          onChange={() => onToggleShipment?.(order.tracking_number!)}
                          className="h-4 w-4 rounded border-champagne-beige text-charcoal"
                        />
                      )}
                    </td>
                  )}
                  <td className="py-3">
                    <Link href={`/admin/orders/${order.order_id}`} className="font-mono text-xs text-charcoal hover:underline">
                      {order.order_number ?? `${order.order_id.slice(0, 8)}...`}
                    </Link>
                    <p className="mt-1 max-w-48 truncate text-xs text-soft-brown">{order.delivery_label}</p>
                  </td>
                  <td className="py-3 text-soft-brown">{order.customer_email}</td>
                  <td className="py-3 font-mono text-xs text-charcoal">{order.tracking_number ?? "-"}</td>
                  <td className="py-3">
                    <span className={cn("rounded-pill border px-2 py-0.5 text-xs", statusTone(order.courier_sync_status ?? order.status))}>
                      {order.courier_sync_status ?? order.status}
                    </span>
                  </td>
                  <td className="py-3 text-right">{actions(order)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function ResultList({ label, values }: { label: string; values: string[] }) {
  return (
    <div className="mt-4 rounded-brand border border-champagne-beige bg-warm-ivory p-3">
      <p className="text-xs font-semibold uppercase text-soft-brown">{label}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {values.map((value) => (
          <span key={value} className="rounded-pill bg-cream px-2.5 py-1 font-mono text-xs text-charcoal">
            {value}
          </span>
        ))}
      </div>
    </div>
  );
}

function Input({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block text-sm">
      <span className="font-medium text-charcoal">{label}</span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm text-charcoal"
      />
    </label>
  );
}

function EventRow({ event }: { event: SpeedyEventResponse }) {
  const category = typeof event.error?.category === "string" ? event.error.category : null;
  return (
    <div className="rounded-brand border border-champagne-beige bg-warm-ivory px-4 py-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-charcoal">{event.action.replaceAll("_", " ")}</p>
          <p className="mt-1 font-mono text-xs text-soft-brown">{event.order_id}</p>
        </div>
        <span className={cn("rounded-pill border px-2.5 py-0.5 text-xs font-medium", statusTone(event.status))}>
          {event.status}
        </span>
      </div>
      <p className="mt-2 text-xs text-soft-brown">{formatDate(event.created_at)}</p>
      {category && <p className="mt-2 text-xs text-red-700">{category}</p>}
    </div>
  );
}
