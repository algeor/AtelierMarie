"use client";

import { useTranslations } from "next-intl";
import { Badge } from "@/components/ui/Badge";
import type { OrderStatus } from "@/lib/types";

const STATUS_STYLES: Record<OrderStatus, string> = {
  pending: "bg-warning/10 text-warning",
  confirmed: "bg-accent-soft/40 text-accent",
  shipped: "bg-primary/15 text-primary-foreground",
  delivered: "bg-success/10 text-success",
  return_in_transit: "bg-warning/10 text-warning",
  returned: "bg-secondary text-secondary-foreground",
  cancelled: "bg-error/10 text-error",
};

interface OrderStatusBadgeProps {
  status: OrderStatus;
}

export function OrderStatusBadge({ status }: OrderStatusBadgeProps) {
  const t = useTranslations("orders.status");

  return (
    <Badge className={STATUS_STYLES[status]}>
      {t(status)}
    </Badge>
  );
}
