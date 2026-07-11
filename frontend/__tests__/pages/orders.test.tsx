import { render, screen, waitFor, act } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import type { OrderListResponse } from "@/lib/types";

vi.mock("@/lib/api", () => ({
  getOrders: vi.fn(),
}));

let mockIsAuthenticated = true;

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    user: mockIsAuthenticated ? { id: "user-001", email: "test@example.com", name: "Test", avatar_url: null, is_admin: false } : null,
    isLoading: false,
    isAuthenticated: mockIsAuthenticated,
    error: null,
    login: vi.fn(),
    logout: vi.fn(),
    loginComplete: vi.fn(),
  }),
}));

import { getOrders } from "@/lib/api";
import OrdersPage from "@/app/orders/page";

const mockedGetOrders = vi.mocked(getOrders);

const mockOrdersResponse: OrderListResponse = {
  orders: [
    {
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
    },
  ],
  total: 1,
  page: 1,
  limit: 20,
};

describe("OrdersPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsAuthenticated = true;
  });

  it("renders loading skeleton initially", () => {
    mockedGetOrders.mockReturnValue(new Promise(() => {})); // never resolves
    render(<OrdersPage />);
    // Skeleton elements are aria-hidden, check for animated elements
    const skeletons = document.querySelectorAll("[aria-hidden='true']");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("renders order list with correct fields", async () => {
    mockedGetOrders.mockResolvedValueOnce(mockOrdersResponse);
    render(<OrdersPage />);

    await waitFor(() => {
      expect(screen.getByText("My Orders")).toBeInTheDocument();
    });

    // Date
    expect(screen.getByText("Jul 1, 2026")).toBeInTheDocument();
    // Truncated ID
    expect(screen.getByText("#a1b2c3d4")).toBeInTheDocument();
    // Status badge
    expect(screen.getByText("Confirmed")).toBeInTheDocument();
    // Item count
    expect(screen.getByText("3 items")).toBeInTheDocument();
    // Total price
    expect(screen.getByText("€77.00")).toBeInTheDocument();
  });

  it("handles empty state with anonymous CTA", async () => {
    mockIsAuthenticated = false;
    render(<OrdersPage />);

    await waitFor(() => {
      expect(screen.getByText("No orders yet")).toBeInTheDocument();
    });
    expect(screen.getByText("Sign in to see all your orders")).toBeInTheDocument();
    expect(screen.getByText("Start Shopping")).toBeInTheDocument();
  });

  it("handles error state with retry button", async () => {
    mockedGetOrders.mockRejectedValueOnce(new Error("fail"));
    render(<OrdersPage />);

    await waitFor(() => {
      expect(
        screen.getByText("Something went wrong loading your orders")
      ).toBeInTheDocument();
    });

    mockedGetOrders.mockResolvedValueOnce(mockOrdersResponse);

    await act(async () => {
      screen.getByText("Try again").click();
    });

    await waitFor(() => {
      expect(screen.getByText("#a1b2c3d4")).toBeInTheDocument();
    });
  });

  it("pagination controls disable at boundaries", async () => {
    mockedGetOrders.mockResolvedValueOnce({
      ...mockOrdersResponse,
      total: 40,
    });
    render(<OrdersPage />);

    await waitFor(() => {
      expect(screen.getByText("Page 1 of 2")).toBeInTheDocument();
    });

    const prevButton = screen.getByText("Previous");
    const nextButton = screen.getByText("Next");

    expect(prevButton).toBeDisabled();
    expect(nextButton).not.toBeDisabled();
  });
});
