import { screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { OrderStatusBadge } from "@/components/orders/OrderStatusBadge";
import type { OrderStatus } from "@/lib/types";
import { renderWithIntl } from "../../test-utils";

describe("OrderStatusBadge", () => {
  const statusCases: { status: OrderStatus; label: string; colorClass: string }[] = [
    { status: "pending", label: "Pending", colorClass: "bg-amber-100" },
    { status: "confirmed", label: "Confirmed", colorClass: "bg-blue-100" },
    { status: "shipped", label: "Shipped", colorClass: "bg-indigo-100" },
    { status: "delivered", label: "Delivered", colorClass: "bg-green-100" },
    { status: "cancelled", label: "Cancelled", colorClass: "bg-red-100" },
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
