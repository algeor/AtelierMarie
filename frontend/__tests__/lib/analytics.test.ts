import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

describe("analytics client", () => {
  beforeEach(() => {
    vi.resetModules();
    document.cookie = "atelier_cookie_consent=; Max-Age=0; Path=/";
    Object.defineProperty(window, "location", {
      configurable: true,
      value: new URL("http://localhost/en/products/lavender-dream-300ml"),
    });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 202 })));
    Object.defineProperty(navigator, "sendBeacon", {
      configurable: true,
      value: vi.fn(() => false),
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("does not send events without analytics consent", async () => {
    const { flushAnalyticsQueue, setAnalyticsConsent, trackAnalytics } = await import("@/lib/analytics");

    setAnalyticsConsent(false);
    trackAnalytics("product_view", { product_id: "lavender-dream-300ml" });
    await flushAnalyticsQueue();

    expect(fetch).not.toHaveBeenCalled();
    expect(navigator.sendBeacon).not.toHaveBeenCalled();
  });

  it("sends a bounded first-party event when analytics consent is accepted", async () => {
    const { flushAnalyticsQueue, setAnalyticsConsent, trackAnalytics } = await import("@/lib/analytics");

    setAnalyticsConsent(true);
    trackAnalytics("add_to_cart", { product_id: "lavender-dream-300ml", quantity: 1 });
    await flushAnalyticsQueue();

    expect(navigator.sendBeacon).toHaveBeenCalledTimes(1);
    expect(fetch).toHaveBeenCalledTimes(1);
    const fetchMock = vi.mocked(fetch);
    const request = fetchMock.mock.calls[0]?.[1] as RequestInit;
    const body = JSON.parse(String(request.body));
    expect(body.events[0]).toMatchObject({
      event_type: "add_to_cart",
      page_path: "/en/products/lavender-dream-300ml",
      properties: { product_id: "lavender-dream-300ml", quantity: 1 },
    });
    expect(JSON.stringify(body)).not.toContain("email");
    expect(JSON.stringify(body)).not.toContain("phone");
  });

  it("clears queued events when analytics consent is withdrawn", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValueOnce(new Error("network")));
    const { flushAnalyticsQueue, setAnalyticsConsent, trackAnalytics } = await import("@/lib/analytics");

    setAnalyticsConsent(true);
    trackAnalytics("cart_open", { item_count: 1, value_cents: 3200, currency: "BGN" });
    await flushAnalyticsQueue();
    expect(fetch).toHaveBeenCalledTimes(1);

    vi.mocked(fetch).mockResolvedValue(new Response("{}", { status: 202 }));
    setAnalyticsConsent(false);
    setAnalyticsConsent(true);
    await flushAnalyticsQueue();

    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("stores events in memory when mock API mode is enabled", async () => {
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK_API", "true");
    const { flushAnalyticsQueue, getMockAnalyticsEvents, setAnalyticsConsent, trackAnalytics } = await import("@/lib/analytics");

    setAnalyticsConsent(true);
    trackAnalytics("checkout_start", { item_count: 1, value_cents: 3200, currency: "BGN" });
    await flushAnalyticsQueue();

    expect(fetch).not.toHaveBeenCalled();
    expect(getMockAnalyticsEvents()).toHaveLength(1);
    expect(getMockAnalyticsEvents()[0]?.event_type).toBe("checkout_start");
  });
});
