import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import PrivacyPage from "@/app/[locale]/privacy/page";
import CookiesPage from "@/app/[locale]/cookies/page";

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href, className }: { children: React.ReactNode; href: string; className?: string }) => (
    <a href={href} className={className}>{children}</a>
  ),
}));

describe("Legal policy pages", () => {
  it("renders the English privacy policy with controller details and cookie link", async () => {
    const ui = await PrivacyPage({ params: Promise.resolve({ locale: "en" }) });
    render(ui);

    expect(screen.getByRole("heading", { name: "Privacy Policy", level: 1 })).toBeInTheDocument();
    expect(screen.getByText("Controller details")).toBeInTheDocument();
    expect(screen.getAllByText("Atelier Marie").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "Cookie Policy" })).toHaveAttribute(
      "href",
      "/cookies"
    );
  });

  it("renders the English cookie policy inventory and privacy link", async () => {
    const ui = await CookiesPage({ params: Promise.resolve({ locale: "en" }) });
    render(ui);

    expect(screen.getByRole("heading", { name: "Cookie Policy", level: 1 })).toBeInTheDocument();
    expect(screen.getByText("session_id")).toBeInTheDocument();
    expect(screen.getByText("atelier_auth")).toBeInTheDocument();
    expect(screen.getByText("NEXT_LOCALE")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Privacy Policy" })).toHaveAttribute(
      "href",
      "/privacy"
    );
  });
});
