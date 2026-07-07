/**
 * Mock API layer — returns hardcoded data matching TypeScript types.
 * Used when NEXT_PUBLIC_USE_MOCK_API is true (the default in development).
 */

import type {
  AuthTokenResponse,
  CartResponse,
  CreateOrderRequest,
  OrderListResponse,
  OrderResponse,
  ProductListResponse,
  ProductResponse,
  UserResponse,
} from "./types";
import { ApiError } from "./api-client";

// --- Helpers ---

function mockError(code: string, message: string): never {
  throw new ApiError({ error: { code, message, details: null } });
}

// --- Mock Data ---

const MOCK_PRODUCTS: ProductResponse[] = [
  {
    id: "lavender-dreams-300ml",
    name: "Lavender Dreams",
    description: "Hand-poured soy candle with French lavender essential oil.",
    materials: "Soy wax, French lavender essential oil, cotton wick",
    days_to_craft: 3,
    price_cents: 3200,
    category: "Floral",
    image_url: "/static/products/lavender-dreams-300ml.webp",
    stock: 24,
    is_active: true,
    is_featured: true,
    created_at: "2024-06-01T10:00:00Z",
    updated_at: "2024-06-01T10:00:00Z",
  },
  {
    id: "midnight-amber-300ml",
    name: "Midnight Amber",
    description: "Warm amber and sandalwood in a black ceramic vessel.",
    materials: "Coconut wax, amber resin, sandalwood oil",
    days_to_craft: 5,
    price_cents: 4500,
    category: "Woody",
    image_url: "/static/products/midnight-amber-300ml.webp",
    stock: 12,
    is_active: true,
    is_featured: true,
    created_at: "2024-06-02T11:00:00Z",
    updated_at: "2024-06-02T11:00:00Z",
  },
  {
    id: "citrus-garden-200ml",
    name: "Citrus Garden",
    description: "Bright blend of bergamot, lemon, and grapefruit.",
    materials: null,
    days_to_craft: 2,
    price_cents: 2800,
    category: "Fresh",
    image_url: null,
    stock: 36,
    is_active: true,
    is_featured: false,
    created_at: "2024-06-03T09:00:00Z",
    updated_at: "2024-06-03T09:00:00Z",
  },
  {
    id: "vanilla-bourbon-300ml",
    name: "Vanilla Bourbon",
    description: null,
    materials: null,
    days_to_craft: null,
    price_cents: 3800,
    category: "Gourmand",
    image_url: "/static/products/vanilla-bourbon-300ml.webp",
    stock: 0,
    is_active: false,
    is_featured: false,
    created_at: "2024-06-04T14:00:00Z",
    updated_at: "2024-06-05T08:00:00Z",
  },
];

const MOCK_USER: UserResponse = {
  id: "user-001",
  email: "marie@ateliermarie.com",
  name: "Marie",
  avatar_url: "https://lh3.googleusercontent.com/example",
  is_admin: true,
};

// --- In-Memory Cart State ---

interface MockCartItem {
  product_id: string;
  quantity: number;
  added_at: string;
}

let mockCart: MockCartItem[] = [
  { product_id: "lavender-dreams-300ml", quantity: 2, added_at: "2024-06-10T15:30:00Z" },
  { product_id: "midnight-amber-300ml", quantity: 1, added_at: "2024-06-10T15:32:00Z" },
];

function buildCartResponse(): CartResponse {
  const items = mockCart
    .map((ci) => {
      const product = MOCK_PRODUCTS.find((p) => p.id === ci.product_id);
      if (!product) return null;
      return {
        product_id: ci.product_id,
        product,
        quantity: ci.quantity,
        added_at: ci.added_at,
      };
    })
    .filter((item): item is NonNullable<typeof item> => item !== null);

  const total_cents = items.reduce(
    (sum, item) => sum + item.product.price_cents * item.quantity,
    0
  );
  return {
    items,
    total_cents,
    item_count: items.reduce((sum, item) => sum + item.quantity, 0),
  };
}

// --- Mock Functions ---

export async function getProducts(
  page = 1,
  limit = 20
): Promise<ProductListResponse> {
  if (limit > 100) mockError("VALIDATION_ERROR", "Limit exceeds maximum of 100");
  const active = MOCK_PRODUCTS.filter((p) => p.is_active);
  const start = (page - 1) * limit;
  const slice = active.slice(start, start + limit);
  return {
    products: slice,
    total: active.length,
    page,
    limit,
  };
}

export async function getProduct(
  productId: string
): Promise<ProductResponse> {
  const product = MOCK_PRODUCTS.find((p) => p.id === productId && p.is_active);
  if (!product) mockError("NOT_FOUND", `Product ${productId} not found`);
  return product;
}

export async function getCart(): Promise<CartResponse> {
  return buildCartResponse();
}

export async function addToCart(
  productId: string,
  quantity = 1
): Promise<CartResponse> {
  const product = MOCK_PRODUCTS.find((p) => p.id === productId && p.is_active);
  if (!product) mockError("NOT_FOUND", `Product ${productId} not found`);
  if (product.stock < quantity) {
    mockError("CONFLICT", `Insufficient stock for ${productId}`);
  }

  const existing = mockCart.find((ci) => ci.product_id === productId);
  if (existing) {
    existing.quantity += quantity;
  } else {
    mockCart.push({
      product_id: productId,
      quantity,
      added_at: new Date().toISOString(),
    });
  }
  return buildCartResponse();
}

export async function updateCartItem(
  productId: string,
  quantity: number
): Promise<CartResponse> {
  if (quantity === 0) {
    mockCart = mockCart.filter((ci) => ci.product_id !== productId);
  } else {
    const existing = mockCart.find((ci) => ci.product_id === productId);
    if (!existing) mockError("NOT_FOUND", `Cart item ${productId} not found`);
    existing.quantity = quantity;
  }
  return buildCartResponse();
}

export async function removeFromCart(
  productId: string
): Promise<CartResponse> {
  mockCart = mockCart.filter((ci) => ci.product_id !== productId);
  return buildCartResponse();
}

export async function createOrder(
  _data: CreateOrderRequest
): Promise<OrderResponse> {
  return {
    id: "order-001",
    status: "pending",
    total_cents: 3200 * 2 + 4500 * 1,
    customer_email: _data.customer_email,
    customer_name: _data.customer_name ?? null,
    shipping_address: _data.shipping_address ?? null,
    notes: _data.notes ?? null,
    items: [
      {
        product_id: "lavender-dreams-300ml",
        product_name: "Lavender Dreams",
        price_cents: 3200,
        quantity: 2,
      },
      {
        product_id: "midnight-amber-300ml",
        product_name: "Midnight Amber",
        price_cents: 4500,
        quantity: 1,
      },
    ],
    created_at: "2024-06-10T16:00:00Z",
    updated_at: "2024-06-10T16:00:00Z",
  };
}

export async function getOrders(
  page = 1,
  limit = 20
): Promise<OrderListResponse> {
  if (limit > 100) mockError("VALIDATION_ERROR", "Limit exceeds maximum of 100");
  const order: OrderResponse = {
    id: "order-001",
    status: "confirmed",
    total_cents: 2 * 3200 + 4500,
    customer_email: "customer@example.com",
    customer_name: "Test Customer",
    shipping_address: "123 Main St, Paris",
    notes: null,
    items: [
      {
        product_id: "lavender-dreams-300ml",
        product_name: "Lavender Dreams",
        price_cents: 3200,
        quantity: 2,
      },
      {
        product_id: "midnight-amber-300ml",
        product_name: "Midnight Amber",
        price_cents: 4500,
        quantity: 1,
      },
    ],
    created_at: "2024-06-10T16:00:00Z",
    updated_at: "2024-06-11T09:00:00Z",
  };
  return { orders: [order], total: 1, page, limit };
}

export async function getOrder(orderId: string): Promise<OrderResponse> {
  const list = await getOrders();
  const order = list.orders.find((o) => o.id === orderId);
  if (!order) mockError("NOT_FOUND", `Order ${orderId} not found`);
  return order;
}

export async function getCurrentUser(): Promise<UserResponse | null> {
  return MOCK_USER;
}

export async function login(
  _code: string,
  _redirectUri: string
): Promise<AuthTokenResponse> {
  return {
    access_token: "mock-jwt-token",
    token_type: "bearer",
    user: MOCK_USER,
  };
}
