import React from "react";
import { screen, waitFor, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { renderWithIntl } from "../../test-utils";

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  usePathname: () => "/",
}));

const mockPush = vi.fn();
const mockReplace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
  usePathname: () => "/admin/orders",
  useParams: () => ({}),
}));

vi.mock("@/lib/api", () => ({
  getCurrentUser: vi.fn(),
  getAdminOrders: vi.fn(),
  updateOrderStatus: vi.fn(),
}));

import { getCurrentUser, getAdminOrders, updateOrderStatus } from "@/lib/api";
import type { OrderListResponse, OrderResponse, UserResponse } from "@/lib/types";

const mockedGetCurrentUser = vi.mocked(getCurrentUser);
const mockedGetAdminOrders = vi.mocked(getAdminOrders);
const mockedUpdateOrderStatus = vi.mocked(updateOrderStatus);

const ADMIN_USER: UserResponse = {
  id: "user-001",
  email: "marie@ateliermarie.com",
  name: "Marie",
  avatar_url: null,
  is_admin: true,
};

const MOCK_ORDERS: OrderResponse[] = [
  {
    id: "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
    status: "pending",
    total_cents: 7700,
    customer_email: "alice@example.com",
    customer_name: "Alice Johnson",
    shipping_address: "123 Main St, Paris, FR",
    notes: null,
    items: [
      { product_id: "lavender-dreams-300ml", product_name: "Lavender Dreams", price_cents: 3200, quantity: 1 },
    ],
    created_at: "2026-07-11T10:00:00Z",
    updated_at: "2026-07-11T10:00:00Z",
  },
  {
    id: "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e",
    status: "confirmed",
    total_cents: 5600,
    customer_email: "bob@example.com",
    customer_name: "Bob Smith",
    shipping_address: "456 Oak Ave, Lyon, FR",
    notes: null,
    items: [
      { product_id: "citrus-garden-200ml", product_name: "Citrus Garden", price_cents: 2800, quantity: 2 },
    ],
    created_at: "2026-07-10T11:00:00Z",
    updated_at: "2026-07-10T11:00:00Z",
  },
];

const MOCK_ORDER_LIST: OrderListResponse = {
  orders: MOCK_ORDERS,
  total: 2,
  page: 1,
  limit: 100,
};

describe("Admin Orders List", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedGetCurrentUser.mockResolvedValue(ADMIN_USER);
  });

  it("renders order table with data", async () => {
    mockedGetAdminOrders.mockResolvedValue(MOCK_ORDER_LIST);

    const { AdminProvider } = await import("@/contexts/AdminContext");
    const { AdminGuard } = await import("@/components/admin/AdminGuard");
    const AdminOrdersPage = (await import("@/app/[locale]/admin/orders/page")).default;

    renderWithIntl(
      <AdminProvider>
        <AdminGuard>
          <AdminOrdersPage />
        </AdminGuard>
      </AdminProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("a***@example.com")).toBeInTheDocument();
      expect(screen.getByText("b***@example.com")).toBeInTheDocument();
    });

    expect(screen.getByText("€77.00")).toBeInTheDocument();
    expect(screen.getByText("€56.00")).toBeInTheDocument();
    expect(screen.getAllByText("Pending").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Confirmed").length).toBeGreaterThan(0);
  });

  it("shows status filter pills", async () => {
    mockedGetAdminOrders.mockResolvedValue(MOCK_ORDER_LIST);

    const { AdminProvider } = await import("@/contexts/AdminContext");
    const { AdminGuard } = await import("@/components/admin/AdminGuard");
    const AdminOrdersPage = (await import("@/app/[locale]/admin/orders/page")).default;

    renderWithIntl(
      <AdminProvider>
        <AdminGuard>
          <AdminOrdersPage />
        </AdminGuard>
      </AdminProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Orders")).toBeInTheDocument();
    });

    // Check filter pill buttons by aria-pressed attribute
    const allButton = screen.getByRole("button", { name: "All" });
    const pendingButton = screen.getByRole("button", { name: "Pending" });
    const shippedButton = screen.getByRole("button", { name: "Shipped" });
    const deliveredButton = screen.getByRole("button", { name: "Delivered" });
    const cancelledButton = screen.getByRole("button", { name: "Cancelled" });

    expect(allButton).toHaveAttribute("aria-pressed", "true");
    expect(pendingButton).toHaveAttribute("aria-pressed", "false");
    expect(shippedButton).toHaveAttribute("aria-pressed", "false");
    expect(deliveredButton).toHaveAttribute("aria-pressed", "false");
    expect(cancelledButton).toHaveAttribute("aria-pressed", "false");
  });

  it("filters orders by status when pill clicked", async () => {
    mockedGetAdminOrders.mockResolvedValue(MOCK_ORDER_LIST);

    const { AdminProvider } = await import("@/contexts/AdminContext");
    const { AdminGuard } = await import("@/components/admin/AdminGuard");
    const AdminOrdersPage = (await import("@/app/[locale]/admin/orders/page")).default;

    renderWithIntl(
      <AdminProvider>
        <AdminGuard>
          <AdminOrdersPage />
        </AdminGuard>
      </AdminProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("a***@example.com")).toBeInTheDocument();
    });

    const pendingPill = screen.getByRole("button", { name: "Pending" });
    fireEvent.click(pendingPill);

    await waitFor(() => {
      expect(mockedGetAdminOrders).toHaveBeenCalledWith(1, 100, "pending");
    });
  });

  it("updates order status via dropdown", async () => {
    mockedGetAdminOrders.mockResolvedValue(MOCK_ORDER_LIST);
    mockedUpdateOrderStatus.mockResolvedValue({
      ...MOCK_ORDERS[0],
      status: "confirmed",
    });

    const { AdminProvider } = await import("@/contexts/AdminContext");
    const { AdminGuard } = await import("@/components/admin/AdminGuard");
    const AdminOrdersPage = (await import("@/app/[locale]/admin/orders/page")).default;

    renderWithIntl(
      <AdminProvider>
        <AdminGuard>
          <AdminOrdersPage />
        </AdminGuard>
      </AdminProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("a***@example.com")).toBeInTheDocument();
    });

    // Find the status dropdown for the pending order
    const selects = screen.getAllByRole("combobox");
    fireEvent.change(selects[0], { target: { value: "confirmed" } });

    await waitFor(() => {
      expect(mockedUpdateOrderStatus).toHaveBeenCalledWith(
        "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
        "confirmed"
      );
    });
  });

  it("rolls back on status update failure", async () => {
    mockedGetAdminOrders.mockResolvedValue(MOCK_ORDER_LIST);
    mockedUpdateOrderStatus.mockRejectedValue(new Error("Server error"));

    const { AdminProvider } = await import("@/contexts/AdminContext");
    const { AdminGuard } = await import("@/components/admin/AdminGuard");
    const AdminOrdersPage = (await import("@/app/[locale]/admin/orders/page")).default;

    renderWithIntl(
      <AdminProvider>
        <AdminGuard>
          <AdminOrdersPage />
        </AdminGuard>
      </AdminProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("a***@example.com")).toBeInTheDocument();
    });

    const selects = screen.getAllByRole("combobox");
    fireEvent.change(selects[0], { target: { value: "confirmed" } });

    await waitFor(() => {
      expect(screen.getByText("Failed to update order status")).toBeInTheDocument();
    });

    // Original status should be restored (pending)
    expect(screen.getAllByText("Pending").length).toBeGreaterThan(0);
  });

  it("shows only valid transition options for each order status", async () => {
    mockedGetAdminOrders.mockResolvedValue(MOCK_ORDER_LIST);

    const { AdminProvider } = await import("@/contexts/AdminContext");
    const { AdminGuard } = await import("@/components/admin/AdminGuard");
    const AdminOrdersPage = (await import("@/app/[locale]/admin/orders/page")).default;

    renderWithIntl(
      <AdminProvider>
        <AdminGuard>
          <AdminOrdersPage />
        </AdminGuard>
      </AdminProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("a***@example.com")).toBeInTheDocument();
    });

    const selects = screen.getAllByRole("combobox");

    // First select is for "pending" order → valid transitions: confirmed, cancelled
    const pendingOptions = selects[0].querySelectorAll("option");
    const pendingValues = Array.from(pendingOptions).map((o) => o.value).filter(Boolean);
    expect(pendingValues).toEqual(["confirmed", "cancelled"]);

    // Second select is for "confirmed" order → valid transitions: shipped, cancelled
    const confirmedOptions = selects[1].querySelectorAll("option");
    const confirmedValues = Array.from(confirmedOptions).map((o) => o.value).filter(Boolean);
    expect(confirmedValues).toEqual(["shipped", "cancelled"]);
  });

  it("shows loading skeletons on initial load", async () => {
    mockedGetAdminOrders.mockImplementation(() => new Promise(() => {}));

    const { AdminProvider } = await import("@/contexts/AdminContext");
    const { AdminGuard } = await import("@/components/admin/AdminGuard");
    const AdminOrdersPage = (await import("@/app/[locale]/admin/orders/page")).default;

    renderWithIntl(
      <AdminProvider>
        <AdminGuard>
          <AdminOrdersPage />
        </AdminGuard>
      </AdminProvider>
    );

    await waitFor(() => {
      const skeletons = document.querySelectorAll('[class*="animate-pulse"]');
      expect(skeletons.length).toBeGreaterThan(0);
    });
  });

  it("shows error banner when loading fails", async () => {
    mockedGetAdminOrders.mockRejectedValue(new Error("Failed to load orders"));

    const { AdminProvider } = await import("@/contexts/AdminContext");
    const { AdminGuard } = await import("@/components/admin/AdminGuard");
    const AdminOrdersPage = (await import("@/app/[locale]/admin/orders/page")).default;

    renderWithIntl(
      <AdminProvider>
        <AdminGuard>
          <AdminOrdersPage />
        </AdminGuard>
      </AdminProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Failed to load orders")).toBeInTheDocument();
    });
  });

  it("shows empty state when no orders exist", async () => {
    mockedGetAdminOrders.mockResolvedValue({
      orders: [],
      total: 0,
      page: 1,
      limit: 100,
    });

    const { AdminProvider } = await import("@/contexts/AdminContext");
    const { AdminGuard } = await import("@/components/admin/AdminGuard");
    const AdminOrdersPage = (await import("@/app/[locale]/admin/orders/page")).default;

    renderWithIntl(
      <AdminProvider>
        <AdminGuard>
          <AdminOrdersPage />
        </AdminGuard>
      </AdminProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("No orders found.")).toBeInTheDocument();
    });
  });
});
