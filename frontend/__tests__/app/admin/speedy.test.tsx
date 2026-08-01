import React from "react";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithIntl } from "../../test-utils";
import { ApiError } from "@/lib/api-client";
import type { SpeedyAdminOverviewResponse } from "@/lib/types";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(""),
}));

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("@/lib/api", () => ({
  cancelSpeedyShipment: vi.fn(),
  createSpeedyWaybill: vi.fn(),
  getSpeedyAdminOverview: vi.fn(),
  getSpeedyPickupTerms: vi.fn(),
  getSpeedyShipmentInfo: vi.fn(),
  refreshSpeedyTracking: vi.fn(),
  requestSpeedyPickup: vi.fn(),
  searchSpeedyShipments: vi.fn(),
}));

import {
  createSpeedyWaybill,
  getSpeedyAdminOverview,
  getSpeedyPickupTerms,
  requestSpeedyPickup,
} from "@/lib/api";
import AdminSpeedyPage from "@/app/[locale]/admin/speedy/page";

const mockedGetOverview = vi.mocked(getSpeedyAdminOverview);
const mockedCreateWaybill = vi.mocked(createSpeedyWaybill);
const mockedGetPickupTerms = vi.mocked(getSpeedyPickupTerms);
const mockedRequestPickup = vi.mocked(requestSpeedyPickup);

const overview: SpeedyAdminOverviewResponse = {
  health: {
    status: "healthy",
    ok: true,
    message: "Speedy configuration is healthy.",
    username_configured: true,
    password_configured: true,
    client_id_configured: true,
    client_id_numeric: true,
    configured_client_id: "123456",
    verified_client_id: "123456",
    client_id_matches: true,
    blockers: [],
    circuit: {
      name: "speedy_operational",
      state: "closed",
      failure_count: 0,
      failure_threshold: 3,
      recovery_remaining_seconds: null,
    },
    last_failure_category: null,
    last_successful_check_at: "2026-08-01T09:00:00Z",
    checked_at: "2026-08-01T10:00:00Z",
  },
  queues: {
    ready_to_ship: [
      {
        order_id: "order-ready-1",
        order_number: "AM-0001",
        status: "confirmed",
        customer_email: "ready@example.com",
        customer_name: "Ready Buyer",
        delivery_method: "office",
        delivery_label: "Sofia Center",
        total_cents: 2500,
        tracking_number: null,
        tracking_url: null,
        courier_status: null,
        courier_sync_status: null,
        courier_last_error: null,
        courier_last_synced_at: null,
        created_at: "2026-08-01T08:00:00Z",
        updated_at: "2026-08-01T08:00:00Z",
      },
    ],
    shipped: [
      {
        order_id: "order-shipped-1",
        order_number: "AM-0002",
        status: "shipped",
        customer_email: "shipped@example.com",
        customer_name: "Shipped Buyer",
        delivery_method: "office",
        delivery_label: "Sofia Center",
        total_cents: 2600,
        tracking_number: "63689182611",
        tracking_url: "https://www.speedy.bg/en/track-shipment?shipmentNumber=63689182611",
        courier_status: "in_transit",
        courier_sync_status: "track_synced",
        courier_last_error: null,
        courier_last_synced_at: "2026-08-01T09:30:00Z",
        created_at: "2026-08-01T08:00:00Z",
        updated_at: "2026-08-01T09:30:00Z",
      },
    ],
  },
  events: [
    {
      id: 1,
      order_id: "order-shipped-1",
      action: "refresh_tracking",
      status: "success",
      request: { shipmentNumber: "63689182611" },
      response: { courier_status: "in_transit" },
      error: null,
      actor_user_id: null,
      created_at: "2026-08-01T09:30:00Z",
    },
  ],
  metrics: {
    recent_successes: 1,
    recent_failures: 0,
    failures_by_category: {},
    cancellation_count: 0,
    pickup_request_count: 0,
    last_successful_health_check_at: "2026-08-01T09:00:00Z",
  },
  office_refresh: {
    status: "success",
    refreshed_at: "2026-08-01T00:00:00Z",
    records: 1284,
    error: null,
  },
};

function blockedOverview(): SpeedyAdminOverviewResponse {
  return {
    ...overview,
    health: {
      ...overview.health,
      status: "blocked",
      ok: false,
      message: "Speedy configuration is incomplete.",
      username_configured: false,
      password_configured: false,
      client_id_configured: false,
      client_id_numeric: false,
      configured_client_id: null,
      verified_client_id: null,
      client_id_matches: null,
      blockers: ["username_missing", "password_missing", "client_id_missing"],
    },
    queues: { ready_to_ship: [], shipped: [] },
  };
}

describe("AdminSpeedyPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedGetOverview.mockResolvedValue(overview);
  });

  it("renders healthy state, queues, metrics, and redacted history", async () => {
    renderWithIntl(<AdminSpeedyPage />);

    expect(await screen.findByText("Speedy Operations")).toBeInTheDocument();
    expect(screen.getByText("Healthy")).toBeInTheDocument();
    expect(screen.getByText("AM-0001")).toBeInTheDocument();
    expect(screen.getByText("AM-0002")).toBeInTheDocument();
    expect(screen.getByText("63689182611")).toBeInTheDocument();
    expect(screen.getByText("Recent history")).toBeInTheDocument();
    expect(screen.queryByText(/speedy-secret/i)).not.toBeInTheDocument();
  });

  it("renders blocked health without shipment actions failing the page", async () => {
    mockedGetOverview.mockResolvedValue(blockedOverview());

    renderWithIntl(<AdminSpeedyPage />);

    expect(await screen.findByText("Blocked")).toBeInTheDocument();
    expect(screen.getByText("Speedy configuration is incomplete.")).toBeInTheDocument();
    expect(screen.getByText("No confirmed Speedy orders waiting for waybills.")).toBeInTheDocument();
  });

  it("creates a waybill and refreshes the overview", async () => {
    mockedCreateWaybill.mockResolvedValue({
      order_id: "order-ready-1",
      action: "create_waybill",
      status: "created",
      shipment_number: "63689182612",
      tracking_url: null,
      courier_status: null,
      status_updated_to: "shipped",
      details: null,
    });
    const user = userEvent.setup();

    renderWithIntl(<AdminSpeedyPage />);
    await user.click(await screen.findByRole("button", { name: "Create waybill" }));

    await waitFor(() => {
      expect(mockedCreateWaybill).toHaveBeenCalledWith("order-ready-1");
    });
    expect(await screen.findByText("Speedy waybill created")).toBeInTheDocument();
    expect(mockedGetOverview).toHaveBeenCalledTimes(2);
  });

  it("shows action failure messages safely", async () => {
    mockedCreateWaybill.mockRejectedValue(
      new ApiError({
        error: { code: "SPEEDY_VALIDATION", message: "Already picked up", details: null },
      }),
    );
    const user = userEvent.setup();

    renderWithIntl(<AdminSpeedyPage />);
    await user.click(await screen.findByRole("button", { name: "Create waybill" }));

    expect(await screen.findByText("Already picked up")).toBeInTheDocument();
    expect(screen.queryByText(/speedy-secret/i)).not.toBeInTheDocument();
  });

  it("requests pickup terms and submits a pickup request for selected shipments", async () => {
    mockedGetPickupTerms.mockResolvedValue({ cutoffs: ["2026-08-02T14:00:00+03:00"] });
    mockedRequestPickup.mockResolvedValue({ orders: [{ id: "pickup-1" }] });
    const user = userEvent.setup();

    renderWithIntl(<AdminSpeedyPage />);
    await user.click(await screen.findByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: "Get terms" }));

    expect(await screen.findByText("2026-08-02T14:00:00+03:00")).toBeInTheDocument();
    await user.type(screen.getByLabelText("Visit end time"), "17:00");
    await user.type(screen.getByLabelText("Contact name"), "Mira");
    await user.type(screen.getByLabelText("Phone"), "+359888123456");
    await user.click(screen.getByRole("button", { name: "Request pickup" }));

    await waitFor(() => {
      expect(mockedRequestPickup).toHaveBeenCalledWith({
        shipment_ids: ["63689182611"],
        pickup_datetime: "2026-08-02T14:00:00+03:00",
        visit_end_time: "17:00",
        contact_name: "Mira",
        phone: "+359888123456",
      });
    });
    expect(await screen.findByText("Pickup requested")).toBeInTheDocument();
  });
});
