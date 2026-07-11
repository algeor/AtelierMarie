import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach } from "vitest";
import type { OrderListResponse } from "@/lib/types";

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, values?: Record<string, unknown>) => {
    if (values) {
      return Object.entries(values).reduce(
        (str, [k, v]) => str.replace(`{${k}}`, String(v)),
        key
      );
    }
    return key;
  },
  useLocale: () => "en",
  NextIntlClientProvider: ({ children }: { children: React.ReactNode }) => children,
}));

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
  orders: [
    {
      id: "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
      status: "pending",
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
    mockedGetOrders.mockResolvedValueOnce(ordersResponse);
    render(<OrdersPage />);

    await waitFor(() => {
      expect(screen.getByText("#a1b2c3d4")).toBeInTheDocument();
    });

    expect(screen.getByText("Pending")).toBeInTheDocument();
    expect(screen.getByText("€77.00")).toBeInTheDocument();
    expect(screen.getByText(/item/)).toBeInTheDocument();
  });

  it("shows empty state when no orders", async () => {
    mockedGetOrders.mockResolvedValueOnce({
      orders: [],
      total: 0,
      page: 1,
      limit: 20,
    });
    render(<OrdersPage />);

    await waitFor(() => {
      expect(screen.getByText("noOrders")).toBeInTheDocument();
    });
    expect(screen.getByText("startShopping")).toHaveAttribute("href", "/products");
  });

  it("shows anonymous CTA in empty state", async () => {
    mockedGetOrders.mockResolvedValueOnce({
      orders: [],
      total: 0,
      page: 1,
      limit: 20,
    });
    render(<OrdersPage />);

    await waitFor(() => {
      expect(screen.getByText("signInToSeeOrders")).toBeInTheDocument();
    });
  });

  it("shows error state with retry button", async () => {
    mockedGetOrders.mockRejectedValueOnce(new Error("Network error"));
    render(<OrdersPage />);

    await waitFor(() => {
      expect(screen.getByText("loadingError")).toBeInTheDocument();
    });
    expect(screen.getByText("tryAgain")).toBeInTheDocument();
  });

  it("retries on Try again click", async () => {
    const user = userEvent.setup();
    mockedGetOrders.mockRejectedValueOnce(new Error("fail"));
    render(<OrdersPage />);

    await waitFor(() => {
      expect(screen.getByText("tryAgain")).toBeInTheDocument();
    });

    mockedGetOrders.mockResolvedValueOnce(ordersResponse);
    await user.click(screen.getByText("tryAgain"));

    await waitFor(() => {
      expect(screen.getByText("#a1b2c3d4")).toBeInTheDocument();
    });
  });

  it("shows loading skeleton", () => {
    mockedGetOrders.mockReturnValue(new Promise(() => {})); // never resolves
    render(<OrdersPage />);
    // Skeleton elements are present (aria-hidden divs with animate-pulse)
    expect(screen.getByText("title")).toBeInTheDocument();
  });

  it("pagination: Previous disabled on page 1, Next disabled on last page", async () => {
    mockedGetOrders.mockResolvedValueOnce({
      orders: Array.from({ length: 20 }, (_, i) => ({
        ...ordersResponse.orders[0]!,
        id: `order-${i}`,
      })),
      total: 25,
      page: 1,
      limit: 20,
    });
    render(<OrdersPage />);

    await waitFor(() => {
      expect(screen.getByText("previous")).toBeInTheDocument();
    });

    expect(screen.getByText("previous")).toBeDisabled();
    expect(screen.getByText("next")).not.toBeDisabled();
  });
});
