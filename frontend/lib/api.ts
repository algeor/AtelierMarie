/**
 * API facade — delegates to mock-api or api-client based on env flag.
 * Import from here in components, never from mock-api or api-client directly.
 */

import * as mockApi from "./mock-api";
import * as apiClient from "./api-client";
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

const USE_MOCK =
  process.env.NEXT_PUBLIC_USE_MOCK_API === "true";

export async function getProducts(
  page = 1,
  limit = 20
): Promise<ProductListResponse> {
  if (USE_MOCK) return mockApi.getProducts(page, limit);
  const params = new URLSearchParams({ page: String(page), limit: String(limit) });
  return apiClient.get<ProductListResponse>(`/v1/products?${params}`);
}

export async function getProduct(
  productId: string
): Promise<ProductResponse> {
  if (USE_MOCK) return mockApi.getProduct(productId);
  return apiClient.get<ProductResponse>(
    `/v1/products/${encodeURIComponent(productId)}`
  );
}

export async function getCart(): Promise<CartResponse> {
  if (USE_MOCK) return mockApi.getCart();
  return apiClient.get<CartResponse>("/v1/cart");
}

export async function addToCart(
  productId: string,
  quantity = 1
): Promise<CartResponse> {
  if (USE_MOCK) return mockApi.addToCart(productId, quantity);
  return apiClient.post<CartResponse>("/v1/cart", {
    product_id: productId,
    quantity,
  });
}

export async function updateCartItem(
  productId: string,
  quantity: number
): Promise<CartResponse> {
  if (USE_MOCK) return mockApi.updateCartItem(productId, quantity);
  return apiClient.patch<CartResponse>(
    `/v1/cart/${encodeURIComponent(productId)}`,
    { quantity }
  );
}

export async function removeFromCart(
  productId: string
): Promise<CartResponse> {
  if (USE_MOCK) return mockApi.removeFromCart(productId);
  return apiClient.del<CartResponse>(
    `/v1/cart/${encodeURIComponent(productId)}`
  );
}

export async function createOrder(
  data: CreateOrderRequest
): Promise<OrderResponse> {
  if (USE_MOCK) return mockApi.createOrder(data);
  return apiClient.post<OrderResponse>("/v1/orders", data);
}

export async function getOrders(
  page = 1,
  limit = 20
): Promise<OrderListResponse> {
  if (USE_MOCK) return mockApi.getOrders(page, limit);
  const params = new URLSearchParams({ page: String(page), limit: String(limit) });
  return apiClient.get<OrderListResponse>(`/v1/orders?${params}`);
}

export async function getOrder(
  orderId: string
): Promise<OrderResponse> {
  if (USE_MOCK) return mockApi.getOrder(orderId);
  return apiClient.get<OrderResponse>(
    `/v1/orders/${encodeURIComponent(orderId)}`
  );
}

export async function getCurrentUser(): Promise<UserResponse | null> {
  if (USE_MOCK) return mockApi.getCurrentUser();
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
  if (USE_MOCK) return mockApi.login(code, redirectUri);
  return apiClient.post<AuthTokenResponse>("/v1/auth/google", {
    code,
    redirect_uri: redirectUri,
  });
}
