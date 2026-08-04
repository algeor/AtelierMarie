import React from "react";
import { describe, expect, it, vi } from "vitest";
import { renderWithIntl } from "../../test-utils";
import { FeaturedProductsShowcase } from "@/components/products/FeaturedProductsShowcase";
import type { ProductResponse } from "@/lib/types";

vi.mock("@/i18n/navigation", () => ({
  Link: ({
    children,
    href,
    className,
    tabIndex,
  }: {
    children: React.ReactNode;
    href: string;
    className?: string;
    tabIndex?: number;
  }) => (
    <a href={href} className={className} tabIndex={tabIndex}>
      {children}
    </a>
  ),
}));

vi.mock("@/contexts/CartContext", () => ({
  useCart: () => ({
    addToCart: vi.fn(),
    openDrawer: vi.fn(),
  }),
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
    is_featured: true,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("FeaturedProductsShowcase", () => {
  it("keeps inactive carousel slides out of the tab order", () => {
    const { container } = renderWithIntl(
      <FeaturedProductsShowcase
        products={[
          product({ id: "first", name: "First candle" }),
          product({ id: "second", name: "Second candle" }),
          product({ id: "third", name: "Third candle" }),
        ]}
      />,
    );

    const cards = Array.from(container.querySelectorAll("article"));
    expect(cards).toHaveLength(3);
    expect(cards[0]).not.toHaveAttribute("aria-hidden");

    for (const inactiveCard of cards.slice(1)) {
      expect(inactiveCard).toHaveAttribute("aria-hidden", "true");
      expect(inactiveCard).toHaveClass("pointer-events-none");

      const interactiveElements = inactiveCard.querySelectorAll("a, button");
      expect(interactiveElements.length).toBeGreaterThan(0);
      interactiveElements.forEach((element) => {
        expect(element).toHaveAttribute("tabindex", "-1");
      });
    }
  });
});
