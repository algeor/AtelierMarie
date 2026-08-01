import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithIntl } from "../../test-utils";

const api = vi.hoisted(() => ({
  getAdminPrivacy: vi.fn(),
  updatePrivacyPage: vi.fn(),
  updatePrivacySection: vi.fn(),
}));

vi.mock("@/lib/api", () => api);

import AdminPrivacyPage from "@/app/[locale]/admin/privacy/page";

const page = {
  id: "privacy",
  meta_title_en: "Privacy Policy | Atelier Marie",
  meta_title_bg: "Политика за поверителност | Ателие Мари",
  meta_description_en: "How Atelier Marie processes personal data.",
  meta_description_bg: "Как Ателие Мари обработва лични данни.",
  eyebrow_en: "Legal information",
  eyebrow_bg: "Правна информация",
  title_en: "Privacy Policy",
  title_bg: "Политика за поверителност",
  subtitle_en: "This policy explains how we use personal data.",
  subtitle_bg: "Тази политика обяснява как използваме лични данни.",
  last_updated_en: "Last updated: 29 July 2026",
  last_updated_bg: "Последна актуализация: 29 юли 2026 г.",
  controller_title_en: "Controller details",
  controller_title_bg: "Данни за администратора",
  created_at: "2026-07-29T00:00:00Z",
  updated_at: "2026-07-29T00:00:00Z",
};

const section = {
  slug: "rights",
  title_en: "Your rights",
  title_bg: "Вашите права",
  nav_en: "Rights",
  nav_bg: "Права",
  body_en: ["You may ask us to access, correct, or erase your data."],
  body_bg: ["Може да поискате достъп, корекция или изтриване на данните си."],
  sort_order: 0,
  created_at: "2026-07-29T00:00:00Z",
  updated_at: "2026-07-29T00:00:00Z",
};

describe("Admin privacy page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getAdminPrivacy.mockResolvedValue({ page, sections: [section] });
    api.updatePrivacyPage.mockResolvedValue({ ...page, title_en: "Privacy details" });
    api.updatePrivacySection.mockResolvedValue(section);
  });

  it("loads and saves privacy page copy", async () => {
    renderWithIntl(<AdminPrivacyPage />);

    expect(await screen.findByRole("heading", { name: "Privacy" })).toBeInTheDocument();
    fireEvent.change(screen.getByDisplayValue("Privacy Policy"), {
      target: { value: "Privacy details" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save page" }));

    await waitFor(() => {
      expect(api.updatePrivacyPage).toHaveBeenCalledWith(
        expect.objectContaining({ title_en: "Privacy details" })
      );
    });
  });
});
