import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import TermsPage from "@/app/[locale]/terms/page";

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
    expect(container.querySelector(".overflow-x-auto")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Returns" })).toHaveClass("min-h-[48px]");
  });

  it("renders Bulgarian terms with the same returns anchor and wrapped mobile nav", async () => {
    const ui = await TermsPage({ params: Promise.resolve({ locale: "bg" }) });
    const { container } = render(ui);

    expect(screen.getByRole("heading", { name: "Общи условия", level: 1 })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Право на отказ и връщане" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Връщане" })).toHaveAttribute("href", "#returns");
    expect(container.querySelector(".overflow-x-auto")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Връщане" })).toHaveClass("min-h-[48px]");
  });
});
