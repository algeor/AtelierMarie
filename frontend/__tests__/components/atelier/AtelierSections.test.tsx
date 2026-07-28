import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { bodyBlocks } from "@/components/atelier/BodyRenderer";
import { renderAtelierSection } from "@/components/atelier/AtelierSections";
import type { AboutSection } from "@/lib/types";

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

function section(overrides: Partial<AboutSection> = {}): AboutSection {
  return {
    slug: "values",
    type: "cards",
    heading: "Our Values",
    subheading: "Principles",
    body: null,
    cta: null,
    image: null,
    items: [
      { id: 1, title: "Craftsmanship", text: "Care in every detail.", image: null, link: null },
    ],
    ...overrides,
  };
}

describe("BodyRenderer", () => {
  it("turns paragraphs and consecutive bullet lines into blocks", () => {
    expect(bodyBlocks("First paragraph.\n\n* One\n- Two\n\nLast paragraph.")).toEqual([
      { type: "p", text: "First paragraph." },
      { type: "ul", items: ["One", "Two"] },
      { type: "p", text: "Last paragraph." },
    ]);
  });
});

describe("renderAtelierSection", () => {
  it("dispatches cards sections to a card grid", () => {
    const { container } = render(<>{renderAtelierSection(section())}</>);
    expect(screen.getByRole("heading", { name: "Our Values" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Craftsmanship" })).toBeInTheDocument();
    expect(container.querySelector("section#values")?.className).toContain("scroll-mt-24");
  });

  it("returns null for unknown types", () => {
    const rendered = renderAtelierSection(section({ type: "unknown" as AboutSection["type"] }));
    expect(rendered).toBeNull();
  });

  it("uses the placeholder image when a collection item has no image", () => {
    const { container } = render(
      <>{renderAtelierSection(section({ slug: "collections", type: "collections" }))}</>
    );
    const image = container.querySelector("img");
    expect(image).toHaveAttribute("src", "/static/products/lavender-dreams-300ml.webp");
  });
});
