import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CookieConsentProvider } from "@/contexts/CookieConsentContext";
import AdminAnalyticsPage from "@/app/[locale]/admin/analytics/page";
import { renderWithIntl } from "../test-utils";

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href, className }: { children: React.ReactNode; href: string; className?: string }) => (
    <a href={href} className={className}>{children}</a>
  ),
  usePathname: () => "/",
}));

vi.mock("@/lib/api", () => ({
  getAdminAnalyticsSummary: vi.fn(async () => ({
    start_date: "2026-07-01",
    end_date: "2026-07-31",
    consented_sessions: 0,
    accepted_events: 0,
    conversion_rate: 0,
    backend_order_count: 0,
    backend_revenue_cents: 0,
    analytics_purchase_count: 0,
    analytics_purchase_revenue_cents: 0,
    coverage_percent: 0,
    consented_order_count: 0,
    consented_order_delta: 0,
    delivery_warning: false,
    health: {
      accepted: 0,
      rejected: 0,
      duplicate: 0,
      validation_failure: 0,
      last_successful_flush_at: null,
      duckdb_load_status: "ok",
      retention_days: 395,
    },
  })),
  getAdminAnalyticsFunnel: vi.fn(async () => ({ steps: [] })),
  getAdminAnalyticsProducts: vi.fn(async () => ({ products: [] })),
  getAdminAnalyticsCheckout: vi.fn(async () => ({
    checkout_starts: 0,
    order_submits: 0,
    payment_redirects: 0,
    purchase_confirmed: 0,
    delivery_methods: {},
    delivery_couriers: {},
    payment_methods: {},
  })),
  getAdminAnalyticsExportUrl: vi.fn(() => "http://localhost/export.csv"),
}));

function setViewport(width: number) {
  Object.defineProperty(window, "innerWidth", { configurable: true, value: width });
  window.dispatchEvent(new Event("resize"));
}

describe("analytics responsive surfaces", () => {
  it.each([375, 1280])("renders consent popup controls at %ipx", (width) => {
    setViewport(width);
    document.cookie = "atelier_cookie_consent=; Max-Age=0; Path=/";

    renderWithIntl(
      <CookieConsentProvider>
        <div>Storefront</div>
      </CookieConsentProvider>
    );

    const popup = screen.getByRole("region", { name: "Cookie preferences" });
    expect(popup).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Accept analytics" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Necessary only" })).toBeInTheDocument();
    expect(popup.firstElementChild).toHaveClass("max-w-3xl");
    expect(popup.querySelector(".sm\\:flex-row")).toBeTruthy();
  });

  it.each([390, 1440])("renders admin analytics responsive sections at %ipx", async (width) => {
    setViewport(width);
    renderWithIntl(<AdminAnalyticsPage />);

    await waitFor(() => expect(screen.getByText("Consented sessions")).toBeInTheDocument());
    expect(screen.getByRole("heading", { name: "Analytics" })).toBeInTheDocument();
    expect(screen.getByText("Funnel").closest("section")?.querySelector(".overflow-x-auto"))
      .toBeTruthy();
    expect(screen.getByText("Checkout, delivery, and payment").closest("section")?.querySelector(".md\\:grid-cols-3"))
      .toBeTruthy();
  });
});
