import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { OrderStatusBadge } from "@/components/orders/OrderStatusBadge";
import type { OrderStatus } from "@/lib/types";

describe("OrderStatusBadge", () => {
  const cases: Array<{ status: OrderStatus; label: string; colorClass: string }> = [
    { status: "pending", label: "Pending", colorClass: "bg-amber-100 text-amber-800" },
    { status: "confirmed", label: "Confirmed", colorClass: "bg-blue-100 text-blue-800" },
    { status: "shipped", label: "Shipped", colorClass: "bg-indigo-100 text-indigo-800" },
    { status: "delivered", label: "Delivered", colorClass: "bg-green-100 text-green-800" },
    { status: "cancelled", label: "Cancelled", colorClass: "bg-red-100 text-red-800" },
  ];

  cases.forEach(({ status, label, colorClass }) => {
    it(`renders "${label}" with correct colors for status "${status}"`, () => {
      render(<OrderStatusBadge status={status} />);
      const badge = screen.getByText(label);
      expect(badge).toBeInTheDocument();
      colorClass.split(" ").forEach((cls) => {
        expect(badge.className).toContain(cls);
      });
    });
  });
});
