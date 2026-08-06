"use client";

import { useTranslations } from "next-intl";
import { buildTrackingUrl } from "@/lib/tracking";
import type { OrderResponse } from "@/lib/types";

interface CourierTrackingSummaryProps {
  order: Pick<
    OrderResponse,
    | "delivery_courier"
    | "tracking_number"
    | "tracking_carrier"
    | "tracking_url"
    | "courier_provider"
    | "courier_shipment_number"
    | "courier_sync_status"
  >;
}

const PUBLIC_STATUS_KEYS: Record<string, "labelCreated" | "traceSynced" | "pending"> = {
  label_created: "labelCreated",
  trace_synced: "traceSynced",
  synced: "traceSynced",
  sync_failed: "pending",
  create_awb_failed: "pending",
  trace_failed: "pending",
};

export function CourierTrackingSummary({ order }: CourierTrackingSummaryProps) {
  const t = useTranslations("orders.tracking");
  const isEcont =
    order.courier_provider === "econt" ||
    order.tracking_carrier === "econt" ||
    order.delivery_courier === "econt";
  const shipmentNumber =
    order.courier_shipment_number ??
    (order.tracking_carrier === "econt" ? order.tracking_number : null);

  if (!isEcont || !shipmentNumber) return null;

  const trackingUrl = order.tracking_url ?? buildTrackingUrl("econt", shipmentNumber);
  const statusKey = order.courier_sync_status
    ? PUBLIC_STATUS_KEYS[order.courier_sync_status] ?? "pending"
    : "labelCreated";

  return (
    <section className="mt-8 border-t border-border/60 pt-6">
      <h2 className="mb-3 text-sm font-medium text-text">{t("sectionTitle")}</h2>
      <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-2 text-sm">
        <dt className="text-muted">{t("shipmentNumber")}</dt>
        <dd className="font-mono text-text">{shipmentNumber}</dd>

        <dt className="text-muted">{t("statusLabel")}</dt>
        <dd className="text-text">{t(`status.${statusKey}`)}</dd>
      </dl>
      {trackingUrl && (
        <a
          href={trackingUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-3 inline-flex text-sm font-medium text-accent underline underline-offset-2 transition-colors duration-fast hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
        >
          {t("trackLink")}
        </a>
      )}
    </section>
  );
}
