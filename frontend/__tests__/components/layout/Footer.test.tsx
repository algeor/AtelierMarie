import React from "react";
import { screen } from "@testing-library/react";
import { vi, describe, it, expect } from "vitest";
import { renderWithIntl } from "../../test-utils";
import { Footer } from "@/components/layout/Footer";

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

const INSTAGRAM_URL =
  "https://www.instagram.com/atelier_marie25?igsh=MWQ1YzA4aHF2a3Q4MA==";
const TIKTOK_URL = "https://www.tiktok.com/@ateliermarie25?_r=1&_t=ZN-98H9buODbdu";

describe("Footer", () => {
  it("links Contact to the localized /contact route", () => {
    renderWithIntl(<Footer />);

    const contact = screen.getByRole("link", { name: "Contact" });
    expect(contact).toHaveAttribute("href", "/contact");
  });

  it("renders the Instagram link with the confirmed URL and safe new-tab attributes", () => {
    renderWithIntl(<Footer />);

    const instagram = screen.getByRole("link", {
      name: "Follow Atelier Marie on Instagram",
    });
    expect(instagram).toHaveAttribute("href", INSTAGRAM_URL);
    expect(instagram).toHaveAttribute("target", "_blank");
    expect(instagram).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("renders the TikTok link with the confirmed URL and safe new-tab attributes", () => {
    renderWithIntl(<Footer />);

    const tiktok = screen.getByRole("link", {
      name: "Follow Atelier Marie on TikTok",
    });
    expect(tiktok).toHaveAttribute("href", TIKTOK_URL);
    expect(tiktok).toHaveAttribute("target", "_blank");
    expect(tiktok).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("keeps existing Home and Shop links unchanged", () => {
    renderWithIntl(<Footer />);

    expect(screen.getByRole("link", { name: "Home" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "Shop" })).toHaveAttribute(
      "href",
      "/products"
    );
  });

  it("links Atelier to the story page", () => {
    renderWithIntl(<Footer />);

    expect(screen.getByRole("link", { name: "Atelier" })).toHaveAttribute(
      "href",
      "/atelier"
    );
  });

  it("links FAQ from the footer", () => {
    renderWithIntl(<Footer />);

    expect(screen.getByRole("link", { name: "FAQ" })).toHaveAttribute("href", "/faq");
  });

  it("links legal policies from the footer without a separate returns link", () => {
    renderWithIntl(<Footer />);

    expect(screen.getByRole("link", { name: "Terms & Conditions" })).toHaveAttribute(
      "href",
      "/terms"
    );
    expect(screen.getByRole("link", { name: "Privacy Policy" })).toHaveAttribute(
      "href",
      "/privacy"
    );
    expect(screen.getByRole("link", { name: "Cookie Policy" })).toHaveAttribute(
      "href",
      "/cookies"
    );
    expect(screen.queryByRole("link", { name: /^returns$/i })).not.toBeInTheDocument();
  });
});
