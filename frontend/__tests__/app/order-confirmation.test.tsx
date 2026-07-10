import { render, screen, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";

const mockRefreshCart = vi.fn();

vi.mock("@/contexts/CartContext", () => ({
  useCart: () => ({ refreshCart: mockRefreshCart }),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "test-order-123" }),
}));

vi.mock("@/lib/api", () => ({
  getOrder: vi.fn(),
}));

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

import { getOrder } from "@/lib/api";
import OrderConfirmationPage from "@/app/orders/[id]/confirmation/page";

const mockedGetOrder = vi.mocked(getOrder);

describe("Order Confirmation Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading skeleton initially", () => {
    mockedGetOrder.mockImplementation(() => new Promise(() => {})); // never resolves
    render(<OrderConfirmationPage />);
    // Skeleton elements are rendered during loading
    const skeletons = document.querySelectorAll('[class*="animate"]');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("shows order details after fetch", async () => {
    mockedGetOrder.mockResolvedValue({
      id: "test-order-123",
      status: "pending",
      total_cents: 5000,
      customer_email: "buyer@example.com",
      customer_name: "Test Buyer",
      shipping_address: "123 Main St",
      notes: null,
      items: [
        { product_id: "candle-1", product_name: "Rose Candle", price_cents: 2500, quantity: 2 },
      ],
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:00Z",
    });

    render(<OrderConfirmationPage />);

    await waitFor(() => {
      expect(screen.getByText(/thank you for your order/i)).toBeInTheDocument();
    });
    expect(screen.getByText("Rose Candle")).toBeInTheDocument();
    expect(screen.getByText(/buyer@example.com/)).toBeInTheDocument();
  });

  it("shows 'Order not found' on error", async () => {
    mockedGetOrder.mockRejectedValue(new Error("Not found"));

    render(<OrderConfirmationPage />);

    await waitFor(() => {
      expect(screen.getByText(/order not found/i)).toBeInTheDocument();
    });
  });

  it("calls refreshCart on mount", () => {
    mockedGetOrder.mockResolvedValue({
      id: "test-order-123",
      status: "pending",
      total_cents: 5000,
      customer_email: "buyer@example.com",
      customer_name: null,
      shipping_address: null,
      notes: null,
      items: [],
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:00Z",
    });

    render(<OrderConfirmationPage />);
    expect(mockRefreshCart).toHaveBeenCalled();
  });
});
