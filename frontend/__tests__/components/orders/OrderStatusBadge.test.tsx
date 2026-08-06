import { screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { OrderStatusBadge } from "@/components/orders/OrderStatusBadge";
import type { OrderStatus } from "@/lib/types";
import { renderWithIntl } from "../../test-utils";

describe("OrderStatusBadge", () => {
  const statusCases: { status: OrderStatus; label: string; colorClass: string }[] = [
    { status: "pending", label: "Pending", colorClass: "bg-warning/10" },
    { status: "confirmed", label: "Confirmed", colorClass: "bg-accent-soft/40" },
    { status: "shipped", label: "Shipped", colorClass: "bg-primary/15" },
    { status: "delivered", label: "Delivered", colorClass: "bg-success/10" },
    { status: "cancelled", label: "Cancelled", colorClass: "bg-error/10" },
  ];

  statusCases.forEach(({ status, label, colorClass }) => {
    it(`renders "${label}" with correct color for status "${status}"`, () => {
      renderWithIntl(<OrderStatusBadge status={status} />);
      const badge = screen.getByText(label);
      expect(badge).toBeInTheDocument();
      expect(badge.className).toContain(colorClass);
    });
  });
});
