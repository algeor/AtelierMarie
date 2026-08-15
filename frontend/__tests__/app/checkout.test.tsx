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
      product: { id: "lavender-dream", name: "Lavender Dream", description: null, safety_warnings: null, care_instructions: null, materials: null, days_to_craft: null, price_cents: 2500, effective_price_cents: 2000, discount_percent: null, discount_active: false, category: null, category_name: null, product_type: "candles", product_type_name: "Candles", labels: [], images: [], video: null, primary_image_url: "/img.jpg", primary_thumbnail_url: "/img.jpg", stock: 5, can_order: true, available_now: true, availability_status: "in_stock", ships_when_complete: true, is_active: true, is_featured: false, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" },
      quantity: 1,
      added_at: "2026-01-01T00:00:00Z",
    },
  ],
  unavailable_items: [] as { product_id: string; product_name: string; reason: string }[],
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

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({ user: null, isLoading: false, error: null }),
}));

vi.mock("@/lib/api", () => ({
  createOrder: vi.fn(),
  getPublicPaymentSettings: vi.fn(),
  calculateShipping: vi.fn().mockResolvedValue({
    quotes: [
      {
        courier: "speedy",
        cents: 500,
        estimated_delivery_days: 2,
        is_fallback: false,
        price_source: "live",
        quoted_at: "2026-07-31 12:00:00",
      },
    ],
  }),
  getDeliverySettings: vi.fn().mockResolvedValue({
    speedy_office_enabled: true,
    speedy_door_enabled: true,
    econt_office_enabled: true,
    econt_door_enabled: true,
    cod_enabled: true,
    card_enabled: true,
    bank_transfer_enabled: true,
    updated_at: "2026-07-31 12:00:00",
  }),
}));

vi.mock("@/components/checkout/DeliverySection", () => ({
  DeliverySection: ({ onChange }: { onChange: (value: unknown) => void }) => {
    React.useEffect(() => {
      onChange({
        method: "office",
        office: {
          courier: "speedy",
          office_id: "SP-1",
          office_name: "Speedy Office 1",
          office_type: "office",
          city: "Sofia",
          phone: "+359888123456",
        },
        door: null,
      });
    }, [onChange]);
    return <div data-testid="delivery-section" />;
  },
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
        city: "Sofia",
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
  default: ({ alt = "", ...props }: Record<string, unknown>) => (
    // eslint-disable-next-line @next/next/no-img-element
    <img alt={String(alt)} {...props} />
  ),
}));

import { createOrder, getPublicPaymentSettings } from "@/lib/api";
import CheckoutPage from "@/app/[locale]/checkout/page";

const mockedCreateOrder = vi.mocked(createOrder);
const mockedGetPublicPaymentSettings = vi.mocked(getPublicPaymentSettings);

describe("Checkout Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedGetPublicPaymentSettings.mockResolvedValue({
      card_payments_enabled: false,
      pay_on_delivery_enabled: true,
      pay_on_delivery_max_cents: 5000,
      bank_transfer_enabled: false,
      available_payment_methods: ["cod"],
    });
    mockCartState.isLoading = false;
    mockCartState.items = [
      {
        product_id: "lavender-dream",
        product: { id: "lavender-dream", name: "Lavender Dream", description: null, safety_warnings: null, care_instructions: null, materials: null, days_to_craft: null, price_cents: 2500, effective_price_cents: 2000, discount_percent: null, discount_active: false, category: null, category_name: null, product_type: "candles", product_type_name: "Candles", labels: [], images: [], video: null, primary_image_url: "/img.jpg", primary_thumbnail_url: "/img.jpg", stock: 5, can_order: true, available_now: true, availability_status: "in_stock", ships_when_complete: true, is_active: true, is_featured: false, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" },
        quantity: 1,
        added_at: "2026-01-01T00:00:00Z",
      },
    ];
    mockCartState.unavailable_items = [];
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

  it("shows 'Name is required' on submit with empty name", async () => {
    renderWithIntl(<CheckoutPage />);
    const emailInput = screen.getByLabelText(/email/i);
    fireEvent.change(emailInput, { target: { value: "test@example.com" } });

    const submitButtons = screen.getAllByRole("button", { name: /place order/i });
    fireEvent.click(submitButtons[0]!);

    await waitFor(() => {
      expect(screen.getByText("Name is required")).toBeInTheDocument();
    });
  });

  it("shows legal disclosures, privacy links, and effective-price summary", async () => {
    renderWithIntl(<CheckoutPage />);

    const termsLinks = screen.getAllByRole("link", { name: "Terms & Conditions" });
    expect(termsLinks).toHaveLength(1);
    for (const link of termsLinks) {
      expect(link).toHaveAttribute("href", "/terms");
    }
    const privacyLinks = screen.getAllByRole("link", { name: "Privacy Policy" });
    expect(privacyLinks).toHaveLength(1);
    for (const link of privacyLinks) {
      expect(link).toHaveAttribute("href", "/privacy");
    }
    expect(screen.getAllByText(/process your contact and delivery data/i)).toHaveLength(1);
    await waitFor(() => {
      expect(screen.getByText("1 × €20.00")).toBeInTheDocument();
    });
    expect(screen.getAllByText("€20.00").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("Shipping")).toBeInTheDocument();
    expect(screen.getByText("Calculated at delivery step")).toBeInTheDocument();
  });

  it("renders the order summary before the submit action", async () => {
    renderWithIntl(<CheckoutPage />);
    const summary = await screen.findByRole("heading", { name: "Order Summary" });
    const submit = screen.getByRole("button", { name: "Place Order" });

    expect(
      Boolean(summary.compareDocumentPosition(submit) & Node.DOCUMENT_POSITION_FOLLOWING)
    ).toBe(true);
  });

  it("shows unavailable cart items in checkout and blocks submission until removed", async () => {
    mockCartState.unavailable_items = [
      { product_id: "old-candle", product_name: "Old Candle", reason: "deactivated" },
    ];
    renderWithIntl(<CheckoutPage />);

    expect(await screen.findByText("Old Candle")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Place Order" }));

    await waitFor(() => {
      expect(
        screen.getAllByText("Some items are no longer available. Please review your cart.").length
      ).toBeGreaterThanOrEqual(1);
    });
    expect(mockedCreateOrder).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Remove" }));
    expect(mockCartState.removeItem).toHaveBeenCalledWith("old-candle");
  });

  it("renders enabled payment methods from backend settings", async () => {
    mockedGetPublicPaymentSettings.mockResolvedValue({
      card_payments_enabled: true,
      pay_on_delivery_enabled: true,
      pay_on_delivery_max_cents: 5000,
      bank_transfer_enabled: false,
      available_payment_methods: ["card", "cod"],
    });

    renderWithIntl(<CheckoutPage />);

    expect(await screen.findByRole("radio", { name: "Card (pay online)" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "Cash on delivery" })).toBeInTheDocument();
    expect(screen.queryByRole("radio", { name: "Bank transfer" })).not.toBeInTheDocument();
    expect(
      screen.getByText("Your items are reserved for 15 minutes while you complete card payment.")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Payment is collected when your order is delivered. Available up to €50.00.")
    ).toBeInTheDocument();
  });

  it("shows unavailable payment message when backend exposes no methods", async () => {
    mockedGetPublicPaymentSettings.mockResolvedValue({
      card_payments_enabled: false,
      pay_on_delivery_enabled: false,
      pay_on_delivery_max_cents: 5000,
      bank_transfer_enabled: false,
      available_payment_methods: [],
    });

    renderWithIntl(<CheckoutPage />);

    expect(
      await screen.findByText("Payment is currently unavailable. Please contact us to place this order.")
    ).toBeInTheDocument();
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
      shipping_price_source: "live",
      shipping_is_fallback: false,
      total_cents: 2500,
      customer_email: "test@example.com",
      customer_name: "Test Buyer",
      delivery_method: null,
      delivery_courier: null,
      delivery_details: null,
      notes: null,
      items: [{ product_id: "lavender-dream", product_name: "Lavender Dream", price_cents: 2500, quantity: 1 }],
      tracking_number: null,
      tracking_carrier: null,
      tracking_url: null,
      courier_status: null,
      label_url: null,
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:00Z",
    });

    renderWithIntl(<CheckoutPage />);
    const emailInput = screen.getByLabelText(/email/i);
    fireEvent.change(emailInput, { target: { value: "test@example.com" } });
    const nameInput = screen.getByLabelText(/name/i);
    fireEvent.change(nameInput, { target: { value: "Test Buyer" } });

    await waitFor(() => {
      expect(screen.getByRole("radio", { name: /speedy/i })).toBeChecked();
    });
    await waitFor(() => {
      expect(screen.getByRole("radio", { name: "Cash on delivery" })).toBeChecked();
    });

    const submitButtons = screen.getAllByRole("button", { name: /place order/i });
    fireEvent.click(submitButtons[0]!);

    await waitFor(() => {
      expect(mockedCreateOrder).toHaveBeenCalledWith(
        expect.objectContaining({
          customer_email: "test@example.com",
          customer_name: "Test Buyer",
          payment_method: "cod",
        })
      );
    });
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/orders/order-abc/confirmation");
    });
  });

  it("keeps the return token when card checkout falls back to confirmation", async () => {
    mockedGetPublicPaymentSettings.mockResolvedValue({
      card_payments_enabled: true,
      pay_on_delivery_enabled: false,
      pay_on_delivery_max_cents: 5000,
      bank_transfer_enabled: false,
      available_payment_methods: ["card"],
    });
    mockedCreateOrder.mockResolvedValue({
      id: "order-card",
      status: "pending",
      payment_method: "card",
      payment_status: "pending",
      payment_return_token: "return-token",
      stripe_checkout_url: null,
      items_total_cents: 2500,
      shipping_cents: 0,
      shipping_price_source: "live",
      shipping_is_fallback: false,
      total_cents: 2500,
      customer_email: "test@example.com",
      customer_name: "Test Buyer",
      delivery_method: null,
      delivery_courier: null,
      delivery_details: null,
      notes: null,
      items: [{ product_id: "lavender-dream", product_name: "Lavender Dream", price_cents: 2500, quantity: 1 }],
      tracking_number: null,
      tracking_carrier: null,
      tracking_url: null,
      courier_status: null,
      label_url: null,
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:00Z",
    });

    renderWithIntl(<CheckoutPage />);
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "test@example.com" } });
    fireEvent.change(screen.getByLabelText(/name/i), { target: { value: "Test Buyer" } });

    await waitFor(() => {
      expect(screen.getByRole("radio", { name: /speedy/i })).toBeChecked();
    });
    await waitFor(() => {
      expect(screen.getByRole("radio", { name: "Card (pay online)" })).toBeChecked();
    });

    fireEvent.click(screen.getAllByRole("button", { name: /place order/i })[0]!);

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith(
        "/orders/order-card/confirmation?token=return-token"
      );
    });
  });
});
