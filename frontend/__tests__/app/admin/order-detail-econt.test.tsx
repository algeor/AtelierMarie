import React from "react";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithIntl } from "../../test-utils";
import AdminOrderDetailPage from "@/app/[locale]/admin/orders/[id]/page";
import type { AdminOrderDetailResponse, EcontOrderFulfillmentResponse } from "@/lib/types";

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
  applyManualPaymentAction: vi.fn(),
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
  getAdminOrder,
  getEcontOrderReadiness,
  repairEcontOrder,
} from "@/lib/api";

const mockedGetAdminOrder = vi.mocked(getAdminOrder);
const mockedGetEcontOrderReadiness = vi.mocked(getEcontOrderReadiness);
const mockedRepairEcontOrder = vi.mocked(repairEcontOrder);
const mockedCreateEcontLabel = vi.mocked(createEcontLabel);

const econtOrder: AdminOrderDetailResponse = {
  id: "order-econt-1",
  order_number: "AM-ECONT-1",
  status: "confirmed",
  payment_method: "cod",
  payment_status: "cod_pending",
  reserved_until: null,
  paid_at: null,
  collected_at: null,
  stripe_checkout_session_id: null,
  stripe_checkout_url: null,
  items_total_cents: 2500,
  shipping_cents: 590,
  shipping_price_source: "live",
  shipping_is_fallback: false,
  total_cents: 3090,
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
    city: "Sofia",
    phone: "+359888123456",
  },
  notes: null,
  items: [{ product_id: "candle", product_name: "Rose Candle", price_cents: 2500, quantity: 1 }],
  tracking_number: null,
  tracking_carrier: null,
  tracking_url: null,
  courier_status: null,
  label_url: null,
  courier_provider: null,
  courier_order_id: null,
  courier_shipment_number: null,
  courier_label_url: null,
  courier_label_created_at: null,
  courier_sync_status: null,
  courier_last_error: null,
  courier_last_synced_at: null,
  created_at: "2026-07-01T00:00:00Z",
  updated_at: "2026-07-01T00:00:00Z",
  payment_events: [],
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

describe("Admin order Econt fulfillment", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedGetAdminOrder.mockResolvedValue(econtOrder);
    mockedGetEcontOrderReadiness.mockResolvedValue(readiness());
  });

  it("shows readiness blockers and disables label creation", async () => {
    mockedGetEcontOrderReadiness.mockResolvedValue(
      readiness({ ready: false, blockers: ["order_office_code_missing"] }),
    );

    renderWithIntl(<AdminOrderDetailPage />);

    expect(await screen.findByText("Recipient office code is missing.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create label" })).toBeDisabled();
  });

  it("saves repair fields before label creation", async () => {
    mockedGetAdminOrder.mockResolvedValue({
      ...econtOrder,
      delivery_details: {
        courier: "econt",
        office_id: "econt-1029",
        office_name: "Econt Sofia Center",
        office_type: "office",
        city: "Sofia",
        phone: "+359888123456",
      },
    });
    mockedGetEcontOrderReadiness.mockResolvedValue(
      readiness({ ready: false, blockers: ["order_office_code_missing"] }),
    );
    mockedRepairEcontOrder.mockResolvedValue(readiness({ ready: true }));
    const user = userEvent.setup();

    renderWithIntl(<AdminOrderDetailPage />);

    await user.type(await screen.findByLabelText("Office code"), "1127");
    await user.clear(screen.getByLabelText("Recipient phone"));
    await user.type(screen.getByLabelText("Recipient phone"), "+359 888 123 456");
    await user.clear(screen.getByLabelText("Package count"));
    await user.type(screen.getByLabelText("Package count"), "2");
    await user.type(screen.getByLabelText("Shipment description"), "Custom candle shipment");
    await user.selectOptions(screen.getByLabelText("Payment side"), "sender");
    await user.click(screen.getByRole("button", { name: "Apply repairs" }));

    await waitFor(() => {
      expect(mockedRepairEcontOrder).toHaveBeenCalledWith("order-econt-1", {
        office_code: "1127",
        recipient_phone: "+359 888 123 456",
        pack_count: 2,
        shipment_description: "Custom candle shipment",
        payment_side: "sender",
      });
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
});
