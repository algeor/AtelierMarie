import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithIntl } from "../test-utils";
import { PriceDisplay } from "@/components/products/PriceDisplay";
import type { ProductResponse } from "@/lib/types";

function product(overrides: Partial<ProductResponse> = {}): ProductResponse {
  return {
    id: "x",
    name: "Candle",
    description: null,
    safety_warnings: null,
    care_instructions: null,
    materials: null,
    days_to_craft: null,
    price_cents: 3250,
    effective_price_cents: 3250,
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
    stock: 10,
    can_order: true,
    available_now: true,
    availability_status: "in_stock",
    ships_when_complete: true,
    is_active: true,
    is_featured: false,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("PriceDisplay", () => {
  it("shows sale price, struck-through original, and −X% badge when active", () => {
    renderWithIntl(
      <PriceDisplay
        product={product({
          price_cents: 3250,
          effective_price_cents: 2600,
          discount_percent: 20,
          discount_active: true,
        })}
      />
    );
    expect(screen.getByText("€26.00")).toBeInTheDocument();
    const original = screen.getByText("€32.50");
    expect(original).toBeInTheDocument();
    expect(original.className).toContain("line-through");
    expect(screen.getByText("−20%")).toBeInTheDocument();
  });

  it("shows only the regular price with no badge when inactive", () => {
    renderWithIntl(
      <PriceDisplay
        product={product({
          price_cents: 3250,
          effective_price_cents: 3250,
          discount_percent: null,
          discount_active: false,
        })}
      />
    );
    expect(screen.getByText("€32.50")).toBeInTheDocument();
    expect(screen.queryByText(/−\d+%/)).not.toBeInTheDocument();
    // No strikethrough element present.
    expect(document.querySelector(".line-through")).toBeNull();
  });
});
