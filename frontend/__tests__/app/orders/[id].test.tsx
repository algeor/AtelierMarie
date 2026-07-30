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
  payment_method: "cod",
  payment_status: "cod_pending",
  items_total_cents: 7700,
  shipping_cents: 0,
  total_cents: 7700,
  customer_email: "alice@example.com",
  customer_name: "Alice",
  delivery_method: null,
  delivery_courier: null,
  delivery_details: null,
  notes: null,
  items: [
    { product_id: "p1", product_name: "Lavender Dreams", price_cents: 3200, quantity: 1 },
    { product_id: "p2", product_name: "Midnight Amber", price_cents: 4500, quantity: 1 },
  ],
  tracking_number: null,
  tracking_carrier: null,
  tracking_url: null,
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
    expect(screen.queryByText("Shipment")).not.toBeInTheDocument();
  });

  it("shows public Econt tracking and hides raw courier errors", async () => {
    mockedGetOrder.mockResolvedValueOnce({
      ...mockOrder,
      delivery_courier: "econt",
      tracking_number: "1234567890",
      tracking_carrier: "econt",
      tracking_url: "https://www.econt.com/services/track-shipment/1234567890",
      courier_provider: "econt",
      courier_shipment_number: "1234567890",
      courier_sync_status: "trace_failed",
      courier_last_error: "Authorization private-demo-key timeout",
    } as OrderResponse & { courier_last_error: string });

    renderWithIntl(<OrderDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Shipment")).toBeInTheDocument();
    });
    expect(screen.getByText("1234567890")).toBeInTheDocument();
    expect(screen.getByText("Tracking update pending")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Track with Econt" })).toHaveAttribute(
      "href",
      "https://www.econt.com/services/track-shipment/1234567890"
    );
    expect(screen.queryByText(/private-demo-key/)).not.toBeInTheDocument();
    expect(screen.queryByText(/timeout/)).not.toBeInTheDocument();
  });

  it("hides Econt tracking after label deletion", async () => {
    mockedGetOrder.mockResolvedValueOnce({
      ...mockOrder,
      delivery_courier: "econt",
      tracking_number: null,
      tracking_carrier: null,
      tracking_url: null,
      courier_provider: "econt",
      courier_order_id: "remote-order-1",
      courier_shipment_number: null,
      courier_sync_status: "label_deleted",
    } as OrderResponse);

    renderWithIntl(<OrderDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Order #a1b2c3d4")).toBeInTheDocument();
    });
    expect(screen.queryByText("Shipment")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Track with Econt" })).not.toBeInTheDocument();
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
