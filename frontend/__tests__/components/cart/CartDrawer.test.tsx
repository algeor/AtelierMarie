import React from "react";
import { screen, fireEvent } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { renderWithIntl } from "../../test-utils";

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  usePathname: () => "/",
}));

const mockUseCart = vi.fn();

vi.mock("@/contexts/CartContext", () => ({
  useCart: () => mockUseCart(),
}));

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("next/image", () => ({
  default: (props: Record<string, unknown>) => <img {...props} />,
}));

import { CartDrawer } from "@/components/cart/CartDrawer";

const baseCartState = {
  items: [],
  unavailable_items: [],
  total_cents: 0,
  item_count: 0,
  isLoading: false,
  error: null,
  isDrawerOpen: false,
  addToCart: vi.fn(),
  updateQuantity: vi.fn(),
  removeItem: vi.fn(),
  openDrawer: vi.fn(),
  closeDrawer: vi.fn(),
  refreshCart: vi.fn(),
  dismissError: vi.fn(),
};

describe("CartDrawer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseCart.mockReturnValue(baseCartState);
  });

  it("is hidden when isDrawerOpen is false", () => {
    mockUseCart.mockReturnValue({ ...baseCartState, isDrawerOpen: false });
    renderWithIntl(<CartDrawer />);
    const wrapper = document.querySelector('[data-testid="cart-drawer-root"]');
    expect(wrapper).toHaveAttribute("aria-hidden", "true");
  });

  it("is visible when isDrawerOpen is true", () => {
    mockUseCart.mockReturnValue({ ...baseCartState, isDrawerOpen: true });
    renderWithIntl(<CartDrawer />);
    const wrapper = document.querySelector('[data-testid="cart-drawer-root"]');
    expect(wrapper).toHaveAttribute("aria-hidden", "false");
  });

  it("calls closeDrawer on Escape key", () => {
    const closeDrawer = vi.fn();
    mockUseCart.mockReturnValue({ ...baseCartState, isDrawerOpen: true, closeDrawer });
    renderWithIntl(<CartDrawer />);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(closeDrawer).toHaveBeenCalled();
  });

  it("shows empty state when items array is empty", () => {
    mockUseCart.mockReturnValue({ ...baseCartState, isDrawerOpen: true, items: [] });
    renderWithIntl(<CartDrawer />);
    expect(screen.getByText("Your cart is empty")).toBeInTheDocument();
  });

  it("shows items when present", () => {
    mockUseCart.mockReturnValue({
      ...baseCartState,
      isDrawerOpen: true,
      items: [
        {
          product_id: "test-candle",
          product: {
            id: "test-candle",
            name: "Test Candle",
            price_cents: 3000,
            effective_price_cents: 3000,
            discount_percent: null,
            discount_active: false,
            images: [],
            primary_image_url: "/img/test.jpg",
            primary_thumbnail_url: "/img/test.jpg",
            stock: 5,
          },
          quantity: 2,
          added_at: "2026-01-01T00:00:00Z",
        },
      ],
      total_cents: 6000,
      item_count: 2,
    });
    renderWithIntl(<CartDrawer />);
    expect(screen.getByText("Test Candle")).toBeInTheDocument();
    expect(document.querySelector('img[src="/img/test.jpg"]')).toBeInTheDocument();
  });

  it("shows unavailable items with a remove action", () => {
    const removeItem = vi.fn();
    mockUseCart.mockReturnValue({
      ...baseCartState,
      isDrawerOpen: true,
      unavailable_items: [
        { product_id: "old-candle", product_name: "Old Candle", reason: "deactivated" },
      ],
      removeItem,
    });
    renderWithIntl(<CartDrawer />);
    expect(screen.getByText("Unavailable items")).toBeInTheDocument();
    expect(screen.getByText("Old Candle")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Remove" }));
    expect(removeItem).toHaveBeenCalledWith("old-candle");
  });

  it("caps quantity increments at available stock", () => {
    mockUseCart.mockReturnValue({
      ...baseCartState,
      isDrawerOpen: true,
      items: [
        {
          product_id: "limited-candle",
          product: {
            id: "limited-candle",
            name: "Limited Candle",
            price_cents: 3000,
            effective_price_cents: 3000,
            discount_percent: null,
            discount_active: false,
            images: [],
            primary_image_url: null,
            primary_thumbnail_url: null,
            stock: 5,
          },
          quantity: 5,
          added_at: "2026-01-01T00:00:00Z",
        },
      ],
      total_cents: 15000,
      item_count: 5,
    });
    renderWithIntl(<CartDrawer />);
    expect(screen.getByRole("button", { name: "Increase quantity" })).toBeDisabled();
    expect(screen.getByText("Only 5 available")).toBeInTheDocument();
  });
});
