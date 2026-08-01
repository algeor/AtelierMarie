import React from "react";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import FaqPage from "@/app/[locale]/faq/page";
import { getFaq } from "@/lib/api";

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href, className }: { children: React.ReactNode; href: string; className?: string }) => (
    <a href={href} className={className}>{children}</a>
  ),
}));

vi.mock("@/lib/api", () => ({
  getFaq: vi.fn(),
}));

vi.mock("next-intl/server", () => ({
  getTranslations: async () => (key: string) => key,
}));

const mockedGetFaq = vi.mocked(getFaq);

describe("FAQ page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the English uncollected/refused parcel answer with a Terms link", async () => {
    mockedGetFaq.mockResolvedValue({
      sections: [
        {
          slug: "shipping",
          title: "Orders, Shipping & Returns",
          icon: null,
          items: [
            {
              id: 1,
              question: "Do you accept returns?",
              answer:
                "Uncollected or refused courier parcels are reviewed before refund timing, refund amount, or next steps are confirmed. See the [Terms & Conditions returns section](/en/terms#returns) for the full policy.",
            },
          ],
        },
      ],
    });

    const ui = await FaqPage({ params: Promise.resolve({ locale: "en" }) });
    render(ui);

    expect(mockedGetFaq).toHaveBeenCalledWith("en");
    expect(screen.getByText(/Uncollected or refused courier parcels are reviewed/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Terms & Conditions returns section" })).toHaveAttribute(
      "href",
      "/en/terms#returns"
    );
  });

  it("renders the Bulgarian uncollected/refused parcel answer with a Terms link", async () => {
    mockedGetFaq.mockResolvedValue({
      sections: [
        {
          slug: "shipping",
          title: "Поръчки, доставка и връщане",
          icon: null,
          items: [
            {
              id: 1,
              question: "Приемате ли връщания?",
              answer:
                "Непотърсените или отказани куриерски пратки се преглеждат, преди да потвърдим срок, сума за възстановяване или следваща стъпка. Вижте [раздела за връщания в Общите условия](/bg/terms#returns) за пълната политика.",
            },
          ],
        },
      ],
    });

    const ui = await FaqPage({ params: Promise.resolve({ locale: "bg" }) });
    render(ui);

    expect(mockedGetFaq).toHaveBeenCalledWith("bg");
    expect(screen.getByText(/Непотърсените или отказани куриерски пратки/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "раздела за връщания в Общите условия" })).toHaveAttribute(
      "href",
      "/bg/terms#returns"
    );
  });
});
