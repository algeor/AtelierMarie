import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api-client";
import { getAdminStats, getCurrentUser, getProduct, getProducts, updateLocalePreference } from "@/lib/api";

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

  it("passes public product listing filters to product list requests", async () => {
    await getProducts(2, 24, "en", {
      product_type: "candles",
      category: "small",
      labels: ["floral", "gift"],
      q: "lavender",
      sort: "price_asc",
      in_stock: true,
    });

    expect(global.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/v1/products?page=2&limit=24&locale=en&product_type=candles&category=small&labels=floral%2Cgift&q=lavender&sort=price_asc&in_stock=1",
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

  it("treats 204 auth hydration as anonymous", async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(new Response(null, { status: 204 }));

    await expect(getCurrentUser()).resolves.toBeNull();
  });

  it("treats NOT_AUTHENTICATED as anonymous for auth hydration", async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          error: { code: "NOT_AUTHENTICATED", message: "User not found", details: null },
        }),
        {
          status: 401,
          headers: { "Content-Type": "application/json" },
        }
      )
    );

    await expect(getCurrentUser()).resolves.toBeNull();
  });

  it("still rethrows non-auth API failures from auth hydration", async () => {
    vi.mocked(global.fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          error: { code: "RATE_LIMITED", message: "Slow down", details: null },
        }),
        {
          status: 429,
          headers: { "Content-Type": "application/json" },
        }
      )
    );

    await expect(getCurrentUser()).rejects.toBeInstanceOf(ApiError);
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
      low_stock_count: 2,
      contact_messages_needing_attention: 0,
      orders: {
        total: 5,
        revenue_cents: 22000,
        by_status: {},
        by_payment_status: {},
      },
      products: {
        total: 4,
        active: 3,
      },
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
