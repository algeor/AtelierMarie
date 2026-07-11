"use client";

import { useTranslations } from "next-intl";
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
  cancelled: -1,
};

interface StatusTimelineProps {
  currentStatus: OrderStatus;
}

export function StatusTimeline({ currentStatus }: StatusTimelineProps) {
  const t = useTranslations("orders.status");

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

  return (
    <div className="space-y-4">
      {STEPS.map((status, index) => (
        <TimelineStep
          key={status}
          label={t(status)}
          isCompleted={index <= currentIndex}
          isCurrent={index === currentIndex}
        />
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
