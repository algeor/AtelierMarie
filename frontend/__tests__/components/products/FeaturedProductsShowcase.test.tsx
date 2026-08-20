import React from "react";
import { act, fireEvent } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
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
    can_order: true,
    available_now: true,
    availability_status: "in_stock",
    ships_when_complete: true,
    is_active: true,
    is_featured: true,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function featuredProducts() {
  return [
    product({ id: "first", name: "First candle" }),
    product({ id: "second", name: "Second candle" }),
    product({ id: "third", name: "Third candle" }),
  ];
}

describe("FeaturedProductsShowcase", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("keeps inactive carousel slides out of the tab order", () => {
    const { container } = renderWithIntl(<FeaturedProductsShowcase products={featuredProducts()} />);

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

  it("auto-rotates featured products every 10 seconds", () => {
    vi.useFakeTimers();

    const { container } = renderWithIntl(<FeaturedProductsShowcase products={featuredProducts()} />);
    const cards = Array.from(container.querySelectorAll("article"));

    expect(cards[0]).not.toHaveAttribute("aria-hidden");

    act(() => {
      vi.advanceTimersByTime(10000);
    });

    expect(cards[0]).toHaveAttribute("aria-hidden", "true");
    expect(cards[1]).not.toHaveAttribute("aria-hidden");
  });

  it("moves to the next product on horizontal swipe", () => {
    const { container } = renderWithIntl(<FeaturedProductsShowcase products={featuredProducts()} />);
    const viewport = container.querySelector(".featured-carousel-viewport");
    const cards = Array.from(container.querySelectorAll("article"));

    expect(viewport).not.toBeNull();
    expect(cards[0]).not.toHaveAttribute("aria-hidden");

    fireEvent.pointerDown(viewport!, {
      button: 0,
      clientX: 220,
      clientY: 120,
      pointerId: 1,
      pointerType: "touch",
    });
    fireEvent.pointerUp(viewport!, {
      clientX: 120,
      clientY: 124,
      pointerId: 1,
      pointerType: "touch",
    });

    expect(cards[0]).toHaveAttribute("aria-hidden", "true");
    expect(cards[1]).not.toHaveAttribute("aria-hidden");
  });

  it("uses fixed-size panel text clamps for long product copy", () => {
    const { container, getByText } = renderWithIntl(
      <FeaturedProductsShowcase
        products={[
          product({
            id: "long",
            name: "A very long atelier candle name that should stay polished inside the card",
            category_name: "A very long handcrafted seasonal collection label",
          }),
        ]}
      />,
    );

    expect(container.querySelector(".featured-preview-card__panel")).toHaveClass("flex", "flex-col");
    expect(getByText("A very long handcrafted seasonal collection label")).toHaveClass(
      "featured-preview-card__descriptor",
    );
    expect(container.querySelector(".featured-preview-card__title")).toHaveTextContent(
      "A very long atelier candle name that should stay polished inside the card",
    );
  });
});
