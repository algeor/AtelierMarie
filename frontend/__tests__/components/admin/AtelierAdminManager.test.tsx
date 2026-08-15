import React from "react";
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithIntl } from "../../test-utils";
import { AtelierAdminManager } from "@/components/admin/AtelierAdminManager";
import type { AboutAdminResponse, AboutItemAdmin, AboutSectionAdmin, TaxonomyResponse } from "@/lib/types";

const navigationState = {
  searchParams: new URLSearchParams(),
};

vi.mock("next/navigation", () => ({
  useSearchParams: () => navigationState.searchParams,
}));

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href, className }: { children: React.ReactNode; href: string; className?: string }) => (
    <a href={href} className={className}>{children}</a>
  ),
}));

vi.mock("@/lib/api", () => ({
  clearAboutItemImage: vi.fn(),
  clearAboutSectionImage: vi.fn(),
  createAboutItem: vi.fn(),
  deleteAboutItem: vi.fn(),
  getAdminAbout: vi.fn(),
  getTaxonomy: vi.fn(),
  reorderAboutItems: vi.fn(),
  reorderAboutSections: vi.fn(),
  setAboutItemPublished: vi.fn(),
  setAboutSectionPublished: vi.fn(),
  updateAboutItem: vi.fn(),
  updateAboutSection: vi.fn(),
  uploadAboutItemImage: vi.fn(),
  uploadAboutSectionImage: vi.fn(),
}));

import { createAboutItem, getAdminAbout, getTaxonomy, updateAboutItem, updateAboutSection } from "@/lib/api";

const NOW = "2026-01-01T00:00:00Z";

function makeItem(overrides: Partial<AboutItemAdmin> = {}): AboutItemAdmin {
  return {
    id: 10,
    section: "differentiators",
    title_en: "Handcrafted With Attention to Detail",
    title_bg: "Ръчна изработка с внимание към детайла",
    text_en: "Every candle is individually created in our atelier.",
    text_bg: "Всяка свещ се създава индивидуално в нашето ателие.",
    image_id: null,
    image: null,
    link_href: null,
    sort_order: 0,
    is_published: true,
    created_at: NOW,
    updated_at: NOW,
    ...overrides,
  };
}

function makeSection(overrides: Partial<AboutSectionAdmin> = {}): AboutSectionAdmin {
  return {
    slug: "hero",
    type: "hero",
    heading_en: "The Atelier Marie",
    heading_bg: "The Atelier Marie",
    subheading_en: "Handcrafted Elegance",
    subheading_bg: "Ръчно изработена елегантност",
    body_en: "Atelier intro copy.",
    body_bg: "Уводен текст за ателието.",
    cta_label_en: "Explore our collection",
    cta_label_bg: "Разгледайте колекцията",
    cta_href: "/products",
    image_id: null,
    image: null,
    sort_order: 0,
    is_published: true,
    created_at: NOW,
    updated_at: NOW,
    items: [],
    ...overrides,
  };
}

function makeAbout(): AboutAdminResponse {
  return {
    sections: [
      makeSection(),
      makeSection({
        slug: "differentiators",
        type: "cards",
        heading_en: "What Makes Our Candles Different",
        heading_bg: "Какво отличава нашите свещи",
        subheading_en: "More Than a Candle",
        subheading_bg: "Повече от свещ",
        body_en: null,
        body_bg: null,
        cta_label_en: null,
        cta_label_bg: null,
        cta_href: null,
        sort_order: 1,
        items: [makeItem()],
      }),
      makeSection({
        slug: "collections",
        type: "collections",
        heading_en: "Our Collections",
        heading_bg: "Нашите колекции",
        subheading_en: "Designed to Suit Every Space and Story",
        subheading_bg: "Създадени да подхождат на всяко пространство и история",
        body_en: null,
        body_bg: null,
        cta_label_en: null,
        cta_label_bg: null,
        cta_href: null,
        sort_order: 2,
        items: [
          makeItem({
            id: 20,
            section: "collections",
            title_en: "Floral Collection",
            title_bg: "Флорална колекция",
            text_en: "Romantic designs inspired by nature.",
            text_bg: "Романтични дизайни, вдъхновени от природата.",
            link_href: "/products?category=floral",
          }),
        ],
      }),
      makeSection({
        slug: "emotional",
        type: "text_band",
        heading_en: "A Little Beauty for Everyday Moments",
        heading_bg: "Малко красота за ежедневните мигове",
        subheading_en: "Designed to Become Part of Your Story",
        subheading_bg: "Създадени да станат част от вашата история",
        body_en: "We believe the most beautiful objects are the ones that create a feeling.",
        body_bg: "Вярваме, че най-красивите предмети са тези, които създават усещане.",
        cta_label_en: "Discover the collection",
        cta_label_bg: "Открийте колекцията",
        cta_href: "/products",
        sort_order: 8,
        items: [],
      }),
    ],
  };
}

const TAXONOMY: TaxonomyResponse = {
  product_types: [{ slug: "candles", name: "Candles", sort_order: 0 }],
  categories: [{ slug: "small", name: "Small", sort_order: 0 }],
  labels: [{ slug: "floral", name: "Floral", sort_order: 0 }],
};

const mockedGetAdminAbout = vi.mocked(getAdminAbout);
const mockedGetTaxonomy = vi.mocked(getTaxonomy);
const mockedCreateAboutItem = vi.mocked(createAboutItem);
const mockedUpdateAboutItem = vi.mocked(updateAboutItem);
const mockedUpdateAboutSection = vi.mocked(updateAboutSection);

describe("AtelierAdminManager", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    navigationState.searchParams = new URLSearchParams();
    mockedGetAdminAbout.mockImplementation(async () => makeAbout());
    mockedGetTaxonomy.mockResolvedValue(TAXONOMY);
    mockedCreateAboutItem.mockImplementation(async (slug, data) =>
      makeItem({
        id: 99,
        section: slug,
        title_en: data.title_en,
        title_bg: data.title_bg ?? null,
        text_en: data.text_en ?? null,
        text_bg: data.text_bg ?? null,
        link_href: data.link_href ?? null,
        is_published: data.is_published ?? true,
      })
    );
    mockedUpdateAboutSection.mockImplementation(async (_slug, data) => ({
      ...makeAbout().sections[0]!,
      ...data,
    }));
    mockedUpdateAboutItem.mockImplementation(async (_slug, itemId, data) => ({
      ...makeAbout().sections.flatMap((section) => section.items).find((item) => item.id === itemId)!,
      ...data,
    }));
  });

  it("starts as a focused page builder instead of opening every item form", async () => {
    renderWithIntl(<AtelierAdminManager />);

    expect(await screen.findByRole("heading", { name: "Atelier story" })).toBeInTheDocument();
    expect(screen.getByText("Page sections")).toBeInTheDocument();
    expect(screen.getByText("4 total")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /What Makes Our Candles Different/ }));
    expect(screen.queryByRole("button", { name: "Save item" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Items" }));
    expect(screen.getByText("Handcrafted With Attention to Detail")).toBeInTheDocument();
    expect(screen.queryByLabelText("Link href")).not.toBeInTheDocument();

    const itemCard = screen.getByText("Handcrafted With Attention to Detail").closest("article");
    expect(itemCard).not.toBeNull();
    fireEvent.click(within(itemCard!).getByRole("button", { name: "Edit" }));

    expect(screen.getByRole("button", { name: "Save item" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Link href")).not.toBeInTheDocument();
  });

  it("uses real taxonomy filters for collection item links", async () => {
    renderWithIntl(<AtelierAdminManager />);
    await screen.findByRole("heading", { name: "Atelier story" });

    fireEvent.click(screen.getByRole("button", { name: /Our Collections/ }));
    fireEvent.click(screen.getByRole("tab", { name: "Items" }));

    const itemCard = screen.getByText("Floral Collection").closest("article");
    expect(itemCard).not.toBeNull();
    fireEvent.click(within(itemCard!).getByRole("button", { name: "Edit" }));

    expect(screen.getByText(/floral is a product label/i)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Product filter target"), {
      target: { value: "labels:floral" },
    });

    expect(screen.getByLabelText("Link href")).toHaveValue("/products?labels=floral");
  });

  it("lets local section clicks override the initial URL-selected section", async () => {
    navigationState.searchParams = new URLSearchParams("section=collections&part=content");

    renderWithIntl(<AtelierAdminManager />);

    await waitFor(() => {
      expect(screen.getByLabelText("CTA label EN")).toHaveValue("");
    });

    fireEvent.click(screen.getByRole("button", { name: /A Little Beauty for Everyday Moments/ }));

    await waitFor(() => {
      expect(screen.getByLabelText("CTA label EN")).toHaveValue("Discover the collection");
    });
  });

  it("saves the selected section content through the existing admin API", async () => {
    renderWithIntl(<AtelierAdminManager />);
    await screen.findAllByDisplayValue("The Atelier Marie");

    fireEvent.change(screen.getAllByLabelText("Heading")[0]!, {
      target: { value: "Updated atelier hero" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save content" }));

    await waitFor(() => {
      expect(mockedUpdateAboutSection).toHaveBeenCalledWith(
        "hero",
        expect.objectContaining({ heading_en: "Updated atelier hero" }),
      );
    });
  });

  it("sends only patchable fields when saving a collection item", async () => {
    renderWithIntl(<AtelierAdminManager />);
    await screen.findByRole("heading", { name: "Atelier story" });

    fireEvent.click(screen.getByRole("button", { name: /Our Collections/ }));
    fireEvent.click(screen.getByRole("tab", { name: "Items" }));

    const itemCard = screen.getByText("Floral Collection").closest("article");
    expect(itemCard).not.toBeNull();
    fireEvent.click(within(itemCard!).getByRole("button", { name: "Edit" }));
    fireEvent.click(screen.getByRole("button", { name: "Save item" }));

    await waitFor(() => {
      expect(mockedUpdateAboutItem).toHaveBeenCalledWith(
        "collections",
        20,
        {
          title_en: "Floral Collection",
          title_bg: "Флорална колекция",
          text_en: "Romantic designs inspired by nature.",
          text_bg: "Романтични дизайни, вдъхновени от природата.",
          link_href: "/products?category=floral",
          is_published: true,
        },
      );
    });

    expect(mockedUpdateAboutItem.mock.calls[0]?.[2]).not.toHaveProperty("id");
    expect(mockedUpdateAboutItem.mock.calls[0]?.[2]).not.toHaveProperty("section");
    expect(mockedUpdateAboutItem.mock.calls[0]?.[2]).not.toHaveProperty("created_at");
    expect(mockedUpdateAboutItem.mock.calls[0]?.[2]).not.toHaveProperty("updated_at");
  });

  it("creates a new collection link through the admin API", async () => {
    renderWithIntl(<AtelierAdminManager />);
    await screen.findByRole("heading", { name: "Atelier story" });

    fireEvent.click(screen.getByRole("button", { name: /Our Collections/ }));
    fireEvent.click(screen.getByRole("tab", { name: "Items" }));
    fireEvent.click(screen.getAllByRole("button", { name: "Add link" })[0]!);

    fireEvent.change(screen.getByLabelText("Title EN"), {
      target: { value: "Seasonal Collection" },
    });
    fireEvent.change(screen.getByLabelText("Title BG"), {
      target: { value: "Сезонна колекция" },
    });
    fireEvent.change(screen.getByLabelText("Product filter target"), {
      target: { value: "labels:floral" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Create link" }));

    await waitFor(() => {
      expect(mockedCreateAboutItem).toHaveBeenCalledWith("collections", {
        title_en: "Seasonal Collection",
        title_bg: "Сезонна колекция",
        text_en: null,
        text_bg: null,
        link_href: "/products?labels=floral",
      });
    });

    await waitFor(() => {
      expect(screen.queryByRole("button", { name: "Create link" })).not.toBeInTheDocument();
    });
  });
});
