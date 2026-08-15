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
    renderWithIntl(<AddToCartButton productId="test-candle" availableNow />);
    expect(screen.getByRole("button")).toHaveTextContent("Add to Cart");
  });

  it("keeps ordering enabled and shows crafted-later copy when unavailable now", () => {
    renderWithIntl(<AddToCartButton productId="test-candle" availableNow={false} />);
    expect(screen.getByRole("button")).toHaveTextContent("Add to Cart");
    expect(screen.getByText(/crafted and shipped once ready/i)).toBeInTheDocument();
  });

  it("calls addToCart and openDrawer on click", async () => {
    renderWithIntl(<AddToCartButton productId="test-candle" availableNow />);
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
    renderWithIntl(<AddToCartButton productId="test-candle" availableNow />);
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByRole("button")).toBeDisabled();
  });
});
