import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

async function loadMedia() {
  vi.resetModules();
  return import("@/lib/media");
}

describe("media URL resolution", () => {
  it("uses NEXT_PUBLIC_MEDIA_URL for backend static media", async () => {
    vi.stubEnv("NEXT_PUBLIC_MEDIA_URL", "https://cdn.example.com/assets/");
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://api.example.com/");
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK_API", "false");

    const { MEDIA_URL, resolveMediaUrl } = await loadMedia();

    expect(MEDIA_URL).toBe("https://cdn.example.com/assets");
    expect(resolveMediaUrl("/static/products/candle.webp")).toBe(
      "https://cdn.example.com/assets/static/products/candle.webp"
    );
  });

  it("falls back to the API origin for real backend mode", async () => {
    vi.stubEnv("NEXT_PUBLIC_MEDIA_URL", "");
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://api.example.com/");
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK_API", "false");

    const { MEDIA_URL, resolveMediaUrl } = await loadMedia();

    expect(MEDIA_URL).toBe("https://api.example.com");
    expect(resolveMediaUrl("/static/products/candle.webp")).toBe(
      "https://api.example.com/static/products/candle.webp"
    );
  });

  it("keeps bundled mock media relative when no media origin is configured", async () => {
    vi.stubEnv("NEXT_PUBLIC_MEDIA_URL", "");
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://api.example.com/");
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK_API", "true");

    const { MEDIA_URL, resolveMediaUrl } = await loadMedia();

    expect(MEDIA_URL).toBe("");
    expect(resolveMediaUrl("/static/products/candle.webp")).toBe(
      "/static/products/candle.webp"
    );
  });

  it("leaves external and non-static URLs unchanged", async () => {
    vi.stubEnv("NEXT_PUBLIC_MEDIA_URL", "https://cdn.example.com");
    vi.stubEnv("NEXT_PUBLIC_USE_MOCK_API", "false");

    const { resolveMediaUrl } = await loadMedia();

    expect(resolveMediaUrl("https://images.example.com/candle.webp")).toBe(
      "https://images.example.com/candle.webp"
    );
    expect(resolveMediaUrl("/images/candle.webp")).toBe("/images/candle.webp");
    expect(resolveMediaUrl(null)).toBeNull();
  });
});
