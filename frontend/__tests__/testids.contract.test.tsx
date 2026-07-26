/**
 * Contract test — asserts every E2E-covered component renders its data-testid.
 *
 * If a developer removes a `data-testid` from a component covered by the
 * Selenium suite, this test fails loudly in `make test-frontend` before any
 * PR merges. Cheaper feedback than a Selenium timeout.
 */
import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import { TEST_IDS } from "@/lib/testids";

// next-intl requires a provider in tests; the components below call useTranslations
// so we stub it to a passthrough that returns the key.
vi.mock("next-intl", () => ({
  useTranslations: () => (k: string) => k,
  useLocale: () => "en",
}));

// AuthContext / CartContext are consumed by some components — stub them.
vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({ isAuthenticated: false, login: () => {}, logout: () => {} }),
}));
vi.mock("@/contexts/CartContext", () => ({
  useCart: () => ({
    items: [],
    total_cents: 0,
    item_count: 0,
    isDrawerOpen: false,
    isLoading: false,
    openDrawer: () => {},
    closeDrawer: () => {},
    addToCart: async () => {},
    updateQuantity: () => {},
    removeItem: () => {},
    refreshCart: async () => {},
    dismissError: () => {},
    error: null,
  }),
}));

// i18n navigation Link → plain anchor for testing
vi.mock("@/i18n/navigation", async () => {
  const React = await import("react");
  return {
    Link: ({ href, children, ...rest }: any) =>
      React.createElement("a", { href, ...rest }, children),
    useRouter: () => ({ push: () => {} }),
  };
});

// api-client stubs (some components import from here on render)
vi.mock("@/lib/api", () => ({
  getReactions: async () => ({ heart: { count: 0, reacted: false }, thumbs_up: { count: 0, reacted: false } }),
  toggleReaction: async () => ({}),
  postComment: async () => ({}),
  getAdminProducts: async () => ({ products: [] }),
  updateProduct: async () => ({}),
  getOrders: async () => ({ items: [], total: 0 }),
  createOrder: async () => ({}),
  getDeliveryCities: async () => [],
  getDeliveryOffices: async () => [],
}));

import { ProductCard } from "@/components/products/ProductCard";
import { CategoryFilter } from "@/components/products/CategoryFilter";
import { CartBadge } from "@/components/cart/CartBadge";
import { CartDrawer } from "@/components/cart/CartDrawer";
import { CartItem } from "@/components/cart/CartItem";
import { AddToCartButton } from "@/components/cart/AddToCartButton";
import { AddToCartSection } from "@/components/products/AddToCartSection";
import { CommentForm } from "@/components/products/CommentForm";
import { CommentCard } from "@/components/products/CommentCard";
import { OrderStatusBadge } from "@/components/orders/OrderStatusBadge";
import { LoginButton } from "@/components/auth/LoginButton";

const mockProduct = {
  id: "sku-1",
  name: "Test",
  price_cents: 100,
  stock: 5,
  primary_image_url: null,
  category: null,
  is_active: true,
} as any;

describe("testid contract", () => {
  it("ProductCard renders productCard testid", () => {
    const { container } = render(<ProductCard product={mockProduct} />);
    expect(container.querySelector(`[data-testid="${TEST_IDS.productCard}"]`)).toBeTruthy();
  });

  it("CategoryFilter renders categoryFilter testid", () => {
    const { container } = render(
      <CategoryFilter
        categories={["A", "B"]}
        activeCategory="All"
        onCategoryChange={() => {}}
        resultCount={2}
      />
    );
    expect(container.querySelector(`[data-testid="${TEST_IDS.categoryFilter}"]`)).toBeTruthy();
  });

  it("CartBadge renders cartBadge testid", () => {
    const { container } = render(<CartBadge count={3} />);
    expect(container.querySelector(`[data-testid="${TEST_IDS.cartBadge}"]`)).toBeTruthy();
  });

  it("CartDrawer renders cartDrawer testid", () => {
    const { container } = render(<CartDrawer />);
    expect(container.querySelector(`[data-testid="${TEST_IDS.cartDrawer}"]`)).toBeTruthy();
  });

  it("CartItem renders cartItem and cartRemove testids", () => {
    const item = {
      product_id: "sku-1",
      quantity: 1,
      product: mockProduct,
    } as any;
    const { container } = render(
      <CartItem item={item} onUpdateQuantity={() => {}} onRemove={() => {}} />
    );
    expect(container.querySelector(`[data-testid="${TEST_IDS.cartItem("sku-1")}"]`)).toBeTruthy();
    expect(container.querySelector(`[data-testid="${TEST_IDS.cartRemove("sku-1")}"]`)).toBeTruthy();
  });

  it("AddToCartButton renders addToCartBtn testid", () => {
    const { container } = render(<AddToCartButton productId="sku-1" stock={5} />);
    expect(container.querySelector(`[data-testid="${TEST_IDS.addToCartBtn}"]`)).toBeTruthy();
  });

  it("AddToCartSection renders addToCartBtn testid (product detail page)", () => {
    const { container } = render(<AddToCartSection productId="sku-1" stock={5} />);
    expect(container.querySelector(`[data-testid="${TEST_IDS.addToCartBtn}"]`)).toBeTruthy();
  });

  it("CommentForm renders commentForm testid", () => {
    const { container } = render(
      <CommentForm productId="sku-1" isLoggedInWithName={false} onCommentPosted={() => {}} />
    );
    expect(container.querySelector(`[data-testid="${TEST_IDS.commentForm}"]`)).toBeTruthy();
  });

  it("CommentCard renders commentCard testid", () => {
    const comment = {
      id: "c1",
      display_name: "Alice",
      body: "Hi",
      created_at: new Date().toISOString(),
    } as any;
    const { container } = render(<CommentCard comment={comment} />);
    expect(container.querySelector(`[data-testid="${TEST_IDS.commentCard}"]`)).toBeTruthy();
  });

  it("OrderStatusBadge renders orderStatus testid", () => {
    const { container } = render(<OrderStatusBadge status="pending" />);
    expect(container.querySelector(`[data-testid="${TEST_IDS.orderStatus}"]`)).toBeTruthy();
  });

  it("LoginButton renders loginButton testid", () => {
    const { container } = render(<LoginButton />);
    expect(container.querySelector(`[data-testid="${TEST_IDS.loginButton}"]`)).toBeTruthy();
  });
});
