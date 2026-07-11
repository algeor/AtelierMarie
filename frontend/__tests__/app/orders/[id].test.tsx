import React from "react";
import { screen, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import type { OrderResponse } from "@/lib/types";
import { renderWithIntl } from "../../test-utils";

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  usePathname: () => "/",
}));

vi.mock("@/lib/api", () => ({
  getOrder: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d" }),
}));

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

import { getOrder } from "@/lib/api";
import OrderDetailPage from "@/app/[locale]/orders/[id]/page";

const mockedGetOrder = vi.mocked(getOrder);

const mockOrder: OrderResponse = {
  id: "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
  status: "confirmed",
  total_cents: 7700,
  customer_email: "alice@example.com",
  customer_name: "Alice",
  shipping_address: null,
  notes: null,
  items: [
    { product_id: "p1", product_name: "Lavender Dreams", price_cents: 3200, quantity: 1 },
    { product_id: "p2", product_name: "Midnight Amber", price_cents: 4500, quantity: 1 },
  ],
  created_at: "2026-07-01T10:00:00Z",
  updated_at: "2026-07-01T10:00:00Z",
};

describe("OrderDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("displays order details", async () => {
    mockedGetOrder.mockResolvedValueOnce(mockOrder);
    renderWithIntl(<OrderDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Order #a1b2c3d4")).toBeInTheDocument();
    });

    expect(screen.getAllByText("Confirmed").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Lavender Dreams")).toBeInTheDocument();
    expect(screen.getByText("Midnight Amber")).toBeInTheDocument();
    expect(screen.getByText("€77.00")).toBeInTheDocument();
    expect(screen.getByText("alice@example.com")).toBeInTheDocument();
  });

  it("shows status timeline", async () => {
    mockedGetOrder.mockResolvedValueOnce(mockOrder);
    renderWithIntl(<OrderDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Pending")).toBeInTheDocument();
    });
    expect(screen.getAllByText("Confirmed").length).toBe(2); // badge + timeline
    expect(screen.getByText("Shipped")).toBeInTheDocument();
    expect(screen.getByText("Delivered")).toBeInTheDocument();
  });

  it("shows 'Order not found' on 404", async () => {
    mockedGetOrder.mockRejectedValueOnce(new Error("Not found"));
    renderWithIntl(<OrderDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Order not found")).toBeInTheDocument();
    });
    expect(screen.getByText("Back to Orders")).toHaveAttribute("href", "/orders");
  });

  it("shows loading skeleton", () => {
    mockedGetOrder.mockReturnValue(new Promise(() => {}));
    renderWithIntl(<OrderDetailPage />);

    // Skeleton elements visible (aria-hidden pulse divs)
    const skeletons = document.querySelectorAll("[aria-hidden='true']");
    expect(skeletons.length).toBeGreaterThan(0);
  });
});
