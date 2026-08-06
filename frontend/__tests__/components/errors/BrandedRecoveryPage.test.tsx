import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { BrandedRecoveryPage } from "@/components/errors/BrandedRecoveryPage";

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href, className }: { children: React.ReactNode; href: string; className?: string }) => (
    <a href={href} className={className}>{children}</a>
  ),
}));

vi.mock("next/image", () => ({
  default: ({ alt = "", ...props }: Record<string, unknown>) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img alt={String(alt)} {...props} />
  ),
}));

describe("BrandedRecoveryPage", () => {
  it("renders a localized recovery action without technical error details", () => {
    render(
      <BrandedRecoveryPage
        code="404"
        eyebrow="Lost page"
        title="Not Found"
        description="The page is not available."
        backLabel="Back to Home"
        brandName="Atelier Marie"
        brandMarkTitle="Atelier Marie signature M"
      />
    );

    expect(screen.getByText("404")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Not Found" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to Home" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("img", { name: "Atelier Marie signature M" })).toBeInTheDocument();
    expect(screen.queryByText(/stack|digest|exception|trace/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /try again/i })).not.toBeInTheDocument();
  });

  it("shows Try Again only when a reset callback is available", async () => {
    const user = userEvent.setup();
    const onReset = vi.fn();

    render(
      <BrandedRecoveryPage
        eyebrow="A quiet pause"
        title="Something went wrong."
        description="The page hit a temporary issue."
        backLabel="Back to Home"
        tryAgainLabel="Try Again"
        onReset={onReset}
        brandName="Atelier Marie"
        brandMarkTitle="Atelier Marie signature M"
      />
    );

    await user.click(screen.getByRole("button", { name: "Try Again" }));

    expect(onReset).toHaveBeenCalledTimes(1);
  });
});
