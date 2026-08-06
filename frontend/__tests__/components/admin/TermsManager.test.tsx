import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithIntl } from "../../test-utils";
import type { TermsAdminResponse, TermsSectionAdminResponse } from "@/lib/types";

vi.mock("@/lib/api", () => ({
  getAdminTerms: vi.fn(),
  updateTermsPage: vi.fn(),
  updateTermsSection: vi.fn(),
}));

import { getAdminTerms, updateTermsSection } from "@/lib/api";
import { TermsManager } from "@/components/admin/TermsManager";

const SECTION: TermsSectionAdminResponse = {
  slug: "returns",
  title_en: "Returns",
  title_bg: "Връщане",
  nav_en: "Returns",
  nav_bg: "Връщане",
  body_en: ["Old paragraph"],
  body_bg: ["Стар параграф"],
  model_form_title_en: "Model form",
  model_form_title_bg: "Формуляр",
  model_form_intro_en: "Copy this:",
  model_form_intro_bg: "Копирайте това:",
  model_form_lines_en: ["Line one"],
  model_form_lines_bg: ["Ред едно"],
  sort_order: 0,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const TERMS: TermsAdminResponse = {
  page: {
    id: "terms",
    meta_title_en: "Terms meta",
    meta_title_bg: "Общи условия meta",
    meta_description_en: "Terms description",
    meta_description_bg: "Описание",
    eyebrow_en: "Atelier Marie",
    eyebrow_bg: "Ателие Мари",
    title_en: "Terms & Conditions",
    title_bg: "Общи условия",
    subtitle_en: "Please read these terms.",
    subtitle_bg: "Моля, прочетете условията.",
    last_updated_en: "Last updated",
    last_updated_bg: "Последна актуализация",
    identity_intro_en: "Identity intro",
    identity_intro_bg: "Текст под датата",
    policy_links_title_en: "Related policies",
    policy_links_title_bg: "Свързани политики",
    privacy_link_en: "Privacy Policy",
    privacy_link_bg: "Поверителност",
    cookies_link_en: "Cookie Policy",
    cookies_link_bg: "Бисквитки",
    nav_label_en: "Terms sections",
    nav_label_bg: "Раздели",
    back_to_top_en: "Back to top",
    back_to_top_bg: "Нагоре",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  sections: [SECTION],
};

const mockedGetAdminTerms = vi.mocked(getAdminTerms);
const mockedUpdateTermsSection = vi.mocked(updateTermsSection);

describe("TermsManager", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedGetAdminTerms.mockResolvedValue(TERMS);
    mockedUpdateTermsSection.mockResolvedValue(SECTION);
  });

  it("saves section body and model form lines in both languages", async () => {
    renderWithIntl(<TermsManager />);
    await screen.findByDisplayValue("Terms & Conditions");

    fireEvent.click(screen.getByRole("button", { name: /Returns/ }));

    fireEvent.change(screen.getAllByLabelText("Body")[0]!, {
      target: { value: "First paragraph\n\nSecond paragraph" },
    });
    fireEvent.change(screen.getAllByLabelText("Form lines")[0]!, {
      target: { value: "Line A\nLine B" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save section" }));

    await waitFor(() => {
      expect(mockedUpdateTermsSection).toHaveBeenCalledWith(
        "returns",
        expect.objectContaining({
          body_en: ["First paragraph", "Second paragraph"],
          model_form_lines_en: ["Line A", "Line B"],
        })
      );
    });
  });
});
