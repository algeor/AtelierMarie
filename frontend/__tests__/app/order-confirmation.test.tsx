import React from "react";
import { screen, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { renderWithIntl } from "../test-utils";

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

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  usePathname: () => "/",
}));

import { getOrder } from "@/lib/api";
import OrderConfirmationPage from "@/app/[locale]/orders/[id]/confirmation/page";

const mockedGetOrder = vi.mocked(getOrder);

describe("Order Confirmation Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading skeleton initially", () => {
    mockedGetOrder.mockImplementation(() => new Promise(() => {})); // never resolves
    renderWithIntl(<OrderConfirmationPage />);
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

    renderWithIntl(<OrderConfirmationPage />);

    await waitFor(() => {
      expect(screen.getByText(/thank you for your order/i)).toBeInTheDocument();
    });
    expect(screen.getByText("Rose Candle")).toBeInTheDocument();
    expect(screen.getByText(/buyer@example.com/)).toBeInTheDocument();
  });

  it("shows 'Order not found' on error", async () => {
    mockedGetOrder.mockRejectedValue(new Error("Not found"));

    renderWithIntl(<OrderConfirmationPage />);

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

    renderWithIntl(<OrderConfirmationPage />);
    expect(mockRefreshCart).toHaveBeenCalled();
  });
});
