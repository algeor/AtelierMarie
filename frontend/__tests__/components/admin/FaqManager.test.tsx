import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithIntl } from "../../test-utils";
import type { FaqAdminResponse, FaqItemAdminResponse } from "@/lib/types";

vi.mock("@/lib/api", () => ({
  getAdminFaq: vi.fn(),
  createFaqItem: vi.fn(),
  updateFaqItem: vi.fn(),
  deleteFaqItem: vi.fn(),
  reorderFaqItems: vi.fn(),
  updateFaqSection: vi.fn(),
}));

import { getAdminFaq, updateFaqItem } from "@/lib/api";
import { FaqManager } from "@/components/admin/FaqManager";

const ITEM: FaqItemAdminResponse = {
  id: 10,
  section: "care",
  question_en: "Old EN question",
  question_bg: "Old BG question",
  answer_en: "Old EN answer",
  answer_bg: "Old BG answer",
  sort_order: 0,
  is_published: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const FAQ: FaqAdminResponse = {
  sections: [
    {
      slug: "care",
      title_en: "Candle Care & Safety",
      title_bg: "Грижа и безопасност",
      icon: "✨",
      sort_order: 0,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      items: [ITEM],
    },
  ],
};

const mockedGetAdminFaq = vi.mocked(getAdminFaq);
const mockedUpdateFaqItem = vi.mocked(updateFaqItem);

describe("FaqManager", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedGetAdminFaq.mockResolvedValue(FAQ);
    mockedUpdateFaqItem.mockResolvedValue(ITEM);
  });

  it("requires English question before saving", async () => {
    renderWithIntl(<FaqManager />);
    await screen.findByText("Old EN question");

    const itemCard = screen.getByText("Old EN question").closest("article");
    expect(itemCard).not.toBeNull();
    fireEvent.click(within(itemCard!).getByRole("button", { name: "Edit" }));

    fireEvent.change(screen.getAllByLabelText("Question (EN)")[0]!, {
      target: { value: "" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save item" }));

    expect(await screen.findByText("English question is required.")).toBeInTheDocument();
    expect(mockedUpdateFaqItem).not.toHaveBeenCalled();
  });

  it("saves both-language item fields through the admin API", async () => {
    mockedUpdateFaqItem.mockResolvedValue({
      ...ITEM,
      question_en: "New EN question",
      question_bg: "New BG question",
      answer_en: "New EN answer",
      answer_bg: "New BG answer",
    });
    renderWithIntl(<FaqManager />);
    await screen.findByText("Old EN question");

    const itemCard = screen.getByText("Old EN question").closest("article");
    expect(itemCard).not.toBeNull();
    fireEvent.click(within(itemCard!).getByRole("button", { name: "Edit" }));

    fireEvent.change(screen.getAllByLabelText("Question (EN)")[0]!, {
      target: { value: "New EN question" },
    });
    fireEvent.change(screen.getAllByLabelText("Question (BG)")[0]!, {
      target: { value: "New BG question" },
    });
    fireEvent.change(screen.getAllByLabelText("Answer (EN)")[0]!, {
      target: { value: "New EN answer" },
    });
    fireEvent.change(screen.getAllByLabelText("Answer (BG)")[0]!, {
      target: { value: "New BG answer" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save item" }));

    await waitFor(() => {
      expect(mockedUpdateFaqItem).toHaveBeenCalledWith(
        10,
        expect.objectContaining({
          question_en: "New EN question",
          question_bg: "New BG question",
          answer_en: "New EN answer",
          answer_bg: "New BG answer",
        })
      );
    });
  });
});
