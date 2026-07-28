import React from "react";
import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithIntl } from "../../test-utils";
import { ProductGallery } from "@/components/products/ProductGallery";
import type { ProductImage } from "@/lib/types";

vi.mock("next/image", () => ({
  default: ({ src, alt, ...props }: { src: string; alt: string }) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt={alt} {...props} />
  ),
}));

const image: ProductImage = {
  id: "image-1",
  image_url: "/static/products/lavender.webp",
  thumbnail_url: "/static/products/lavender_thumb.webp",
  zoom_url: "/static/products/lavender_zoom.webp",
  sort_order: 0,
  is_primary: true,
};

describe("ProductGallery", () => {
  it("renders the main image first and opens the zoom image lazily", () => {
    const { container } = renderWithIntl(
      <ProductGallery name="Lavender Dreams" images={[image]} primaryImageUrl={image.image_url} />
    );

    expect(screen.getByAltText("Lavender Dreams")).toHaveAttribute(
      "src",
      expect.stringContaining("/static/products/lavender.webp")
    );
    expect(container.innerHTML).not.toContain("lavender_zoom.webp");

    fireEvent.click(screen.getByRole("button", { name: "Zoom image" }));

    const dialog = screen.getByRole("dialog", { name: "Zoom image" });
    expect(dialog).toBeInTheDocument();
    const renderedImages = screen.getAllByAltText("Lavender Dreams");
    expect(renderedImages[renderedImages.length - 1]).toHaveAttribute(
      "src",
      expect.stringContaining("/static/products/lavender_zoom.webp")
    );

    fireEvent.mouseDown(dialog);
    expect(screen.queryByRole("dialog", { name: "Zoom image" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Zoom image" }));

    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog", { name: "Zoom image" })).not.toBeInTheDocument();
  });

  it("falls back to the main image when zoom_url is missing", () => {
    renderWithIntl(
      <ProductGallery
        name="Lavender Dreams"
        images={[{ ...image, zoom_url: null }]}
        primaryImageUrl={image.image_url}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Zoom image" }));

    const renderedImages = screen.getAllByAltText("Lavender Dreams");
    expect(renderedImages[renderedImages.length - 1]).toHaveAttribute(
      "src",
      expect.stringContaining("/static/products/lavender.webp")
    );
  });
});
