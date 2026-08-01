"use client";

import { useTranslations } from "next-intl";
import { carrierLabel } from "@/lib/tracking";
import type { OrderStatus } from "@/lib/types";

const STEPS: OrderStatus[] = [
  "pending",
  "confirmed",
  "shipped",
  "delivered",
];

const STATUS_INDEX: Record<OrderStatus, number> = {
  pending: 0,
  confirmed: 1,
  shipped: 2,
  delivered: 3,
  return_in_transit: 3,
  returned: 3,
  cancelled: -1,
};

interface StatusTimelineProps {
  currentStatus: OrderStatus;
  trackingNumber?: string | null;
  trackingCarrier?: string | null;
  trackingUrl?: string | null;
}

export function StatusTimeline({
  currentStatus,
  trackingNumber,
  trackingCarrier,
  trackingUrl,
}: StatusTimelineProps) {
  const t = useTranslations("orders.status");
  const tTracking = useTranslations("orders");

  // For cancelled orders, show simplified timeline
  if (currentStatus === "cancelled") {
    return (
      <div className="space-y-4">
        <TimelineStep label={t("pending")} isCompleted isCurrent={false} />
        <TimelineStep label={t("cancelled")} isCompleted isCurrent isCancelled />
      </div>
    );
  }

  const currentIndex = STATUS_INDEX[currentStatus];
  const hasTracking = Boolean(trackingNumber);

  return (
    <div className="space-y-4">
      {STEPS.map((status, index) => (
        <div key={status}>
          <TimelineStep
            label={t(status)}
            isCompleted={index <= currentIndex}
            isCurrent={index === currentIndex}
          />
          {status === "shipped" && index <= currentIndex && hasTracking && (
            <div className="ml-6 mt-2 space-y-1 text-sm text-soft-brown">
              {trackingCarrier && (
                <p>
                  <span className="font-medium text-charcoal">
                    {tTracking("carrier")}:
                  </span>{" "}
                  {carrierLabel(trackingCarrier)}
                </p>
              )}
              <p>
                <span className="font-medium text-charcoal">
                  {tTracking("trackingNumber")}:
                </span>{" "}
                <span className="font-mono">{trackingNumber}</span>
              </p>
              {trackingUrl && (
                <a
                  href={trackingUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-block text-muted-gold underline underline-offset-2 hover:text-charcoal transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown"
                >
                  {tTracking("trackPackage")}
                </a>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function TimelineStep({
  label,
  isCompleted,
  isCurrent,
  isCancelled = false,
}: {
  label: string;
  isCompleted: boolean;
  isCurrent: boolean;
  isCancelled?: boolean;
}) {
  return (
    <div className="flex items-center gap-3">
      <div
        className={`w-3 h-3 rounded-full flex-shrink-0 ${
          isCancelled
            ? "bg-red-500"
            : isCompleted
              ? "bg-green-500"
              : "bg-gray-200"
        }`}
      />
      <span
        className={`text-sm ${
          isCancelled
            ? "text-red-700 font-medium"
            : isCurrent
              ? "text-charcoal font-medium"
              : isCompleted
                ? "text-charcoal"
                : "text-gray-400"
        }`}
      >
        {label}
      </span>
    </div>
  );
}
