/**
 * Mock API layer — returns hardcoded data matching TypeScript types.
 * Used when NEXT_PUBLIC_USE_MOCK_API is true (the default in development).
 */

import type {
  AdminProductListResponse,
  AdminProductResponse,
  AdminStats,
  AuthTokenResponse,
  CartItemResponse,
  CartResponse,
  CommentCreateRequest,
  CommentListResponse,
  CommentResponse,
  CommentSort,
  CreateOrderRequest,
  CreateProductRequest,
  ImageUploadResponse,
  OrderListResponse,
  OrderResponse,
  OrderStatus,
  ProductListResponse,
  ProductResponse,
  ReactionCountsResponse,
  ReactionToggleRequest,
  ReactionToggleResponse,
  UpdateProductRequest,
  UserResponse,
} from "./types";
import { ApiError } from "./api-client";

// --- Helpers ---

function mockError(code: string, message: string): never {
  throw new ApiError({ error: { code, message, details: null } });
}

/** Simulate network latency (50–150ms). */
function delay(): Promise<void> {
  const ms = 50 + Math.floor(Math.random() * 100);
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** Generate a UUID-like identifier for orders. */
function generateOrderId(): string {
  const hex = () => Math.floor(Math.random() * 16).toString(16);
  const seg = (n: number) => Array.from({ length: n }, hex).join("");
  return `${seg(8)}-${seg(4)}-4${seg(3)}-${seg(4)}-${seg(12)}`;
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

let mockCartItems: MockCartItem[] = [];

// --- In-Memory Auth State ---

let mockIsAuthenticated = true;

// --- In-Memory Order Store ---

const mockOrders: OrderResponse[] = [];

// --- Cart Helpers ---

function buildCartResponse(): CartResponse {
  const items: CartItemResponse[] = mockCartItems
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
  limit = 20,
  _locale?: string
): Promise<ProductListResponse> {
  await delay();
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
  productId: string,
  _locale?: string
): Promise<ProductResponse> {
  await delay();
  const product = MOCK_PRODUCTS.find((p) => p.id === productId && p.is_active);
  if (!product) mockError("NOT_FOUND", `Product ${productId} not found`);
  return product;
}

export async function getCart(): Promise<CartResponse> {
  await delay();
  return buildCartResponse();
}

export async function addToCart(
  productId: string,
  quantity = 1
): Promise<CartResponse> {
  await delay();
  const product = MOCK_PRODUCTS.find((p) => p.id === productId && p.is_active);
  if (!product) mockError("NOT_FOUND", `Product ${productId} not found`);

  if (!Number.isInteger(quantity) || quantity < 1 || quantity > 99) {
    mockError("VALIDATION_ERROR", "Quantity must be between 1 and 99");
  }

  const existing = mockCartItems.find((ci) => ci.product_id === productId);
  const currentQty = existing ? existing.quantity : 0;
  const requestedTotal = currentQty + quantity;

  if (requestedTotal > product.stock) {
    mockError("CONFLICT", `Insufficient stock for ${productId}`);
  }

  if (existing) {
    existing.quantity = requestedTotal;
  } else {
    mockCartItems.push({
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
  await delay();
  const existing = mockCartItems.find((ci) => ci.product_id === productId);
  if (!existing) mockError("NOT_FOUND", `Cart item ${productId} not found`);

  if (quantity === 0) {
    mockCartItems = mockCartItems.filter((ci) => ci.product_id !== productId);
  } else {
    const product = MOCK_PRODUCTS.find((p) => p.id === productId);
    if (product && quantity > product.stock) {
      mockError("CONFLICT", `Insufficient stock for ${productId}`);
    }
    existing.quantity = quantity;
  }
  return buildCartResponse();
}

export async function removeFromCart(
  productId: string
): Promise<CartResponse> {
  await delay();
  const existing = mockCartItems.find((ci) => ci.product_id === productId);
  if (!existing) mockError("NOT_FOUND", `Cart item ${productId} not found`);

  mockCartItems = mockCartItems.filter((ci) => ci.product_id !== productId);
  return buildCartResponse();
}

export async function createOrder(
  data: CreateOrderRequest
): Promise<OrderResponse> {
  await delay();
  if (mockCartItems.length === 0) {
    mockError("VALIDATION_ERROR", "Cart is empty");
  }

  const cart = buildCartResponse();
  const now = new Date().toISOString();

  const order: OrderResponse = {
    id: generateOrderId(),
    status: "pending",
    total_cents: cart.total_cents,
    customer_email: data.customer_email,
    customer_name: data.customer_name ?? null,
    shipping_address: data.shipping_address ?? null,
    notes: data.notes ?? null,
    items: cart.items.map((item) => ({
      product_id: item.product_id,
      product_name: item.product.name,
      price_cents: item.product.price_cents,
      quantity: item.quantity,
    })),
    created_at: now,
    updated_at: now,
  };

  mockOrders.push(order);
  mockCartItems = [];

  return order;
}

export async function getOrders(
  page = 1,
  limit = 20
): Promise<OrderListResponse> {
  await delay();
  if (limit > 100) mockError("VALIDATION_ERROR", "Limit exceeds maximum of 100");

  const start = (page - 1) * limit;
  const slice = mockOrders.slice(start, start + limit);
  return {
    orders: slice,
    total: mockOrders.length,
    page,
    limit,
  };
}

export async function getOrder(orderId: string): Promise<OrderResponse> {
  await delay();
  const order = mockOrders.find((o) => o.id === orderId);
  if (!order) mockError("NOT_FOUND", `Order ${orderId} not found`);
  return order;
}

export async function getCurrentUser(): Promise<UserResponse | null> {
  await delay();
  return mockIsAuthenticated ? MOCK_USER : null;
}

export async function login(
  _code: string,
  _redirectUri: string
): Promise<AuthTokenResponse> {
  await delay();
  mockIsAuthenticated = true;
  return {
    access_token: "mock-jwt-token",
    token_type: "bearer",
    user: MOCK_USER,
  };
}

export function mockLogout(): void {
  mockIsAuthenticated = false;
  window.dispatchEvent(new Event("session-rotated"));
}

export function mockLogin(): void {
  mockIsAuthenticated = true;
}

// --- Admin Functions ---

const MOCK_ORDERS_SEEDED: OrderResponse[] = [
  {
    id: "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
    status: "pending",
    total_cents: 7700,
    customer_email: "alice@example.com",
    customer_name: "Alice Johnson",
    shipping_address: "123 Main St, Paris, FR",
    notes: null,
    items: [
      { product_id: "lavender-dreams-300ml", product_name: "Lavender Dreams", price_cents: 3200, quantity: 1 },
      { product_id: "midnight-amber-300ml", product_name: "Midnight Amber", price_cents: 4500, quantity: 1 },
    ],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e",
    status: "confirmed",
    total_cents: 5600,
    customer_email: "bob@example.com",
    customer_name: "Bob Smith",
    shipping_address: "456 Oak Ave, Lyon, FR",
    notes: "Gift wrapping please",
    items: [
      { product_id: "citrus-garden-200ml", product_name: "Citrus Garden", price_cents: 2800, quantity: 2 },
    ],
    created_at: new Date(Date.now() - 86400000).toISOString(),
    updated_at: new Date(Date.now() - 43200000).toISOString(),
  },
  {
    id: "c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f",
    status: "shipped",
    total_cents: 3200,
    customer_email: "carol@example.com",
    customer_name: "Carol Davis",
    shipping_address: "789 Pine Rd, Marseille, FR",
    notes: null,
    items: [
      { product_id: "lavender-dreams-300ml", product_name: "Lavender Dreams", price_cents: 3200, quantity: 1 },
    ],
    created_at: new Date(Date.now() - 172800000).toISOString(),
    updated_at: new Date(Date.now() - 86400000).toISOString(),
  },
  {
    id: "d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f8a",
    status: "delivered",
    total_cents: 9000,
    customer_email: "dave@example.com",
    customer_name: "Dave Wilson",
    shipping_address: "321 Elm St, Nice, FR",
    notes: null,
    items: [
      { product_id: "midnight-amber-300ml", product_name: "Midnight Amber", price_cents: 4500, quantity: 2 },
    ],
    created_at: new Date(Date.now() - 604800000).toISOString(),
    updated_at: new Date(Date.now() - 259200000).toISOString(),
  },
];

export async function getAdminStats(): Promise<AdminStats> {
  await delay();
  const today = new Date().toISOString().split("T")[0]!;
  const allOrders = [...MOCK_ORDERS_SEEDED, ...mockOrders];
  const ordersToday = allOrders.filter(
    (o) => o.created_at.startsWith(today)
  ).length;
  const weekAgo = Date.now() - 7 * 86400000;
  const revenueThisWeek = allOrders
    .filter((o) => new Date(o.created_at).getTime() > weekAgo && o.status !== "cancelled")
    .reduce((sum, o) => sum + o.total_cents, 0);
  const activeProducts = MOCK_PRODUCTS.filter((p) => p.is_active).length;
  return {
    orders_today: ordersToday,
    revenue_this_week_cents: revenueThisWeek,
    active_product_count: activeProducts,
  };
}

/** Convert a public ProductResponse to an AdminProductResponse for mock admin endpoints. */
function toAdminProduct(product: ProductResponse): AdminProductResponse {
  return {
    id: product.id,
    name_en: product.name,
    name_bg: null,
    description_en: product.description,
    description_bg: null,
    materials: product.materials,
    days_to_craft: product.days_to_craft,
    price_cents: product.price_cents,
    category: product.category,
    image_url: product.image_url,
    stock: product.stock,
    is_active: product.is_active,
    is_featured: product.is_featured,
    translation_stale_bg: false,
    translation_stale_en: false,
    created_at: product.created_at,
    updated_at: product.updated_at,
  };
}

export async function getAdminProducts(
  page = 1,
  limit = 20
): Promise<AdminProductListResponse> {
  await delay();
  const start = (page - 1) * limit;
  const slice = MOCK_PRODUCTS.slice(start, start + limit);
  return {
    products: slice.map(toAdminProduct),
    total: MOCK_PRODUCTS.length,
    page,
    limit,
  };
}

export async function getAdminProduct(productId: string): Promise<AdminProductResponse> {
  await delay();
  const product = MOCK_PRODUCTS.find((p) => p.id === productId);
  if (!product) mockError("NOT_FOUND", `Product ${productId} not found`);
  return toAdminProduct(product);
}

export async function createProduct(data: CreateProductRequest): Promise<AdminProductResponse> {
  await delay();
  const existing = MOCK_PRODUCTS.find((p) => p.id === data.id);
  if (existing) mockError("CONFLICT", `Product ${data.id} already exists`);
  const now = new Date().toISOString();
  const product: ProductResponse = {
    id: data.id,
    name: data.name_en,
    description: data.description_en ?? null,
    materials: data.materials ?? null,
    days_to_craft: data.days_to_craft ?? null,
    price_cents: data.price_cents,
    category: data.category,
    image_url: data.image_url ?? null,
    stock: data.stock,
    is_active: true,
    is_featured: data.is_featured ?? false,
    created_at: now,
    updated_at: now,
  };
  MOCK_PRODUCTS.push(product);
  return toAdminProduct(product);
}

export async function updateProduct(
  productId: string,
  data: UpdateProductRequest
): Promise<AdminProductResponse> {
  await delay();
  const product = MOCK_PRODUCTS.find((p) => p.id === productId);
  if (!product) mockError("NOT_FOUND", `Product ${productId} not found`);
  // Map bilingual fields to the mock's single-language store
  if (data.name_en !== undefined) product.name = data.name_en;
  if (data.description_en !== undefined) product.description = data.description_en;
  if (data.materials !== undefined) product.materials = data.materials;
  if (data.days_to_craft !== undefined) product.days_to_craft = data.days_to_craft;
  if (data.price_cents !== undefined) product.price_cents = data.price_cents;
  if (data.category !== undefined) product.category = data.category;
  if (data.image_url !== undefined) product.image_url = data.image_url;
  if (data.stock !== undefined) product.stock = data.stock;
  if (data.is_active !== undefined) product.is_active = data.is_active;
  if (data.is_featured !== undefined) product.is_featured = data.is_featured;
  product.updated_at = new Date().toISOString();
  return toAdminProduct(product);
}

export async function uploadProductImage(
  productId: string,
  file: File
): Promise<ImageUploadResponse> {
  await delay();
  const product = MOCK_PRODUCTS.find((p) => p.id === productId);
  if (!product) mockError("product_not_found", `Product ${productId} not found`);
  if (!/^image\/(jpeg|png)$/.test(file.type)) {
    mockError("invalid_image_type", "Only JPEG and PNG images are accepted");
  }
  const imageUrl = `/static/products/${productId}.webp`;
  product.image_url = imageUrl;
  product.updated_at = new Date().toISOString();
  return {
    image_url: imageUrl,
    thumbnail_url: `/static/products/${productId}_thumb.webp`,
  };
}

export async function getAdminOrders(
  page = 1,
  limit = 20,
  status?: string
): Promise<OrderListResponse> {
  await delay();
  const allOrders = [...MOCK_ORDERS_SEEDED, ...mockOrders];
  const filtered = status
    ? allOrders.filter((o) => o.status === status)
    : allOrders;
  const start = (page - 1) * limit;
  const slice = filtered.slice(start, start + limit);
  return {
    orders: slice,
    total: filtered.length,
    page,
    limit,
  };
}

export async function updateOrderStatus(
  orderId: string,
  status: OrderStatus
): Promise<OrderResponse> {
  await delay();
  const allOrders = [...MOCK_ORDERS_SEEDED, ...mockOrders];
  const order = allOrders.find((o) => o.id === orderId);
  if (!order) mockError("NOT_FOUND", `Order ${orderId} not found`);

  const validTransitions: Record<OrderStatus, OrderStatus[]> = {
    pending: ["confirmed", "cancelled"],
    confirmed: ["shipped", "cancelled"],
    shipped: ["delivered"],
    delivered: [],
    cancelled: [],
  };

  if (!validTransitions[order.status].includes(status)) {
    mockError("VALIDATION_ERROR", `Cannot transition from ${order.status} to ${status}`);
  }

  order.status = status;
  order.updated_at = new Date().toISOString();
  return order;
}

// --- Reactions Mock ---

const mockReactions: Map<string, Set<string>> = new Map(); // key: "productId:type", value: set of sessions

export async function toggleReaction(
  productId: string,
  body: ReactionToggleRequest
): Promise<ReactionToggleResponse> {
  await delay();
  const key = `${productId}:${body.reaction_type}`;
  const sessions = mockReactions.get(key) ?? new Set();
  const mockSessionId = "mock-session";

  let active: boolean;
  if (sessions.has(mockSessionId)) {
    sessions.delete(mockSessionId);
    active = false;
  } else {
    sessions.add(mockSessionId);
    active = true;
  }
  mockReactions.set(key, sessions);

  return { reaction_type: body.reaction_type, active };
}

export async function getReactions(
  productId: string
): Promise<ReactionCountsResponse> {
  await delay();
  const heartKey = `${productId}:heart`;
  const thumbsKey = `${productId}:thumbs_up`;
  const mockSessionId = "mock-session";

  const heartSessions = mockReactions.get(heartKey) ?? new Set();
  const thumbsSessions = mockReactions.get(thumbsKey) ?? new Set();

  return {
    heart: { count: heartSessions.size, reacted: heartSessions.has(mockSessionId) },
    thumbs_up: { count: thumbsSessions.size, reacted: thumbsSessions.has(mockSessionId) },
  };
}

// --- Comments Mock ---

const mockComments: CommentResponse[] = [
  {
    id: "comment-1",
    display_name: "Marie",
    body: "This candle smells absolutely divine! Perfect for relaxing evenings.",
    created_at: new Date(Date.now() - 86400000).toISOString(),
  },
  {
    id: "comment-2",
    display_name: "Sophie",
    body: "Bought this as a gift and my friend loved it!",
    created_at: new Date(Date.now() - 172800000).toISOString(),
  },
];

export async function postComment(
  productId: string,
  body: CommentCreateRequest
): Promise<CommentResponse> {
  await delay();
  const product = MOCK_PRODUCTS.find((p) => p.id === productId);
  if (!product) mockError("NOT_FOUND", `Product ${productId} not found`);

  const comment: CommentResponse = {
    id: generateOrderId(),
    display_name: body.display_name ?? "Anonymous",
    body: body.body,
    created_at: new Date().toISOString(),
  };
  mockComments.unshift(comment);
  return comment;
}

export async function getComments(
  _productId: string,
  sort: CommentSort = "newest",
  page: number = 1,
  limit: number = 20
): Promise<CommentListResponse> {
  await delay();
  const sorted = [...mockComments].sort((a, b) => {
    const cmp = a.created_at.localeCompare(b.created_at);
    return sort === "newest" ? -cmp : cmp;
  });
  const start = (page - 1) * limit;
  const items = sorted.slice(start, start + limit);
  return { items, total: mockComments.length, page, limit };
}
