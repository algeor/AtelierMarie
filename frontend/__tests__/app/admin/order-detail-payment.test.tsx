import React from "react";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithIntl } from "../../test-utils";
import AdminOrderDetailPage from "@/app/[locale]/admin/orders/[id]/page";
import type { AdminOrderDetailResponse, OrderResponse } from "@/lib/types";

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "order-1" }),
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

import { applyManualPaymentAction, getAdminOrder, getEcontOrderReadiness } from "@/lib/api";

const mockedGetAdminOrder = vi.mocked(getAdminOrder);
const mockedApplyManualPaymentAction = vi.mocked(applyManualPaymentAction);
const mockedGetEcontOrderReadiness = vi.mocked(getEcontOrderReadiness);

const ORDER: AdminOrderDetailResponse = {
  id: "order-1",
  order_number: "AM-1A2B3C",
  status: "pending",
  payment_method: "card",
  payment_status: "pending",
  reserved_until: "2026-07-31T12:15:00Z",
  stripe_checkout_session_id: "cs_test_123",
  stripe_checkout_url: null,
  items_total_cents: 3200,
  shipping_cents: 0,
  shipping_price_source: "live",
  shipping_is_fallback: false,
  total_cents: 3200,
  customer_email: "buyer@example.com",
  customer_name: "Buyer",
  delivery_method: "office",
  delivery_courier: "econt",
  delivery_details: {
    courier: "econt",
    office_id: "1001",
    office_name: "Econt Sofia Center",
    office_type: "office",
    city: "Sofia",
    phone: "+359888123456",
  },
  notes: null,
  items: [
    {
      product_id: "lavender-dreams-300ml",
      product_name: "Lavender Dreams",
      price_cents: 3200,
      quantity: 1,
    },
  ],
  tracking_number: null,
  tracking_carrier: null,
  tracking_url: null,
  courier_status: null,
  label_url: null,
  created_at: "2026-07-31T12:00:00Z",
  updated_at: "2026-07-31T12:00:00Z",
  payment_events: [
    {
      id: "evt-1",
      order_id: "order-1",
      payment_id: "pay-1",
      event_type: "checkout.session.completed",
      source: "stripe",
      stripe_event_id: "evt_test_123",
      stripe_event_type: "checkout.session.completed",
      provider: "stripe",
      provider_status: "pending",
      processing_status: "processed",
      created_at: "2026-07-31T12:01:00Z",
    },
  ],
};

describe("Admin order payment detail", () => {
  beforeEach(() => {
    mockedGetAdminOrder.mockReset();
    mockedApplyManualPaymentAction.mockReset();
    mockedGetAdminOrder.mockResolvedValue(ORDER);
    mockedGetEcontOrderReadiness.mockResolvedValue({
      order_id: ORDER.id,
      ready: false,
      blockers: ["order_office_code_missing"],
      courier_provider: null,
      courier_order_id: null,
      courier_shipment_number: null,
      courier_label_url: null,
      courier_sync_status: null,
      courier_last_error: null,
      courier_last_synced_at: null,
      tracking_number: null,
      tracking_url: null,
    });
    mockedApplyManualPaymentAction.mockResolvedValue({
      ...ORDER,
      payment_status: "failed",
    } as OrderResponse);
  });

  it("shows payment summary and timeline", async () => {
    renderWithIntl(<AdminOrderDetailPage />);

    expect(await screen.findByText("AM-1A2B3C")).toBeInTheDocument();
    expect(screen.getByText("Awaiting payment")).toBeInTheDocument();
    expect(screen.getByText("cs_test_123")).toBeInTheDocument();
    expect(screen.getByText("Payment timeline")).toBeInTheDocument();
    expect(screen.getByText("checkout session completed")).toBeInTheDocument();
    expect(screen.getByText("evt_test_123")).toBeInTheDocument();
  });

  it("requires a note before applying manual payment action", async () => {
    mockedGetAdminOrder
      .mockResolvedValueOnce(ORDER)
      .mockResolvedValueOnce({
        ...ORDER,
        payment_status: "failed",
        payment_events: [
          ...ORDER.payment_events,
          {
            id: "evt-2",
            order_id: "order-1",
            event_type: "manual_mark_review",
            source: "admin",
            provider: "stripe",
            provider_status: "failed",
            processing_status: "processed",
            admin_note: "Late Stripe success after expiry",
            created_at: "2026-07-31T12:02:00Z",
          },
        ],
      });

    renderWithIntl(<AdminOrderDetailPage />);

    fireEvent.click(await screen.findByRole("button", { name: "Mark for review" }));
    fireEvent.click(screen.getByRole("button", { name: "Apply action" }));

    expect(await screen.findByText("A note is required.")).toBeInTheDocument();
    expect(mockedApplyManualPaymentAction).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText("Admin note"), {
      target: { value: "Late Stripe success after expiry" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply action" }));

    await waitFor(() =>
      expect(mockedApplyManualPaymentAction).toHaveBeenCalledWith(
        "order-1",
        "mark_review",
        "Late Stripe success after expiry",
      ),
    );
    expect(await screen.findByText("Payment action recorded.")).toBeInTheDocument();
    expect(await screen.findByText("manual mark review")).toBeInTheDocument();
  });
});
