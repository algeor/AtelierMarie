import { beforeEach, describe, expect, it, vi } from "vitest";
import { getProduct, getProducts, updateLocalePreference } from "@/lib/api";

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
});
