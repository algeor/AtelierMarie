import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BrandMark, CategoryLineArt, type CategoryLineArtKind } from "@/components/rebrand";

describe("rebrand assets", () => {
  it("renders the signature M mark without using candle logo semantics", () => {
    render(<BrandMark title="Atelier Marie signature M" animated />);

    const mark = screen.getByRole("img", { name: "Atelier Marie signature M" });
    expect(mark).toHaveClass("signature-mark--draw");
    expect(mark).toHaveAttribute("viewBox", "0 0 96 72");
    expect(mark).toHaveAttribute("width", "96");
    expect(mark).toHaveAttribute("height", "72");
    expect(mark.textContent).not.toMatch(/candle/i);
  });

  it("renders a stable small-size static mark", () => {
    render(<BrandMark variant="small" title="Small Atelier Marie signature M" />);

    const mark = screen.getByRole("img", { name: "Small Atelier Marie signature M" });
    expect(mark).toHaveClass("signature-mark--small");
    expect(mark).not.toHaveClass("signature-mark--draw");
    expect(mark).toHaveAttribute("width", "48");
    expect(mark).toHaveAttribute("height", "36");
  });

  it("renders category line drawings with stable dimensions", () => {
    const kinds: CategoryLineArtKind[] = ["candles", "christmas-balls", "custom-boxes", "notebooks"];

    for (const kind of kinds) {
      const { unmount } = render(<CategoryLineArt kind={kind} title={kind} />);
      const art = screen.getByRole("img", { name: kind });
      expect(art).toHaveClass("category-line-art");
      expect(art).toHaveClass("rebrand-line-draw");
      expect(art).toHaveAttribute("viewBox", "0 0 160 120");
      expect(art).toHaveAttribute("width", "160");
      expect(art).toHaveAttribute("height", "120");
      unmount();
    }
  });
});
