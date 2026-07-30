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

const product: AdminProductResponse = {
  id: "lavender-dreams-300ml",
  name_en: "Lavender Dreams",
  name_bg: null,
  description_en: "Hand-poured soy candle",
  description_bg: null,
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
  images: [],
  primary_image_url: null,
  primary_thumbnail_url: null,
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

describe("ProductForm image upload size checks", () => {
  it("adds a small image without prompting", () => {
    renderForm();

    const input = screen.getByLabelText("Product images") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [sizedImage(2 * 1024 * 1024)] } });

    expect(screen.getByText("1 file(s) selected")).toBeInTheDocument();
    expect(screen.queryByRole("dialog", { name: "Large image" })).not.toBeInTheDocument();
  });

  it("asks before adding a 15-25MB image", () => {
    renderForm();

    const input = screen.getByLabelText("Product images") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [sizedImage(16 * 1024 * 1024)] } });

    const dialog = screen.getByRole("dialog", { name: "Large image" });
    expect(dialog).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));
    expect(screen.queryByText("1 file(s) selected")).not.toBeInTheDocument();

    fireEvent.change(input, { target: { files: [sizedImage(16 * 1024 * 1024)] } });
    fireEvent.click(
      within(screen.getByRole("dialog", { name: "Large image" })).getByRole("button", {
        name: "Add anyway",
      })
    );

    expect(screen.getByText("1 file(s) selected")).toBeInTheDocument();
  });

  it("blocks images over 25MB before adding them", () => {
    renderForm();

    const input = screen.getByLabelText("Product images") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [sizedImage(26 * 1024 * 1024)] } });

    expect(screen.getByText("Image must be 25 MB or smaller")).toBeInTheDocument();
    expect(screen.queryByText("1 file(s) selected")).not.toBeInTheDocument();
    expect(screen.queryByRole("dialog", { name: "Large image" })).not.toBeInTheDocument();
  });

  it("warns at exactly the 15MB threshold", () => {
    renderForm();

    const input = screen.getByLabelText("Product images") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [sizedImage(15 * 1024 * 1024)] } });

    expect(screen.getByRole("dialog", { name: "Large image" })).toBeInTheDocument();
  });

  it("warns (does not block) at exactly the 25MB cap", () => {
    renderForm();

    const input = screen.getByLabelText("Product images") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [sizedImage(25 * 1024 * 1024)] } });

    expect(screen.getByRole("dialog", { name: "Large image" })).toBeInTheDocument();
    expect(screen.queryByText("Image must be 25 MB or smaller")).not.toBeInTheDocument();
  });

  it("resets the input value so the same file can be re-selected", () => {
    renderForm();

    const input = screen.getByLabelText("Product images") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [sizedImage(2 * 1024 * 1024)] } });

    expect(input.value).toBe("");
  });

  it("keeps the large-image dialog modal and blocks submit until resolved", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    renderForm(onSubmit);

    const input = screen.getByLabelText("Product images") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [sizedImage(16 * 1024 * 1024)] } });

    const dialog = screen.getByRole("dialog", { name: "Large image" });
    const cancel = within(dialog).getByRole("button", { name: "Cancel" });
    const addAnyway = within(dialog).getByRole("button", { name: "Add anyway" });
    expect(cancel).toHaveFocus();

    fireEvent.keyDown(document, { key: "Tab", shiftKey: true });
    expect(addAnyway).toHaveFocus();

    fireEvent.submit(screen.getByRole("button", { name: "Save" }).closest("form")!);
    expect(onSubmit).not.toHaveBeenCalled();

    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog", { name: "Large image" })).not.toBeInTheDocument();

    fireEvent.change(input, { target: { files: [sizedImage(16 * 1024 * 1024)] } });
    fireEvent.mouseDown(screen.getByRole("dialog", { name: "Large image" }).parentElement!);
    expect(screen.queryByRole("dialog", { name: "Large image" })).not.toBeInTheDocument();

    fireEvent.change(input, { target: { files: [sizedImage(16 * 1024 * 1024)] } });
    fireEvent.click(
      within(screen.getByRole("dialog", { name: "Large image" })).getByRole("button", {
        name: "Add anyway",
      })
    );
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit.mock.calls[0]![0].image_files).toHaveLength(1);
  });
});
