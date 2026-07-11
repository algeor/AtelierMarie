import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string, values?: Record<string, unknown>) => {
    if (values) {
      return Object.entries(values).reduce(
        (str, [k, v]) => str.replace(`{${k}}`, String(v)),
        key
      );
    }
    return key;
  },
  useLocale: () => "en",
  NextIntlClientProvider: ({ children }: { children: React.ReactNode }) => children,
}));

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
  useRouter: () => ({ replace: vi.fn(), push: mockPush }),
  usePathname: () => "/",
}));

const mockCartState = {
  items: [
    {
      product_id: "lavender-dream",
      product: { id: "lavender-dream", name: "Lavender Dream", price_cents: 2500, image_url: "/img.jpg", stock: 5 },
      quantity: 1,
      added_at: "2026-01-01T00:00:00Z",
    },
  ],
  total_cents: 2500,
  item_count: 1,
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

vi.mock("@/contexts/CartContext", () => ({
  useCart: () => mockCartState,
}));

vi.mock("@/lib/api", () => ({
  createOrder: vi.fn(),
}));

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("next/image", () => ({
  default: (props: Record<string, unknown>) => <img {...props} />,
}));

import { createOrder } from "@/lib/api";
import CheckoutPage from "@/app/[locale]/checkout/page";

const mockedCreateOrder = vi.mocked(createOrder);

describe("Checkout Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockCartState.isLoading = false;
    mockCartState.items = [
      {
        product_id: "lavender-dream",
        product: { id: "lavender-dream", name: "Lavender Dream", price_cents: 2500, image_url: "/img.jpg", stock: 5 },
        quantity: 1,
        added_at: "2026-01-01T00:00:00Z",
      },
    ];
    mockCartState.item_count = 1;
  });

  it("redirects to /products when cart is empty", () => {
    mockCartState.items = [];
    mockCartState.item_count = 0;
    render(<CheckoutPage />);
    expect(mockPush).toHaveBeenCalledWith("/products");
  });

  it("shows email validation error on blur with invalid email", async () => {
    render(<CheckoutPage />);
    const emailInput = screen.getByLabelText(/email/i);
    fireEvent.change(emailInput, { target: { value: "not-an-email" } });
    fireEvent.blur(emailInput);
    await waitFor(() => {
      expect(screen.getByText("emailInvalid")).toBeInTheDocument();
    });
  });

  it("shows 'Email is required' on submit with empty email", async () => {
    render(<CheckoutPage />);
    const submitButtons = screen.getAllByRole("button", { name: /placeOrder/i });
    fireEvent.click(submitButtons[0]);
    await waitFor(() => {
      expect(screen.getByText("emailRequired")).toBeInTheDocument();
    });
  });

  it("successful submission calls createOrder and navigates", async () => {
    mockedCreateOrder.mockResolvedValue({
      id: "order-abc",
      status: "pending",
      total_cents: 2500,
      customer_email: "test@example.com",
      customer_name: null,
      shipping_address: null,
      notes: null,
      items: [{ product_id: "lavender-dream", product_name: "Lavender Dream", price_cents: 2500, quantity: 1 }],
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:00Z",
    });

    render(<CheckoutPage />);
    const emailInput = screen.getByLabelText(/email/i);
    fireEvent.change(emailInput, { target: { value: "test@example.com" } });

    const submitButtons = screen.getAllByRole("button", { name: /placeOrder/i });
    fireEvent.click(submitButtons[0]);

    await waitFor(() => {
      expect(mockedCreateOrder).toHaveBeenCalledWith(
        expect.objectContaining({ customer_email: "test@example.com" })
      );
    });
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/orders/order-abc/confirmation");
    });
  });
});
