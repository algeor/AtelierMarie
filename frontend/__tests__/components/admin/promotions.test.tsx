import { screen, waitFor, fireEvent, within } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { renderWithIntl } from "../../test-utils";
import type {
  AdminProductResponse,
  BulkDiscountResponse,
  CampaignListResponse,
  CampaignResponse,
} from "@/lib/types";

vi.mock("@/lib/api", () => ({
  getCampaigns: vi.fn(),
  getCampaign: vi.fn(),
  createCampaign: vi.fn(),
  updateCampaign: vi.fn(),
  deleteCampaign: vi.fn(),
  applyCampaign: vi.fn(),
  removeCampaign: vi.fn(),
  bulkDiscount: vi.fn(),
  getAdminProducts: vi.fn(),
  getAdminBanner: vi.fn(),
  updateBanner: vi.fn(),
}));

import {
  getCampaigns,
  applyCampaign,
  getAdminProducts,
  createCampaign,
  updateCampaign,
  bulkDiscount,
  getAdminBanner,
} from "@/lib/api";
import { CampaignsPanel } from "@/components/admin/promotions/CampaignsPanel";
import { CampaignForm } from "@/components/admin/promotions/CampaignForm";
import { BannerPanel } from "@/components/admin/promotions/BannerPanel";
import { ProductBulkDiscountBar } from "@/components/admin/promotions/ProductBulkDiscountBar";
import { BulkResultSummary } from "@/components/admin/promotions/BulkResultSummary";

const mockedGetCampaigns = vi.mocked(getCampaigns);
const mockedApplyCampaign = vi.mocked(applyCampaign);
const mockedGetAdminProducts = vi.mocked(getAdminProducts);
const mockedCreateCampaign = vi.mocked(createCampaign);
const mockedUpdateCampaign = vi.mocked(updateCampaign);
const mockedBulkDiscount = vi.mocked(bulkDiscount);
const mockedGetAdminBanner = vi.mocked(getAdminBanner);

const CAMPAIGN: CampaignResponse = {
  id: "c1",
  name: "Spring Sale",
  note: null,
  discount_percent: 20,
  discount_starts_at: null,
  discount_ends_at: null,
  target_type: "ids",
  target_count: 2,
  target_ids: ["candle-1", "candle-2"],
  target_filter: null,
  status: "draft",
  applied_at: null,
  removed_at: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  last_result: null,
};

const APPLY_RESULT: BulkDiscountResponse = {
  success_count: 1,
  failure_count: 1,
  results: [
    { id: "a", status: "updated" },
    { id: "ghost", status: "failed", error: "Product not found: ghost" },
  ],
};

function adminProduct(id: string, name: string): AdminProductResponse {
  return {
    id,
    name_en: name,
    name_bg: null,
    description_en: null,
    description_bg: null,
    materials: null,
    days_to_craft: null,
    price_cents: 1000,
    discount_percent: null,
    discount_starts_at: null,
    discount_ends_at: null,
    effective_price_cents: 1000,
    discount_active: false,
    category: "candles",
    images: [],
    primary_image_url: null,
    primary_thumbnail_url: null,
    stock: 1,
    is_active: true,
    is_featured: false,
    translation_stale_bg: false,
    translation_stale_en: false,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

describe("BulkResultSummary", () => {
  it("renders N updated, M failed with failed detail", () => {
    renderWithIntl(<BulkResultSummary result={APPLY_RESULT} />);
    expect(screen.getByText("1 updated, 1 failed")).toBeInTheDocument();
    expect(screen.getByText("ghost")).toBeInTheDocument();
  });
});

describe("CampaignsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedGetCampaigns.mockResolvedValue({ items: [CAMPAIGN], total: 1 } as CampaignListResponse);
  });

  it("lists campaigns with status and discount summary", async () => {
    renderWithIntl(<CampaignsPanel />);
    expect(await screen.findByText("Spring Sale")).toBeInTheDocument();
    expect(screen.getByText("Draft")).toBeInTheDocument();
    expect(screen.getByText("20% off")).toBeInTheDocument();
    expect(screen.getByText("Active window")).toBeInTheDocument();
    expect(screen.getByText("Always on")).toBeInTheDocument();
  });

  it("apply shows confirmation then result summary", async () => {
    mockedApplyCampaign.mockResolvedValue(APPLY_RESULT);
    renderWithIntl(<CampaignsPanel />);
    await screen.findByText("Spring Sale");

    fireEvent.click(screen.getByRole("button", { name: "Apply" }));
    // Confirmation dialog appears.
    const heading = await screen.findByText("Apply campaign discount?");
    const dialog = heading.closest("div")!;
    expect(within(dialog).getByText(/Window: Always on/)).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "Apply" }));

    await waitFor(() => {
      expect(mockedApplyCampaign).toHaveBeenCalledWith("c1");
      expect(screen.getByText("1 updated, 1 failed")).toBeInTheDocument();
    });
  });
});

describe("CampaignForm validation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedGetAdminProducts.mockResolvedValue({ products: [], total: 0, page: 1, limit: 100 });
  });

  it("blocks submit with invalid percent and no target", async () => {
    const { container } = renderWithIntl(
      <CampaignForm campaign={null} onSaved={vi.fn()} onCancel={vi.fn()} />
    );
    // Fill name, invalid percent 100.
    fireEvent.change(screen.getByLabelText("Campaign name"), { target: { value: "X" } });
    fireEvent.change(screen.getByLabelText("Discount percent (1–99)"), {
      target: { value: "100" },
    });
    fireEvent.submit(container.querySelector("form")!);

    await waitFor(() => {
      expect(
        screen.getByText(/Discount percent must be between 1 and 99/)
      ).toBeInTheDocument();
    });
    expect(mockedCreateCampaign).not.toHaveBeenCalled();
  });

  it("preserves an existing filter target when editing metadata", async () => {
    const filterCampaign: CampaignResponse = {
      ...CAMPAIGN,
      id: "filter-campaign",
      target_type: "filter",
      target_count: 3,
      target_ids: null,
      target_filter: { category: "spring" },
    };
    mockedUpdateCampaign.mockResolvedValue(filterCampaign);
    const { container } = renderWithIntl(
      <CampaignForm campaign={filterCampaign} onSaved={vi.fn()} onCancel={vi.fn()} />
    );

    fireEvent.change(screen.getByLabelText("Campaign name"), {
      target: { value: "Renamed" },
    });
    fireEvent.submit(container.querySelector("form")!);

    await waitFor(() => {
      expect(mockedUpdateCampaign).toHaveBeenCalledWith(
        "filter-campaign",
        expect.objectContaining({ name: "Renamed" })
      );
    });
    const payload = mockedUpdateCampaign.mock.calls[0]![1];
    expect(payload).not.toHaveProperty("filter");
    expect(payload).not.toHaveProperty("product_ids");
  });

  it("selects explicit campaign targets across product pages", async () => {
    mockedGetAdminProducts.mockImplementation(async (page = 1, limit = 100) => ({
      products:
        page === 1
          ? [adminProduct("first-product", "First product")]
          : [adminProduct("second-product", "Second product")],
      total: 101,
      page,
      limit,
    }));
    mockedCreateCampaign.mockResolvedValue(CAMPAIGN);
    const { container } = renderWithIntl(
      <CampaignForm campaign={null} onSaved={vi.fn()} onCancel={vi.fn()} />
    );

    fireEvent.change(screen.getByLabelText("Campaign name"), {
      target: { value: "Two-page campaign" },
    });
    fireEvent.change(screen.getByLabelText("Discount percent (1–99)"), {
      target: { value: "15" },
    });

    fireEvent.click(await screen.findByLabelText(/First product/));
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    fireEvent.click(await screen.findByLabelText(/Second product/));
    fireEvent.submit(container.querySelector("form")!);

    await waitFor(() => {
      expect(mockedCreateCampaign).toHaveBeenCalledWith(
        expect.objectContaining({
          product_ids: ["first-product", "second-product"],
        })
      );
    });
  });
});

describe("BannerPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedGetAdminBanner.mockResolvedValue({
      message_en: "Hello",
      message_bg: null,
      link_label_en: null,
      link_label_bg: null,
      link_url: null,
      is_enabled: true,
      starts_at: null,
      ends_at: null,
      version: 1,
      updated_at: "2026-01-01T00:00:00Z",
    });
  });

  it("shows a live preview of the message", async () => {
    renderWithIntl(<BannerPanel />);
    // Preview reflects the loaded message.
    await waitFor(() => {
      const previews = screen.getAllByText("Hello");
      expect(previews.length).toBeGreaterThan(0);
    });
  });
});

describe("ProductBulkDiscountBar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("applies discount and shows N updated, M failed", async () => {
    mockedBulkDiscount.mockResolvedValue(APPLY_RESULT);
    renderWithIntl(<ProductBulkDiscountBar selectedIds={["a", "ghost"]} onDone={vi.fn()} />);

    expect(screen.getByText("2 selected")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Discount percent (1–99)"), {
      target: { value: "20" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply discount" }));

    await waitFor(() => {
      expect(mockedBulkDiscount).toHaveBeenCalledWith(
        expect.objectContaining({ operation: "apply", product_ids: ["a", "ghost"], discount_percent: 20 })
      );
      expect(screen.getByText("1 updated, 1 failed")).toBeInTheDocument();
    });
  });
});
