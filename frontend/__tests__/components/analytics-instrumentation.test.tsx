import React from "react";
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithIntl } from "../test-utils";
import type { CartItemResponse, ProductResponse, TaxonomyResponse } from "@/lib/types";

const mockTrackAnalytics = vi.fn();
const mockCreateOrder = vi.fn();
const mockPush = vi.fn();
const mockAddToCart = vi.fn();
const mockOpenDrawer = vi.fn();

const cartItem: CartItemResponse = {
  product_id: "lavender-dream",
  product: {
    id: "lavender-dream",
    name: "Lavender Dream",
    description: null,
    safety_warnings: null,
    care_instructions: null,
    materials: null,
    days_to_craft: null,
    price_cents: 2500,
    effective_price_cents: 2000,
    discount_percent: null,
    discount_active: false,
    category: "candles",
    category_name: "Candles",
    product_type: "candles",
    product_type_name: "Candles",
    labels: [],
    images: [],
    video: null,
    primary_image_url: "/img.jpg",
    primary_thumbnail_url: "/img.jpg",
    stock: 5,
    is_active: true,
    is_featured: false,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  quantity: 1,
  added_at: "2026-01-01T00:00:00Z",
};

const mockCartState = {
  items: [cartItem],
  total_cents: 2000,
  item_count: 1,
  isLoading: false,
  error: null,
  isDrawerOpen: false,
  addToCart: mockAddToCart,
  updateQuantity: vi.fn(),
  removeItem: vi.fn(),
  openDrawer: mockOpenDrawer,
  closeDrawer: vi.fn(),
  refreshCart: vi.fn(),
  dismissError: vi.fn(),
};

vi.mock("@/lib/analytics", () => ({
  trackAnalytics: (...args: unknown[]) => mockTrackAnalytics(...args),
}));

vi.mock("@/lib/api", () => ({
  createOrder: (...args: unknown[]) => mockCreateOrder(...args),
}));

vi.mock("@/contexts/CartContext", () => ({
  useCart: () => mockCartState,
}));

vi.mock("@/contexts/CookieConsentContext", () => ({
  useCookieConsent: () => ({ analytics: true }),
}));

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href, className, onClick }: { children: React.ReactNode; href: string; className?: string; onClick?: () => void }) => (
    <a href={href} className={className} onClick={onClick}>{children}</a>
  ),
  useRouter: () => ({ replace: vi.fn(), push: mockPush }),
  usePathname: () => "/",
}));

vi.mock("@/components/checkout/DeliverySection", () => ({
  DeliverySection: ({ onChange }: { onChange: (value: unknown) => void }) => (
    <button
      type="button"
      onClick={() =>
        onChange({
          method: "office",
          office: {
            courier: "speedy",
            office_id: "SP-1",
            office_name: "Speedy Office 1",
            office_type: "office",
            phone: "+359888123456",
          },
          door: null,
        })
      }
    >
      Select delivery
    </button>
  ),
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

vi.mock("next/image", () => ({
  default: (props: Record<string, unknown>) => <img {...props} />,
}));

import { AddToCartButton } from "@/components/cart/AddToCartButton";
import { CartDrawer } from "@/components/cart/CartDrawer";
import { ProductListingClient } from "@/components/products/ProductListingClient";
import { ProductViewTracker } from "@/components/products/ProductViewTracker";
import CheckoutPage from "@/app/[locale]/checkout/page";

function product(overrides: Partial<ProductResponse>): ProductResponse {
  return {
    id: "product-1",
    name: "Product",
    description: null,
    safety_warnings: null,
    care_instructions: null,
    materials: null,
    days_to_craft: null,
    price_cents: 1200,
    effective_price_cents: 1200,
    discount_percent: null,
    discount_active: false,
    category: "small",
    category_name: "Small",
    product_type: "candles",
    product_type_name: "Candles",
    labels: [],
    images: [],
    video: null,
    primary_image_url: null,
    primary_thumbnail_url: null,
    stock: 3,
    is_active: true,
    is_featured: false,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

const taxonomy: TaxonomyResponse = {
  product_types: [
    { slug: "candles", name: "Candles", sort_order: 0 },
    { slug: "boxes", name: "Boxes", sort_order: 1 },
  ],
  categories: [
    { slug: "small", name: "Small", sort_order: 0 },
    { slug: "premium", name: "Premium", sort_order: 1 },
  ],
  labels: [],
};

describe("storefront analytics instrumentation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAddToCart.mockResolvedValue(undefined);
    mockCartState.items = [cartItem];
    mockCartState.item_count = 1;
    mockCartState.total_cents = 2000;
    mockCartState.isLoading = false;
    mockCartState.isDrawerOpen = false;
    window.history.replaceState(null, "", "/en/products");
  });

  it("emits product, listing, add-to-cart, and cart-open events", async () => {
    const user = userEvent.setup();
    renderWithIntl(
      <ProductViewTracker productId="lavender-dream" category="candles" valueCents={2000} />
    );

    await waitFor(() => expect(mockTrackAnalytics).toHaveBeenCalledWith(
      "product_view",
      expect.objectContaining({ product_id: "lavender-dream" })
    ));

    renderWithIntl(
      <ProductListingClient
        products={[
          product({ id: "small", name: "Small", product_type: "candles", category: "small" }),
          product({ id: "box", name: "Box", product_type: "boxes", category: "premium" }),
        ]}
        taxonomy={taxonomy}
      />
    );
    await user.click(screen.getByRole("button", { name: "Open product menu" }));
    const menu = screen.getByLabelText("Product menu");
    await user.click(within(menu).getByRole("button", { name: /Boxes/ }));
    await waitFor(() => expect(mockTrackAnalytics).toHaveBeenCalledWith(
      "listing_filter",
      { filter_name: "product_type", filter_value: "boxes" }
    ));

    renderWithIntl(<AddToCartButton productId="lavender-dream" stock={5} />);
    const addButtons = screen.getAllByRole("button", { name: "Add to Cart" });
    fireEvent.click(addButtons[addButtons.length - 1]!);
    await waitFor(() => expect(mockTrackAnalytics).toHaveBeenCalledWith(
      "add_to_cart",
      { product_id: "lavender-dream", quantity: 1 }
    ));

    mockCartState.isDrawerOpen = true;
    renderWithIntl(<CartDrawer />);
    await waitFor(() => expect(mockTrackAnalytics).toHaveBeenCalledWith(
      "cart_open",
      expect.objectContaining({ item_count: 1, value_cents: 2000 })
    ));
  });

  it("emits checkout, delivery, order-submit, and payment-redirect events", async () => {
    mockCreateOrder.mockResolvedValue({
      id: "order-stripe",
      status: "pending",
      payment_method: "card",
      payment_status: "pending",
      stripe_checkout_url: "https://stripe.test/session",
      analytics_consent: true,
      items_total_cents: 2000,
      shipping_cents: 0,
      total_cents: 2000,
      customer_email: "test@example.com",
      customer_name: null,
      delivery_method: "office",
      delivery_courier: "speedy",
      delivery_details: null,
      notes: null,
      items: [],
      tracking_number: null,
      tracking_carrier: null,
      tracking_url: null,
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:00Z",
    });

    renderWithIntl(<CheckoutPage />);

    await waitFor(() => expect(mockTrackAnalytics).toHaveBeenCalledWith(
      "checkout_start",
      expect.objectContaining({ item_count: 1, value_cents: 2000 })
    ));

    fireEvent.click(screen.getByRole("button", { name: "Select delivery" }));
    expect(mockTrackAnalytics).toHaveBeenCalledWith(
      "delivery_selected",
      { delivery_method: "office", delivery_courier: "speedy" }
    );

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "test@example.com" } });
    fireEvent.click(screen.getAllByRole("button", { name: /place order/i })[0]!);

    await waitFor(() => expect(mockTrackAnalytics).toHaveBeenCalledWith(
      "order_submit",
      expect.objectContaining({ payment_method: "cod", delivery_method: "office" })
    ));
    await waitFor(() => expect(mockTrackAnalytics).toHaveBeenCalledWith(
      "payment_redirect",
      expect.objectContaining({ order_id: "order-stripe", payment_provider: "stripe" })
    ));

    expect(mockTrackAnalytics).not.toHaveBeenCalledWith(
      "shipping_quote_selected",
      expect.anything()
    );
    expect(mockTrackAnalytics).not.toHaveBeenCalledWith(
      "purchase_confirmed",
      expect.anything()
    );
  });
});
