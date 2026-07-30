import React from "react";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithIntl } from "../../test-utils";
import type { EcontOrderFulfillmentResponse, OrderResponse } from "@/lib/types";

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "order-econt-1" }),
}));

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("@/lib/api", () => ({
  getAdminOrder: vi.fn(),
  getEcontOrderReadiness: vi.fn(),
  repairEcontOrder: vi.fn(),
  syncEcontOrder: vi.fn(),
  createEcontLabel: vi.fn(),
  deleteEcontLabel: vi.fn(),
  refreshEcontTrace: vi.fn(),
  updateOrderStatus: vi.fn(),
}));

import {
  createEcontLabel,
  deleteEcontLabel,
  getAdminOrder,
  getEcontOrderReadiness,
  repairEcontOrder,
  refreshEcontTrace,
  updateOrderStatus,
} from "@/lib/api";
import AdminOrderDetailPage from "@/app/[locale]/admin/orders/[id]/page";

const mockedGetAdminOrder = vi.mocked(getAdminOrder);
const mockedGetEcontOrderReadiness = vi.mocked(getEcontOrderReadiness);
const mockedRepairEcontOrder = vi.mocked(repairEcontOrder);
const mockedCreateEcontLabel = vi.mocked(createEcontLabel);
const mockedDeleteEcontLabel = vi.mocked(deleteEcontLabel);
const mockedRefreshEcontTrace = vi.mocked(refreshEcontTrace);
const mockedUpdateOrderStatus = vi.mocked(updateOrderStatus);

const econtOrder: OrderResponse = {
  id: "order-econt-1",
  status: "confirmed",
  payment_method: "cod",
  payment_status: "cod_pending",
  stripe_checkout_url: null,
  items_total_cents: 2500,
  shipping_cents: 0,
  total_cents: 2500,
  customer_email: "buyer@example.com",
  customer_name: "Buyer",
  delivery_method: "office",
  delivery_courier: "econt",
  delivery_details: {
    courier: "econt",
    office_id: "econt-1029",
    office_code: "1127",
    office_name: "Econt Sofia Center",
    office_type: "office",
    phone: "+359888123456",
  },
  notes: null,
  items: [{ product_id: "candle", product_name: "Rose Candle", price_cents: 2500, quantity: 1 }],
  tracking_number: null,
  tracking_carrier: null,
  tracking_url: null,
  created_at: "2026-07-01T00:00:00Z",
  updated_at: "2026-07-01T00:00:00Z",
};

function readiness(overrides: Partial<EcontOrderFulfillmentResponse> = {}): EcontOrderFulfillmentResponse {
  return {
    order_id: "order-econt-1",
    ready: true,
    blockers: [],
    courier_provider: null,
    courier_order_id: null,
    courier_shipment_number: null,
    courier_label_url: null,
    courier_sync_status: null,
    courier_last_error: null,
    courier_last_synced_at: null,
    tracking_number: null,
    tracking_url: null,
    ...overrides,
  };
}

describe("AdminOrderDetailPage Econt fulfillment", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedGetAdminOrder.mockResolvedValue(econtOrder);
    mockedGetEcontOrderReadiness.mockResolvedValue(readiness());
  });

  it("shows non-Econt state", async () => {
    mockedGetAdminOrder.mockResolvedValue({ ...econtOrder, delivery_courier: "speedy" });
    renderWithIntl(<AdminOrderDetailPage />);

    expect(await screen.findByText("This order is not an Econt delivery.")).toBeInTheDocument();
  });

  it("shows readiness blockers and disables label creation", async () => {
    mockedGetEcontOrderReadiness.mockResolvedValue(
      readiness({ ready: false, blockers: ["order_office_code_missing"] }),
    );
    renderWithIntl(<AdminOrderDetailPage />);

    expect(await screen.findByText("Recipient office code is missing.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create label" })).toBeDisabled();
  });

  it("applies repair controls before label creation", async () => {
    mockedGetAdminOrder.mockResolvedValue({
      ...econtOrder,
      delivery_details: {
        courier: "econt",
        office_id: "econt-1029",
        office_name: "Econt Sofia Center",
        office_type: "office",
        phone: "+359888123456",
      },
    });
    mockedGetEcontOrderReadiness.mockResolvedValue(
      readiness({ ready: false, blockers: ["order_office_code_missing"] }),
    );
    mockedRepairEcontOrder.mockResolvedValue(readiness({ ready: true }));
    const user = userEvent.setup();
    renderWithIntl(<AdminOrderDetailPage />);

    await user.clear(await screen.findByLabelText("Office code"));
    await user.type(screen.getByLabelText("Office code"), "1127");
    await user.clear(screen.getByLabelText("Recipient phone"));
    await user.type(screen.getByLabelText("Recipient phone"), "+359 888 123 456");
    await user.type(screen.getByLabelText("Package count"), "2");
    await user.type(screen.getByLabelText("Shipment description"), "Custom candle shipment");
    await user.selectOptions(screen.getByLabelText("Payment side"), "sender");
    await user.click(screen.getByRole("button", { name: "Apply repairs" }));

    await waitFor(() => {
      expect(mockedRepairEcontOrder).toHaveBeenCalledWith(
        "order-econt-1",
        {
          office_code: "1127",
          recipient_phone: "+359 888 123 456",
          pack_count: 2,
          shipment_description: "Custom candle shipment",
          payment_side: "sender",
        },
      );
    });
  });

  it("creates an Econt label from a ready order", async () => {
    mockedCreateEcontLabel.mockResolvedValue({
      order_id: "order-econt-1",
      action: "create_label",
      status: "label_created",
      courier_order_id: "remote-1",
      shipment_number: "1234567890",
      label_url: "https://label.test/123.pdf",
      tracking_url: "https://www.econt.com/services/track-shipment/1234567890",
    });
    const user = userEvent.setup();
    renderWithIntl(<AdminOrderDetailPage />);

    await user.click(await screen.findByRole("button", { name: "Create label" }));

    await waitFor(() => expect(mockedCreateEcontLabel).toHaveBeenCalledWith("order-econt-1"));
    expect(await screen.findByText("Econt label created")).toBeInTheDocument();
  });

  it("shows created label actions", async () => {
    mockedGetAdminOrder.mockResolvedValue({
      ...econtOrder,
      courier_provider: "econt",
      courier_shipment_number: "1234567890",
      tracking_number: "1234567890",
      tracking_carrier: "econt",
      tracking_url: "https://www.econt.com/services/track-shipment/1234567890",
    });
    mockedGetEcontOrderReadiness.mockResolvedValue(
      readiness({
        courier_provider: "econt",
        courier_shipment_number: "1234567890",
        courier_label_url: "https://label.test/123.pdf",
        tracking_number: "1234567890",
        tracking_url: "https://www.econt.com/services/track-shipment/1234567890",
      }),
    );
    mockedRefreshEcontTrace.mockResolvedValue({
      order_id: "order-econt-1",
      action: "refresh_trace",
      status: "trace_synced",
      courier_order_id: null,
      shipment_number: "1234567890",
      label_url: "https://label.test/123.pdf",
      tracking_url: "https://www.econt.com/services/track-shipment/1234567890",
    });
    mockedDeleteEcontLabel.mockResolvedValue({
      order_id: "order-econt-1",
      action: "delete_label",
      status: "label_deleted",
      courier_order_id: null,
      shipment_number: null,
      label_url: null,
      tracking_url: null,
    });
    mockedUpdateOrderStatus.mockResolvedValue({ ...econtOrder, status: "shipped" });
    const user = userEvent.setup();
    renderWithIntl(<AdminOrderDetailPage />);

    expect(await screen.findByRole("link", { name: "Open label PDF" })).toHaveAttribute(
      "href",
      "https://label.test/123.pdf",
    );
    await user.click(screen.getByRole("button", { name: "Refresh trace" }));
    await waitFor(() => expect(mockedRefreshEcontTrace).toHaveBeenCalledWith("order-econt-1"));

    await user.click(screen.getByRole("button", { name: "Mark shipped" }));
    await waitFor(() => {
      expect(mockedUpdateOrderStatus).toHaveBeenCalledWith(
        "order-econt-1",
        "shipped",
        expect.objectContaining({ tracking_number: "1234567890", tracking_carrier: "econt" }),
      );
    });

    await user.click(screen.getByRole("button", { name: "Delete label" }));
    await waitFor(() => expect(mockedDeleteEcontLabel).toHaveBeenCalledWith("order-econt-1"));
  });

  it("keeps actions retryable after failure", async () => {
    mockedCreateEcontLabel
      .mockRejectedValueOnce(new Error("timeout"))
      .mockResolvedValueOnce({
        order_id: "order-econt-1",
        action: "create_label",
        status: "label_created",
        courier_order_id: null,
        shipment_number: "1234567890",
        label_url: "https://label.test/123.pdf",
        tracking_url: "https://www.econt.com/services/track-shipment/1234567890",
      });
    const user = userEvent.setup();
    renderWithIntl(<AdminOrderDetailPage />);

    const createButton = await screen.findByRole("button", { name: "Create label" });
    await user.click(createButton);
    expect(await screen.findByText("Econt action failed")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Create label" }));
    await waitFor(() => expect(mockedCreateEcontLabel).toHaveBeenCalledTimes(2));
  });
});
