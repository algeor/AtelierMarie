import { describe, expect, it } from "vitest";
import sitemap from "@/app/sitemap";

describe("sitemap", () => {
  it("includes key public marketing and support pages in both locales", () => {
    const entries = sitemap();
    const urls = entries.map((entry) => entry.url);

    expect(urls).toContain("https://ateliermarie.com/en/atelier");
    expect(urls).toContain("https://ateliermarie.com/bg/atelier");
    expect(urls).toContain("https://ateliermarie.com/en/faq");
    expect(urls).toContain("https://ateliermarie.com/bg/faq");
    expect(urls).toContain("https://ateliermarie.com/en/contact");
    expect(urls).toContain("https://ateliermarie.com/bg/contact");
  });
});
