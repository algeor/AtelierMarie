import type { OrderStatus } from "@/lib/types";

const STEPS: { status: OrderStatus; label: string }[] = [
  { status: "pending", label: "Pending" },
  { status: "confirmed", label: "Confirmed" },
  { status: "shipped", label: "Shipped" },
  { status: "delivered", label: "Delivered" },
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
  // For cancelled orders, show simplified timeline
  if (currentStatus === "cancelled") {
    return (
      <div className="space-y-4">
        <TimelineStep label="Pending" isCompleted isCurrent={false} />
        <TimelineStep label="Cancelled" isCompleted isCurrent isCancelled />
      </div>
    );
  }

  const currentIndex = STATUS_INDEX[currentStatus];

  return (
    <div className="space-y-4">
      {STEPS.map((step, index) => (
        <TimelineStep
          key={step.status}
          label={step.label}
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
