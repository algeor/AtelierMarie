import { describe, expect, it, vi } from "vitest";
import sitemap from "@/app/sitemap";

vi.mock("@/lib/api", () => ({
  getProducts: vi.fn(async () => ({
    products: [],
    total: 0,
    page: 1,
    limit: 100,
  })),
}));

describe("sitemap", () => {
  it("includes key public marketing and support pages in both locales", async () => {
    const entries = await sitemap();
    const urls = entries.map((entry) => entry.url);

    expect(urls).toContain("https://ateliermarie.com/en/atelier");
    expect(urls).toContain("https://ateliermarie.com/bg/atelier");
    expect(urls).toContain("https://ateliermarie.com/en/faq");
    expect(urls).toContain("https://ateliermarie.com/bg/faq");
    expect(urls).toContain("https://ateliermarie.com/en/contact");
    expect(urls).toContain("https://ateliermarie.com/bg/contact");
    expect(urls).toContain("https://ateliermarie.com/en/handmade-candles");
    expect(urls).toContain("https://ateliermarie.com/bg/rachno-izraboteni-sveshti");
  });

  it("omits private and transactional pages", async () => {
    const entries = await sitemap();
    const urls = entries.map((entry) => entry.url);

    expect(urls).not.toContain("https://ateliermarie.com/en/checkout");
    expect(urls).not.toContain("https://ateliermarie.com/en/orders");
    expect(urls).not.toContain("https://ateliermarie.com/en/account");
  });
});
