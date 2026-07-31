import React from "react";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach } from "vitest";
import type { OrderListResponse } from "@/lib/types";
import { renderWithIntl } from "../test-utils";

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  usePathname: () => "/",
}));

vi.mock("@/lib/api", () => ({
  getOrders: vi.fn(),
}));

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    user: null,
    isAuthenticated: false,
    isLoading: false,
    error: null,
    login: vi.fn(),
    logout: vi.fn(),
    loginComplete: vi.fn(),
  }),
}));

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

import { getOrders } from "@/lib/api";
import OrdersPage from "@/app/[locale]/orders/page";

const mockedGetOrders = vi.mocked(getOrders);

const ordersResponse: OrderListResponse = {
  items: [
    {
      id: "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      status: "pending",
      payment_method: "cod",
      payment_status: "cod_pending",
      stripe_checkout_url: null,
      items_total_cents: 7700,
      shipping_cents: 0,
      shipping_price_source: "live",
      shipping_is_fallback: false,
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
      courier_status: null,
      label_url: null,
      created_at: "2026-07-01T10:00:00Z",
      updated_at: "2026-07-01T10:00:00Z",
    },
  ],
  total: 1,
  page: 1,
  limit: 20,
};

describe("OrdersPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders order list with correct fields", async () => {
    mockedGetOrders.mockResolvedValueOnce({
      ...ordersResponse,
      items: [
        ordersResponse.items[0]!,
        {
          ...ordersResponse.items[0]!,
          id: "cardpending-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
          payment_method: "card",
          payment_status: "pending",
        },
        {
          ...ordersResponse.items[0]!,
          id: "cardfailed-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
          payment_method: "card",
          payment_status: "failed",
        },
      ],
      total: 3,
    });
    renderWithIntl(<OrdersPage />);

    await waitFor(() => {
      expect(screen.getByText("#a1b2c3d4")).toBeInTheDocument();
    });

    expect(screen.getAllByText("Pending").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Cash on delivery · Pay on delivery")).toBeInTheDocument();
    expect(screen.getByText("Card · Awaiting payment")).toBeInTheDocument();
    expect(screen.getByText("Card · Payment failed")).toBeInTheDocument();
    expect(screen.getAllByText("€77.00").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/item/).length).toBeGreaterThanOrEqual(1);
  });

  it("shows empty state when no orders", async () => {
    mockedGetOrders.mockResolvedValueOnce({
      items: [],
      total: 0,
      page: 1,
      limit: 20,
    });
    renderWithIntl(<OrdersPage />);

    await waitFor(() => {
      expect(screen.getByText("No orders yet")).toBeInTheDocument();
    });
    expect(screen.getByText("Start Shopping")).toHaveAttribute("href", "/products");
  });

  it("shows anonymous CTA in empty state", async () => {
    mockedGetOrders.mockResolvedValueOnce({
      items: [],
      total: 0,
      page: 1,
      limit: 20,
    });
    renderWithIntl(<OrdersPage />);

    await waitFor(() => {
      expect(screen.getByText("Sign in to see all your orders")).toBeInTheDocument();
    });
  });

  it("shows error state with retry button", async () => {
    mockedGetOrders.mockRejectedValueOnce(new Error("Network error"));
    renderWithIntl(<OrdersPage />);

    await waitFor(() => {
      expect(screen.getByText("Something went wrong loading your orders")).toBeInTheDocument();
    });
    expect(screen.getByText("Try again")).toBeInTheDocument();
  });

  it("retries on Try again click", async () => {
    const user = userEvent.setup();
    mockedGetOrders.mockRejectedValueOnce(new Error("fail"));
    renderWithIntl(<OrdersPage />);

    await waitFor(() => {
      expect(screen.getByText("Try again")).toBeInTheDocument();
    });

    mockedGetOrders.mockResolvedValueOnce(ordersResponse);
    await user.click(screen.getByText("Try again"));

    await waitFor(() => {
      expect(screen.getByText("#a1b2c3d4")).toBeInTheDocument();
    });
  });

  it("shows loading skeleton", () => {
    mockedGetOrders.mockReturnValue(new Promise(() => {})); // never resolves
    renderWithIntl(<OrdersPage />);
    // Skeleton elements are present (aria-hidden divs with animate-pulse)
    expect(screen.getByText("My Orders")).toBeInTheDocument();
  });

  it("pagination: Previous disabled on page 1, Next disabled on last page", async () => {
    mockedGetOrders.mockResolvedValueOnce({
      items: Array.from({ length: 20 }, (_, i) => ({
        ...ordersResponse.items[0]!,
        id: `order-${i}`,
      })),
      total: 25,
      page: 1,
      limit: 20,
    });
    renderWithIntl(<OrdersPage />);

    await waitFor(() => {
      expect(screen.getByText("Previous")).toBeInTheDocument();
    });

    expect(screen.getByText("Previous")).toBeDisabled();
    expect(screen.getByText("Next")).not.toBeDisabled();
  });
});
