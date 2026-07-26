/**
 * Single source of truth for data-testid values used by the E2E test suite.
 *
 * NEVER hardcode a testid string in a component — always import from here.
 * When you add, remove, or rename a testid, run `make generate-testids` to
 * regenerate `tests/e2e/testids.py`, and commit both files together.
 */
export const TEST_IDS = {
  // Products
  productCard: "product-card",
  categoryFilter: "category-filter",

  // Cart
  cartBadge: "cart-badge",
  cartDrawer: "cart-drawer",
  cartItem: (productId: string) => `cart-item-${productId}`,
  cartRemove: (productId: string) => `cart-remove-${productId}`,
  addToCartBtn: "add-to-cart-btn",

  // Comments
  commentForm: "comment-form",
  commentCard: "comment-card",

  // Admin
  adminProductRow: (id: string) => `admin-product-row-${id}`,
  adminEditLink: (id: string) => `admin-edit-${id}`,

  // Orders
  orderRow: (id: string) => `order-row-${id}`,
  orderStatus: "order-status",

  // Auth
  loginButton: "login-button",
} as const;
