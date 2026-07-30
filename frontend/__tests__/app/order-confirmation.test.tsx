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
      items_total_cents: 5000,
      shipping_cents: 0,
      total_cents: 5000,
      customer_email: "buyer@example.com",
      customer_name: "Test Buyer",
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
        { product_id: "candle-1", product_name: "Rose Candle", price_cents: 2500, quantity: 2 },
      ],
      tracking_number: null,
      tracking_carrier: null,
      tracking_url: null,
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:00Z",
    });

    renderWithIntl(<OrderConfirmationPage />);

    await waitFor(() => {
      expect(screen.getByText(/thank you for your order/i)).toBeInTheDocument();
    });
    expect(screen.getByText("Rose Candle")).toBeInTheDocument();
    expect(screen.getByText(/buyer@example.com/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Terms & Conditions" })).toHaveAttribute(
      "href",
      "/terms"
    );
    expect(screen.getByRole("link", { name: "Privacy Policy" })).toHaveAttribute(
      "href",
      "/privacy"
    );
    expect(screen.getByText("Subtotal")).toBeInTheDocument();
    expect(screen.getAllByText("Delivery").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/No separate delivery charge in this order/)).toBeInTheDocument();
    expect(screen.getAllByText("€50.00").length).toBeGreaterThanOrEqual(2);
    expect(screen.queryByText("Shipment")).not.toBeInTheDocument();
  });

  it("shows Econt shipment tracking when a label exists", async () => {
    mockedGetOrder.mockResolvedValue({
      id: "test-order-123",
      status: "confirmed",
      payment_method: "cod",
      payment_status: "cod_pending",
      stripe_checkout_url: null,
      items_total_cents: 2500,
      shipping_cents: 0,
      total_cents: 2500,
      customer_email: "buyer@example.com",
      customer_name: "Test Buyer",
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
      items: [
        { product_id: "candle-1", product_name: "Rose Candle", price_cents: 2500, quantity: 1 },
      ],
      tracking_number: "1234567890",
      tracking_carrier: "econt",
      tracking_url: "https://www.econt.com/services/track-shipment/1234567890",
      courier_provider: "econt",
      courier_shipment_number: "1234567890",
      courier_sync_status: "trace_synced",
      courier_last_synced_at: "2026-07-01T12:00:00Z",
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:00Z",
    });

    renderWithIntl(<OrderConfirmationPage />);

    await waitFor(() => {
      expect(screen.getByText("Shipment")).toBeInTheDocument();
    });
    expect(screen.getByText("1234567890")).toBeInTheDocument();
    expect(screen.getByText("Tracking refreshed")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Track with Econt" })).toHaveAttribute(
      "href",
      "https://www.econt.com/services/track-shipment/1234567890"
    );
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
      items_total_cents: 5000,
      shipping_cents: 0,
      total_cents: 5000,
      customer_email: "buyer@example.com",
      customer_name: null,
      delivery_method: null,
      delivery_courier: null,
      delivery_details: null,
      notes: null,
      items: [],
      tracking_number: null,
      tracking_carrier: null,
      tracking_url: null,
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:00Z",
    });

    renderWithIntl(<OrderConfirmationPage />);
    expect(mockRefreshCart).toHaveBeenCalled();
  });
});
