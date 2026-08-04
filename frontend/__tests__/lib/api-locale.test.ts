import { beforeEach, describe, expect, it, vi } from "vitest";
import { getAdminStats, getProduct, getProducts, updateLocalePreference } from "@/lib/api";

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("API locale contracts", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    global.fetch = vi.fn().mockResolvedValue(
      jsonResponse({ products: [], total: 0, page: 1, limit: 100 })
    );
  });

  it("passes locale to product list requests", async () => {
    await getProducts(1, 100, "bg");

    expect(global.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/v1/products?page=1&limit=100&locale=bg",
      expect.any(Object)
    );
  });

  it("passes locale to product detail requests", async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(jsonResponse({ id: "candle" }));

    await getProduct("candle", "bg");

    expect(global.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/v1/products/candle?locale=bg",
      expect.any(Object)
    );
  });

  it("updates backend session locale through the locale endpoint", async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(jsonResponse({ locale: "bg" }));

    await updateLocalePreference("bg");

    expect(global.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/v1/locale",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ locale: "bg" }),
      })
    );
  });
  it("normalizes nested backend admin stats", async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(
      jsonResponse({
        products: { total: 4, active: 3 },
        orders: { total: 5, revenue_cents: 22000, by_status: {} },
        low_stock_count: 2,
      })
    );

    await expect(getAdminStats()).resolves.toEqual({
      orders_today: 5,
      revenue_this_week_cents: 22000,
      active_product_count: 3,
    });
  });

  it("uses the dashboard endpoint for admin stats", async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(
      jsonResponse({
        orders_today: 0,
        revenue_this_week_cents: 0,
        active_product_count: 0,
      })
    );

    await getAdminStats();

    expect(global.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/v1/admin/dashboard",
      expect.any(Object)
    );
  });

});
