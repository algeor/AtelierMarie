import { render, screen, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import type { OrderResponse } from "@/lib/types";

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d" }),
}));

vi.mock("@/lib/api", () => ({
  getOrder: vi.fn(),
}));

vi.mock("@/lib/api-client", () => ({
  ApiError: class ApiError extends Error {
    code: string;
    details: null;
    constructor(response: { error: { code: string; message: string; details: null } }) {
      super(response.error.message);
      this.name = "ApiError";
      this.code = response.error.code;
      this.details = null;
    }
  },
}));

import { getOrder } from "@/lib/api";
import { ApiError } from "@/lib/api-client";
import OrderDetailPage from "@/app/orders/[id]/page";

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
    { product_id: "lavender-dreams-300ml", product_name: "Lavender Dreams", price_cents: 3200, quantity: 2 },
    { product_id: "midnight-amber-300ml", product_name: "Midnight Amber", price_cents: 4500, quantity: 1 },
  ],
  created_at: "2026-07-01T10:00:00Z",
  updated_at: "2026-07-01T10:00:00Z",
};

describe("OrderDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading skeleton initially", () => {
    mockedGetOrder.mockReturnValue(new Promise(() => {}));
    render(<OrderDetailPage />);
    const skeletons = document.querySelectorAll("[aria-hidden='true']");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("displays order details", async () => {
    mockedGetOrder.mockResolvedValueOnce(mockOrder);
    render(<OrderDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Order #a1b2c3d4")).toBeInTheDocument();
    });

    // Status badge
    expect(screen.getByText("Confirmed")).toBeInTheDocument();
    // Date
    expect(screen.getByText("July 1, 2026")).toBeInTheDocument();
    // Items
    expect(screen.getByText("Lavender Dreams")).toBeInTheDocument();
    expect(screen.getByText("Midnight Amber")).toBeInTheDocument();
    // Total
    expect(screen.getByText("€77.00")).toBeInTheDocument();
    // Customer email
    expect(screen.getByText("Contact: alice@example.com")).toBeInTheDocument();
  });

  it("shows timeline", async () => {
    mockedGetOrder.mockResolvedValueOnce(mockOrder);
    render(<OrderDetailPage />);

    await waitFor(() => {
      expect(screen.getByRole("list", { name: /order status timeline/i })).toBeInTheDocument();
    });
  });

  it("handles 404 - shows Order not found", async () => {
    mockedGetOrder.mockRejectedValueOnce(
      new ApiError({ error: { code: "NOT_FOUND", message: "Order not found", details: null } })
    );
    render(<OrderDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Order not found")).toBeInTheDocument();
    });
    expect(screen.getByText("Back to Orders")).toBeInTheDocument();
  });
});
