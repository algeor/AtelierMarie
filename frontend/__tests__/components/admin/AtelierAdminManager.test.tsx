import React from "react";
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithIntl } from "../../test-utils";
import { AtelierAdminManager } from "@/components/admin/AtelierAdminManager";
import type { AboutAdminResponse, AboutItemAdmin, AboutSectionAdmin } from "@/lib/types";

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
  reorderAboutItems: vi.fn(),
  reorderAboutSections: vi.fn(),
  setAboutItemPublished: vi.fn(),
  setAboutSectionPublished: vi.fn(),
  updateAboutItem: vi.fn(),
  updateAboutSection: vi.fn(),
  uploadAboutItemImage: vi.fn(),
  uploadAboutSectionImage: vi.fn(),
}));

import { getAdminAbout, updateAboutSection } from "@/lib/api";

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
    ],
  };
}

const mockedGetAdminAbout = vi.mocked(getAdminAbout);
const mockedUpdateAboutSection = vi.mocked(updateAboutSection);

describe("AtelierAdminManager", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedGetAdminAbout.mockImplementation(async () => makeAbout());
    mockedUpdateAboutSection.mockImplementation(async (_slug, data) => ({
      ...makeAbout().sections[0]!,
      ...data,
    }));
  });

  it("starts as a focused page builder instead of opening every item form", async () => {
    renderWithIntl(<AtelierAdminManager />);

    expect(await screen.findByRole("heading", { name: "Atelier story" })).toBeInTheDocument();
    expect(screen.getByText("Page sections")).toBeInTheDocument();
    expect(screen.getByText("2 total")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /What Makes Our Candles Different/ }));
    expect(screen.queryByRole("button", { name: "Save item" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Items" }));
    expect(screen.getByText("Handcrafted With Attention to Detail")).toBeInTheDocument();
    expect(screen.queryByLabelText("Link href")).not.toBeInTheDocument();

    const itemCard = screen.getByText("Handcrafted With Attention to Detail").closest("article");
    expect(itemCard).not.toBeNull();
    fireEvent.click(within(itemCard!).getByRole("button", { name: "Edit" }));

    expect(screen.getByRole("button", { name: "Save item" })).toBeInTheDocument();
    expect(screen.getByLabelText("Link href")).toBeInTheDocument();
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
});
