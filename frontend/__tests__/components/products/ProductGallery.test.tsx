import React from "react";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithIntl } from "../../test-utils";
import { ProductGallery } from "@/components/products/ProductGallery";
import type { ProductImage, ProductVideo } from "@/lib/types";

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

const secondImage: ProductImage = {
  id: "image-2",
  image_url: "/static/products/amber.webp",
  thumbnail_url: "/static/products/amber_thumb.webp",
  zoom_url: "/static/products/amber_zoom.webp",
  sort_order: 2,
  is_primary: false,
};

const readyVideo: ProductVideo = {
  id: "vid-1",
  product_id: "lavender-dreams",
  status: "ready",
  video_url: "/static/products/lavender_video.mp4",
  poster_url: "/static/products/lavender_poster.webp",
  sort_order: 1,
  duration_secs: 12,
  failure_reason: null,
  created_at: "2024-06-01T10:00:00Z",
  updated_at: "2024-06-01T10:00:00Z",
};

describe("ProductGallery", () => {
  it("renders the main image and loads the zoom asset only when the lightbox opens", () => {
    const { container } = renderWithIntl(
      <ProductGallery name="Lavender Dreams" images={[image]} primaryImageUrl={image.image_url} />
    );

    // Hero uses the main derivative; the zoom asset is not requested up front.
    expect(screen.getByAltText("Lavender Dreams")).toHaveAttribute(
      "src",
      expect.stringContaining("/static/products/lavender.webp")
    );
    expect(container.ownerDocument.body.innerHTML).not.toContain("lavender_zoom.webp");

    fireEvent.click(screen.getByRole("button", { name: "Zoom image" }));

    // The open lightbox renders the high-res zoom derivative.
    const zoomImg = Array.from(document.querySelectorAll("img")).find((img) =>
      img.getAttribute("src")?.includes("lavender_zoom.webp")
    );
    expect(zoomImg).toBeTruthy();
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

    // No zoom asset exists, so the lightbox slide uses the main image_url.
    const slideImg = Array.from(document.querySelectorAll("img")).find((img) =>
      img.getAttribute("src")?.includes("/static/products/lavender.webp")
    );
    expect(slideImg).toBeTruthy();
    expect(document.body.innerHTML).not.toContain("lavender_zoom.webp");
  });

  it("closes the lightbox via the close control", async () => {
    renderWithIntl(
      <ProductGallery name="Lavender Dreams" images={[image]} primaryImageUrl={image.image_url} />
    );

    fireEvent.click(screen.getByRole("button", { name: "Zoom image" }));
    const closeButton = screen.getByRole("button", { name: "Close zoom" });
    expect(closeButton).toBeInTheDocument();

    fireEvent.click(closeButton);
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Close zoom" })).not.toBeInTheDocument()
    );
  });

  it("builds one ordered carousel over images and the video", () => {
    renderWithIntl(
      <ProductGallery
        name="Lavender Dreams"
        images={[image, secondImage]}
        video={readyVideo}
        primaryImageUrl={image.image_url}
      />
    );

    // Open the lightbox from the hero, then page across to the video slide.
    fireEvent.click(screen.getByRole("button", { name: "Zoom image" }));
    fireEvent.click(screen.getByRole("button", { name: "Next" }));

    // The video slide (sort_order 1, between the two images) is reachable in the
    // same viewer and carries the video source.
    const source = document.querySelector('video source[src*="lavender_video.mp4"]');
    expect(source).toBeTruthy();
  });

  it("opens the lightbox on the selected thumbnail's image", () => {
    renderWithIntl(
      <ProductGallery
        name="Lavender Dreams"
        images={[image, secondImage]}
        primaryImageUrl={image.image_url}
      />
    );

    // Thumbnail buttons are labelled with the product name; select the second.
    const thumbs = screen.getAllByRole("button", { name: "Lavender Dreams" });
    fireEvent.click(thumbs[thumbs.length - 1]!);

    fireEvent.click(screen.getByRole("button", { name: "Zoom image" }));

    const zoomImg = Array.from(document.querySelectorAll("img")).find((img) =>
      img.getAttribute("src")?.includes("amber_zoom.webp")
    );
    expect(zoomImg).toBeTruthy();
  });
});
