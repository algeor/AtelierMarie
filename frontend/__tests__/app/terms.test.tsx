import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import TermsPage from "@/app/[locale]/terms/page";

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href, className }: { children: React.ReactNode; href: string; className?: string }) => (
    <a href={href} className={className}>{children}</a>
  ),
}));

describe("Terms page", () => {
  it("renders English terms content with the returns anchor", async () => {
    const ui = await TermsPage({ params: Promise.resolve({ locale: "en" }) });
    const { container } = render(ui);

    expect(
      screen.getByRole("heading", { name: "Terms & Conditions", level: 1 })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Right of withdrawal and returns" })
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Returns" })).toHaveAttribute(
      "href",
      "#returns"
    );
    expect(document.getElementById("returns")).toBeInTheDocument();
    expect(screen.getByText("Model withdrawal form")).toBeInTheDocument();
    expect(screen.getByText(/photos are not required/i)).toBeInTheDocument();
    expect(screen.getByText(/not collected, or a delivery is refused/i)).toBeInTheDocument();
    expect(screen.getByText(/payment-on-delivery orders where no card payment was collected/i)).toBeInTheDocument();
    expect(screen.getByText(/courier claim details/i)).toBeInTheDocument();
    expect(screen.getByText(/not treat a courier return status as an automatic full refund/i)).toBeInTheDocument();
    expect(container.querySelector(".overflow-x-auto")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Returns" })).toHaveClass("min-h-[48px]");
    expect(document.getElementById("terms-top")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Back to top" })).toHaveLength(9);
    expect(screen.getAllByRole("link", { name: "Back to top" })[0]).toHaveAttribute(
      "href",
      "#terms-top"
    );
  });

  it("renders Bulgarian terms with the same returns anchor and wrapped mobile nav", async () => {
    const ui = await TermsPage({ params: Promise.resolve({ locale: "bg" }) });
    const { container } = render(ui);

    expect(screen.getByRole("heading", { name: "Общи условия", level: 1 })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Право на отказ и връщане" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Връщане" })).toHaveAttribute("href", "#returns");
    expect(screen.getByText(/не бъде потърсена или доставката бъде отказана/i)).toBeInTheDocument();
    expect(screen.getByText(/не е събрано картово плащане/i)).toBeInTheDocument();
    expect(screen.getByText(/куриерска претенция/i)).toBeInTheDocument();
    expect(screen.getByText(/автоматично пълно възстановяване/i)).toBeInTheDocument();
    expect(container.querySelector(".overflow-x-auto")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Връщане" })).toHaveClass("min-h-[48px]");
    expect(screen.getAllByRole("link", { name: "Нагоре" })).toHaveLength(9);
  });
});
