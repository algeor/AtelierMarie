import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ProductResponse } from "@/lib/types";
import ProductDetailPage from "@/app/[locale]/products/[id]/page";
import { getProduct } from "@/lib/api";

vi.mock("next/navigation", () => ({
  notFound: vi.fn(() => {
    throw new Error("not found");
  }),
}));

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href, className }: { children: React.ReactNode; href: string; className?: string }) => (
    <a href={href} className={className}>{children}</a>
  ),
}));

vi.mock("@/lib/api", () => ({
  getProduct: vi.fn(),
}));

vi.mock("next-intl/server", () => ({
  getTranslations: async ({ namespace }: { namespace: string }) => {
    const products: Record<string, string> = {
      materials: "Materials & Ingredients",
      craftingTime: "Crafting Time",
      craftingTimeDays: "Lovingly handcrafted over 3 days",
      safetyTitle: "Product safety",
      productIdentifier: "Product identifier",
      responsibleParty: "Responsible party",
      responsiblePartyAddress: "Address",
      responsiblePartyEmail: "Contact email",
      safetyWarnings: "Safety warnings",
      careInstructions: "Care and use instructions",
      faqLinksTitle: "Helpful links",
      faqCare: "Candle Care",
      faqCustom: "Custom Orders",
      faqShipping: "Shipping & Returns",
    };
    return (key: string) => (namespace === "products" ? products[key] ?? key : key);
  },
}));

vi.mock("@/components/products/ProductGallery", () => ({
  ProductGallery: () => <div data-testid="product-gallery" />,
}));

vi.mock("@/components/products/PriceDisplay", () => ({
  PriceDisplay: () => <span>€24.00</span>,
}));

vi.mock("@/components/products/AddToCartSection", () => ({
  AddToCartSection: () => <button>Add to Cart</button>,
}));

vi.mock("@/components/products/ProductSocialSection", () => ({
  ProductSocialSection: () => <div data-testid="product-social" />,
}));

const mockedGetProduct = vi.mocked(getProduct);

const PRODUCT: ProductResponse = {
  id: "safety-candle",
  name: "Safety Candle",
  description: "A candle with safety text.",
  safety_warnings: "Never leave a burning candle unattended.",
  care_instructions: "Trim wick before each use.",
  materials: "Soy wax",
  days_to_craft: 3,
  price_cents: 2400,
  effective_price_cents: 2400,
  discount_percent: null,
  discount_active: false,
  category: "medium",
  category_name: "Medium",
  product_type: "candles",
  product_type_name: "Candles",
  labels: [],
  images: [],
  video: null,
  primary_image_url: null,
  primary_thumbnail_url: null,
  stock: 5,
  is_active: true,
  is_featured: false,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("Product detail safety section", () => {
  it("renders product safety metadata and responsible-party details", async () => {
    mockedGetProduct.mockResolvedValue(PRODUCT);

    const ui = await ProductDetailPage({
      params: Promise.resolve({ id: "safety-candle", locale: "en" }),
    });
    render(ui);

    expect(screen.getByRole("heading", { name: "Product safety" })).toBeInTheDocument();
    expect(screen.getByText("safety-candle")).toBeInTheDocument();
    expect(screen.getByText("Never leave a burning candle unattended.")).toBeInTheDocument();
    expect(screen.getByText("Trim wick before each use.")).toBeInTheDocument();
    expect(screen.getByText("Responsible party")).toBeInTheDocument();
    expect(screen.getByText("Atelier Marie")).toBeInTheDocument();
    expect(screen.getByText("contacts@theateliermarie.com")).toBeInTheDocument();
  });
});
