import React from "react";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithIntl } from "../../test-utils";
import AdminOrderDetailPage from "@/app/[locale]/admin/orders/[id]/page";
import type { AdminOrderDetailResponse, ReturnCaseResponse } from "@/lib/types";

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "order-return-1" }),
}));

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("@/lib/api", () => ({
  getAdminOrder: vi.fn(),
  applyManualPaymentAction: vi.fn(),
  createReturnCase: vi.fn(),
  receiveReturnCase: vi.fn(),
  inspectReturnCase: vi.fn(),
  closeReturnCase: vi.fn(),
  updateReturnAccounting: vi.fn(),
  createStripeRefund: vi.fn(),
  recordCodSettlement: vi.fn(),
  getEcontOrderReadiness: vi.fn(),
  repairEcontOrder: vi.fn(),
  syncEcontOrder: vi.fn(),
  createAndShipEcontOrder: vi.fn(),
  createEcontLabel: vi.fn(),
  deleteEcontLabel: vi.fn(),
  refreshEcontTrace: vi.fn(),
  updateOrderStatus: vi.fn(),
  listOrderAccountingDocuments: vi.fn(),
  createAccountingDocument: vi.fn(),
  updateAccountingDocument: vi.fn(),
}));

import {
  applyManualPaymentAction,
  closeReturnCase,
  createReturnCase,
  createStripeRefund,
  getAdminOrder,
  getEcontOrderReadiness,
  inspectReturnCase,
  listOrderAccountingDocuments,
  receiveReturnCase,
  recordCodSettlement,
  updateReturnAccounting,
} from "@/lib/api";

const mockedGetAdminOrder = vi.mocked(getAdminOrder);
const mockedGetEcontOrderReadiness = vi.mocked(getEcontOrderReadiness);
const mockedCreateReturnCase = vi.mocked(createReturnCase);
const mockedReceiveReturnCase = vi.mocked(receiveReturnCase);
const mockedInspectReturnCase = vi.mocked(inspectReturnCase);
const mockedCloseReturnCase = vi.mocked(closeReturnCase);
const mockedUpdateReturnAccounting = vi.mocked(updateReturnAccounting);
const mockedCreateStripeRefund = vi.mocked(createStripeRefund);
const mockedRecordCodSettlement = vi.mocked(recordCodSettlement);
const mockedApplyManualPaymentAction = vi.mocked(applyManualPaymentAction);
const mockedListOrderAccountingDocuments = vi.mocked(listOrderAccountingDocuments);

function returnCase(overrides: Partial<ReturnCaseResponse> = {}): ReturnCaseResponse {
  return {
    id: "return-1",
    order_id: "order-return-1",
    reason: "customer_return",
    source: "admin",
    status: "return_in_transit",
    refund_amount_cents: null,
    courier_return_fee_cents: 0,
    courier_claim_id: null,
    courier_claim_status: "none",
    courier_claim_amount_cents: null,
    restock_decision: "pending",
    returned_at: "2026-08-01T10:00:00Z",
    received_at: null,
    inspected_at: null,
    closed_at: null,
    notes: null,
    created_by_admin_id: null,
    updated_by_admin_id: null,
    created_at: "2026-08-01T10:00:00Z",
    updated_at: "2026-08-01T10:00:00Z",
    ...overrides,
  };
}

function order(overrides: Partial<AdminOrderDetailResponse> = {}): AdminOrderDetailResponse {
  return {
    id: "order-return-1",
    order_number: "AM-RETURN-1",
    status: "shipped",
    payment_method: "card",
    payment_status: "paid",
    reserved_until: null,
    paid_at: "2026-08-01T09:00:00Z",
    collected_at: null,
    stripe_checkout_session_id: "cs_test_return",
    stripe_checkout_url: null,
    items_total_cents: 5000,
    shipping_cents: 500,
    shipping_price_source: "live",
    shipping_is_fallback: false,
    total_cents: 5500,
    customer_email: "buyer@example.com",
    customer_name: "Buyer",
    delivery_method: "door",
    delivery_courier: "speedy",
    delivery_details: {
      courier: "speedy",
      city: "Sofia",
      postal_code: "1000",
      street: "Main 1",
      building: null,
      apartment: null,
      phone: "+359888123456",
    },
    notes: null,
    items: [
      {
        product_id: "custom-candle",
        product_name: "Custom Candle",
        price_cents: 5000,
        quantity: 1,
      },
    ],
    tracking_number: "SP123",
    tracking_carrier: "speedy",
    tracking_url: "https://track.test/SP123",
    courier_status: "in_transit",
    label_url: null,
    courier_provider: "speedy",
    courier_order_id: null,
    courier_shipment_number: "SP123",
    courier_label_url: null,
    courier_label_created_at: null,
    courier_sync_status: "synced",
    courier_last_error: null,
    courier_last_synced_at: "2026-08-01T10:00:00Z",
    created_at: "2026-08-01T08:00:00Z",
    updated_at: "2026-08-01T10:00:00Z",
    payment_events: [],
    return_cases: [],
    return_events: [],
    refund_records: [],
    cod_settlement: null,
    cod_settlement_required: false,
    econt_cod_evidence: null,
    ...overrides,
  };
}

describe("Admin order return/refund workflow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedGetAdminOrder.mockResolvedValue(order());
    mockedListOrderAccountingDocuments.mockResolvedValue({ items: [], total: 0 });
    mockedGetEcontOrderReadiness.mockResolvedValue({
      order_id: "order-return-1",
      ready: false,
      blockers: ["order_not_econt"],
      courier_provider: "speedy",
      courier_order_id: null,
      courier_shipment_number: "SP123",
      courier_label_url: null,
      courier_sync_status: "synced",
      courier_last_error: null,
      courier_last_synced_at: "2026-08-01T10:00:00Z",
      tracking_number: "SP123",
      tracking_url: "https://track.test/SP123",
    });
    mockedCreateReturnCase.mockResolvedValue(returnCase());
    mockedReceiveReturnCase.mockResolvedValue(returnCase({ status: "received" }));
    mockedInspectReturnCase.mockResolvedValue(
      returnCase({ status: "inspected", restock_decision: "partial" }),
    );
    mockedCloseReturnCase.mockResolvedValue(returnCase({ status: "closed" }));
    mockedUpdateReturnAccounting.mockResolvedValue(
      returnCase({ courier_return_fee_cents: 650, courier_claim_id: "CLM-123" }),
    );
    mockedCreateStripeRefund.mockResolvedValue({
      id: "refund-1",
      order_id: "order-return-1",
      payment_id: null,
      provider: "stripe",
      provider_refund_id: "re_test_1",
      amount_cents: 1000,
      status: "pending",
      reason: "Returned item",
      idempotency_key: "admin-refund-order-return-1-test",
      failure_reason: null,
      created_by_admin_id: null,
      created_at: "2026-08-01T11:00:00Z",
      confirmed_at: null,
    });
    mockedRecordCodSettlement.mockResolvedValue({
      id: "cod-1",
      order_id: "order-return-1",
      amount_cents: 5500,
      settlement_date: "2026-08-01",
      courier_reference: "COD-123",
      notes: "Paid by courier",
      mismatch_review: false,
      created_by_admin_id: null,
      created_at: "2026-08-01T11:00:00Z",
      updated_at: "2026-08-01T11:00:00Z",
    });
    mockedApplyManualPaymentAction.mockResolvedValue(order({ payment_method: "cod", payment_status: "cod_pending" }));
  });

  it("creates quick uncollected and refused return cases", async () => {
    const user = userEvent.setup();
    renderWithIntl(<AdminOrderDetailPage />);

    await user.click(await screen.findByRole("button", { name: "Mark uncollected" }));
    await waitFor(() => expect(mockedCreateReturnCase).toHaveBeenCalledTimes(1));
    await user.click(screen.getByRole("button", { name: "Mark refused" }));

    await waitFor(() => {
      expect(mockedCreateReturnCase).toHaveBeenNthCalledWith(1, "order-return-1", {
        reason: "not_picked_up",
        status: "return_in_transit",
        source: "admin",
      });
      expect(mockedCreateReturnCase).toHaveBeenNthCalledWith(2, "order-return-1", {
        reason: "refused_delivery",
        status: "return_in_transit",
        source: "admin",
      });
    });
  });

  it("receives return cases with an explicit admin action", async () => {
    const user = userEvent.setup();
    mockedGetAdminOrder.mockResolvedValue(
      order({ return_cases: [returnCase({ status: "return_in_transit" })] }),
    );

    renderWithIntl(<AdminOrderDetailPage />);
    await user.click(await screen.findByRole("button", { name: "Receive return" }));

    await waitFor(() => expect(mockedReceiveReturnCase).toHaveBeenCalledWith("order-return-1", "return-1"));
  });

  it("inspects received returns with partial restock quantities", async () => {
    const user = userEvent.setup();
    mockedGetAdminOrder.mockResolvedValue(
      order({ return_cases: [returnCase({ status: "received", received_at: "2026-08-01T11:00:00Z" })] }),
    );
    renderWithIntl(<AdminOrderDetailPage />);
    await user.selectOptions(await screen.findByLabelText("Restock decision"), "partial");
    await user.type(screen.getByLabelText("Partial quantities"), "custom-candle:1");
    await user.click(screen.getByRole("button", { name: "Inspect return" }));

    await waitFor(() =>
      expect(mockedInspectReturnCase).toHaveBeenCalledWith("order-return-1", "return-1", {
        restock_decision: "partial",
        restock_quantities: { "custom-candle": 1 },
        notes: null,
      }),
    );
  });

  it("closes inspected return cases", async () => {
    const user = userEvent.setup();
    mockedGetAdminOrder.mockResolvedValue(
      order({ return_cases: [returnCase({ status: "inspected", restock_decision: "restock" })] }),
    );
    renderWithIntl(<AdminOrderDetailPage />);
    await user.click(await screen.findByRole("button", { name: "Close return" }));

    await waitFor(() => expect(mockedCloseReturnCase).toHaveBeenCalledWith("order-return-1", "return-1"));
  });

  it("validates and creates Stripe refunds with personalized item warning", async () => {
    const user = userEvent.setup();
    renderWithIntl(<AdminOrderDetailPage />);

    expect(await screen.findByText("Stripe refund")).toBeInTheDocument();
    expect(screen.getByText(/custom or personalized item policy/i)).toBeInTheDocument();

    await user.type(screen.getByLabelText("Amount, cents"), "999999");
    await user.click(screen.getByRole("button", { name: "Create refund" }));

    expect(await screen.findByText(/between 1 cent and the remaining refundable amount/i)).toBeInTheDocument();
    expect(mockedCreateStripeRefund).not.toHaveBeenCalled();

    await user.clear(screen.getByLabelText("Amount, cents"));
    await user.type(screen.getByLabelText("Amount, cents"), "1000");
    await user.type(screen.getByLabelText("Refund reason"), "Returned item");
    await user.click(screen.getByRole("button", { name: "Create refund" }));

    await waitFor(() =>
      expect(mockedCreateStripeRefund).toHaveBeenCalledWith("order-return-1", {
        amount_cents: 1000,
        reason: "Returned item",
        idempotency_key: expect.stringMatching(/^admin-refund-order-return-1-/),
      }),
    );
  });

  it("records abandoned card callbacks and confirmed conversion to payment on delivery", async () => {
    const user = userEvent.setup();
    mockedGetAdminOrder.mockResolvedValue(
      order({ status: "pending", payment_method: "card", payment_status: "review_required" }),
    );

    renderWithIntl(<AdminOrderDetailPage />);

    await user.selectOptions(await screen.findByLabelText("Callback outcome"), "unreachable");
    await user.type(screen.getByLabelText("Admin note"), "Left voicemail");
    await user.click(screen.getByRole("button", { name: "Record callback" }));

    await waitFor(() =>
      expect(mockedApplyManualPaymentAction).toHaveBeenCalledWith(
        "order-return-1",
        "record_callback",
        "Left voicemail",
        "unreachable",
      ),
    );

    await user.clear(screen.getByLabelText("Admin note"));
    await user.type(screen.getByLabelText("Admin note"), "Customer confirmed COD");
    await user.click(screen.getByRole("button", { name: "Convert to delivery payment" }));

    await waitFor(() =>
      expect(mockedApplyManualPaymentAction).toHaveBeenCalledWith(
        "order-return-1",
        "convert_to_cod",
        "Customer confirmed COD",
        "confirmed",
      ),
    );
  });

  it("records courier claim fields and COD settlements", async () => {
    const user = userEvent.setup();
    mockedGetAdminOrder.mockResolvedValue(
      order({
        payment_method: "cod",
        payment_status: "cod_pending",
        status: "delivered",
        return_cases: [returnCase({ reason: "damaged_by_courier", status: "received" })],
        cod_settlement_required: true,
      }),
    );

    renderWithIntl(<AdminOrderDetailPage />);

    await user.type(await screen.findByLabelText("Courier fee, cents"), "650");
    await user.type(screen.getByLabelText("Claim ID"), "CLM-123");
    await user.selectOptions(screen.getByLabelText("Claim status"), "filed");
    await user.type(screen.getByLabelText("Claim amount, cents"), "3000");
    await user.click(screen.getByRole("button", { name: "Save accounting" }));

    await waitFor(() =>
      expect(mockedUpdateReturnAccounting).toHaveBeenCalledWith("order-return-1", "return-1", {
        courier_return_fee_cents: 650,
        courier_claim_id: "CLM-123",
        courier_claim_status: "filed",
        courier_claim_amount_cents: 3000,
        notes: null,
      }),
    );

    await user.clear(screen.getByLabelText("Amount, cents"));
    await user.type(screen.getByLabelText("Amount, cents"), "5500");
    await user.clear(screen.getByLabelText("Settlement date"));
    await user.type(screen.getByLabelText("Settlement date"), "2026-08-01");
    await user.type(screen.getByLabelText("Courier reference"), "COD-123");
    await user.click(screen.getByRole("button", { name: "Record settlement" }));

    await waitFor(() =>
      expect(mockedRecordCodSettlement).toHaveBeenCalledWith("order-return-1", {
        amount_cents: 5500,
        settlement_date: "2026-08-01",
        courier_reference: "COD-123",
        notes: null,
      }),
    );
  });
});
