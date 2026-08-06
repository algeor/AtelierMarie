import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CookiesManager } from "@/components/admin/CookiesManager";
import type { CookiesAdminResponse, CookieSectionAdminResponse } from "@/lib/types";
import { renderWithIntl } from "../../test-utils";

vi.mock("@/lib/api", () => ({
  getAdminCookies: vi.fn(),
  updateCookiesPage: vi.fn(),
  updateCookieSection: vi.fn(),
}));

import { getAdminCookies, updateCookieSection } from "@/lib/api";

const SECTION: CookieSectionAdminResponse = {
  slug: "controls",
  title_en: "Cookie controls",
  title_bg: "Контрол на бисквитки",
  body_en: ["Old paragraph"],
  body_bg: ["Стар параграф"],
  sort_order: 0,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const COOKIES: CookiesAdminResponse = {
  page: {
    id: "cookies",
    meta_title_en: "Cookie Policy",
    meta_title_bg: "Политика за бисквитки",
    meta_description_en: "Cookie description",
    meta_description_bg: "Описание",
    eyebrow_en: "Legal information",
    eyebrow_bg: "Правна информация",
    title_en: "Cookie Policy",
    title_bg: "Политика за бисквитки",
    subtitle_en: "Current cookie inventory.",
    subtitle_bg: "Текущ списък с бисквитки.",
    last_updated_en: "Last updated",
    last_updated_bg: "Последна актуализация",
    inventory_title_en: "Current cookie inventory",
    inventory_title_bg: "Текущ cookie inventory",
    header_name_en: "Name",
    header_name_bg: "Име",
    header_purpose_en: "Purpose",
    header_purpose_bg: "Цел",
    header_type_en: "Type",
    header_type_bg: "Тип",
    header_duration_en: "Duration",
    header_duration_bg: "Срок",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  cookies: [
    {
      name: "atelier_cookie_consent",
      purpose_en: "Stores consent choice.",
      purpose_bg: "Запазва избора за съгласие.",
      type_en: "Consent preference cookie",
      type_bg: "Cookie за съгласие",
      duration_en: "Up to 1 year.",
      duration_bg: "До 1 година.",
      source: "browser_cookie_audit",
      first_seen_at: "2026-01-01T00:00:00Z",
      last_seen_at: "2026-01-02T00:00:00Z",
      last_audited_at: "2026-01-02T00:00:00Z",
      observed_on: ["/en"],
      is_active: true,
      auto_detected: true,
      sort_order: 0,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-02T00:00:00Z",
    },
  ],
  sections: [SECTION],
};

const mockedGetAdminCookies = vi.mocked(getAdminCookies);
const mockedUpdateCookieSection = vi.mocked(updateCookieSection);

describe("CookiesManager", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedGetAdminCookies.mockResolvedValue(COOKIES);
    mockedUpdateCookieSection.mockResolvedValue({
      ...SECTION,
      body_en: ["First paragraph", "Second paragraph"],
    });
  });

  it("shows auto-generated inventory and saves editable section text", async () => {
    renderWithIntl(<CookiesManager />);
    await screen.findAllByDisplayValue("Cookie Policy");

    fireEvent.click(screen.getByRole("button", { name: /Cookie inventory/ }));

    expect(screen.getAllByText("Rows are populated automatically by the deploy cookie audit.").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("atelier_cookie_consent")).toBeInTheDocument();
    expect(screen.getByText("Auto-detected")).toBeInTheDocument();
    expect(screen.getByText(/Source: browser_cookie_audit/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Cookie controls/ }));

    fireEvent.change(screen.getAllByLabelText("Body")[0]!, {
      target: { value: "First paragraph\n\nSecond paragraph" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save section" }));

    await waitFor(() => {
      expect(mockedUpdateCookieSection).toHaveBeenCalledWith(
        "controls",
        expect.objectContaining({ body_en: ["First paragraph", "Second paragraph"] })
      );
    });
  });
});
