import type { OrderStatus } from "@/lib/types";

interface StatusTimelineProps {
  currentStatus: OrderStatus;
}

interface TimelineStep {
  label: string;
  status: "completed" | "current" | "future";
}

const STANDARD_STEPS: OrderStatus[] = [
  "pending",
  "confirmed",
  "shipped",
  "delivered",
];

const STEP_LABELS: Record<OrderStatus, string> = {
  pending: "Pending",
  confirmed: "Confirmed",
  shipped: "Shipped",
  delivered: "Delivered",
  cancelled: "Cancelled",
};

function getSteps(currentStatus: OrderStatus): TimelineStep[] {
  // Cancelled: show simplified "Pending → Cancelled" sequence
  if (currentStatus === "cancelled") {
    return [
      { label: "Pending", status: "completed" },
      { label: "Cancelled", status: "current" },
    ];
  }

  const currentIndex = STANDARD_STEPS.indexOf(currentStatus);

  return STANDARD_STEPS.map((step, index) => {
    if (index < currentIndex) {
      return { label: STEP_LABELS[step], status: "completed" };
    }
    if (index === currentIndex) {
      return { label: STEP_LABELS[step], status: "current" };
    }
    return { label: STEP_LABELS[step], status: "future" };
  });
}

export function StatusTimeline({ currentStatus }: StatusTimelineProps) {
  const steps = getSteps(currentStatus);

  return (
    <div className="flex flex-col gap-0" role="list" aria-label="Order status timeline">
      {steps.map((step, index) => (
        <div key={step.label} className="flex items-start gap-3" role="listitem">
          {/* Dot and connector line */}
          <div className="flex flex-col items-center">
            <div
              className={`h-3 w-3 rounded-full ${
                step.status === "future"
                  ? "border-2 border-gray-300 bg-white"
                  : step.label === "Cancelled"
                    ? "bg-red-500"
                    : "bg-muted-gold"
              }`}
            />
            {index < steps.length - 1 && (
              <div
                className={`h-8 w-0.5 ${
                  step.status === "future" ? "bg-gray-200" : "bg-muted-gold"
                }`}
              />
            )}
          </div>

          {/* Label */}
          <span
            className={`text-sm ${
              step.status === "future"
                ? "text-gray-400"
                : step.label === "Cancelled"
                  ? "font-medium text-red-700"
                  : "font-medium text-charcoal"
            }`}
          >
            {step.label}
          </span>
        </div>
      ))}
    </div>
  );
}
