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
  createAndShipEcontOrder: vi.fn(),
  updateOrderStatus: vi.fn(),
}));

import {
  createAndShipEcontOrder,
  getAdminOrders,
  getCurrentUser,
  updateOrderStatus,
} from "@/lib/api";
import type { OrderListResponse, OrderResponse, UserResponse } from "@/lib/types";

const mockedGetCurrentUser = vi.mocked(getCurrentUser);
const mockedGetAdminOrders = vi.mocked(getAdminOrders);
const mockedCreateAndShipEcontOrder = vi.mocked(createAndShipEcontOrder);
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
    payment_method: "cod",
    payment_status: "cod_pending",
    stripe_checkout_url: null,
    items_total_cents: 7700,
    shipping_cents: 0,
    shipping_price_source: "live",
    shipping_is_fallback: false,
    total_cents: 7700,
    customer_email: "alice@example.com",
    customer_name: "Alice Johnson",
    delivery_method: "door",
    delivery_courier: "speedy",
    delivery_details: {
      courier: "speedy",
      city: "Sofia",
      postal_code: "1000",
      street: "123 Main St",
      building: null,
      apartment: null,
      phone: "+359888123456",
    },
    notes: null,
    items: [
      { product_id: "lavender-dreams-300ml", product_name: "Lavender Dreams", price_cents: 3200, quantity: 1 },
    ],
    tracking_number: null,
    tracking_carrier: null,
    tracking_url: null,
    courier_status: null,
    label_url: null,
    created_at: "2026-07-11T10:00:00Z",
    updated_at: "2026-07-11T10:00:00Z",
  },
  {
    id: "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e",
    status: "confirmed",
    payment_method: "cod",
    payment_status: "cod_pending",
    stripe_checkout_url: null,
    items_total_cents: 5600,
    shipping_cents: 0,
    shipping_price_source: "live",
    shipping_is_fallback: false,
    total_cents: 5600,
    customer_email: "bob@example.com",
    customer_name: "Bob Smith",
    delivery_method: "office",
    delivery_courier: "econt",
    delivery_details: {
      courier: "econt",
      office_id: "1001",
      office_name: "Econt Sofia Center",
      office_type: "office",
      city: "Sofia",
      phone: "+359888654321",
    },
    notes: null,
    items: [
      { product_id: "citrus-garden-200ml", product_name: "Citrus Garden", price_cents: 2800, quantity: 2 },
    ],
    tracking_number: null,
    tracking_carrier: null,
    tracking_url: null,
    courier_status: null,
    label_url: null,
    created_at: "2026-07-10T11:00:00Z",
    updated_at: "2026-07-10T11:00:00Z",
  },
];

const MOCK_ORDER_LIST: OrderListResponse = {
  items: MOCK_ORDERS,
  total: 2,
  page: 1,
  limit: 100,
};

const PREVIOUS_STATUS_FILTER_VALUES = [
  "",
  "pending",
  "confirmed",
  "shipped",
  "delivered",
  "return_in_transit",
  "returned",
  "cancelled",
];

const PREVIOUS_PAYMENT_STATUS_FILTER_VALUES = [
  "",
  "pending",
  "paid",
  "cod_pending",
  "failed",
  "refunded",
];

const PREVIOUS_PAYMENT_METHOD_FILTER_VALUES = ["", "card", "cod", "bank_transfer"];

const PREVIOUS_ACCOUNTING_FILTER_VALUES = [
  "",
  "missing_document_reference",
  "unresolved_exception",
  "payout_mismatch",
  "cod_settlement_pending",
  "refund_document_missing",
  "vat_review_required",
  "missing_batch_assignment",
  "missing_inventory_movement",
  "missing_cogs_row",
  "valuation_exception",
  "return_inventory_review_pending",
];

async function filterMenuOptionValues(name: string): Promise<string[]> {
  fireEvent.click(screen.getByRole("button", { name }));
  const options = await screen.findAllByRole("menuitemradio");
  const values = options.map((option) => option.getAttribute("data-value") ?? "");
  fireEvent.keyDown(document, { key: "Escape" });
  await waitFor(() => {
    expect(screen.queryByRole("menuitemradio")).not.toBeInTheDocument();
  });
  return values;
}

async function openStatusMenu(index = 0) {
  const statusMenus = screen.getAllByRole("button", {
    name: /Update status for order/i,
  });
  fireEvent.click(statusMenus[index]!);
  return screen.findAllByRole("menuitem");
}

async function selectStatusOption(index: number, name: string) {
  await openStatusMenu(index);
  fireEvent.click(await screen.findByRole("menuitem", { name }));
}

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

  it("shows compact order filters", async () => {
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

    expect(screen.getByRole("button", { name: "All orders" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Needs attention" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("searchbox", { name: "Search" })).toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "Date range" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Date range" })).toHaveTextContent("All dates");
    expect(screen.getByRole("button", { name: "Status" })).toHaveTextContent("All");
    expect(screen.getByRole("button", { name: "Payment status" })).toHaveTextContent("All");
  });

  it("keeps every previous filter option reachable", async () => {
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

    expect(await filterMenuOptionValues("Status")).toEqual(
      PREVIOUS_STATUS_FILTER_VALUES
    );
    expect(await filterMenuOptionValues("Payment status")).toEqual(
      expect.arrayContaining(PREVIOUS_PAYMENT_STATUS_FILTER_VALUES)
    );

    fireEvent.click(screen.getByRole("button", { name: "Filters" }));

    expect(await filterMenuOptionValues("Payment method")).toEqual(
      PREVIOUS_PAYMENT_METHOD_FILTER_VALUES
    );
    expect(await filterMenuOptionValues("Accounting filter")).toEqual(
      PREVIOUS_ACCOUNTING_FILTER_VALUES
    );
  });

  it("filters orders by status when selected", async () => {
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

    fireEvent.click(screen.getByRole("button", { name: "Status" }));
    fireEvent.click(await screen.findByRole("menuitemradio", { name: "Pending" }));

    await waitFor(() => {
      expect(mockedGetAdminOrders).toHaveBeenCalledWith(1, 100, "pending");
    });
  });

  it("filters orders by missing COGS inventory review", async () => {
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

    fireEvent.click(screen.getByRole("button", { name: "Filters" }));
    fireEvent.click(screen.getByRole("button", { name: "Accounting filter" }));
    fireEvent.click(await screen.findByRole("menuitemradio", { name: "Missing sold cost" }));

    await waitFor(() => {
      expect(mockedGetAdminOrders).toHaveBeenCalledWith(
        1,
        100,
        undefined,
        undefined,
        undefined,
        "missing_cogs_row"
      );
    });
  });

  it("updates order status via dropdown", async () => {
    mockedGetAdminOrders.mockResolvedValue(MOCK_ORDER_LIST);
    mockedUpdateOrderStatus.mockResolvedValue({
      ...MOCK_ORDERS[0]!,
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

    await selectStatusOption(0, "Confirmed");

    await waitFor(() => {
      expect(mockedUpdateOrderStatus).toHaveBeenCalledWith(
        "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
        "confirmed",
        undefined
      );
    });
  });

  it("creates and ships Econt orders directly from the list", async () => {
    mockedGetAdminOrders.mockResolvedValue(MOCK_ORDER_LIST);
    mockedCreateAndShipEcontOrder.mockResolvedValue({
      order_id: MOCK_ORDERS[1]!.id,
      action: "create_label_and_ship",
      status: "shipped",
      courier_order_id: null,
      shipment_number: "1234567890",
      label_url: "https://label.test/123.pdf",
      tracking_url: "https://www.econt.com/services/track-shipment/1234567890",
      courier_status: null,
      status_updated_to: "shipped",
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
      expect(screen.getByText("b***@example.com")).toBeInTheDocument();
    });

    await selectStatusOption(1, "Shipped");

    await waitFor(() => {
      expect(mockedCreateAndShipEcontOrder).toHaveBeenCalledWith(MOCK_ORDERS[1]!.id);
    });
    expect(mockedUpdateOrderStatus).not.toHaveBeenCalledWith(
      MOCK_ORDERS[1]!.id,
      "shipped",
      expect.anything()
    );
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

    await selectStatusOption(0, "Confirmed");

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

    const pendingOptions = await openStatusMenu(0);
    expect(pendingOptions.map((option) => option.textContent)).toEqual([
      "Confirmed",
      "Cancelled",
    ]);

    fireEvent.keyDown(document, { key: "Escape" });
    await waitFor(() => {
      expect(screen.queryByRole("menuitem")).not.toBeInTheDocument();
    });

    const confirmedOptions = await openStatusMenu(1);
    expect(confirmedOptions.map((option) => option.textContent)).toEqual([
      "Shipped",
      "Cancelled",
    ]);
  });

  it("opens the ship modal for orders without a courier integration", async () => {
    // Speedy and Econt orders auto-ship (integration handles labels/tracking),
    // so the manual ShipOrderModal is only shown for orders whose courier has no
    // integration. Use a confirmed order with no delivery_courier to reach it.
    const manualOrder: OrderResponse = {
      ...MOCK_ORDERS[1]!,
      delivery_courier: null,
      delivery_details: null,
    };
    mockedGetAdminOrders.mockResolvedValue({
      items: [manualOrder],
      total: 1,
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
      expect(screen.getByText("b***@example.com")).toBeInTheDocument();
    });

    await selectStatusOption(0, "Shipped");

    expect(screen.getByRole("dialog", { name: "Ship order" })).toBeInTheDocument();
    // Manual carrier defaults to the first tracking carrier (Speedy) when the
    // order carries no courier to pre-select.
    expect(screen.getByLabelText("Carrier")).toHaveValue("speedy");
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
      items: [],
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
