/**
 * API facade — delegates to mock-api or api-client based on env flag.
 * Import from here in components, never from mock-api or api-client directly.
 */

import * as apiClient from "./api-client";
import type {
  AdminStats,
  AuthTokenResponse,
  CartResponse,
  CreateOrderRequest,
  CreateProductRequest,
  OrderListResponse,
  OrderResponse,
  OrderStatus,
  ProductListResponse,
  ProductResponse,
  UpdateProductRequest,
  UserResponse,
} from "./types";

const USE_MOCK =
  process.env.NEXT_PUBLIC_USE_MOCK_API === "true";

/** Lazy-load mock API only when needed (keeps it out of production bundles). */
function getMock() {
  return import("./mock-api");
}

export async function getProducts(
  page = 1,
  limit = 20
): Promise<ProductListResponse> {
  if (USE_MOCK) return (await getMock()).getProducts(page, limit);
  const params = new URLSearchParams({ page: String(page), limit: String(limit) });
  return apiClient.get<ProductListResponse>(`/v1/products?${params}`);
}

export async function getProduct(
  productId: string
): Promise<ProductResponse> {
  if (USE_MOCK) return (await getMock()).getProduct(productId);
  return apiClient.get<ProductResponse>(
    `/v1/products/${encodeURIComponent(productId)}`
  );
}

export async function getCart(): Promise<CartResponse> {
  if (USE_MOCK) return (await getMock()).getCart();
  return apiClient.get<CartResponse>("/v1/cart");
}

export async function addToCart(
  productId: string,
  quantity = 1
): Promise<CartResponse> {
  if (USE_MOCK) return (await getMock()).addToCart(productId, quantity);
  return apiClient.post<CartResponse>("/v1/cart", {
    product_id: productId,
    quantity,
  });
}

export async function updateCartItem(
  productId: string,
  quantity: number
): Promise<CartResponse> {
  if (USE_MOCK) return (await getMock()).updateCartItem(productId, quantity);
  return apiClient.patch<CartResponse>(
    `/v1/cart/${encodeURIComponent(productId)}`,
    { quantity }
  );
}

export async function removeFromCart(
  productId: string
): Promise<CartResponse> {
  if (USE_MOCK) return (await getMock()).removeFromCart(productId);
  return apiClient.del<CartResponse>(
    `/v1/cart/${encodeURIComponent(productId)}`
  );
}

export async function createOrder(
  data: CreateOrderRequest
): Promise<OrderResponse> {
  if (USE_MOCK) return (await getMock()).createOrder(data);
  return apiClient.post<OrderResponse>("/v1/orders", data);
}

export async function getOrders(
  page = 1,
  limit = 20
): Promise<OrderListResponse> {
  if (USE_MOCK) return (await getMock()).getOrders(page, limit);
  const params = new URLSearchParams({ page: String(page), limit: String(limit) });
  return apiClient.get<OrderListResponse>(`/v1/orders?${params}`);
}

export async function getOrder(
  orderId: string
): Promise<OrderResponse> {
  if (USE_MOCK) return (await getMock()).getOrder(orderId);
  return apiClient.get<OrderResponse>(
    `/v1/orders/${encodeURIComponent(orderId)}`
  );
}

export async function getCurrentUser(): Promise<UserResponse | null> {
  if (USE_MOCK) return (await getMock()).getCurrentUser();
  try {
    return await apiClient.get<UserResponse>("/v1/auth/me");
  } catch (error) {
    // Only treat auth failures as "not logged in" — re-throw network errors
    if (
      error instanceof apiClient.ApiError &&
      (error.code === "UNAUTHORIZED" || error.code === "FORBIDDEN")
    ) {
      return null;
    }
    throw error;
  }
}

export async function login(
  code: string,
  redirectUri: string
): Promise<AuthTokenResponse> {
  if (USE_MOCK) return (await getMock()).login(code, redirectUri);
  return apiClient.post<AuthTokenResponse>("/v1/auth/google", {
    code,
    redirect_uri: redirectUri,
  });
}

// --- Admin ---

export async function getAdminStats(): Promise<AdminStats> {
  if (USE_MOCK) return (await getMock()).getAdminStats();
  return apiClient.get<AdminStats>("/v1/admin/stats");
}

export async function getAdminProducts(
  page = 1,
  limit = 20
): Promise<ProductListResponse> {
  if (USE_MOCK) return (await getMock()).getAdminProducts(page, limit);
  const params = new URLSearchParams({ page: String(page), limit: String(limit) });
  return apiClient.get<ProductListResponse>(`/v1/admin/products?${params}`);
}

export async function getAdminProduct(productId: string): Promise<ProductResponse> {
  if (USE_MOCK) return (await getMock()).getAdminProduct(productId);
  return apiClient.get<ProductResponse>(`/v1/admin/products/${encodeURIComponent(productId)}`);
}

export async function createProduct(data: CreateProductRequest): Promise<ProductResponse> {
  if (USE_MOCK) return (await getMock()).createProduct(data);
  return apiClient.post<ProductResponse>("/v1/admin/products", data);
}

export async function updateProduct(
  productId: string,
  data: UpdateProductRequest
): Promise<ProductResponse> {
  if (USE_MOCK) return (await getMock()).updateProduct(productId, data);
  return apiClient.patch<ProductResponse>(
    `/v1/admin/products/${encodeURIComponent(productId)}`,
    data
  );
}

export async function getAdminOrders(
  page = 1,
  limit = 20,
  status?: string
): Promise<OrderListResponse> {
  if (USE_MOCK) return (await getMock()).getAdminOrders(page, limit, status);
  const params = new URLSearchParams({ page: String(page), limit: String(limit) });
  if (status) params.set("status", status);
  return apiClient.get<OrderListResponse>(`/v1/admin/orders?${params}`);
}

export async function updateOrderStatus(
  orderId: string,
  status: OrderStatus
): Promise<OrderResponse> {
  if (USE_MOCK) return (await getMock()).updateOrderStatus(orderId, status);
  return apiClient.patch<OrderResponse>(
    `/v1/admin/orders/${encodeURIComponent(orderId)}/status`,
    { status }
  );
}
