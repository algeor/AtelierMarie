import React from "react";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { renderWithIntl } from "../../test-utils";
import { ProductListingClient } from "@/components/products/ProductListingClient";
import type { ProductResponse, TaxonomyResponse } from "@/lib/types";

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href, className }: { children: React.ReactNode; href: string; className?: string }) => (
    <a href={href} className={className}>{children}</a>
  ),
}));

vi.mock("@/contexts/CartContext", () => ({
  useCart: () => ({
    addToCart: vi.fn(),
    openDrawer: vi.fn(),
  }),
}));

const taxonomy: TaxonomyResponse = {
  product_types: [
    { slug: "candles", name: "Candles", sort_order: 0 },
    { slug: "boxes", name: "Boxes", sort_order: 1 },
  ],
  categories: [
    { slug: "small", name: "Small", sort_order: 0 },
    { slug: "medium", name: "Medium", sort_order: 1 },
    { slug: "premium", name: "Premium", sort_order: 2 },
  ],
  labels: [],
};

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
    category: "small",
    category_name: "Small",
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

const products = [
  product({ id: "candle-small", name: "Small Candle", category: "small", category_name: "Small" }),
  product({ id: "candle-medium", name: "Medium Candle", category: "medium", category_name: "Medium" }),
  product({
    id: "box-premium",
    name: "Premium Gift Box",
    category: "premium",
    category_name: "Premium",
    product_type: "boxes",
    product_type_name: "Boxes",
  }),
];

describe("ProductListingClient taxonomy menu", () => {
  beforeEach(() => {
    window.history.replaceState(null, "", "/en/products");
  });

  it("opens a hamburger product menu with product types and nested categories", async () => {
    const user = userEvent.setup();
    renderWithIntl(<ProductListingClient products={products} taxonomy={taxonomy} />);

    await user.click(screen.getByRole("button", { name: "Open product menu" }));

    const menu = screen.getByLabelText("Product menu");
    expect(within(menu).getByRole("button", { name: /Candles/ })).toBeInTheDocument();
    expect(within(menu).getByRole("button", { name: /Boxes/ })).toBeInTheDocument();
    expect(within(menu).getByRole("button", { name: "Small" })).toBeInTheDocument();
    expect(within(menu).getByRole("button", { name: "Medium" })).toBeInTheDocument();
    expect(within(menu).queryByRole("button", { name: "Premium" })).not.toBeInTheDocument();

    await user.click(within(menu).getByRole("button", { name: /Boxes/ }));

    expect(within(menu).getByRole("button", { name: "Premium" })).toBeInTheDocument();
  });

  it("filters by product type and category from the menu", async () => {
    const user = userEvent.setup();
    renderWithIntl(<ProductListingClient products={products} taxonomy={taxonomy} />);

    await user.click(screen.getByRole("button", { name: "Open product menu" }));
    const menu = screen.getByLabelText("Product menu");
    await user.click(within(menu).getByRole("button", { name: /Boxes/ }));
    await user.click(within(menu).getByRole("button", { name: "Premium" }));

    expect(screen.queryByLabelText("Product menu")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Premium Gift Box" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Small Candle" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Boxes/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Premium/ })).toBeInTheDocument();
  });

  it("sorts by effective sale price", async () => {
    window.history.replaceState(null, "", "/en/products?sort=price_asc");
    renderWithIntl(
      <ProductListingClient
        products={[
          product({
            id: "sale-candle",
            name: "Sale Candle",
            price_cents: 5000,
            effective_price_cents: 1000,
            discount_percent: 80,
            discount_active: true,
          }),
          product({
            id: "plain-candle",
            name: "Plain Candle",
            price_cents: 2000,
            effective_price_cents: 2000,
          }),
        ]}
        taxonomy={taxonomy}
      />
    );

    await waitFor(() => {
      const names = screen.getAllByRole("heading", { level: 3 }).map((heading) => heading.textContent);
      expect(names).toEqual(["Sale Candle", "Plain Candle"]);
    });
  });

  it("hydrates supported product type and category filters from the URL", async () => {
    window.history.replaceState(null, "", "/en/products?type=boxes&category=premium");

    renderWithIntl(<ProductListingClient products={products} taxonomy={taxonomy} />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Premium Gift Box" })).toBeInTheDocument();
      expect(screen.queryByRole("heading", { name: "Small Candle" })).not.toBeInTheDocument();
      expect(screen.queryByRole("heading", { name: "Medium Candle" })).not.toBeInTheDocument();
    });

    expect(screen.getByRole("button", { name: /Boxes/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Premium/ })).toBeInTheDocument();
  });

  it("falls back to all products for unsupported URL filters", async () => {
    window.history.replaceState(null, "", "/en/products?type=missing&category=ghost");

    renderWithIntl(<ProductListingClient products={products} taxonomy={taxonomy} />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Small Candle" })).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Medium Candle" })).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Premium Gift Box" })).toBeInTheDocument();
    });
  });
});
