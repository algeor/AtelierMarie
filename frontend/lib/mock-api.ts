/**
 * Mock API layer — returns hardcoded data matching TypeScript types.
 * Used when NEXT_PUBLIC_USE_MOCK_API is true (the default in development).
 */

import type {
  AdminProductListResponse,
  AdminProductResponse,
  AdminStats,
  AdminTaxonomyTerm,
  AuthTokenResponse,
  BannerAdminResponse,
  BannerUpdateRequest,
  BulkDiscountRequest,
  BulkDiscountResponse,
  BulkResultItem,
  CampaignCreateRequest,
  CampaignListResponse,
  CampaignResponse,
  CampaignUpdateRequest,
  CartItemResponse,
  CartResponse,
  CommentCreateRequest,
  CommentListResponse,
  CommentResponse,
  CommentSort,
  ContactRequest,
  ContactResponse,
  Courier,
  CreateOrderRequest,
  CreateProductRequest,
  CreateTaxonomyTermRequest,
  ImageUploadResponse,
  OfficeResponse,
  OfficeType,
  OrderListResponse,
  OrderResponse,
  OrderStatus,
  ProductListResponse,
  ProductImage,
  ProductResponse,
  ProductVideo,
  PublicBannerResponse,
  ReactionCountsResponse,
  ReactionToggleRequest,
  ReactionToggleResponse,
  TaxonomyKind,
  TaxonomyResponse,
  UpdateProductRequest,
  UpdateTaxonomyTermRequest,
  UserResponse,
  VideoUploadResponse,
} from "./types";
import { ApiError } from "./api-client";
import { buildTrackingUrl } from "./tracking";

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

// The mock store carries admin-only fields even though ProductResponse omits them.
type MockProduct = ProductResponse & {
  weight_grams: number;
  discount_starts_at: string | null;
  discount_ends_at: string | null;
};

/** Strip admin-only fields so public responses match the real API. */
function toPublicProduct(product: MockProduct): ProductResponse {
  const {
    weight_grams: _weight_grams,
    discount_starts_at: _discount_starts_at,
    discount_ends_at: _discount_ends_at,
    ...pub
  } = product;
  return pub;
}

function mockProductImage(productId: string, sortOrder = 0, isPrimary = true): ProductImage {
  return {
    id: `${productId}-${sortOrder}`,
    image_url: `/static/products/${productId}.webp`,
    thumbnail_url: `/static/products/${productId}_thumb.webp`,
    sort_order: sortOrder,
    is_primary: isPrimary,
  };
}

function mockProductVideo(productId: string, sortOrder = 1): ProductVideo {
  return {
    id: `${productId}-video`,
    product_id: productId,
    status: "ready",
    video_url: `/static/products/${productId}_video.mp4`,
    poster_url: `/static/products/${productId}_thumb.webp`,
    sort_order: sortOrder,
    duration_secs: 18,
    failure_reason: null,
    created_at: "2024-06-01T10:00:00Z",
    updated_at: "2024-06-01T10:00:00Z",
  };
}

function primaryImageUrl(images: ProductImage[]): string | null {
  return images.find((image) => image.is_primary)?.image_url ?? null;
}

function primaryThumbnailUrl(images: ProductImage[]): string | null {
  return images.find((image) => image.is_primary)?.thumbnail_url ?? null;
}

/** Recompute discount_active + effective_price_cents from the raw config (mirrors backend). */
function applyMockPricing(product: MockProduct): MockProduct {
  const percent = product.discount_percent;
  const now = new Date();
  const active =
    percent != null &&
    (!product.discount_starts_at || now >= new Date(product.discount_starts_at)) &&
    (!product.discount_ends_at || now <= new Date(product.discount_ends_at));
  product.discount_active = active;
  product.effective_price_cents =
    active && percent != null
      ? Math.max(1, Math.floor((product.price_cents * (100 - percent) + 50) / 100))
      : product.price_cents;
  return product;
}
const MOCK_PRODUCTS: MockProduct[] = [
  {
    id: "lavender-dreams-300ml",
    name: "Lavender Dreams",
    description: "Hand-poured soy candle with French lavender essential oil.",
    materials: "Soy wax, French lavender essential oil, cotton wick",
    days_to_craft: 3,
    price_cents: 3200,
    effective_price_cents: 2560,
    discount_percent: 20,
    discount_active: true,
    discount_starts_at: null,
    discount_ends_at: null,
    category: "medium",
    category_name: "Medium",
    product_type: "candles",
    product_type_name: "Candles",
    labels: [{ slug: "floral", name: "Floral" }],
    images: [mockProductImage("lavender-dreams-300ml")],
    video: mockProductVideo("lavender-dreams-300ml"),
    primary_image_url: "/static/products/lavender-dreams-300ml.webp",
    primary_thumbnail_url: "/static/products/lavender-dreams-300ml_thumb.webp",
    stock: 24,
    weight_grams: 300,
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
    effective_price_cents: 4500,
    discount_percent: null,
    discount_active: false,
    discount_starts_at: null,
    discount_ends_at: null,
    category: "premium",
    category_name: "Premium",
    product_type: "candles",
    product_type_name: "Candles",
    labels: [
      { slug: "woody", name: "Woody" },
      { slug: "gift", name: "Gift" },
    ],
    images: [mockProductImage("midnight-amber-300ml")],
    video: null,
    primary_image_url: "/static/products/midnight-amber-300ml.webp",
    primary_thumbnail_url: "/static/products/midnight-amber-300ml_thumb.webp",
    stock: 12,
    weight_grams: 450,
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
    effective_price_cents: 2800,
    discount_percent: null,
    discount_active: false,
    discount_starts_at: null,
    discount_ends_at: null,
    category: "small",
    category_name: "Small",
    product_type: "candles",
    product_type_name: "Candles",
    labels: [
      { slug: "fresh", name: "Fresh" },
      { slug: "citrus", name: "Citrus" },
    ],
    images: [],
    video: null,
    primary_image_url: null,
    primary_thumbnail_url: null,
    stock: 36,
    weight_grams: 250,
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
    effective_price_cents: 3800,
    discount_percent: null,
    discount_active: false,
    discount_starts_at: null,
    discount_ends_at: null,
    category: null,
    category_name: null,
    product_type: "candles",
    product_type_name: "Candles",
    labels: [{ slug: "gourmand", name: "Gourmand" }],
    images: [mockProductImage("vanilla-bourbon-300ml")],
    video: null,
    primary_image_url: "/static/products/vanilla-bourbon-300ml.webp",
    primary_thumbnail_url: "/static/products/vanilla-bourbon-300ml_thumb.webp",
    stock: 0,
    weight_grams: 500,
    is_active: false,
    is_featured: false,
    created_at: "2024-06-04T14:00:00Z",
    updated_at: "2024-06-05T08:00:00Z",
  },
];

// --- In-Memory Taxonomy State (mock) ---

interface MockTerm {
  slug: string;
  name_en: string;
  name_bg: string | null;
  sort_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

function mockTerm(slug: string, name_en: string, name_bg: string, sort_order: number): MockTerm {
  return {
    slug,
    name_en,
    name_bg,
    sort_order,
    is_active: true,
    created_at: "2024-06-01T10:00:00Z",
    updated_at: "2024-06-01T10:00:00Z",
  };
}

const MOCK_TAXONOMY: Record<TaxonomyKind, MockTerm[]> = {
  "product-types": [mockTerm("candles", "Candles", "Свещи", 0), mockTerm("boxes", "Boxes", "Кутии", 1)],
  categories: [
    mockTerm("small", "Small", "Малка", 0),
    mockTerm("medium", "Medium", "Средна", 1),
    mockTerm("premium", "Premium", "Премиум", 2),
  ],
  labels: [
    mockTerm("floral", "Floral", "Флорални", 0),
    mockTerm("woody", "Woody", "Дървесни", 1),
    mockTerm("fresh", "Fresh", "Свежи", 2),
    mockTerm("gourmand", "Gourmand", "Гурме", 3),
    mockTerm("citrus", "Citrus", "Цитрусови", 4),
    mockTerm("winter", "Winter", "Зима", 5),
    mockTerm("gift", "Gift", "Подарък", 6),
  ],
};

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
    (sum, item) => sum + item.product.effective_price_cents * item.quantity,
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
    products: slice.map(toPublicProduct),
    total: active.length,
    page,
    limit,
  };
}

export async function submitContact(
  data: ContactRequest
): Promise<ContactResponse> {
  await delay();
  if (data.website?.trim()) return { status: "received", message_id: null };
  if (!data.name.trim() || !data.email.trim() || !data.message.trim()) {
    mockError("VALIDATION_ERROR", "Please check your input and try again");
  }
  return { status: "received", message_id: Date.now() };
}

export async function getProduct(
  productId: string,
  _locale?: string
): Promise<ProductResponse> {
  await delay();
  const product = MOCK_PRODUCTS.find((p) => p.id === productId && p.is_active);
  if (!product) mockError("NOT_FOUND", `Product ${productId} not found`);
  return toPublicProduct(product);
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

// --- Mock Delivery Data ---

const MOCK_OFFICES: Record<Courier, OfficeResponse[]> = {
  speedy: [
    { id: "speedy-sf-001", name: "Speedy офис София Център - бул. Витоша 50", type: "office", city: "София", address: "бул. Витоша 50", working_hours: "Mon-Fri 09:00-18:00, Sat 09:00-14:00" },
    { id: "speedy-sf-002", name: "Speedy офис София Младост", type: "office", city: "София", address: "бул. Александър Малинов 12", working_hours: "Mon-Fri 09:00-18:00" },
    { id: "speedy-apt-sf-01", name: "Speedy Автомат Витоша Мол", type: "apt", city: "София", address: "Витоша Мол, паркинг", working_hours: "24/7" },
    { id: "speedy-plovdiv-001", name: "Speedy офис Пловдив Централ", type: "office", city: "Пловдив", address: "бул. Мария Луиза 5", working_hours: "Mon-Fri 09:00-18:00" },
    { id: "speedy-varna-001", name: "Speedy офис Варна Център", type: "office", city: "Варна", address: "бул. Сливница 10", working_hours: "Mon-Fri 09:00-18:00" },
  ],
  econt: [
    { id: "econt-sf-001", name: "Econt София Център", type: "office", city: "София", address: "ул. Раковски 100", working_hours: "Mon-Fri 09:00-19:00, Sat 09:00-15:00" },
    { id: "econt-apt-sf-01", name: "Econt Автомат Люлин", type: "apt", city: "София", address: "ж.к. Люлин, до Билла", working_hours: "24/7" },
    { id: "econt-plovdiv-001", name: "Econt Пловдив Централ", type: "office", city: "Пловдив", address: "бул. Шести септември 20", working_hours: "Mon-Fri 09:00-19:00" },
    { id: "econt-burgas-001", name: "Econt Бургас Център", type: "office", city: "Бургас", address: "ул. Александровска 45", working_hours: "Mon-Fri 09:00-18:00" },
  ],
};

export async function getDeliveryOffices(
  courier: Courier,
  city: string,
  type?: OfficeType
): Promise<OfficeResponse[]> {
  await delay();
  const cityLc = city.toLowerCase();
  return MOCK_OFFICES[courier].filter(
    (o) => o.city.toLowerCase() === cityLc && (!type || o.type === type)
  );
}

export async function getDeliveryCities(
  courier: Courier,
  query?: string
): Promise<string[]> {
  await delay();
  const cities = Array.from(new Set(MOCK_OFFICES[courier].map((o) => o.city))).sort();
  if (!query) return cities;
  const q = query.toLowerCase();
  return cities.filter((c) => c.toLowerCase().startsWith(q));
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
    payment_method: (data as { payment_method?: string }).payment_method === "card" ? "card"
      : (data as { payment_method?: string }).payment_method === "bank_transfer" ? "bank_transfer"
      : "cod",
    payment_status: (data as { payment_method?: string }).payment_method === "cod" || !(data as { payment_method?: string }).payment_method
      ? "cod_pending" : "pending",
    stripe_checkout_url: null,
    items_total_cents: cart.total_cents,
    shipping_cents: 0,
    total_cents: cart.total_cents,
    customer_email: data.customer_email,
    customer_name: data.customer_name ?? null,
    delivery_method: data.delivery.method,
    delivery_courier:
      data.delivery.method === "office"
        ? data.delivery.office?.courier ?? null
        : data.delivery.door?.courier ?? null,
    delivery_details:
      data.delivery.method === "office"
        ? data.delivery.office ?? null
        : data.delivery.door ?? null,
    notes: data.notes ?? null,
    items: cart.items.map((item) => ({
      product_id: item.product_id,
      product_name: item.product.name,
      price_cents: item.product.effective_price_cents,
      quantity: item.quantity,
    })),
    tracking_number: null,
    tracking_carrier: null,
    tracking_url: null,
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
    items: slice,
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
    payment_method: "bank_transfer",
    payment_status: "pending",
    stripe_checkout_url: null,
    items_total_cents: 7700,
    shipping_cents: 0,
    total_cents: 7700,
    customer_email: "alice@example.com",
    customer_name: "Alice Johnson",
    delivery_method: "office",
    delivery_courier: "speedy",
    delivery_details: {
      courier: "speedy",
      office_id: "speedy-sf-001",
      office_name: "Speedy офис София Център",
      office_type: "office",
      phone: "+359888123456",
    },
    notes: null,
    items: [
      { product_id: "lavender-dreams-300ml", product_name: "Lavender Dreams", price_cents: 3200, quantity: 1 },
      { product_id: "midnight-amber-300ml", product_name: "Midnight Amber", price_cents: 4500, quantity: 1 },
    ],
    tracking_number: null,
    tracking_carrier: null,
    tracking_url: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e",
    status: "confirmed",
    payment_method: "cod",
    payment_status: "cod_pending",
    stripe_checkout_url: null,
    items_total_cents: 5600,
    shipping_cents: 0,
    total_cents: 5600,
    customer_email: "bob@example.com",
    customer_name: "Bob Smith",
    delivery_method: "door",
    delivery_courier: "econt",
    delivery_details: {
      courier: "econt",
      city: "София",
      postal_code: "1000",
      street: "ул. Оборище 5",
      building: "А",
      apartment: "12",
      phone: "+359888654321",
    },
    notes: "Gift wrapping please",
    items: [
      { product_id: "citrus-garden-200ml", product_name: "Citrus Garden", price_cents: 2800, quantity: 2 },
    ],
    tracking_number: null,
    tracking_carrier: null,
    tracking_url: null,
    created_at: new Date(Date.now() - 86400000).toISOString(),
    updated_at: new Date(Date.now() - 43200000).toISOString(),
  },
  {
    id: "c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f",
    status: "shipped",
    payment_method: "card",
    payment_status: "paid",
    stripe_checkout_url: null,
    items_total_cents: 3200,
    shipping_cents: 0,
    total_cents: 3200,
    customer_email: "carol@example.com",
    customer_name: "Carol Davis",
    delivery_method: "office",
    delivery_courier: "econt",
    delivery_details: {
      courier: "econt",
      office_id: "econt-plovdiv-001",
      office_name: "Econt Пловдив Централ",
      office_type: "office",
      phone: "+359877111222",
    },
    notes: null,
    items: [
      { product_id: "lavender-dreams-300ml", product_name: "Lavender Dreams", price_cents: 3200, quantity: 1 },
    ],
    tracking_number: "1234567890",
    tracking_carrier: "speedy",
    tracking_url: "https://www.speedy.bg/en/track-shipment?shipmentNumber=1234567890",
    created_at: new Date(Date.now() - 172800000).toISOString(),
    updated_at: new Date(Date.now() - 86400000).toISOString(),
  },
  {
    id: "d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f8a",
    status: "delivered",
    payment_method: "cod",
    payment_status: "paid",
    stripe_checkout_url: null,
    items_total_cents: 9000,
    shipping_cents: 0,
    total_cents: 9000,
    customer_email: "dave@example.com",
    customer_name: "Dave Wilson",
    delivery_method: "office",
    delivery_courier: "speedy",
    delivery_details: {
      courier: "speedy",
      office_id: "speedy-apt-sf-01",
      office_name: "Speedy Автомат Витоша Мол",
      office_type: "apt",
      phone: "+359899555000",
    },
    notes: null,
    items: [
      { product_id: "midnight-amber-300ml", product_name: "Midnight Amber", price_cents: 4500, quantity: 2 },
    ],
    tracking_number: "JD014600003922222222",
    tracking_carrier: "dhl",
    tracking_url: "https://www.dhl.com/en/express/tracking.html?AWB=JD014600003922222222",
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

/** Convert a mock product to an AdminProductResponse for mock admin endpoints. */
function toAdminProduct(product: MockProduct): AdminProductResponse {
  return {
    id: product.id,
    name_en: product.name,
    name_bg: null,
    description_en: product.description,
    description_bg: null,
    materials: product.materials,
    days_to_craft: product.days_to_craft,
    price_cents: product.price_cents,
    discount_percent: product.discount_percent,
    discount_starts_at: product.discount_starts_at,
    discount_ends_at: product.discount_ends_at,
    effective_price_cents: product.effective_price_cents,
    discount_active: product.discount_active,
    category: product.category,
    product_type: product.product_type,
    labels: product.labels.map((l) => l.slug),
    images: product.images,
    video: product.video,
    primary_image_url: product.primary_image_url,
    primary_thumbnail_url: product.primary_thumbnail_url,
    stock: product.stock,
    weight_grams: product.weight_grams,
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

function mockTermName(kind: TaxonomyKind, slug: string | null): string | null {
  if (!slug) return null;
  const term = MOCK_TAXONOMY[kind].find((t) => t.slug === slug);
  return term ? term.name_en : slug;
}

function mockLabelRefs(slugs: string[] | undefined): { slug: string; name: string }[] {
  return (slugs ?? []).map((slug) => ({
    slug,
    name: mockTermName("labels", slug) ?? slug,
  }));
}

export async function createProduct(data: CreateProductRequest): Promise<AdminProductResponse> {
  await delay();
  const existing = MOCK_PRODUCTS.find((p) => p.id === data.id);
  if (existing) mockError("CONFLICT", `Product ${data.id} already exists`);
  const now = new Date().toISOString();
  const product: MockProduct = {
    id: data.id,
    name: data.name_en,
    description: data.description_en ?? null,
    materials: data.materials ?? null,
    days_to_craft: data.days_to_craft ?? null,
    price_cents: data.price_cents,
    effective_price_cents: data.price_cents,
    discount_percent: data.discount_percent ?? null,
    discount_active: false,
    discount_starts_at: data.discount_starts_at ?? null,
    discount_ends_at: data.discount_ends_at ?? null,
    category: data.category ?? null,
    category_name: mockTermName("categories", data.category ?? null),
    product_type: data.product_type ?? "candles",
    product_type_name:
      mockTermName("product-types", data.product_type ?? "candles") ??
      (data.product_type ?? "candles"),
    labels: mockLabelRefs(data.labels),
    images: [],
    video: null,
    primary_image_url: null,
    primary_thumbnail_url: null,
    stock: data.stock,
    weight_grams: data.weight_grams ?? 300,
    is_active: data.is_active ?? true,
    is_featured: data.is_featured ?? false,
    created_at: now,
    updated_at: now,
  };
  applyMockPricing(product);
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
  if (data.category !== undefined) {
    product.category = data.category;
    product.category_name = mockTermName("categories", data.category);
  }
  if (data.product_type !== undefined) {
    product.product_type = data.product_type;
    product.product_type_name = mockTermName("product-types", data.product_type) ?? data.product_type;
  }
  if (data.labels !== undefined) product.labels = mockLabelRefs(data.labels);
  if (data.stock !== undefined) product.stock = data.stock;
  if (data.weight_grams !== undefined) product.weight_grams = data.weight_grams;
  if (data.is_active !== undefined) product.is_active = data.is_active;
  if (data.is_featured !== undefined) product.is_featured = data.is_featured;
  // Discount merge: percent = null clears all bounds together.
  if (data.discount_percent === null) {
    product.discount_percent = null;
    product.discount_starts_at = null;
    product.discount_ends_at = null;
  } else {
    if (data.discount_percent !== undefined) product.discount_percent = data.discount_percent;
    if (data.discount_starts_at !== undefined)
      product.discount_starts_at = data.discount_starts_at;
    if (data.discount_ends_at !== undefined) product.discount_ends_at = data.discount_ends_at;
  }
  applyMockPricing(product);
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
  if (product.images.length >= 6) {
    mockError("max_product_images", "Product already has the maximum number of images");
  }
  const imageId = `${productId}-${Date.now()}`;
  const imageUrl = `/static/products/${productId}_${imageId}.webp`;
  const image: ProductImage = {
    id: imageId,
    image_url: imageUrl,
    thumbnail_url: `/static/products/${productId}_${imageId}_thumb.webp`,
    sort_order: product.images.length,
    is_primary: product.images.length === 0,
  };
  product.images.push(image);
  product.primary_image_url = primaryImageUrl(product.images);
  product.primary_thumbnail_url = primaryThumbnailUrl(product.images);
  product.updated_at = new Date().toISOString();
  return image;
}

export async function deleteProductImage(productId: string, imageId: string): Promise<void> {
  await delay();
  const product = MOCK_PRODUCTS.find((p) => p.id === productId);
  if (!product) mockError("product_not_found", `Product ${productId} not found`);
  const image = product.images.find((item) => item.id === imageId);
  if (!image) mockError("image_not_found", `Image ${imageId} not found`);
  product.images = product.images.filter((item) => item.id !== imageId);
  if (image.is_primary && product.images.length > 0) {
    product.images = product.images.map((item, index) => ({ ...item, is_primary: index === 0 }));
  }
  product.images = product.images.map((item, index) => ({ ...item, sort_order: index }));
  product.primary_image_url = primaryImageUrl(product.images);
  product.primary_thumbnail_url = primaryThumbnailUrl(product.images);
}

export async function reorderProductImages(
  productId: string,
  orderedIds: string[]
): Promise<ProductImage[]> {
  await delay();
  const product = MOCK_PRODUCTS.find((p) => p.id === productId);
  if (!product) mockError("product_not_found", `Product ${productId} not found`);
  if (new Set(orderedIds).size !== product.images.length) {
    mockError("invalid_image_order", "ordered_ids must match all images for the product");
  }
  product.images = orderedIds.map((id, index) => {
    const image = product.images.find((item) => item.id === id);
    if (!image) mockError("invalid_image_order", "ordered_ids must match all images for the product");
    return { ...image, sort_order: index };
  });
  return product.images;
}

export async function setPrimaryProductImage(
  productId: string,
  imageId: string
): Promise<ProductImage> {
  await delay();
  const product = MOCK_PRODUCTS.find((p) => p.id === productId);
  if (!product) mockError("product_not_found", `Product ${productId} not found`);
  let primary: ProductImage | undefined;
  product.images = product.images.map((image) => {
    const next = { ...image, is_primary: image.id === imageId };
    if (next.is_primary) primary = next;
    return next;
  });
  if (!primary) mockError("image_not_found", `Image ${imageId} not found`);
  product.primary_image_url = primaryImageUrl(product.images);
  product.primary_thumbnail_url = primaryThumbnailUrl(product.images);
  return primary;
}

export async function uploadProductVideo(
  productId: string,
  file: File
): Promise<VideoUploadResponse> {
  await delay();
  const product = MOCK_PRODUCTS.find((p) => p.id === productId);
  if (!product) mockError("product_not_found", `Product ${productId} not found`);
  if (!file.type.startsWith("video/")) {
    mockError("invalid_video", "Upload a valid video file");
  }
  const now = new Date().toISOString();
  const video: ProductVideo = {
    id: `${productId}-${Date.now()}`,
    product_id: productId,
    status: "queued",
    video_url: null,
    poster_url: product.primary_thumbnail_url,
    sort_order: product.video?.sort_order ?? Math.min(1, product.images.length),
    duration_secs: null,
    failure_reason: null,
    created_at: now,
    updated_at: now,
  };
  product.video = video;
  return video;
}

export async function getProductVideo(productId: string): Promise<ProductVideo> {
  await delay();
  const product = MOCK_PRODUCTS.find((p) => p.id === productId);
  if (!product) mockError("product_not_found", `Product ${productId} not found`);
  if (!product.video) mockError("video_not_found", "Product video not found");
  return product.video;
}

export async function deleteProductVideo(productId: string): Promise<void> {
  await delay();
  const product = MOCK_PRODUCTS.find((p) => p.id === productId);
  if (!product) mockError("product_not_found", `Product ${productId} not found`);
  if (!product.video) mockError("video_not_found", "Product video not found");
  product.video = null;
}

export async function updateProductVideoSortOrder(
  productId: string,
  sortOrder: number
): Promise<ProductVideo> {
  await delay();
  const product = MOCK_PRODUCTS.find((p) => p.id === productId);
  if (!product) mockError("product_not_found", `Product ${productId} not found`);
  if (!product.video) mockError("video_not_found", "Product video not found");
  product.video = { ...product.video, sort_order: sortOrder, updated_at: new Date().toISOString() };
  return product.video;
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
    items: slice,
    total: filtered.length,
    page,
    limit,
  };
}

export async function getAdminOrder(orderId: string): Promise<OrderResponse> {
  await delay();
  const allOrders = [...MOCK_ORDERS_SEEDED, ...mockOrders];
  const order = allOrders.find((o) => o.id === orderId);
  if (!order) mockError("NOT_FOUND", `Order ${orderId} not found`);
  return order;
}

export async function updateOrderStatus(
  orderId: string,
  status: OrderStatus,
  tracking?: {
    tracking_number?: string;
    tracking_carrier?: string;
    tracking_url?: string;
  }
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

  if (status === "shipped") {
    if (!tracking?.tracking_number || !tracking?.tracking_carrier) {
      mockError(
        "TRACKING_REQUIRED",
        "tracking_number and tracking_carrier are required when shipping"
      );
    }
    order.tracking_number = tracking.tracking_number;
    order.tracking_carrier = tracking.tracking_carrier;
    order.tracking_url =
      tracking.tracking_url ??
      buildTrackingUrl(tracking.tracking_carrier, tracking.tracking_number);
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

// --- Taxonomy Mock ---

function localizedName(term: MockTerm, locale?: string): string {
  return locale === "bg" ? term.name_bg ?? term.name_en : term.name_en;
}

export async function getTaxonomy(locale?: string): Promise<TaxonomyResponse> {
  await delay();
  const active = (kind: TaxonomyKind) =>
    MOCK_TAXONOMY[kind]
      .filter((t) => t.is_active)
      .sort((a, b) => a.sort_order - b.sort_order)
      .map((t) => ({ slug: t.slug, name: localizedName(t, locale), sort_order: t.sort_order }));
  return {
    product_types: active("product-types"),
    categories: active("categories"),
    labels: active("labels"),
  };
}

function termProductCount(kind: TaxonomyKind, slug: string): number {
  if (kind === "product-types") {
    return MOCK_PRODUCTS.filter((p) => p.product_type === slug).length;
  }
  if (kind === "categories") {
    return MOCK_PRODUCTS.filter((p) => p.category === slug).length;
  }
  return MOCK_PRODUCTS.filter((p) => p.labels.some((l) => l.slug === slug)).length;
}

function toAdminTerm(kind: TaxonomyKind, term: MockTerm): AdminTaxonomyTerm {
  return {
    slug: term.slug,
    name_en: term.name_en,
    name_bg: term.name_bg,
    sort_order: term.sort_order,
    is_active: term.is_active,
    product_count: termProductCount(kind, term.slug),
    created_at: term.created_at,
    updated_at: term.updated_at,
  };
}

export async function getAdminTaxonomy(kind: TaxonomyKind): Promise<AdminTaxonomyTerm[]> {
  await delay();
  return [...MOCK_TAXONOMY[kind]]
    .sort((a, b) => a.sort_order - b.sort_order)
    .map((t) => toAdminTerm(kind, t));
}

function mockSlugify(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "item";
}

export async function createTaxonomyTerm(
  kind: TaxonomyKind,
  data: CreateTaxonomyTermRequest
): Promise<AdminTaxonomyTerm> {
  await delay();
  const existing = new Set(MOCK_TAXONOMY[kind].map((t) => t.slug));
  let slug = mockSlugify(data.name_en);
  let n = 2;
  while (existing.has(slug)) slug = `${mockSlugify(data.name_en)}-${n++}`;
  const now = new Date().toISOString();
  const term: MockTerm = {
    slug,
    name_en: data.name_en,
    name_bg: data.name_bg ?? null,
    sort_order: data.sort_order ?? 0,
    is_active: true,
    created_at: now,
    updated_at: now,
  };
  MOCK_TAXONOMY[kind].push(term);
  return toAdminTerm(kind, term);
}

export async function updateTaxonomyTerm(
  kind: TaxonomyKind,
  slug: string,
  data: UpdateTaxonomyTermRequest
): Promise<AdminTaxonomyTerm> {
  await delay();
  const term = MOCK_TAXONOMY[kind].find((t) => t.slug === slug);
  if (!term) mockError("NOT_FOUND", `${kind} ${slug} not found`);
  if (data.name_en !== undefined) term.name_en = data.name_en;
  if (data.name_bg !== undefined) term.name_bg = data.name_bg;
  if (data.sort_order !== undefined) term.sort_order = data.sort_order;
  if (data.is_active !== undefined) term.is_active = data.is_active;
  term.updated_at = new Date().toISOString();
  return toAdminTerm(kind, term);
}

export async function deleteTaxonomyTerm(kind: TaxonomyKind, slug: string): Promise<void> {
  await delay();
  const term = MOCK_TAXONOMY[kind].find((t) => t.slug === slug);
  if (!term) mockError("NOT_FOUND", `${kind} ${slug} not found`);
  if (termProductCount(kind, slug) > 0) {
    mockError("TAXONOMY_IN_USE", `${kind} '${slug}' is in use; reassign or deactivate it first`);
  }
  MOCK_TAXONOMY[kind] = MOCK_TAXONOMY[kind].filter((t) => t.slug !== slug);
}

// --- Promotions (campaigns, bulk discount, managed banner) ---

interface AppliedTarget {
  id: string;
  percent: number | null;
  starts_at: string | null;
  ends_at: string | null;
}

const mockCampaigns: CampaignResponse[] = [];
const mockAppliedTargets: Map<string, AppliedTarget[]> = new Map();

let mockBanner: BannerAdminResponse = {
  message_en: "Free shipping on orders over €50 ✨",
  message_bg: "Безплатна доставка за поръчки над 50€ ✨",
  link_label_en: null,
  link_label_bg: null,
  link_url: null,
  is_enabled: true,
  starts_at: null,
  ends_at: null,
  version: 1,
  updated_at: new Date().toISOString(),
};

function deriveCampaignStatus(c: CampaignResponse): CampaignResponse["status"] {
  if (c.removed_at) return "removed";
  if (!c.applied_at) return "draft";
  const now = new Date().toISOString();
  if (c.discount_starts_at && now < c.discount_starts_at) return "scheduled";
  if (c.discount_ends_at && now > c.discount_ends_at) return "ended";
  return "active";
}

function resolveMockTargets(
  productIds: string[] | null | undefined,
  filter: BulkDiscountRequest["filter"]
): string[] {
  if (productIds) return Array.from(new Set(productIds));
  if (!filter) return [];
  return MOCK_PRODUCTS.filter((p) => {
    if (filter.q) {
      const q = filter.q.toLowerCase();
      if (!p.name.toLowerCase().includes(q) && !p.id.toLowerCase().includes(q)) return false;
    }
    if (filter.category && p.category !== filter.category) return false;
    if (filter.is_active != null && p.is_active !== filter.is_active) return false;
    if (filter.in_stock && p.stock <= 0) return false;
    return true;
  }).map((p) => p.id);
}

function runMockBulk(
  operation: "apply" | "remove",
  ids: string[],
  percent: number | null,
  startsAt: string | null,
  endsAt: string | null
): BulkDiscountResponse {
  const results: BulkResultItem[] = [];
  let success = 0;
  for (const id of ids) {
    const product = MOCK_PRODUCTS.find((p) => p.id === id);
    if (!product) {
      results.push({ id, status: "failed", error: `Product not found: ${id}` });
      continue;
    }
    if (operation === "apply") {
      product.discount_percent = percent;
      product.discount_starts_at = startsAt;
      product.discount_ends_at = endsAt;
    } else {
      product.discount_percent = null;
      product.discount_starts_at = null;
      product.discount_ends_at = null;
    }
    results.push({ id, status: "updated" });
    success += 1;
  }
  return { success_count: success, failure_count: results.length - success, results };
}

export async function getCampaigns(): Promise<CampaignListResponse> {
  await delay();
  const items = mockCampaigns.map((c) => ({ ...c, status: deriveCampaignStatus(c) }));
  return { items, total: items.length };
}

export async function getCampaign(campaignId: string): Promise<CampaignResponse> {
  await delay();
  const c = mockCampaigns.find((x) => x.id === campaignId);
  if (!c) mockError("NOT_FOUND", "Campaign not found");
  return { ...c, status: deriveCampaignStatus(c) };
}

export async function createCampaign(
  data: CampaignCreateRequest
): Promise<CampaignResponse> {
  await delay();
  const now = new Date().toISOString();
  const targetType = data.product_ids ? "ids" : "filter";
  const targetCount = data.product_ids
    ? Array.from(new Set(data.product_ids)).length
    : resolveMockTargets(null, data.filter).length;
  const campaign: CampaignResponse = {
    id: `campaign-${Math.round(Math.random() * 1e9)}`,
    name: data.name,
    note: data.note ?? null,
    discount_percent: data.discount_percent,
    discount_starts_at: data.discount_starts_at ?? null,
    discount_ends_at: data.discount_ends_at ?? null,
    target_type: targetType,
    target_count: targetCount,
    target_ids: data.product_ids ? Array.from(new Set(data.product_ids)) : null,
    target_filter: data.product_ids ? null : (data.filter ?? {}),
    status: "draft",
    applied_at: null,
    removed_at: null,
    created_at: now,
    updated_at: now,
    last_result: null,
  };
  // Store the raw target for later apply resolution.
  mockAppliedTargets.set(`${campaign.id}:targets`, [
    ...(data.product_ids ?? resolveMockTargets(null, data.filter)).map((id) => ({
      id,
      percent: null,
      starts_at: null,
      ends_at: null,
    })),
  ]);
  mockCampaigns.unshift(campaign);
  return campaign;
}

export async function updateCampaign(
  campaignId: string,
  data: CampaignUpdateRequest
): Promise<CampaignResponse> {
  await delay();
  const c = mockCampaigns.find((x) => x.id === campaignId);
  if (!c) mockError("NOT_FOUND", "Campaign not found");
  if (data.name != null) c.name = data.name;
  if (data.note !== undefined) c.note = data.note;
  if (data.discount_percent != null) c.discount_percent = data.discount_percent;
  if (data.discount_starts_at !== undefined) c.discount_starts_at = data.discount_starts_at;
  if (data.discount_ends_at !== undefined) c.discount_ends_at = data.discount_ends_at;
  if (data.product_ids) {
    c.target_type = "ids";
    c.target_count = Array.from(new Set(data.product_ids)).length;
    c.target_ids = Array.from(new Set(data.product_ids));
    c.target_filter = null;
    mockAppliedTargets.set(
      `${c.id}:targets`,
      data.product_ids.map((id) => ({ id, percent: null, starts_at: null, ends_at: null }))
    );
  } else if (data.filter) {
    c.target_type = "filter";
    const ids = resolveMockTargets(null, data.filter);
    c.target_count = ids.length;
    c.target_ids = null;
    c.target_filter = data.filter;
    mockAppliedTargets.set(
      `${c.id}:targets`,
      ids.map((id) => ({ id, percent: null, starts_at: null, ends_at: null }))
    );
  }
  c.updated_at = new Date().toISOString();
  return { ...c, status: deriveCampaignStatus(c) };
}

export async function deleteCampaign(campaignId: string): Promise<void> {
  await delay();
  const idx = mockCampaigns.findIndex((x) => x.id === campaignId);
  if (idx === -1) mockError("NOT_FOUND", "Campaign not found");
  mockCampaigns.splice(idx, 1);
  mockAppliedTargets.delete(`${campaignId}:targets`);
  mockAppliedTargets.delete(campaignId);
}

export async function applyCampaign(campaignId: string): Promise<BulkDiscountResponse> {
  await delay();
  const c = mockCampaigns.find((x) => x.id === campaignId);
  if (!c) mockError("NOT_FOUND", "Campaign not found");
  const targets = mockAppliedTargets.get(`${c.id}:targets`) ?? [];
  const ids = targets.map((t) => t.id);
  const result = runMockBulk(
    "apply",
    ids,
    c.discount_percent,
    c.discount_starts_at,
    c.discount_ends_at
  );
  const updatedIds = result.results.filter((r) => r.status === "updated").map((r) => r.id);
  mockAppliedTargets.set(
    campaignId,
    updatedIds.map((id) => ({
      id,
      percent: c.discount_percent,
      starts_at: c.discount_starts_at,
      ends_at: c.discount_ends_at,
    }))
  );
  c.applied_at = new Date().toISOString();
  c.removed_at = null;
  c.last_result = result;
  return result;
}

export async function removeCampaign(campaignId: string): Promise<BulkDiscountResponse> {
  await delay();
  const c = mockCampaigns.find((x) => x.id === campaignId);
  if (!c) mockError("NOT_FOUND", "Campaign not found");
  const applied = mockAppliedTargets.get(campaignId) ?? [];
  const results: BulkResultItem[] = [];
  let success = 0;
  for (const t of applied) {
    const product = MOCK_PRODUCTS.find((p) => p.id === t.id);
    if (!product) {
      results.push({ id: t.id, status: "failed", error: "Product not found" });
      continue;
    }
    const matches =
      product.discount_percent === t.percent &&
      product.discount_starts_at === t.starts_at &&
      product.discount_ends_at === t.ends_at;
    if (!matches) {
      results.push({
        id: t.id,
        status: "skipped",
        error: "discount changed after campaign apply; left unchanged",
      });
      continue;
    }
    product.discount_percent = null;
    product.discount_starts_at = null;
    product.discount_ends_at = null;
    results.push({ id: t.id, status: "updated" });
    success += 1;
  }
  const result: BulkDiscountResponse = {
    success_count: success,
    failure_count: results.length - success,
    results,
  };
  c.removed_at = new Date().toISOString();
  c.last_result = result;
  return result;
}

export async function bulkDiscount(
  data: BulkDiscountRequest
): Promise<BulkDiscountResponse> {
  await delay();
  const ids = resolveMockTargets(data.product_ids, data.filter);
  if (ids.length === 0) mockError("VALIDATION_ERROR", "target resolves to no products");
  if (ids.length > 500) {
    mockError("BULK_TARGET_LIMIT_EXCEEDED", `target resolves to ${ids.length} products; limit is 500`);
  }
  return runMockBulk(
    data.operation,
    ids,
    data.discount_percent ?? null,
    data.discount_starts_at ?? null,
    data.discount_ends_at ?? null
  );
}

export async function getAdminBanner(): Promise<BannerAdminResponse> {
  await delay();
  return { ...mockBanner };
}

export async function updateBanner(
  data: BannerUpdateRequest
): Promise<BannerAdminResponse> {
  await delay();
  const changed =
    mockBanner.message_en !== (data.message_en ?? null) ||
    mockBanner.message_bg !== (data.message_bg ?? null) ||
    mockBanner.link_label_en !== (data.link_label_en ?? null) ||
    mockBanner.link_label_bg !== (data.link_label_bg ?? null) ||
    mockBanner.link_url !== (data.link_url ?? null) ||
    mockBanner.is_enabled !== data.is_enabled ||
    mockBanner.starts_at !== (data.starts_at ?? null) ||
    mockBanner.ends_at !== (data.ends_at ?? null);
  mockBanner = {
    message_en: data.message_en ?? null,
    message_bg: data.message_bg ?? null,
    link_label_en: data.link_label_en ?? null,
    link_label_bg: data.link_label_bg ?? null,
    link_url: data.link_url ?? null,
    is_enabled: data.is_enabled,
    starts_at: data.starts_at ?? null,
    ends_at: data.ends_at ?? null,
    version: changed ? mockBanner.version + 1 : mockBanner.version,
    updated_at: new Date().toISOString(),
  };
  return { ...mockBanner };
}

export async function getPublicBanner(
  locale: string = "en"
): Promise<PublicBannerResponse> {
  await delay();
  if (!mockBanner.is_enabled) return { banner: null };
  const now = new Date().toISOString();
  if (mockBanner.starts_at && now < mockBanner.starts_at) return { banner: null };
  if (mockBanner.ends_at && now > mockBanner.ends_at) return { banner: null };
  const message =
    locale === "bg" && mockBanner.message_bg ? mockBanner.message_bg : mockBanner.message_en;
  if (!message) return { banner: null };
  const linkLabel =
    locale === "bg" && mockBanner.link_label_bg
      ? mockBanner.link_label_bg
      : mockBanner.link_label_en;
  return {
    banner: {
      message,
      link_label: linkLabel,
      link_url: mockBanner.link_url,
      dismiss_key: `default:v${mockBanner.version}`,
    },
  };
}
