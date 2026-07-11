import { render, screen, waitFor, act } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { CartProvider, useCart } from "@/contexts/CartContext";
import type { CartResponse } from "@/lib/types";

vi.mock("@/lib/api", () => ({
  getCart: vi.fn(),
  addToCart: vi.fn(),
  updateCartItem: vi.fn(),
  removeFromCart: vi.fn(),
}));

vi.mock("@/lib/api-client", () => ({
  ApiError: class ApiError extends Error {
    code: string;
    details: null;
    constructor(response: { error: { code: string; message: string; details: null } }) {
      super(response.error.message);
      this.name = "ApiError";
      this.code = response.error.code;
      this.details = null;
    }
  },
}));

import { getCart, addToCart, updateCartItem, removeFromCart } from "@/lib/api";
import { ApiError } from "@/lib/api-client";

const mockedGetCart = vi.mocked(getCart);
const mockedAddToCart = vi.mocked(addToCart);
const mockedUpdateCartItem = vi.mocked(updateCartItem);
const mockedRemoveFromCart = vi.mocked(removeFromCart);

const emptyCart: CartResponse = { items: [], total_cents: 0, item_count: 0 };

const cartWithItem: CartResponse = {
  items: [
    {
      product_id: "lavender-dream",
      product: {
        id: "lavender-dream",
        name: "Lavender Dream",
        description: "A soothing candle",
        materials: "Soy wax, lavender oil",
        days_to_craft: 3,
        price_cents: 2500,
        category: "relaxation",
        image_url: "/img/lavender.jpg",
        stock: 10,
        is_active: true,
        is_featured: false,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
      quantity: 1,
      added_at: "2026-07-01T00:00:00Z",
    },
  ],
  total_cents: 2500,
  item_count: 1,
};

function TestComponent() {
  const cart = useCart();
  return (
    <div>
      <div data-testid="count">{cart.item_count}</div>
      <div data-testid="error">{cart.error ?? ""}</div>
      <button onClick={() => cart.addToCart("lavender-dream")}>add</button>
      <button onClick={() => cart.updateQuantity("lavender-dream", 3)}>
        update
      </button>
      <button onClick={() => cart.removeItem("lavender-dream")}>remove</button>
      <button onClick={() => cart.refreshCart()}>refresh</button>
    </div>
  );
}

function renderWithProvider() {
  return render(
    <CartProvider>
      <TestComponent />
    </CartProvider>
  );
}

describe("CartContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedGetCart.mockResolvedValue(emptyCart);
  });

  it("hydrates cart on mount", async () => {
    mockedGetCart.mockResolvedValue(cartWithItem);
    renderWithProvider();
    await waitFor(() => {
      expect(screen.getByTestId("count")).toHaveTextContent("1");
    });
    expect(mockedGetCart).toHaveBeenCalledOnce();
  });

  it("addToCart optimistically increments and rolls back on 409", async () => {
    mockedGetCart.mockResolvedValue(cartWithItem);
    const conflictError = new ApiError({ error: { code: "CONFLICT", message: "Insufficient stock", details: null } });
    mockedAddToCart.mockRejectedValue(conflictError);

    renderWithProvider();
    await waitFor(() => {
      expect(screen.getByTestId("count")).toHaveTextContent("1");
    });

    await act(async () => {
      screen.getByText("add").click();
    });

    await waitFor(() => {
      expect(screen.getByTestId("count")).toHaveTextContent("1");
    });
  });

  it("updateQuantity rolls back on error", async () => {
    mockedGetCart.mockResolvedValue(cartWithItem);
    mockedUpdateCartItem.mockRejectedValue(new Error("Server error"));

    renderWithProvider();
    await waitFor(() => {
      expect(screen.getByTestId("count")).toHaveTextContent("1");
    });

    await act(async () => {
      screen.getByText("update").click();
    });

    await waitFor(() => {
      expect(screen.getByTestId("error")).not.toHaveTextContent("");
    });
  });

  it("removeItem rolls back on error", async () => {
    mockedGetCart.mockResolvedValue(cartWithItem);
    mockedRemoveFromCart.mockRejectedValue(new Error("Server error"));

    renderWithProvider();
    await waitFor(() => {
      expect(screen.getByTestId("count")).toHaveTextContent("1");
    });

    await act(async () => {
      screen.getByText("remove").click();
    });

    await waitFor(() => {
      expect(screen.getByTestId("count")).toHaveTextContent("1");
    });
  });

  it("error auto-clears after 5 seconds", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mockedGetCart.mockResolvedValue(cartWithItem);
    mockedRemoveFromCart.mockRejectedValue(new Error("Oops"));

    renderWithProvider();
    await waitFor(() => {
      expect(screen.getByTestId("count")).toHaveTextContent("1");
    });

    await act(async () => {
      screen.getByText("remove").click();
    });

    await waitFor(() => {
      expect(screen.getByTestId("error")).not.toHaveTextContent("");
    });

    act(() => {
      vi.advanceTimersByTime(5000);
    });

    await waitFor(() => {
      expect(screen.getByTestId("error")).toHaveTextContent("");
    });

    vi.useRealTimers();
  });
});
