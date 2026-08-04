import React from "react";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import enMessages from "@/messages/en.json";
import type { ProductResponse } from "@/lib/types";
import { getProducts } from "@/lib/api";
import HomePage from "@/app/[locale]/page";

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href, className }: { children: React.ReactNode; href: string; className?: string }) => (
    <a href={href} className={className}>{children}</a>
  ),
}));

vi.mock("@/lib/api", () => ({
  getProducts: vi.fn(),
}));

vi.mock("@/components/products/HeroSection", () => ({
  HeroSection: () => <section data-testid="home-hero" />,
}));

vi.mock("@/components/rebrand", () => ({
  CategoryLineArt: ({ title }: { title: string }) => <svg role="img" aria-label={title} />,
}));

vi.mock("next-intl/server", () => ({
  getTranslations: async ({ namespace }: { namespace: string }) => {
    const messages = (enMessages as Record<string, unknown>)[namespace] as Record<string, unknown>;
    return (key: string, values?: Record<string, unknown>) => {
      const resolved = key.split(".").reduce<unknown>((current, part) => {
        if (!current || typeof current !== "object") return undefined;
        return (current as Record<string, unknown>)[part];
      }, messages);
      if (key === "categoryCta") return `Browse ${values?.count ?? 0} pieces`;
      return typeof resolved === "string" ? resolved : key;
    };
  },
}));

function product(overrides: Partial<ProductResponse>): ProductResponse {
  return {
    id: "product-1",
    name: "Product",
    description: null,
    safety_warnings: null,
    care_instructions: null,
    materials: null,
    days_to_craft: null,
    price_cents: 1200,
    effective_price_cents: 1200,
    discount_percent: null,
    discount_active: false,
    category: null,
    category_name: null,
    product_type: "candles",
    product_type_name: "Candles",
    labels: [],
    images: [],
    video: null,
    primary_image_url: null,
    primary_thumbnail_url: null,
    stock: 3,
    is_active: true,
    is_featured: false,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

const mockedGetProducts = vi.mocked(getProducts);

describe("homepage rebrand", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders landing categories only when matching products exist", async () => {
    mockedGetProducts.mockResolvedValue({
      products: [
        product({ id: "rose-candle", name: "Rose Candle", product_type: "candles", product_type_name: "Candles" }),
        product({ id: "gift-box", name: "Personal gift box", product_type: "boxes", product_type_name: "Boxes" }),
        product({ id: "room-spray", name: "Room Spray", product_type: "sprays", product_type_name: "Sprays" }),
      ],
      total: 3,
      page: 1,
      limit: 100,
    });

    const ui = await HomePage({ params: Promise.resolve({ locale: "en" }) });
    render(ui);

    expect(screen.getByTestId("home-hero")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Candles/ })).toHaveAttribute("href", "/products?type=candles");
    expect(screen.getByRole("link", { name: /Custom boxes/ })).toHaveAttribute("href", "/products?type=boxes");
    expect(screen.queryByRole("link", { name: /Christmas balls/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Notebooks/ })).not.toBeInTheDocument();
  });
});
