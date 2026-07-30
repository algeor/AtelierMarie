import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import { renderWithIntl } from "../test-utils";
import { ProductCard } from "@/components/products/ProductCard";
import { ProductGallery } from "@/components/products/ProductGallery";
import type { ProductImage, ProductResponse, ProductVideo } from "@/lib/types";

vi.mock("next/image", () => ({
  default: ({ src, alt, ...props }: { src: string; alt: string }) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt={alt} {...props} />
  ),
}));

vi.mock("@/i18n/navigation", () => ({
  Link: ({ href, children, ...props }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

vi.mock("@/components/cart/AddToCartButton", () => ({
  AddToCartButton: () => <button type="button">Add to cart</button>,
}));

function image(id: string, sortOrder: number): ProductImage {
  return {
    id,
    image_url: `/static/products/${id}.webp`,
    thumbnail_url: `/static/products/${id}-thumb.webp`,
    sort_order: sortOrder,
    is_primary: sortOrder === 0,
  };
}

function video(overrides: Partial<ProductVideo> = {}): ProductVideo {
  return {
    id: "video-1",
    product_id: "candle",
    status: "ready",
    video_url: "/static/products/candle-video.mp4",
    poster_url: "/static/products/candle-poster.webp",
    sort_order: 1,
    duration_secs: 10,
    failure_reason: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function product(overrides: Partial<ProductResponse> = {}): ProductResponse {
  return {
    id: "candle",
    name: "Candle",
    description: null,
    materials: null,
    days_to_craft: null,
    price_cents: 3200,
    effective_price_cents: 3200,
    discount_percent: null,
    discount_active: false,
    category: null,
    images: [],
    video: null,
    primary_image_url: "/static/products/candle.webp",
    primary_thumbnail_url: "/static/products/candle-thumb.webp",
    stock: 4,
    is_active: true,
    is_featured: false,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
});

describe("product video rendering", () => {
  it("inserts the video thumbnail at the configured gallery position", () => {
    const { container } = renderWithIntl(
      <ProductGallery
        name="Candle"
        images={[image("first", 0), image("second", 1)]}
        video={video({ sort_order: 1 })}
        primaryImageUrl="/static/products/first.webp"
      />
    );

    const thumbnails = [...container.querySelectorAll(".grid img")].map((img) =>
      img.getAttribute("src")
    );

    expect(thumbnails).toEqual([
      "http://localhost:8000/static/products/first-thumb.webp",
      "http://localhost:8000/static/products/candle-poster.webp",
      "http://localhost:8000/static/products/second-thumb.webp",
    ]);
  });

  it("places the video thumbnail last when sort order exceeds image count", () => {
    const { container } = renderWithIntl(
      <ProductGallery
        name="Candle"
        images={[image("first", 0), image("second", 1)]}
        video={video({ sort_order: 10 })}
        primaryImageUrl="/static/products/first.webp"
      />
    );

    const thumbnails = [...container.querySelectorAll(".grid img")].map((img) =>
      img.getAttribute("src")
    );

    expect(thumbnails).toEqual([
      "http://localhost:8000/static/products/first-thumb.webp",
      "http://localhost:8000/static/products/second-thumb.webp",
      "http://localhost:8000/static/products/candle-poster.webp",
    ]);
  });

  it("shows the poster instead of autoplay video for reduced motion", () => {
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: query === "(prefers-reduced-motion: reduce)",
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    const { container } = renderWithIntl(
      <ProductGallery
        name="Candle"
        images={[image("first", 0)]}
        video={video({ sort_order: 0 })}
        primaryImageUrl={null}
      />
    );

    expect(container.querySelector("video")).not.toBeInTheDocument();
    expect(screen.getByAltText("Candle")).toHaveAttribute(
      "src",
      "http://localhost:8000/static/products/candle-poster.webp"
    );
  });

  it("uses the poster still on product cards and never renders a video element", () => {
    const { container } = renderWithIntl(
      <ProductCard product={product({ video: video(), primary_image_url: "/static/products/main.webp" })} />
    );

    expect(screen.getByAltText("Candle")).toHaveAttribute(
      "src",
      "http://localhost:8000/static/products/candle-poster.webp"
    );
    expect(container.querySelector("video")).not.toBeInTheDocument();
  });
});
