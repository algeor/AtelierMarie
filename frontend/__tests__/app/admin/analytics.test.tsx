import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import AdminAnalyticsPage from "@/app/[locale]/admin/analytics/page";
import { renderWithIntl } from "../../test-utils";

vi.mock("@/lib/api", () => ({
  getAdminAnalyticsSummary: vi.fn(async () => ({
    start_date: "2026-07-01",
    end_date: "2026-07-31",
    consented_sessions: 10,
    accepted_events: 42,
    conversion_rate: 20,
    backend_order_count: 5,
    backend_revenue_cents: 16000,
    analytics_purchase_count: 2,
    analytics_purchase_revenue_cents: 6400,
    coverage_percent: 40,
    consented_order_count: 3,
    consented_order_delta: 1,
    delivery_warning: true,
    health: {
      accepted: 42,
      rejected: 1,
      duplicate: 2,
      validation_failure: 1,
      last_successful_flush_at: null,
      duckdb_load_status: "ok",
      retention_days: 395,
    },
  })),
  getAdminAnalyticsFunnel: vi.fn(async () => ({
    steps: [{ event_type: "product_view", count: 10, conversion_from_previous: 0 }],
  })),
  getAdminAnalyticsProducts: vi.fn(async () => ({
    products: [{ product_id: "lavender", product_name: "Lavender", impressions: 20, clicks: 12, views: 10, add_to_cart: 3, purchases: 2, revenue_cents: 6400, click_through_rate: 60, conversion_rate: 20 }],
  })),
  getAdminAnalyticsCheckout: vi.fn(async () => ({
    checkout_starts: 4,
    order_submits: 3,
    payment_redirects: 1,
    purchase_confirmed: 2,
    delivery_methods: { office: 2 },
    delivery_couriers: { speedy: 2 },
    payment_methods: { cod: 2 },
  })),
  getAdminAnalyticsExportUrl: vi.fn(() => "http://localhost/export.csv"),
}));

describe("AdminAnalyticsPage", () => {
  it("renders summary, funnel, product, coverage, health, and export states", async () => {
    renderWithIntl(<AdminAnalyticsPage />);

    expect(screen.getByRole("heading", { name: "Analytics" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Export CSV" })).toHaveAttribute("href", "http://localhost/export.csv");

    await waitFor(() => expect(screen.getByText("Visitors counted")).toBeInTheDocument());
    expect(screen.getByText("Orders counted")).toBeInTheDocument();
    expect(screen.getByText("Tracking health")).toBeInTheDocument();
    expect(screen.getByText("Product view")).toBeInTheDocument();
    expect(screen.getByText("Lavender")).toBeInTheDocument();
    expect(screen.getByText("Delivery methods")).toBeInTheDocument();
  });
});
