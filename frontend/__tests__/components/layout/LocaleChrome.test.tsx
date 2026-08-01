import React from "react";
import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithIntl } from "../../test-utils";

let mockedPathname = "/";

vi.mock("@/i18n/navigation", () => ({
  usePathname: () => mockedPathname,
}));

vi.mock("@/components/layout/AnnouncementBar", () => ({
  AnnouncementBar: () => <div data-testid="announcement-bar" />,
}));

vi.mock("@/components/layout/Header", () => ({
  Header: () => <div data-testid="public-header" />,
}));

vi.mock("@/components/cart/CartDrawer", () => ({
  CartDrawer: () => <div data-testid="cart-drawer" />,
}));

vi.mock("@/components/layout/Footer", () => ({
  Footer: () => <div data-testid="public-footer" />,
}));

vi.mock("@/contexts/CartContext", () => ({
  CartProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="cart-provider">{children}</div>
  ),
}));

import { LocaleChrome } from "@/components/layout/LocaleChrome";

describe("LocaleChrome", () => {
  it("skips public chrome and cart on admin pages", () => {
    mockedPathname = "/admin/orders";

    renderWithIntl(
      <LocaleChrome>
        <div>Admin content</div>
      </LocaleChrome>
    );

    expect(screen.getByText("Admin content")).toBeInTheDocument();
    expect(screen.queryByTestId("public-header")).not.toBeInTheDocument();
    expect(screen.queryByTestId("cart-provider")).not.toBeInTheDocument();
    expect(screen.queryByTestId("cart-drawer")).not.toBeInTheDocument();
  });

  it("renders public chrome on shop pages", () => {
    mockedPathname = "/products";

    renderWithIntl(
      <LocaleChrome>
        <div>Shop content</div>
      </LocaleChrome>
    );

    expect(screen.getByTestId("public-header")).toBeInTheDocument();
    expect(screen.getByTestId("cart-provider")).toBeInTheDocument();
    expect(screen.getByText("Shop content")).toBeInTheDocument();
  });
});
