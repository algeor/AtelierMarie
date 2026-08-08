import { screen, waitFor, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import React from "react";
import { renderWithIntl } from "../../test-utils";
import type { AdminProductListResponse, AdminProductResponse, UserResponse } from "@/lib/types";

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  usePathname: () => "/admin/products",
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/admin/products",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/api", () => ({
  getCurrentUser: vi.fn(),
  getAdminProducts: vi.fn(),
  updateProduct: vi.fn(),
  bulkDiscount: vi.fn(),
}));

import { getCurrentUser, getAdminProducts, bulkDiscount } from "@/lib/api";

const mockedGetCurrentUser = vi.mocked(getCurrentUser);
const mockedGetAdminProducts = vi.mocked(getAdminProducts);
const mockedBulkDiscount = vi.mocked(bulkDiscount);

const ADMIN_USER: UserResponse = {
  id: "u1",
  email: "marie@x.com",
  name: "Marie",
  avatar_url: null,
  is_admin: true,
};

function product(id: string, name: string): AdminProductResponse {
  return {
    id,
    name_en: name,
    name_bg: null,
    description_en: null,
    description_bg: null,
    safety_warnings_en: null,
    safety_warnings_bg: null,
    care_instructions_en: null,
    care_instructions_bg: null,
    materials: null,
    days_to_craft: null,
    price_cents: 3000,
    discount_percent: null,
    discount_starts_at: null,
    discount_ends_at: null,
    effective_price_cents: 3000,
    discount_active: false,
    category: "Floral",
    product_type: "candles",
    labels: [],
    images: [],
    video: null,
    primary_image_url: null,
    primary_thumbnail_url: null,
    stock: 5,
    weight_grams: 300,
    is_active: true,
    is_featured: false,
    translation_stale_bg: false,
    translation_stale_en: false,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

const LIST: AdminProductListResponse = {
  products: [product("a-candle", "Alpha"), product("b-candle", "Beta")],
  total: 2,
  page: 1,
  limit: 100,
};

async function renderPage() {
  const { AdminProvider } = await import("@/contexts/AdminContext");
  const { AdminGuard } = await import("@/components/admin/AdminGuard");
  const Page = (await import("@/app/[locale]/admin/products/page")).default;
  return renderWithIntl(
    <AdminProvider>
      <AdminGuard>
        <Page />
      </AdminGuard>
    </AdminProvider>
  );
}

describe("Admin products list — multi-select + bulk bar (task 9.10)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedGetCurrentUser.mockResolvedValue(ADMIN_USER);
    mockedGetAdminProducts.mockResolvedValue(LIST);
  });

  it("bulk bar is hidden until a row is selected, then shows the count", async () => {
    await renderPage();
    expect((await screen.findAllByText("Alpha")).length).toBeGreaterThan(0);

    // No selection → no bulk bar.
    expect(screen.queryByText(/selected/)).not.toBeInTheDocument();

    // Select the first product row (aria-label is the product name).
    fireEvent.click(screen.getAllByLabelText("Alpha")[0]!);

    expect(await screen.findByText("1 selected")).toBeInTheDocument();
  });

  it("select-all checks every row; toggling again clears the selection", async () => {
    await renderPage();
    expect((await screen.findAllByText("Alpha")).length).toBeGreaterThan(0);

    fireEvent.click(screen.getByLabelText("Select all"));
    expect(await screen.findByText("2 selected")).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("Select all"));
    await waitFor(() => {
      expect(screen.queryByText(/selected/)).not.toBeInTheDocument();
    });
  });

  it("applies a bulk discount to the selection and shows the summary", async () => {
    mockedBulkDiscount.mockResolvedValue({
      success_count: 2,
      failure_count: 0,
      results: [
        { id: "a-candle", status: "updated" },
        { id: "b-candle", status: "updated" },
      ],
    });
    await renderPage();
    expect((await screen.findAllByText("Alpha")).length).toBeGreaterThan(0);

    fireEvent.click(screen.getByLabelText("Select all"));
    await screen.findByText("2 selected");

    fireEvent.change(screen.getByLabelText("Discount percent (1–99)"), {
      target: { value: "20" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply discount" }));

    await waitFor(() => {
      expect(mockedBulkDiscount).toHaveBeenCalledWith(
        expect.objectContaining({
          operation: "apply",
          product_ids: ["a-candle", "b-candle"],
          discount_percent: 20,
        })
      );
      expect(screen.getByText("2 updated, 0 failed")).toBeInTheDocument();
    });
  });
});
