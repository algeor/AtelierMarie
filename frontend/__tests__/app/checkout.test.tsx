import React from "react";
import { screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { renderWithIntl } from "../test-utils";

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
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
      product: { id: "lavender-dream", name: "Lavender Dream", price_cents: 2500, effective_price_cents: 2000, images: [], primary_image_url: "/img.jpg", primary_thumbnail_url: "/img.jpg", stock: 5 },
      quantity: 1,
      added_at: "2026-01-01T00:00:00Z",
    },
  ],
  total_cents: 2000,
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

vi.mock("@/contexts/CookieConsentContext", () => ({
  useCookieConsent: () => ({ analytics: true }),
}));

vi.mock("@/lib/analytics", () => ({
  trackAnalytics: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  createOrder: vi.fn(),
}));

vi.mock("@/components/checkout/DeliverySection", () => ({
  DeliverySection: () => <div data-testid="delivery-section" />,
  validateDelivery: () => ({
    valid: true,
    errors: {},
    normalized: {
      method: "office",
      office: {
        courier: "speedy",
        office_id: "SP-1",
        office_name: "Speedy Office 1",
        office_type: "office",
        phone: "+359888123456",
      },
      door: null,
    },
  }),
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
        product: { id: "lavender-dream", name: "Lavender Dream", price_cents: 2500, effective_price_cents: 2000, images: [], primary_image_url: "/img.jpg", primary_thumbnail_url: "/img.jpg", stock: 5 },
        quantity: 1,
        added_at: "2026-01-01T00:00:00Z",
      },
    ];
    mockCartState.item_count = 1;
  });

  it("redirects to /products when cart is empty", () => {
    mockCartState.items = [];
    mockCartState.item_count = 0;
    renderWithIntl(<CheckoutPage />);
    expect(mockPush).toHaveBeenCalledWith("/products");
  });

  it("shows email validation error on blur with invalid email", async () => {
    renderWithIntl(<CheckoutPage />);
    const emailInput = screen.getByLabelText(/email/i);
    fireEvent.change(emailInput, { target: { value: "not-an-email" } });
    fireEvent.blur(emailInput);
    await waitFor(() => {
      expect(screen.getByText("Please enter a valid email address")).toBeInTheDocument();
    });
  });

  it("shows 'Email is required' on submit with empty email", async () => {
    renderWithIntl(<CheckoutPage />);
    const submitButtons = screen.getAllByRole("button", { name: /place order/i });
    fireEvent.click(submitButtons[0]!);
    await waitFor(() => {
      expect(screen.getByText("Email is required")).toBeInTheDocument();
    });
  });

  it("shows legal disclosures, privacy links, and effective-price summary", () => {
    renderWithIntl(<CheckoutPage />);

    const termsLinks = screen.getAllByRole("link", { name: "Terms & Conditions" });
    expect(termsLinks).toHaveLength(2);
    for (const link of termsLinks) {
      expect(link).toHaveAttribute("href", "/terms");
    }
    const privacyLinks = screen.getAllByRole("link", { name: "Privacy Policy" });
    expect(privacyLinks).toHaveLength(2);
    for (const link of privacyLinks) {
      expect(link).toHaveAttribute("href", "/privacy");
    }
    expect(screen.getAllByText(/process your contact and delivery data/i)).toHaveLength(2);
    expect(screen.getByText("1 × €20.00")).toBeInTheDocument();
    expect(screen.getAllByText("€20.00").length).toBeGreaterThanOrEqual(3);
    expect(screen.getByText("Delivery")).toBeInTheDocument();
    expect(screen.getByText("Not separately calculated in this checkout")).toBeInTheDocument();
  });

  it("successful submission calls createOrder and navigates", async () => {
    mockedCreateOrder.mockResolvedValue({
      id: "order-abc",
      status: "pending",
      payment_method: "cod",
      payment_status: "cod_pending",
      stripe_checkout_url: null,
      items_total_cents: 2500,
      shipping_cents: 0,
      total_cents: 2500,
      customer_email: "test@example.com",
      customer_name: null,
      delivery_method: null,
      delivery_courier: null,
      delivery_details: null,
      notes: null,
      items: [{ product_id: "lavender-dream", product_name: "Lavender Dream", price_cents: 2500, quantity: 1 }],
      tracking_number: null,
      tracking_carrier: null,
      tracking_url: null,
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:00Z",
    });

    renderWithIntl(<CheckoutPage />);
    const emailInput = screen.getByLabelText(/email/i);
    fireEvent.change(emailInput, { target: { value: "test@example.com" } });

    const submitButtons = screen.getAllByRole("button", { name: /place order/i });
    fireEvent.click(submitButtons[0]!);

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
