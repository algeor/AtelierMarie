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
  AdminTaxonomyTerm,
  AboutAdminResponse,
  AnalyticsFunnelResponse,
  AnalyticsHealthResponse,
  AnalyticsSummaryResponse,
  AboutItemAdmin,
  AboutPublicResponse,
  AboutSectionAdmin,
  BannerAdminResponse,
  BannerUpdateRequest,
  BulkDiscountRequest,
  BulkDiscountResponse,
  CalculateShippingRequest,
  CalculateShippingResponse,
  CampaignCreateRequest,
  CampaignListResponse,
  CampaignResponse,
  CampaignUpdateRequest,
  PublicBannerResponse,
  CartResponse,
  CommentCreateRequest,
  CommentListResponse,
  CommentResponse,
  CommentSort,
  ContactRequest,
  ContactResponse,
  CheckoutAnalyticsResponse,
  Courier,
  DeliverySettingsResponse,
  DeliverySettingsUpdate,
  CreateOrderRequest,
  CreateAboutItemRequest,
  CreateProductRequest,
  CreateTaxonomyTermRequest,
  CreateFaqItemRequest,
  CityPlace,
  FaqAdminResponse,
  FaqItemAdminResponse,
  FaqResponse,
  FaqSectionAdminResponse,
  ImageUploadResponse,
  OfficeResponse,
  OfficeType,
  OrderListResponse,
  OrderResponse,
  OrderStatus,
  ProductListResponse,
  ProductAnalyticsResponse,
  ProductResponse,
  ReactionCountsResponse,
  ReactionToggleRequest,
  ReactionToggleResponse,
  ProductImage,
  PatchAboutItemRequest,
  PatchAboutSectionRequest,
  ProductVideo,
  TaxonomyKind,
  TaxonomyResponse,
  ReorderFaqItemsRequest,
  UpdateFaqItemRequest,
  UpdateFaqSectionRequest,
  UpdateProductRequest,
  UpdateTaxonomyTermRequest,
  UserResponse,
  VideoUploadResponse,
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

// --- Taxonomy ---

export async function getTaxonomy(locale?: Locale): Promise<TaxonomyResponse> {
  if (USE_MOCK) return (await getMock()).getTaxonomy(locale);
  const params = new URLSearchParams();
  if (locale) params.set("locale", locale);
  const query = params.size > 0 ? `?${params}` : "";
  return apiClient.get<TaxonomyResponse>(`/v1/taxonomy${query}`);
}

// --- Atelier Story / About ---

export async function getAbout(locale?: Locale): Promise<AboutPublicResponse> {
  if (USE_MOCK) return (await getMock()).getAbout(locale);
  const params = new URLSearchParams();
  if (locale) params.set("locale", locale);
  const query = params.size > 0 ? `?${params}` : "";
  return apiClient.get<AboutPublicResponse>(`/v1/about${query}`);
}

export async function getAdminAbout(): Promise<AboutAdminResponse> {
  if (USE_MOCK) return (await getMock()).getAdminAbout();
  return apiClient.get<AboutAdminResponse>("/v1/admin/about");
}

export async function updateAboutSection(
  slug: string,
  data: PatchAboutSectionRequest
): Promise<AboutSectionAdmin> {
  if (USE_MOCK) return (await getMock()).updateAboutSection(slug, data);
  return apiClient.patch<AboutSectionAdmin>(
    `/v1/admin/about/sections/${encodeURIComponent(slug)}`,
    data
  );
}

export async function createAboutItem(
  slug: string,
  data: CreateAboutItemRequest
): Promise<AboutItemAdmin> {
  if (USE_MOCK) return (await getMock()).createAboutItem(slug, data);
  return apiClient.post<AboutItemAdmin>(
    `/v1/admin/about/sections/${encodeURIComponent(slug)}/items`,
    data
  );
}

export async function updateAboutItem(
  slug: string,
  itemId: number,
  data: PatchAboutItemRequest
): Promise<AboutItemAdmin> {
  if (USE_MOCK) return (await getMock()).updateAboutItem(slug, itemId, data);
  return apiClient.patch<AboutItemAdmin>(
    `/v1/admin/about/sections/${encodeURIComponent(slug)}/items/${itemId}`,
    data
  );
}

export async function deleteAboutItem(slug: string, itemId: number): Promise<void> {
  if (USE_MOCK) return (await getMock()).deleteAboutItem(slug, itemId);
  return apiClient.del<void>(
    `/v1/admin/about/sections/${encodeURIComponent(slug)}/items/${itemId}`
  );
}

export async function reorderAboutSections(slugs: string[]): Promise<AboutSectionAdmin[]> {
  if (USE_MOCK) return (await getMock()).reorderAboutSections(slugs);
  return apiClient.post<AboutSectionAdmin[]>("/v1/admin/about/sections/reorder", { slugs });
}

export async function reorderAboutItems(
  slug: string,
  ids: number[]
): Promise<AboutItemAdmin[]> {
  if (USE_MOCK) return (await getMock()).reorderAboutItems(slug, ids);
  return apiClient.post<AboutItemAdmin[]>(
    `/v1/admin/about/sections/${encodeURIComponent(slug)}/items/reorder`,
    { ids }
  );
}

export async function setAboutSectionPublished(
  slug: string,
  isPublished: boolean
): Promise<AboutSectionAdmin> {
  if (USE_MOCK) return (await getMock()).setAboutSectionPublished(slug, isPublished);
  return apiClient.patch<AboutSectionAdmin>(
    `/v1/admin/about/sections/${encodeURIComponent(slug)}/publish`,
    { is_published: isPublished }
  );
}

export async function setAboutItemPublished(
  slug: string,
  itemId: number,
  isPublished: boolean
): Promise<AboutItemAdmin> {
  if (USE_MOCK) return (await getMock()).setAboutItemPublished(slug, itemId, isPublished);
  return apiClient.patch<AboutItemAdmin>(
    `/v1/admin/about/sections/${encodeURIComponent(slug)}/items/${itemId}/publish`,
    { is_published: isPublished }
  );
}

export async function uploadAboutSectionImage(
  slug: string,
  file: File
): Promise<AboutSectionAdmin> {
  if (USE_MOCK) return (await getMock()).uploadAboutSectionImage(slug, file);
  const formData = new FormData();
  formData.append("file", file);
  return apiClient.postForm<AboutSectionAdmin>(
    `/v1/admin/about/sections/${encodeURIComponent(slug)}/image`,
    formData
  );
}

export async function clearAboutSectionImage(slug: string): Promise<AboutSectionAdmin> {
  if (USE_MOCK) return (await getMock()).clearAboutSectionImage(slug);
  return apiClient.del<AboutSectionAdmin>(
    `/v1/admin/about/sections/${encodeURIComponent(slug)}/image`
  );
}

export async function uploadAboutItemImage(
  slug: string,
  itemId: number,
  file: File
): Promise<AboutItemAdmin> {
  if (USE_MOCK) return (await getMock()).uploadAboutItemImage(slug, itemId, file);
  const formData = new FormData();
  formData.append("file", file);
  return apiClient.postForm<AboutItemAdmin>(
    `/v1/admin/about/sections/${encodeURIComponent(slug)}/items/${itemId}/image`,
    formData
  );
}

export async function clearAboutItemImage(slug: string, itemId: number): Promise<AboutItemAdmin> {
  if (USE_MOCK) return (await getMock()).clearAboutItemImage(slug, itemId);
  return apiClient.del<AboutItemAdmin>(
    `/v1/admin/about/sections/${encodeURIComponent(slug)}/items/${itemId}/image`
  );
}

export async function getAdminTaxonomy(kind: TaxonomyKind): Promise<AdminTaxonomyTerm[]> {
  if (USE_MOCK) return (await getMock()).getAdminTaxonomy(kind);
  return apiClient.get<AdminTaxonomyTerm[]>(`/v1/admin/taxonomy/${kind}`);
}

export async function createTaxonomyTerm(
  kind: TaxonomyKind,
  data: CreateTaxonomyTermRequest
): Promise<AdminTaxonomyTerm> {
  if (USE_MOCK) return (await getMock()).createTaxonomyTerm(kind, data);
  return apiClient.post<AdminTaxonomyTerm>(`/v1/admin/taxonomy/${kind}`, data);
}

export async function updateTaxonomyTerm(
  kind: TaxonomyKind,
  slug: string,
  data: UpdateTaxonomyTermRequest
): Promise<AdminTaxonomyTerm> {
  if (USE_MOCK) return (await getMock()).updateTaxonomyTerm(kind, slug, data);
  return apiClient.patch<AdminTaxonomyTerm>(
    `/v1/admin/taxonomy/${kind}/${encodeURIComponent(slug)}`,
    data
  );
}

export async function deleteTaxonomyTerm(kind: TaxonomyKind, slug: string): Promise<void> {
  if (USE_MOCK) return (await getMock()).deleteTaxonomyTerm(kind, slug);
  return apiClient.del<void>(`/v1/admin/taxonomy/${kind}/${encodeURIComponent(slug)}`);
}

// --- FAQ ---

export async function getFaq(locale?: Locale): Promise<FaqResponse> {
  if (USE_MOCK) return (await getMock()).getFaq(locale);
  const params = new URLSearchParams();
  if (locale) params.set("locale", locale);
  const query = params.size > 0 ? `?${params}` : "";
  return apiClient.get<FaqResponse>(`/v1/faq${query}`);
}

export async function getAdminFaq(): Promise<FaqAdminResponse> {
  if (USE_MOCK) return (await getMock()).getAdminFaq();
  return apiClient.get<FaqAdminResponse>("/v1/admin/faq");
}

export async function createFaqItem(
  data: CreateFaqItemRequest
): Promise<FaqItemAdminResponse> {
  if (USE_MOCK) return (await getMock()).createFaqItem(data);
  return apiClient.post<FaqItemAdminResponse>("/v1/admin/faq", data);
}

export async function updateFaqItem(
  itemId: number,
  data: UpdateFaqItemRequest
): Promise<FaqItemAdminResponse> {
  if (USE_MOCK) return (await getMock()).updateFaqItem(itemId, data);
  return apiClient.patch<FaqItemAdminResponse>(
    `/v1/admin/faq/items/${encodeURIComponent(String(itemId))}`,
    data
  );
}

export async function deleteFaqItem(itemId: number): Promise<void> {
  if (USE_MOCK) return (await getMock()).deleteFaqItem(itemId);
  return apiClient.del<void>(`/v1/admin/faq/items/${encodeURIComponent(String(itemId))}`);
}

export async function reorderFaqItems(
  data: ReorderFaqItemsRequest
): Promise<FaqAdminResponse> {
  if (USE_MOCK) return (await getMock()).reorderFaqItems(data);
  return apiClient.patch<FaqAdminResponse>("/v1/admin/faq/reorder", data);
}

export async function updateFaqSection(
  slug: string,
  data: UpdateFaqSectionRequest
): Promise<FaqSectionAdminResponse> {
  if (USE_MOCK) return (await getMock()).updateFaqSection(slug, data);
  return apiClient.patch<FaqSectionAdminResponse>(
    `/v1/admin/faq/sections/${encodeURIComponent(slug)}`,
    data
  );
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

export async function createStripeRetrySession(
  orderId: string
): Promise<{ stripe_checkout_url: string }> {
  return apiClient.post<{ stripe_checkout_url: string }>(
    `/v1/orders/${encodeURIComponent(orderId)}/stripe-session`,
    {}
  );
}

// --- Delivery ---

export async function getDeliveryOffices(
  courier: Courier,
  city: string,
  type?: OfficeType,
  locale?: Locale
): Promise<OfficeResponse[]> {
  if (USE_MOCK) return (await getMock()).getDeliveryOffices(courier, city, type);
  const params = new URLSearchParams({ courier, city });
  if (type) params.set("type", type);
  if (locale) params.set("locale", locale);
  return apiClient.get<OfficeResponse[]>(`/v1/delivery/offices?${params}`);
}

export async function getDeliveryCities(
  courier: Courier,
  query?: string,
  locale?: Locale
): Promise<string[]> {
  if (USE_MOCK) return (await getMock()).getDeliveryCities(courier, query);
  const params = new URLSearchParams({ courier });
  if (query) params.set("q", query);
  if (locale) params.set("locale", locale);
  return apiClient.get<string[]>(`/v1/delivery/cities?${params}`);
}

export async function getDeliveryPlaces(
  courier: Courier,
  query?: string,
  locale?: Locale
): Promise<CityPlace[]> {
  if (USE_MOCK) return (await getMock()).getDeliveryPlaces(courier, query);
  const params = new URLSearchParams({ courier });
  if (query) params.set("q", query);
  if (locale) params.set("locale", locale);
  return apiClient.get<CityPlace[]>(`/v1/delivery/places?${params}`);
}

export async function calculateShipping(
  payload: CalculateShippingRequest
): Promise<CalculateShippingResponse> {
  if (USE_MOCK) return (await getMock()).calculateShipping(payload);
  return apiClient.calculateShipping(payload);
}

export async function getDeliverySettings(): Promise<DeliverySettingsResponse> {
  if (USE_MOCK) return (await getMock()).getDeliverySettings();
  return apiClient.get<DeliverySettingsResponse>("/v1/delivery/settings");
}

export async function getAdminDeliverySettings(): Promise<DeliverySettingsResponse> {
  if (USE_MOCK) return (await getMock()).getAdminDeliverySettings();
  return apiClient.get<DeliverySettingsResponse>("/v1/admin/delivery-settings");
}

export async function updateAdminDeliverySettings(
  data: DeliverySettingsUpdate
): Promise<DeliverySettingsResponse> {
  if (USE_MOCK) return (await getMock()).updateAdminDeliverySettings(data);
  return apiClient.put<DeliverySettingsResponse>("/v1/admin/delivery-settings", data);
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

// --- Contact ---

export async function submitContact(
  data: ContactRequest
): Promise<ContactResponse> {
  if (USE_MOCK) return (await getMock()).submitContact(data);
  return apiClient.post<ContactResponse>("/v1/contact", data);
}

// --- Admin ---

export async function getAdminStats(): Promise<AdminStats> {
  if (USE_MOCK) return (await getMock()).getAdminStats();
  const stats = await apiClient.get<
    AdminStats & {
      products?: { active?: number };
      orders?: { total?: number; revenue_cents?: number };
    }
  >("/v1/admin/dashboard");

  return {
    orders_today: stats.orders_today ?? stats.orders?.total ?? 0,
    revenue_this_week_cents:
      stats.revenue_this_week_cents ?? stats.orders?.revenue_cents ?? 0,
    active_product_count: stats.active_product_count ?? stats.products?.active ?? 0,
  };
}

function analyticsQuery(startDate?: string, endDate?: string): string {
  const params = new URLSearchParams();
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  return params.size ? `?${params}` : "";
}

export async function getAdminAnalyticsSummary(
  startDate?: string,
  endDate?: string
): Promise<AnalyticsSummaryResponse> {
  if (USE_MOCK) {
    return {
      start_date: startDate || "",
      end_date: endDate || "",
      consented_sessions: 0,
      accepted_events: 0,
      conversion_rate: 0,
      backend_order_count: 0,
      backend_revenue_cents: 0,
      analytics_purchase_count: 0,
      analytics_purchase_revenue_cents: 0,
      coverage_percent: 0,
      consented_order_count: 0,
      consented_order_delta: 0,
      delivery_warning: false,
      health: {
        accepted: 0,
        rejected: 0,
        duplicate: 0,
        validation_failure: 0,
        last_successful_flush_at: null,
        duckdb_load_status: "mock",
        retention_days: 395,
      },
    };
  }
  return apiClient.get<AnalyticsSummaryResponse>(
    `/v1/admin/analytics/summary${analyticsQuery(startDate, endDate)}`
  );
}

export async function getAdminAnalyticsFunnel(
  startDate?: string,
  endDate?: string
): Promise<AnalyticsFunnelResponse> {
  if (USE_MOCK) return { steps: [] };
  return apiClient.get<AnalyticsFunnelResponse>(
    `/v1/admin/analytics/funnel${analyticsQuery(startDate, endDate)}`
  );
}

export async function getAdminAnalyticsProducts(
  startDate?: string,
  endDate?: string
): Promise<ProductAnalyticsResponse> {
  if (USE_MOCK) return { products: [] };
  return apiClient.get<ProductAnalyticsResponse>(
    `/v1/admin/analytics/products${analyticsQuery(startDate, endDate)}`
  );
}

export async function getAdminAnalyticsCheckout(
  startDate?: string,
  endDate?: string
): Promise<CheckoutAnalyticsResponse> {
  if (USE_MOCK) {
    return {
      checkout_starts: 0,
      order_submits: 0,
      payment_redirects: 0,
      purchase_confirmed: 0,
      delivery_methods: {},
      delivery_couriers: {},
      payment_methods: {},
    };
  }
  return apiClient.get<CheckoutAnalyticsResponse>(
    `/v1/admin/analytics/checkout${analyticsQuery(startDate, endDate)}`
  );
}

export function getAdminAnalyticsExportUrl(startDate?: string, endDate?: string): string {
  return `${apiClient.BASE_URL}/v1/admin/analytics/export.csv${analyticsQuery(startDate, endDate)}`;
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
    `/v1/admin/products/${encodeURIComponent(productId)}/images`,
    formData
  );
}

export async function deleteProductImage(
  productId: string,
  imageId: string
): Promise<void> {
  if (USE_MOCK) return (await getMock()).deleteProductImage(productId, imageId);
  return apiClient.del<void>(
    `/v1/admin/products/${encodeURIComponent(productId)}/images/${encodeURIComponent(imageId)}`
  );
}

export async function reorderProductImages(
  productId: string,
  orderedIds: string[]
): Promise<ProductImage[]> {
  if (USE_MOCK) return (await getMock()).reorderProductImages(productId, orderedIds);
  return apiClient.patch<ProductImage[]>(
    `/v1/admin/products/${encodeURIComponent(productId)}/images/reorder`,
    { ordered_ids: orderedIds }
  );
}

export async function setPrimaryProductImage(
  productId: string,
  imageId: string
): Promise<ProductImage> {
  if (USE_MOCK) return (await getMock()).setPrimaryProductImage(productId, imageId);
  return apiClient.patch<ProductImage>(
    `/v1/admin/products/${encodeURIComponent(productId)}/images/${encodeURIComponent(imageId)}/primary`,
    {}
  );
}

export async function uploadProductVideo(
  productId: string,
  file: File
): Promise<VideoUploadResponse> {
  if (USE_MOCK) return (await getMock()).uploadProductVideo(productId, file);
  const formData = new FormData();
  formData.append("file", file);
  return apiClient.postForm<VideoUploadResponse>(
    `/v1/admin/products/${encodeURIComponent(productId)}/video`,
    formData
  );
}

export async function getProductVideo(productId: string): Promise<ProductVideo> {
  if (USE_MOCK) return (await getMock()).getProductVideo(productId);
  return apiClient.get<ProductVideo>(
    `/v1/admin/products/${encodeURIComponent(productId)}/video`
  );
}

export async function deleteProductVideo(productId: string): Promise<void> {
  if (USE_MOCK) return (await getMock()).deleteProductVideo(productId);
  return apiClient.del<void>(`/v1/admin/products/${encodeURIComponent(productId)}/video`);
}

export async function updateProductVideoSortOrder(
  productId: string,
  sortOrder: number
): Promise<ProductVideo> {
  if (USE_MOCK) return (await getMock()).updateProductVideoSortOrder(productId, sortOrder);
  return apiClient.patch<ProductVideo>(
    `/v1/admin/products/${encodeURIComponent(productId)}/video`,
    { sort_order: sortOrder }
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

export async function getAdminOrder(orderId: string): Promise<OrderResponse> {
  if (USE_MOCK) return (await getMock()).getAdminOrder(orderId);
  return apiClient.get<OrderResponse>(
    `/v1/admin/orders/${encodeURIComponent(orderId)}`
  );
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
  if (USE_MOCK) return (await getMock()).updateOrderStatus(orderId, status, tracking);
  return apiClient.patch<OrderResponse>(
    `/v1/admin/orders/${encodeURIComponent(orderId)}/status`,
    { status, ...tracking }
  );
}

// --- Promotions (campaigns, bulk discount, managed banner) ---

export async function getCampaigns(): Promise<CampaignListResponse> {
  if (USE_MOCK) return (await getMock()).getCampaigns();
  return apiClient.get<CampaignListResponse>("/v1/admin/promotions/campaigns");
}

export async function getCampaign(campaignId: string): Promise<CampaignResponse> {
  if (USE_MOCK) return (await getMock()).getCampaign(campaignId);
  return apiClient.get<CampaignResponse>(
    `/v1/admin/promotions/campaigns/${encodeURIComponent(campaignId)}`
  );
}

export async function createCampaign(
  data: CampaignCreateRequest
): Promise<CampaignResponse> {
  if (USE_MOCK) return (await getMock()).createCampaign(data);
  return apiClient.post<CampaignResponse>("/v1/admin/promotions/campaigns", data);
}

export async function updateCampaign(
  campaignId: string,
  data: CampaignUpdateRequest
): Promise<CampaignResponse> {
  if (USE_MOCK) return (await getMock()).updateCampaign(campaignId, data);
  return apiClient.patch<CampaignResponse>(
    `/v1/admin/promotions/campaigns/${encodeURIComponent(campaignId)}`,
    data
  );
}

export async function deleteCampaign(campaignId: string): Promise<void> {
  if (USE_MOCK) return (await getMock()).deleteCampaign(campaignId);
  return apiClient.del<void>(
    `/v1/admin/promotions/campaigns/${encodeURIComponent(campaignId)}`
  );
}

export async function applyCampaign(
  campaignId: string
): Promise<BulkDiscountResponse> {
  if (USE_MOCK) return (await getMock()).applyCampaign(campaignId);
  return apiClient.post<BulkDiscountResponse>(
    `/v1/admin/promotions/campaigns/${encodeURIComponent(campaignId)}/apply`
  );
}

export async function removeCampaign(
  campaignId: string
): Promise<BulkDiscountResponse> {
  if (USE_MOCK) return (await getMock()).removeCampaign(campaignId);
  return apiClient.post<BulkDiscountResponse>(
    `/v1/admin/promotions/campaigns/${encodeURIComponent(campaignId)}/remove`
  );
}

export async function bulkDiscount(
  data: BulkDiscountRequest
): Promise<BulkDiscountResponse> {
  if (USE_MOCK) return (await getMock()).bulkDiscount(data);
  return apiClient.patch<BulkDiscountResponse>("/v1/admin/products/bulk-discount", data);
}

export async function getAdminBanner(): Promise<BannerAdminResponse> {
  if (USE_MOCK) return (await getMock()).getAdminBanner();
  return apiClient.get<BannerAdminResponse>("/v1/admin/promotions/banner");
}

export async function updateBanner(
  data: BannerUpdateRequest
): Promise<BannerAdminResponse> {
  if (USE_MOCK) return (await getMock()).updateBanner(data);
  return apiClient.put<BannerAdminResponse>("/v1/admin/promotions/banner", data);
}

export async function getPublicBanner(
  locale: Locale = "en"
): Promise<PublicBannerResponse> {
  if (USE_MOCK) return (await getMock()).getPublicBanner(locale);
  return apiClient.get<PublicBannerResponse>(
    `/v1/promotions/banner?locale=${encodeURIComponent(locale)}`
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
