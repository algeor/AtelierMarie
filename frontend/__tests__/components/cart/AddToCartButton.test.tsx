import React from "react";
import { screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { renderWithIntl } from "../../test-utils";

const mockAddToCart = vi.fn();
const mockOpenDrawer = vi.fn();

vi.mock("@/contexts/CartContext", () => ({
  useCart: () => ({
    addToCart: mockAddToCart,
    openDrawer: mockOpenDrawer,
  }),
}));

import { AddToCartButton } from "@/components/cart/AddToCartButton";

describe("AddToCartButton", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAddToCart.mockResolvedValue(undefined);
  });

  it("shows 'Add to Cart' text when idle", () => {
    renderWithIntl(<AddToCartButton productId="test-candle" stock={5} />);
    expect(screen.getByRole("button")).toHaveTextContent("Add to Cart");
  });

  it("shows 'Out of Stock' and is disabled when stock is 0", () => {
    renderWithIntl(<AddToCartButton productId="test-candle" stock={0} />);
    const button = screen.getByRole("button");
    expect(button).toHaveTextContent("Out of Stock");
    expect(button).toBeDisabled();
  });

  it("calls addToCart and openDrawer on click", async () => {
    renderWithIntl(<AddToCartButton productId="test-candle" stock={5} />);
    fireEvent.click(screen.getByRole("button"));
    await waitFor(() => {
      expect(mockAddToCart).toHaveBeenCalledWith("test-candle", 1);
    });
    await waitFor(() => {
      expect(mockOpenDrawer).toHaveBeenCalled();
    });
  });

  it("button is disabled while loading", async () => {
    mockAddToCart.mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 1000))
    );
    renderWithIntl(<AddToCartButton productId="test-candle" stock={5} />);
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByRole("button")).toBeDisabled();
  });
});
