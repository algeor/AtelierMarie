import React from "react";
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ProductForm } from "@/components/admin/ProductForm";
import type { AdminProductResponse } from "@/lib/types";
import { renderWithIntl } from "../../test-utils";

vi.mock("next/image", () => ({
  default: ({ src, alt, ...props }: { src: string; alt: string }) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt={alt} {...props} />
  ),
}));

vi.mock("@/i18n/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/lib/api", () => ({
  getAdminTaxonomy: vi.fn((kind: string) => {
    const terms = {
      "product-types": [
        {
          slug: "candles",
          name_en: "Candles",
          name_bg: null,
          sort_order: 0,
          is_active: true,
          product_count: 1,
          created_at: "2024-06-01T10:00:00Z",
          updated_at: "2024-06-01T10:00:00Z",
        },
      ],
      categories: [
        {
          slug: "floral",
          name_en: "Floral",
          name_bg: null,
          sort_order: 0,
          is_active: true,
          product_count: 1,
          created_at: "2024-06-01T10:00:00Z",
          updated_at: "2024-06-01T10:00:00Z",
        },
      ],
      labels: [],
    } as const;
    return Promise.resolve(terms[kind as keyof typeof terms] ?? []);
  }),
}));

// Stub the cropper: report a crop area immediately so the confirm button enables.
vi.mock("react-easy-crop", () => ({
  default: ({
    onCropComplete,
  }: {
    onCropComplete?: (a: unknown, b: unknown) => void;
  }) => {
    React.useEffect(() => {
      onCropComplete?.(
        { x: 0, y: 0, width: 100, height: 100 },
        { x: 0, y: 0, width: 100, height: 100 }
      );
    }, [onCropComplete]);
    return <div data-testid="cropper" />;
  },
}));

// Control the framed-blob size the editor exports, per test.
const cropState = vi.hoisted(() => ({ size: 2 * 1024 * 1024 }));
vi.mock("@/lib/cropImage", () => ({
  getCroppedImg: vi.fn(async () => {
    const file = new File(["x"], "cropped.jpg", { type: "image/jpeg" });
    Object.defineProperty(file, "size", { value: cropState.size });
    return file;
  }),
}));

const product: AdminProductResponse = {
  id: "lavender-dreams-300ml",
  name_en: "Lavender Dreams",
  name_bg: null,
  description_en: "Hand-poured soy candle",
  description_bg: null,
  safety_warnings_en: "Never leave unattended.",
  safety_warnings_bg: null,
  care_instructions_en: "Trim wick before use.",
  care_instructions_bg: null,
  materials: "Soy wax",
  days_to_craft: 3,
  price_cents: 3200,
  discount_percent: null,
  discount_starts_at: null,
  discount_ends_at: null,
  effective_price_cents: 3200,
  discount_active: false,
  category: "Floral",
  product_type: "candles",
  labels: [],
  images: [
    {
      id: "img-1",
      image_url: "/static/products/lavender.webp",
      thumbnail_url: "/static/products/lavender-thumb.webp",
      zoom_url: null,
      sort_order: 0,
      is_primary: true,
    },
  ],
  video: null,
  primary_image_url: "/static/products/lavender.webp",
  primary_thumbnail_url: "/static/products/lavender-thumb.webp",
  stock: 24,
  weight_grams: 300,
  is_active: true,
  is_featured: false,
  translation_stale_bg: false,
  translation_stale_en: false,
  created_at: "2024-06-01T10:00:00Z",
  updated_at: "2024-06-01T10:00:00Z",
};

function sizedImage(size: number): File {
  const file = new File(["x"], "candle.jpg", { type: "image/jpeg" });
  Object.defineProperty(file, "size", { value: size });
  return file;
}

function renderForm(onSubmit = vi.fn()) {
  return renderWithIntl(
    <ProductForm product={product} onSubmit={onSubmit} submitLabel="Save" />
  );
}

/** Select a file, then confirm the crop editor with the configured output size. */
async function selectAndFrame(input: HTMLInputElement, file: File, framedSize?: number) {
  if (framedSize !== undefined) cropState.size = framedSize;
  fireEvent.change(input, { target: { files: [file] } });
  const useImage = await screen.findByRole("button", { name: "Use image" });
  fireEvent.click(useImage);
}

describe("ProductForm image crop editor", () => {
  it("opens the crop editor on selection and commits the framed image", async () => {
    cropState.size = 2 * 1024 * 1024;
    renderForm();

    const input = screen.getByLabelText("Product images") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [sizedImage(2 * 1024 * 1024)] } });

    // Editor appears; image is not committed until confirmed.
    expect(await screen.findByRole("dialog", { name: "Adjust image" })).toBeInTheDocument();
    expect(screen.queryByText("1 file(s) selected")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Use image" }));

    await waitFor(() => expect(screen.getByText("1 file(s) selected")).toBeInTheDocument());
  });

  it("discards the file when the editor is cancelled", async () => {
    renderForm();

    const input = screen.getByLabelText("Product images") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [sizedImage(2 * 1024 * 1024)] } });

    const dialog = await screen.findByRole("dialog", { name: "Adjust image" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));

    expect(screen.queryByRole("dialog", { name: "Adjust image" })).not.toBeInTheDocument();
    expect(screen.queryByText("1 file(s) selected")).not.toBeInTheDocument();
  });

  it("blocks originals over 25MB before the editor opens", () => {
    renderForm();

    const input = screen.getByLabelText("Product images") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [sizedImage(26 * 1024 * 1024)] } });

    expect(screen.getByText("Image must be 25 MB or smaller")).toBeInTheDocument();
    expect(screen.queryByRole("dialog", { name: "Adjust image" })).not.toBeInTheDocument();
  });

  it("warns before adding a framed image between 15 and 25MB", async () => {
    renderForm();

    const input = screen.getByLabelText("Product images") as HTMLInputElement;
    await selectAndFrame(input, sizedImage(2 * 1024 * 1024), 16 * 1024 * 1024);

    const dialog = await screen.findByRole("dialog", { name: "Large image" });
    expect(dialog).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));
    expect(screen.queryByText("1 file(s) selected")).not.toBeInTheDocument();

    await selectAndFrame(input, sizedImage(2 * 1024 * 1024), 16 * 1024 * 1024);
    fireEvent.click(
      within(await screen.findByRole("dialog", { name: "Large image" })).getByRole("button", {
        name: "Add anyway",
      })
    );
    expect(screen.getByText("1 file(s) selected")).toBeInTheDocument();
  });

  it("blocks a framed image over 25MB", async () => {
    renderForm();

    const input = screen.getByLabelText("Product images") as HTMLInputElement;
    await selectAndFrame(input, sizedImage(2 * 1024 * 1024), 26 * 1024 * 1024);

    await waitFor(() =>
      expect(screen.getByText("Image must be 25 MB or smaller")).toBeInTheDocument()
    );
    expect(screen.queryByText("1 file(s) selected")).not.toBeInTheDocument();
  });

  it("submits the framed image in image_files", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    renderForm(onSubmit);

    const input = screen.getByLabelText("Product images") as HTMLInputElement;
    await selectAndFrame(input, sizedImage(2 * 1024 * 1024), 2 * 1024 * 1024);
    await waitFor(() => expect(screen.getByText("1 file(s) selected")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit.mock.calls[0]![0].image_files).toHaveLength(1);
  });

  it("submits localized safety metadata", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    renderForm(onSubmit);

    fireEvent.change(screen.getByLabelText("Safety warnings (English)"), {
      target: { value: "Keep away from curtains." },
    });
    fireEvent.change(screen.getByLabelText("Care instructions (Bulgarian)"), {
      target: { value: "Подрязвайте фитила." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit.mock.calls[0]![0]).toEqual(
      expect.objectContaining({
        safety_warnings_en: "Keep away from curtains.",
        safety_warnings_bg: "",
        care_instructions_en: "Trim wick before use.",
        care_instructions_bg: "Подрязвайте фитила.",
      })
    );
  });

  it("blocks active products without a product image", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    renderWithIntl(
      <ProductForm
        product={{ ...product, images: [], primary_image_url: null, primary_thumbnail_url: null, is_active: true }}
        onSubmit={onSubmit}
        submitLabel="Save"
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findAllByText("Active products need at least one product image.")).not.toHaveLength(0);
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
