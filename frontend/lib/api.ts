/**
 * API facade — delegates to mock-api or api-client based on env flag.
 * Import from here in components, never from mock-api or api-client directly.
 */

import * as apiClient from "./api-client";
import type { Locale } from "@/i18n/routing";
import type {
  AdminProductListResponse,
  AdminProductResponse,
  AdminStats,
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

const USE_MOCK =
  process.env.NEXT_PUBLIC_USE_MOCK_API === "true";

/** Lazy-load mock API only when needed (keeps it out of production bundles). */
function getMock() {
  return import("./mock-api");
}

export async function getProducts(
  page = 1,
  limit = 20,
  locale?: Locale
): Promise<ProductListResponse> {
  if (USE_MOCK) return (await getMock()).getProducts(page, limit, locale);
  const params = new URLSearchParams({ page: String(page), limit: String(limit) });
  if (locale) params.set("locale", locale);
  return apiClient.get<ProductListResponse>(`/v1/products?${params}`);
}

export async function getProduct(
  productId: string,
  locale?: Locale
): Promise<ProductResponse> {
  if (USE_MOCK) return (await getMock()).getProduct(productId, locale);
  const params = new URLSearchParams();
  if (locale) params.set("locale", locale);
  const query = params.size > 0 ? `?${params}` : "";
  return apiClient.get<ProductResponse>(
    `/v1/products/${encodeURIComponent(productId)}${query}`
  );
}

export async function updateLocalePreference(locale: Locale): Promise<{ locale: Locale }> {
  if (USE_MOCK) return { locale };
  return apiClient.patch<{ locale: Locale }>("/v1/locale", { locale });
}

function localeQuery(locale?: Locale): string {
  return locale ? `?locale=${encodeURIComponent(locale)}` : "";
}

export async function getCart(locale?: Locale): Promise<CartResponse> {
  if (USE_MOCK) return (await getMock()).getCart();
  return apiClient.get<CartResponse>(`/v1/cart${localeQuery(locale)}`);
}

export async function addToCart(
  productId: string,
  quantity = 1,
  locale?: Locale
): Promise<CartResponse> {
  if (USE_MOCK) return (await getMock()).addToCart(productId, quantity);
  return apiClient.post<CartResponse>(`/v1/cart${localeQuery(locale)}`, {
    product_id: productId,
    quantity,
  });
}

export async function updateCartItem(
  productId: string,
  quantity: number,
  locale?: Locale
): Promise<CartResponse> {
  if (USE_MOCK) return (await getMock()).updateCartItem(productId, quantity);
  return apiClient.patch<CartResponse>(
    `/v1/cart/${encodeURIComponent(productId)}${localeQuery(locale)}`,
    { quantity }
  );
}

export async function removeFromCart(
  productId: string,
  locale?: Locale
): Promise<CartResponse> {
  if (USE_MOCK) return (await getMock()).removeFromCart(productId);
  return apiClient.del<CartResponse>(
    `/v1/cart/${encodeURIComponent(productId)}${localeQuery(locale)}`
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

export async function logout(): Promise<void> {
  if (USE_MOCK) {
    (await getMock()).mockLogout();
    return;
  }
  await apiClient.post<void>("/v1/auth/logout");
}

// --- Admin ---

export async function getAdminStats(): Promise<AdminStats> {
  if (USE_MOCK) return (await getMock()).getAdminStats();
  return apiClient.get<AdminStats>("/v1/admin/stats");
}

export async function getAdminProducts(
  page = 1,
  limit = 20
): Promise<AdminProductListResponse> {
  if (USE_MOCK) return (await getMock()).getAdminProducts(page, limit);
  const params = new URLSearchParams({ page: String(page), limit: String(limit) });
  return apiClient.get<AdminProductListResponse>(`/v1/admin/products?${params}`);
}

export async function getAdminProduct(productId: string): Promise<AdminProductResponse> {
  if (USE_MOCK) return (await getMock()).getAdminProduct(productId);
  return apiClient.get<AdminProductResponse>(`/v1/admin/products/${encodeURIComponent(productId)}`);
}

export async function createProduct(data: CreateProductRequest): Promise<AdminProductResponse> {
  if (USE_MOCK) return (await getMock()).createProduct(data);
  return apiClient.post<AdminProductResponse>("/v1/admin/products", data);
}

export async function updateProduct(
  productId: string,
  data: UpdateProductRequest
): Promise<AdminProductResponse> {
  if (USE_MOCK) return (await getMock()).updateProduct(productId, data);
  return apiClient.patch<AdminProductResponse>(
    `/v1/admin/products/${encodeURIComponent(productId)}`,
    data
  );
}

export async function uploadProductImage(
  productId: string,
  file: File
): Promise<ImageUploadResponse> {
  if (USE_MOCK) return (await getMock()).uploadProductImage(productId, file);
  const formData = new FormData();
  formData.append("file", file);
  return apiClient.postForm<ImageUploadResponse>(
    `/v1/admin/products/${encodeURIComponent(productId)}/image`,
    formData
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

// --- Reactions ---

export async function toggleReaction(
  productId: string,
  body: ReactionToggleRequest
): Promise<ReactionToggleResponse> {
  if (USE_MOCK) return (await getMock()).toggleReaction(productId, body);
  return apiClient.toggleReaction(productId, body);
}

export async function getReactions(
  productId: string
): Promise<ReactionCountsResponse> {
  if (USE_MOCK) return (await getMock()).getReactions(productId);
  return apiClient.getReactions(productId);
}

// --- Comments ---

export async function postComment(
  productId: string,
  body: CommentCreateRequest
): Promise<CommentResponse> {
  if (USE_MOCK) return (await getMock()).postComment(productId, body);
  return apiClient.postComment(productId, body);
}

export async function getComments(
  productId: string,
  sort: CommentSort = "newest",
  page: number = 1,
  limit: number = 20
): Promise<CommentListResponse> {
  if (USE_MOCK) return (await getMock()).getComments(productId, sort, page, limit);
  return apiClient.getComments(productId, sort, page, limit);
}
