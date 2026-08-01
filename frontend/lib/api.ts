/**
 * API facade — delegates to mock-api or api-client based on env flag.
 * Import from here in components, never from mock-api or api-client directly.
 */

import * as apiClient from "./api-client";
import type { Locale } from "@/i18n/routing";
import type {
  AdminProductListResponse,
  AdminProductResponse,
  AdminOrderDetailResponse,
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
  CallbackOutcome,
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
  CodSettlementResponse,
  CreateStripeRefundRequest,
  DeliveryConfigResponse,
  DeliverySettingsResponse,
  DeliverySettingsUpdate,
  EcontConnectionTestResponse,
  EcontFulfillmentActionResponse,
  EcontManualStatusRequest,
  EcontOrderFulfillmentResponse,
  EcontOrderRepairRequest,
  EcontSettingsResponse,
  EcontSettingsUpdate,
  SpeedyActionResponse,
  SpeedyAdminOverviewResponse,
  SpeedyCancelShipmentRequest,
  SpeedyPickupRequest,
  SpeedyPickupResponse,
  SpeedyPickupTermsRequest,
  SpeedyPickupTermsResponse,
  SpeedyShipmentInfoRequest,
  SpeedyShipmentInfoResponse,
  SpeedyShipmentSearchRequest,
  SpeedyShipmentSearchResponse,
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
  InspectReturnCaseRequest,
  OfficeResponse,
  OfficeType,
  OrderListResponse,
  OrderResponse,
  OrderStatus,
  PaymentRefundResponse,
  PaymentMethod,
  PaymentSettingsResponse,
  PaymentSettingsUpdate,
  PaymentStatus,
  ManualPaymentAction,
  ProductListResponse,
  ProductAnalyticsResponse,
  PublicPaymentSettingsResponse,
  ProductResponse,
  ReactionCountsResponse,
  RecordCodSettlementRequest,
  ReactionToggleRequest,
  ReactionToggleResponse,
  ReturnCaseResponse,
  CreateReturnCaseRequest,
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
  UpdateReturnAccountingRequest,
  UpdateTaxonomyTermRequest,
  UserResponse,
  VideoUploadResponse,
} from "./types";

import type {
  AccountantAcceptanceRequest,
  AccountingConfigurationResponse,
  AccountingDocumentListResponse,
  AccountingDocumentRequest,
  AccountingDocumentResponse,
  AccountingLedgerName,
  AccountingLedgerResponse,
  AdminOrderAccountingFilter,
  CategoryMappingRequest,
  CategoryMappingResponse,
  ExportSchemaSettingsRequest,
  ExportSchemaSettingsResponse,
  ExpenseEvidenceListResponse,
  ExpenseEvidenceRequest,
  ExpenseEvidenceResponse,
  ExpenseEvidenceSettingsRequest,
  ExpenseEvidenceSettingsResponse,
  ExpensePaymentStatusRequest,
  FinanceExceptionActionRequest,
  FinanceExceptionListResponse,
  FinanceExceptionResponse,
  FinanceExceptionStatus,
  FinanceExportPackageListResponse,
  FinanceExportPackageResponse,
  FinancePeriodActionRequest,
  FinancePeriodCreateRequest,
  FinancePeriodListResponse,
  FinancePeriodResponse,
  CogsLedgerListResponse,
  InventoryClosePreviewResponse,
  InventoryExceptionResponse,
  InventoryMovementListResponse,
  InventoryMovementResponse,
  InventoryValuationSettingsRequest,
  InventoryValuationSettingsResponse,
  MaterialAdjustmentRequest,
  MaterialDetailResponse,
  MaterialListResponse,
  MaterialLotListResponse,
  MaterialReceiptRequest,
  MaterialReceiptResponse,
  MaterialRequest,
  MaterialResponse,
  MaterialUpdateRequest,
  MissingProductCostDiagnosticsResponse,
  OpeningBalanceRequest,
  ProductionBatchCorrectionRequest,
  ProductionBatchListResponse,
  ProductionBatchPostRequest,
  ProductionBatchRequest,
  ProductionBatchResponse,
  ProductionBatchUpdateRequest,
  ProductionTraceabilityResponse,
  ProductCostSettingsRequest,
  ProductCostSettingsResponse,
  ProductCostVersionListResponse,
  ProductCostVersionRequest,
  ProductCostVersionResponse,
  RecipeCostSnapshotRequest,
  RecipeCostSnapshotResponse,
  RecipeDiagnosticsListResponse,
  RecipeReviewRequest,
  RecipeVersionListResponse,
  RecipeVersionRequest,
  RecipeVersionResponse,
  RecipeVersionUpdateRequest,
  SellerLegalProfileRequest,
  SellerLegalProfileResponse,
  StripeBalanceImportResponse,
  StripePayoutImportStatusResponse,
  ValuationLayerListResponse,
  ValuationLayerResponse,
  VatFiscalSettingsRequest,
  VatFiscalSettingsResponse,
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
  orderId: string,
  paymentReturnToken?: string | null
): Promise<{ stripe_checkout_url: string }> {
  return apiClient.post<{ stripe_checkout_url: string }>(
    `/v1/orders/${encodeURIComponent(orderId)}/stripe-session`,
    { payment_return_token: paymentReturnToken ?? "" }
  );
}

// --- Delivery ---

export async function getDeliveryConfig(): Promise<DeliveryConfigResponse> {
  if (USE_MOCK) return (await getMock()).getDeliveryConfig();
  return apiClient.get<DeliveryConfigResponse>("/v1/delivery/config");
}

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

export async function getPublicPaymentSettings(): Promise<PublicPaymentSettingsResponse> {
  if (USE_MOCK) return (await getMock()).getPublicPaymentSettings();
  return apiClient.get<PublicPaymentSettingsResponse>("/v1/settings/payments");
}

export async function getAdminPaymentSettings(): Promise<PaymentSettingsResponse> {
  if (USE_MOCK) return (await getMock()).getAdminPaymentSettings();
  return apiClient.get<PaymentSettingsResponse>("/v1/admin/settings/payments");
}

export async function updateAdminPaymentSettings(
  data: PaymentSettingsUpdate
): Promise<PaymentSettingsResponse> {
  if (USE_MOCK) return (await getMock()).updateAdminPaymentSettings(data);
  return apiClient.put<PaymentSettingsResponse>("/v1/admin/settings/payments", data);
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

export async function getEcontSettings(): Promise<EcontSettingsResponse> {
  if (USE_MOCK) return (await getMock()).getEcontSettings();
  return apiClient.get<EcontSettingsResponse>("/v1/admin/econt/settings");
}

export async function updateEcontSettings(
  data: EcontSettingsUpdate
): Promise<EcontSettingsResponse> {
  if (USE_MOCK) return (await getMock()).updateEcontSettings(data);
  return apiClient.patch<EcontSettingsResponse>("/v1/admin/econt/settings", data);
}

export async function testEcontConnection(): Promise<EcontConnectionTestResponse> {
  if (USE_MOCK) return (await getMock()).testEcontConnection();
  return apiClient.post<EcontConnectionTestResponse>("/v1/admin/econt/test-connection");
}

export async function getEcontOrderReadiness(
  orderId: string
): Promise<EcontOrderFulfillmentResponse> {
  if (USE_MOCK) return (await getMock()).getEcontOrderReadiness(orderId);
  return apiClient.get<EcontOrderFulfillmentResponse>(
    `/v1/admin/orders/${encodeURIComponent(orderId)}/econt/readiness`
  );
}

export async function repairEcontOrder(
  orderId: string,
  data: EcontOrderRepairRequest
): Promise<EcontOrderFulfillmentResponse> {
  if (USE_MOCK) return (await getMock()).repairEcontOrder(orderId, data);
  return apiClient.patch<EcontOrderFulfillmentResponse>(
    `/v1/admin/orders/${encodeURIComponent(orderId)}/econt/repair`,
    data
  );
}

export async function syncEcontOrder(orderId: string): Promise<EcontFulfillmentActionResponse> {
  if (USE_MOCK) return (await getMock()).syncEcontOrder(orderId);
  return apiClient.post<EcontFulfillmentActionResponse>(
    `/v1/admin/orders/${encodeURIComponent(orderId)}/econt/sync`
  );
}

export async function createEcontLabel(orderId: string): Promise<EcontFulfillmentActionResponse> {
  if (USE_MOCK) return (await getMock()).createEcontLabel(orderId);
  return apiClient.post<EcontFulfillmentActionResponse>(
    `/v1/admin/orders/${encodeURIComponent(orderId)}/econt/label`
  );
}

export async function createAndShipEcontOrder(
  orderId: string
): Promise<EcontFulfillmentActionResponse> {
  if (USE_MOCK) return (await getMock()).createAndShipEcontOrder(orderId);
  return apiClient.post<EcontFulfillmentActionResponse>(
    `/v1/admin/orders/${encodeURIComponent(orderId)}/econt/ship`
  );
}

export async function deleteEcontLabel(orderId: string): Promise<EcontFulfillmentActionResponse> {
  if (USE_MOCK) return (await getMock()).deleteEcontLabel(orderId);
  return apiClient.del<EcontFulfillmentActionResponse>(
    `/v1/admin/orders/${encodeURIComponent(orderId)}/econt/label`
  );
}

export async function refreshEcontTrace(orderId: string): Promise<EcontFulfillmentActionResponse> {
  if (USE_MOCK) return (await getMock()).refreshEcontTrace(orderId);
  return apiClient.post<EcontFulfillmentActionResponse>(
    `/v1/admin/orders/${encodeURIComponent(orderId)}/econt/trace`
  );
}

export async function recordEcontManualStatus(
  orderId: string,
  data: EcontManualStatusRequest
): Promise<EcontFulfillmentActionResponse> {
  if (USE_MOCK) return (await getMock()).recordEcontManualStatus(orderId, data);
  return apiClient.post<EcontFulfillmentActionResponse>(
    `/v1/admin/orders/${encodeURIComponent(orderId)}/econt/manual-status`,
    data
  );
}

export async function getSpeedyAdminOverview(
  orderId?: string | null
): Promise<SpeedyAdminOverviewResponse> {
  if (USE_MOCK) return (await getMock()).getSpeedyAdminOverview(orderId);
  const params = new URLSearchParams();
  if (orderId) params.set("order_id", orderId);
  const query = params.size > 0 ? `?${params}` : "";
  return apiClient.get<SpeedyAdminOverviewResponse>(`/v1/admin/speedy${query}`);
}

export async function createSpeedyWaybill(orderId: string): Promise<SpeedyActionResponse> {
  if (USE_MOCK) return (await getMock()).createSpeedyWaybill(orderId);
  return apiClient.post<SpeedyActionResponse>(
    `/v1/admin/speedy/orders/${encodeURIComponent(orderId)}/ship`
  );
}

export async function refreshSpeedyTracking(orderId: string): Promise<SpeedyActionResponse> {
  if (USE_MOCK) return (await getMock()).refreshSpeedyTracking(orderId);
  return apiClient.post<SpeedyActionResponse>(
    `/v1/admin/speedy/orders/${encodeURIComponent(orderId)}/track`
  );
}

export async function searchSpeedyShipments(
  data: SpeedyShipmentSearchRequest
): Promise<SpeedyShipmentSearchResponse> {
  if (USE_MOCK) return (await getMock()).searchSpeedyShipments(data);
  return apiClient.post<SpeedyShipmentSearchResponse>("/v1/admin/speedy/shipments/search", data);
}

export async function getSpeedyShipmentInfo(
  data: SpeedyShipmentInfoRequest
): Promise<SpeedyShipmentInfoResponse> {
  if (USE_MOCK) return (await getMock()).getSpeedyShipmentInfo(data);
  return apiClient.post<SpeedyShipmentInfoResponse>("/v1/admin/speedy/shipments/info", data);
}

export async function cancelSpeedyShipment(
  orderId: string,
  data: SpeedyCancelShipmentRequest = {}
): Promise<SpeedyActionResponse> {
  if (USE_MOCK) return (await getMock()).cancelSpeedyShipment(orderId, data);
  return apiClient.post<SpeedyActionResponse>(
    `/v1/admin/speedy/orders/${encodeURIComponent(orderId)}/cancel-shipment`,
    data
  );
}

export async function getSpeedyPickupTerms(
  data: SpeedyPickupTermsRequest
): Promise<SpeedyPickupTermsResponse> {
  if (USE_MOCK) return (await getMock()).getSpeedyPickupTerms(data);
  return apiClient.post<SpeedyPickupTermsResponse>("/v1/admin/speedy/pickup/terms", data);
}

export async function requestSpeedyPickup(
  data: SpeedyPickupRequest
): Promise<SpeedyPickupResponse> {
  if (USE_MOCK) return (await getMock()).requestSpeedyPickup(data);
  return apiClient.post<SpeedyPickupResponse>("/v1/admin/speedy/pickup", data);
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
  orderId: string,
  paymentReturnToken?: string | null
): Promise<OrderResponse> {
  if (USE_MOCK) return (await getMock()).getOrder(orderId);
  const params = new URLSearchParams();
  if (paymentReturnToken) params.set("payment_return_token", paymentReturnToken);
  const query = params.size > 0 ? `?${params}` : "";
  return apiClient.get<OrderResponse>(
    `/v1/orders/${encodeURIComponent(orderId)}${query}`
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
  status?: string,
  paymentStatus?: PaymentStatus | "",
  paymentMethod?: PaymentMethod | "",
  accountingFilter?: AdminOrderAccountingFilter | "",
  financePeriodId?: string
): Promise<OrderListResponse> {
  if (USE_MOCK) {
    return (await getMock()).getAdminOrders(
      page,
      limit,
      status,
      paymentStatus,
      paymentMethod,
      accountingFilter,
      financePeriodId
    );
  }
  const params = new URLSearchParams({ page: String(page), limit: String(limit) });
  if (status) params.set("status", status);
  if (paymentStatus) params.set("payment_status", paymentStatus);
  if (paymentMethod) params.set("payment_method", paymentMethod);
  if (accountingFilter) params.set("accounting_filter", accountingFilter);
  if (financePeriodId) params.set("finance_period_id", financePeriodId);
  return apiClient.get<OrderListResponse>(`/v1/admin/orders?${params}`);
}

export async function getAdminOrder(orderId: string): Promise<AdminOrderDetailResponse> {
  if (USE_MOCK) return (await getMock()).getAdminOrder(orderId);
  return apiClient.get<AdminOrderDetailResponse>(
    `/v1/admin/orders/${encodeURIComponent(orderId)}`
  );
}

// --- Admin Inventory ---

export async function listMaterials(filters: {
  active?: boolean;
  category?: string;
  needsReorder?: boolean;
  limit?: number;
  offset?: number;
} = {}): Promise<MaterialListResponse> {
  const params = new URLSearchParams();
  if (filters.active !== undefined) params.set("active", String(filters.active));
  if (filters.category) params.set("category", filters.category);
  if (filters.needsReorder) params.set("needs_reorder", "true");
  if (filters.limit) params.set("limit", String(filters.limit));
  if (filters.offset) params.set("offset", String(filters.offset));
  const query = params.size > 0 ? `?${params}` : "";
  return apiClient.get<MaterialListResponse>(`/v1/admin/inventory/materials${query}`);
}

export async function getMaterial(materialId: string): Promise<MaterialDetailResponse> {
  return apiClient.get<MaterialDetailResponse>(`/v1/admin/inventory/materials/${encodeURIComponent(materialId)}`);
}

export async function createMaterial(data: MaterialRequest): Promise<MaterialResponse> {
  return apiClient.post<MaterialResponse>("/v1/admin/inventory/materials", data);
}

export async function updateMaterial(materialId: string, data: MaterialUpdateRequest): Promise<MaterialResponse> {
  return apiClient.patch<MaterialResponse>(`/v1/admin/inventory/materials/${encodeURIComponent(materialId)}`, data);
}

export async function createMaterialReceipt(materialId: string, data: MaterialReceiptRequest): Promise<MaterialReceiptResponse> {
  return apiClient.post<MaterialReceiptResponse>(`/v1/admin/inventory/materials/${encodeURIComponent(materialId)}/receipts`, data);
}

export async function createMaterialAdjustment(materialId: string, data: MaterialAdjustmentRequest): Promise<InventoryMovementResponse> {
  return apiClient.post<InventoryMovementResponse>(`/v1/admin/inventory/materials/${encodeURIComponent(materialId)}/adjustments`, data);
}

export async function listMaterialLots(materialId: string, productionDate?: string): Promise<MaterialLotListResponse> {
  const params = new URLSearchParams();
  if (productionDate) params.set("production_date", productionDate);
  const query = params.size > 0 ? `?${params}` : "";
  return apiClient.get<MaterialLotListResponse>(`/v1/admin/inventory/materials/${encodeURIComponent(materialId)}/lots${query}`);
}

export async function listMaterialMovements(materialId: string, limit = 100): Promise<InventoryMovementListResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  return apiClient.get<InventoryMovementListResponse>(`/v1/admin/inventory/materials/${encodeURIComponent(materialId)}/movements?${params}`);
}

export async function listInventoryMovements(filters: {
  itemType?: "material" | "finished_good";
  itemId?: string;
  sourceType?: string;
  sourceId?: string;
  movementType?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<InventoryMovementListResponse> {
  const params = new URLSearchParams();
  if (filters.itemType) params.set("item_type", filters.itemType);
  if (filters.itemId) params.set("item_id", filters.itemId);
  if (filters.sourceType) params.set("source_type", filters.sourceType);
  if (filters.sourceId) params.set("source_id", filters.sourceId);
  if (filters.movementType) params.set("movement_type", filters.movementType);
  if (filters.limit) params.set("limit", String(filters.limit));
  if (filters.offset) params.set("offset", String(filters.offset));
  const query = params.size > 0 ? `?${params}` : "";
  return apiClient.get<InventoryMovementListResponse>(`/v1/admin/inventory/movements${query}`);
}

export async function listRecipes(filters: { productId?: string; status?: string } = {}): Promise<RecipeVersionListResponse> {
  const params = new URLSearchParams();
  if (filters.productId) params.set("product_id", filters.productId);
  if (filters.status) params.set("status", filters.status);
  const query = params.size > 0 ? `?${params}` : "";
  return apiClient.get<RecipeVersionListResponse>(`/v1/admin/inventory/recipes${query}`);
}

export async function getRecipe(recipeId: string): Promise<RecipeVersionResponse> {
  return apiClient.get<RecipeVersionResponse>(`/v1/admin/inventory/recipes/${encodeURIComponent(recipeId)}`);
}

export async function createRecipe(data: RecipeVersionRequest): Promise<RecipeVersionResponse> {
  return apiClient.post<RecipeVersionResponse>("/v1/admin/inventory/recipes", data);
}

export async function updateRecipe(recipeId: string, data: RecipeVersionUpdateRequest): Promise<RecipeVersionResponse> {
  return apiClient.patch<RecipeVersionResponse>(`/v1/admin/inventory/recipes/${encodeURIComponent(recipeId)}`, data);
}

export async function activateRecipe(recipeId: string): Promise<RecipeVersionResponse> {
  return apiClient.post<RecipeVersionResponse>(`/v1/admin/inventory/recipes/${encodeURIComponent(recipeId)}/activate`, {});
}

export async function archiveRecipe(recipeId: string): Promise<RecipeVersionResponse> {
  return apiClient.post<RecipeVersionResponse>(`/v1/admin/inventory/recipes/${encodeURIComponent(recipeId)}/archive`, {});
}

export async function createRecipeCostSnapshot(recipeId: string, data: RecipeCostSnapshotRequest): Promise<RecipeCostSnapshotResponse> {
  return apiClient.post<RecipeCostSnapshotResponse>(`/v1/admin/inventory/recipes/${encodeURIComponent(recipeId)}/cost-snapshots`, data);
}

export async function reviewRecipe(recipeId: string, data: RecipeReviewRequest): Promise<RecipeVersionResponse> {
  return apiClient.post<RecipeVersionResponse>(`/v1/admin/inventory/recipes/${encodeURIComponent(recipeId)}/review`, data);
}

export async function getRecipeDiagnostics(recipeId: string): Promise<RecipeDiagnosticsListResponse> {
  return apiClient.get<RecipeDiagnosticsListResponse>(`/v1/admin/inventory/recipes/${encodeURIComponent(recipeId)}/diagnostics`);
}

export async function listProductionBatches(filters: { productId?: string; status?: string } = {}): Promise<ProductionBatchListResponse> {
  const params = new URLSearchParams();
  if (filters.productId) params.set("product_id", filters.productId);
  if (filters.status) params.set("status", filters.status);
  const query = params.size > 0 ? `?${params}` : "";
  return apiClient.get<ProductionBatchListResponse>(`/v1/admin/inventory/batches${query}`);
}

export async function getProductionBatch(batchId: string): Promise<ProductionBatchResponse> {
  return apiClient.get<ProductionBatchResponse>(`/v1/admin/inventory/batches/${encodeURIComponent(batchId)}`);
}

export async function createProductionBatch(data: ProductionBatchRequest): Promise<ProductionBatchResponse> {
  return apiClient.post<ProductionBatchResponse>("/v1/admin/inventory/batches", data);
}

export async function updateProductionBatch(batchId: string, data: ProductionBatchUpdateRequest): Promise<ProductionBatchResponse> {
  return apiClient.patch<ProductionBatchResponse>(`/v1/admin/inventory/batches/${encodeURIComponent(batchId)}`, data);
}

export async function postProductionBatch(batchId: string, data: ProductionBatchPostRequest): Promise<ProductionBatchResponse> {
  return apiClient.post<ProductionBatchResponse>(`/v1/admin/inventory/batches/${encodeURIComponent(batchId)}/post`, data);
}

export async function cancelProductionBatch(batchId: string): Promise<ProductionBatchResponse> {
  return apiClient.post<ProductionBatchResponse>(`/v1/admin/inventory/batches/${encodeURIComponent(batchId)}/cancel`, {});
}

export async function correctProductionBatch(batchId: string, data: ProductionBatchCorrectionRequest): Promise<InventoryMovementResponse> {
  return apiClient.post<InventoryMovementResponse>(`/v1/admin/inventory/batches/${encodeURIComponent(batchId)}/correct`, data);
}

export async function getProductionTraceability(batchId: string): Promise<ProductionTraceabilityResponse> {
  return apiClient.get<ProductionTraceabilityResponse>(`/v1/admin/inventory/batches/${encodeURIComponent(batchId)}/traceability`);
}

export async function getInventoryValuationSettings(): Promise<InventoryValuationSettingsResponse> {
  return apiClient.get<InventoryValuationSettingsResponse>("/v1/admin/inventory/valuation/settings");
}

export async function updateInventoryValuationSettings(data: InventoryValuationSettingsRequest): Promise<InventoryValuationSettingsResponse> {
  return apiClient.put<InventoryValuationSettingsResponse>("/v1/admin/inventory/valuation/settings", data);
}

export async function recordOpeningBalance(data: OpeningBalanceRequest): Promise<ValuationLayerResponse | null> {
  return apiClient.post<ValuationLayerResponse | null>("/v1/admin/inventory/valuation/opening-balances", data);
}

export async function generateValuationLayers(): Promise<ValuationLayerListResponse> {
  return apiClient.post<ValuationLayerListResponse>("/v1/admin/inventory/valuation/layers/generate", {});
}

export async function listValuationLayers(filters: { itemType?: "material" | "finished_good"; itemId?: string } = {}): Promise<ValuationLayerListResponse> {
  const params = new URLSearchParams();
  if (filters.itemType) params.set("item_type", filters.itemType);
  if (filters.itemId) params.set("item_id", filters.itemId);
  const query = params.size > 0 ? `?${params}` : "";
  return apiClient.get<ValuationLayerListResponse>(`/v1/admin/inventory/valuation/layers${query}`);
}

export async function generateCogsRows(): Promise<CogsLedgerListResponse> {
  return apiClient.post<CogsLedgerListResponse>("/v1/admin/inventory/valuation/cogs/generate", {});
}

export async function listCogsRows(): Promise<CogsLedgerListResponse> {
  return apiClient.get<CogsLedgerListResponse>("/v1/admin/inventory/valuation/cogs");
}

export async function getInventoryClosePreview(periodStart: string, periodEnd: string): Promise<InventoryClosePreviewResponse> {
  const params = new URLSearchParams({ period_start: periodStart, period_end: periodEnd });
  return apiClient.get<InventoryClosePreviewResponse>(`/v1/admin/inventory/valuation/close-preview?${params}`);
}

export async function listInventoryExceptions(): Promise<InventoryExceptionResponse[]> {
  return apiClient.get<InventoryExceptionResponse[]>("/v1/admin/inventory/valuation/exceptions");
}

// --- Accounting & Finance Hub ---

export async function getAccountingConfig(): Promise<AccountingConfigurationResponse> {
  if (USE_MOCK) return (await getMock()).getAccountingConfig();
  return apiClient.get<AccountingConfigurationResponse>("/v1/admin/accounting/config");
}

export async function createSellerLegalProfile(
  data: SellerLegalProfileRequest
): Promise<SellerLegalProfileResponse> {
  if (USE_MOCK) return (await getMock()).createSellerLegalProfile(data);
  return apiClient.post<SellerLegalProfileResponse>("/v1/admin/accounting/config/seller-profile", data);
}

export async function createVatFiscalSettings(
  data: VatFiscalSettingsRequest
): Promise<VatFiscalSettingsResponse> {
  if (USE_MOCK) return (await getMock()).createVatFiscalSettings(data);
  return apiClient.post<VatFiscalSettingsResponse>("/v1/admin/accounting/config/vat-fiscal", data);
}

export async function upsertAccountingCategoryMapping(
  mappingKey: string,
  data: CategoryMappingRequest
): Promise<CategoryMappingResponse> {
  if (USE_MOCK) return (await getMock()).upsertAccountingCategoryMapping(mappingKey, data);
  return apiClient.put<CategoryMappingResponse>(
    `/v1/admin/accounting/config/category-mappings/${encodeURIComponent(mappingKey)}`,
    data
  );
}

export async function updateAccountingExportSchema(
  data: ExportSchemaSettingsRequest
): Promise<ExportSchemaSettingsResponse> {
  if (USE_MOCK) return (await getMock()).updateAccountingExportSchema(data);
  return apiClient.put<ExportSchemaSettingsResponse>("/v1/admin/accounting/config/export-schema", data);
}

export async function updateExpenseEvidenceSettings(
  data: ExpenseEvidenceSettingsRequest
): Promise<ExpenseEvidenceSettingsResponse> {
  if (USE_MOCK) return (await getMock()).updateExpenseEvidenceSettings(data);
  return apiClient.put<ExpenseEvidenceSettingsResponse>("/v1/admin/accounting/config/expense-settings", data);
}

export async function updateProductCostSettings(
  data: ProductCostSettingsRequest
): Promise<ProductCostSettingsResponse> {
  if (USE_MOCK) return (await getMock()).updateProductCostSettings(data);
  return apiClient.put<ProductCostSettingsResponse>("/v1/admin/accounting/config/product-cost-settings", data);
}

export async function listFinancePeriods(status?: string): Promise<FinancePeriodListResponse> {
  if (USE_MOCK) return (await getMock()).listFinancePeriods(status);
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  const query = params.size > 0 ? `?${params}` : "";
  return apiClient.get<FinancePeriodListResponse>(`/v1/admin/accounting/periods${query}`);
}

export async function createFinancePeriod(
  data: FinancePeriodCreateRequest
): Promise<FinancePeriodResponse> {
  if (USE_MOCK) return (await getMock()).createFinancePeriod(data);
  return apiClient.post<FinancePeriodResponse>("/v1/admin/accounting/periods", data);
}

export async function reviewFinancePeriod(periodId: string): Promise<FinancePeriodResponse> {
  if (USE_MOCK) return (await getMock()).reviewFinancePeriod(periodId);
  return apiClient.post<FinancePeriodResponse>(
    `/v1/admin/accounting/periods/${encodeURIComponent(periodId)}/review`
  );
}

export async function closeFinancePeriod(periodId: string): Promise<FinancePeriodResponse> {
  if (USE_MOCK) return (await getMock()).closeFinancePeriod(periodId);
  return apiClient.post<FinancePeriodResponse>(
    `/v1/admin/accounting/periods/${encodeURIComponent(periodId)}/close`
  );
}

export async function reopenFinancePeriod(
  periodId: string,
  data: FinancePeriodActionRequest
): Promise<FinancePeriodResponse> {
  if (USE_MOCK) return (await getMock()).reopenFinancePeriod(periodId, data);
  return apiClient.post<FinancePeriodResponse>(
    `/v1/admin/accounting/periods/${encodeURIComponent(periodId)}/reopen`,
    data
  );
}

export async function acceptFinancePeriod(
  periodId: string,
  data: FinancePeriodActionRequest
): Promise<FinancePeriodResponse> {
  if (USE_MOCK) return (await getMock()).acceptFinancePeriod(periodId, data);
  return apiClient.post<FinancePeriodResponse>(
    `/v1/admin/accounting/periods/${encodeURIComponent(periodId)}/accept`,
    data
  );
}

export async function listFinanceExceptions(
  periodId: string,
  status?: FinanceExceptionStatus | ""
): Promise<FinanceExceptionListResponse> {
  if (USE_MOCK) return (await getMock()).listFinanceExceptions(periodId, status);
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  const query = params.size > 0 ? `?${params}` : "";
  return apiClient.get<FinanceExceptionListResponse>(
    `/v1/admin/accounting/periods/${encodeURIComponent(periodId)}/exceptions${query}`
  );
}

export async function resolveFinanceException(
  exceptionId: string,
  data: FinanceExceptionActionRequest
): Promise<FinanceExceptionResponse> {
  if (USE_MOCK) return (await getMock()).resolveFinanceException(exceptionId, data);
  return apiClient.post<FinanceExceptionResponse>(
    `/v1/admin/accounting/exceptions/${encodeURIComponent(exceptionId)}/resolve`,
    data
  );
}

export async function waiveFinanceException(
  exceptionId: string,
  data: FinanceExceptionActionRequest
): Promise<FinanceExceptionResponse> {
  if (USE_MOCK) return (await getMock()).waiveFinanceException(exceptionId, data);
  return apiClient.post<FinanceExceptionResponse>(
    `/v1/admin/accounting/exceptions/${encodeURIComponent(exceptionId)}/waive`,
    data
  );
}

export async function getAccountingLedger(
  periodId: string,
  ledger: AccountingLedgerName,
  options: { dateBasis?: string; page?: number; limit?: number } = {}
): Promise<AccountingLedgerResponse> {
  if (USE_MOCK) return (await getMock()).getAccountingLedger(periodId, ledger, options);
  const params = new URLSearchParams({
    page: String(options.page ?? 1),
    limit: String(options.limit ?? 100),
  });
  if (options.dateBasis) params.set("date_basis", options.dateBasis);
  return apiClient.get<AccountingLedgerResponse>(
    `/v1/admin/accounting/periods/${encodeURIComponent(periodId)}/ledgers/${encodeURIComponent(ledger)}?${params}`
  );
}

export function getAccountingExportDownloadUrl(exportId: string, file = "xlsx"): string {
  const params = new URLSearchParams({ file });
  return `${apiClient.BASE_URL}/v1/admin/accounting/exports/${encodeURIComponent(exportId)}/download?${params}`;
}

export async function listAccountingDocuments(filters: {
  orderId?: string;
  refundId?: string;
  periodId?: string;
} = {}): Promise<AccountingDocumentListResponse> {
  if (USE_MOCK) return (await getMock()).listAccountingDocuments(filters);
  const params = new URLSearchParams();
  if (filters.orderId) params.set("order_id", filters.orderId);
  if (filters.refundId) params.set("refund_id", filters.refundId);
  if (filters.periodId) params.set("period_id", filters.periodId);
  const query = params.size > 0 ? `?${params}` : "";
  return apiClient.get<AccountingDocumentListResponse>(`/v1/admin/accounting/documents${query}`);
}

export async function listOrderAccountingDocuments(orderId: string): Promise<AccountingDocumentListResponse> {
  if (USE_MOCK) return (await getMock()).listOrderAccountingDocuments(orderId);
  return apiClient.get<AccountingDocumentListResponse>(
    `/v1/admin/accounting/orders/${encodeURIComponent(orderId)}/documents`
  );
}

export async function createAccountingDocument(
  data: AccountingDocumentRequest
): Promise<AccountingDocumentResponse> {
  if (USE_MOCK) return (await getMock()).createAccountingDocument(data);
  return apiClient.post<AccountingDocumentResponse>("/v1/admin/accounting/documents", data);
}

export async function updateAccountingDocument(
  documentId: string,
  data: AccountingDocumentRequest
): Promise<AccountingDocumentResponse> {
  if (USE_MOCK) return (await getMock()).updateAccountingDocument(documentId, data);
  return apiClient.put<AccountingDocumentResponse>(
    `/v1/admin/accounting/documents/${encodeURIComponent(documentId)}`,
    data
  );
}

export async function listExpenseEvidence(filters: {
  categoryKey?: string;
  reviewStatus?: string;
} = {}): Promise<ExpenseEvidenceListResponse> {
  if (USE_MOCK) return (await getMock()).listExpenseEvidence(filters);
  const params = new URLSearchParams();
  if (filters.categoryKey) params.set("category_key", filters.categoryKey);
  if (filters.reviewStatus) params.set("review_status", filters.reviewStatus);
  const query = params.size > 0 ? `?${params}` : "";
  return apiClient.get<ExpenseEvidenceListResponse>(`/v1/admin/accounting/expenses${query}`);
}

export async function createExpenseEvidence(
  data: ExpenseEvidenceRequest
): Promise<ExpenseEvidenceResponse> {
  if (USE_MOCK) return (await getMock()).createExpenseEvidence(data);
  return apiClient.post<ExpenseEvidenceResponse>("/v1/admin/accounting/expenses", data);
}

export async function updateExpenseEvidence(
  expenseId: string,
  data: ExpenseEvidenceRequest
): Promise<ExpenseEvidenceResponse> {
  if (USE_MOCK) return (await getMock()).updateExpenseEvidence(expenseId, data);
  return apiClient.put<ExpenseEvidenceResponse>(
    `/v1/admin/accounting/expenses/${encodeURIComponent(expenseId)}`,
    data
  );
}

export async function updateExpensePaymentStatus(
  expenseId: string,
  data: ExpensePaymentStatusRequest
): Promise<ExpenseEvidenceResponse> {
  if (USE_MOCK) return (await getMock()).updateExpensePaymentStatus(expenseId, data);
  return apiClient.patch<ExpenseEvidenceResponse>(
    `/v1/admin/accounting/expenses/${encodeURIComponent(expenseId)}/payment-status`,
    data
  );
}

export async function listProductCosts(productId?: string): Promise<ProductCostVersionListResponse> {
  if (USE_MOCK) return (await getMock()).listProductCosts(productId);
  const params = new URLSearchParams();
  if (productId) params.set("product_id", productId);
  const query = params.size > 0 ? `?${params}` : "";
  return apiClient.get<ProductCostVersionListResponse>(`/v1/admin/accounting/product-costs${query}`);
}

export async function createProductCost(
  data: ProductCostVersionRequest
): Promise<ProductCostVersionResponse> {
  if (USE_MOCK) return (await getMock()).createProductCost(data);
  return apiClient.post<ProductCostVersionResponse>("/v1/admin/accounting/product-costs", data);
}

export async function updateProductCost(
  costVersionId: string,
  data: ProductCostVersionRequest
): Promise<ProductCostVersionResponse> {
  if (USE_MOCK) return (await getMock()).updateProductCost(costVersionId, data);
  return apiClient.put<ProductCostVersionResponse>(
    `/v1/admin/accounting/product-costs/${encodeURIComponent(costVersionId)}`,
    data
  );
}

export async function getMissingProductCosts(periodId: string): Promise<MissingProductCostDiagnosticsResponse> {
  if (USE_MOCK) return (await getMock()).getMissingProductCosts(periodId);
  const params = new URLSearchParams({ period_id: periodId });
  return apiClient.get<MissingProductCostDiagnosticsResponse>(`/v1/admin/accounting/product-costs/missing?${params}`);
}

export async function listAccountingExports(periodId?: string): Promise<FinanceExportPackageListResponse> {
  if (USE_MOCK) return (await getMock()).listAccountingExports(periodId);
  const params = new URLSearchParams();
  if (periodId) params.set("period_id", periodId);
  const query = params.size > 0 ? `?${params}` : "";
  return apiClient.get<FinanceExportPackageListResponse>(`/v1/admin/accounting/exports${query}`);
}

export async function generateAccountingExport(periodId: string): Promise<FinanceExportPackageResponse> {
  if (USE_MOCK) return (await getMock()).generateAccountingExport(periodId);
  return apiClient.post<FinanceExportPackageResponse>(
    `/v1/admin/accounting/periods/${encodeURIComponent(periodId)}/exports`
  );
}

export async function acceptAccountingExport(
  exportId: string,
  data: AccountantAcceptanceRequest
): Promise<FinanceExportPackageResponse> {
  if (USE_MOCK) return (await getMock()).acceptAccountingExport(exportId, data);
  return apiClient.post<FinanceExportPackageResponse>(
    `/v1/admin/accounting/exports/${encodeURIComponent(exportId)}/accept`,
    data
  );
}

export async function getStripePayoutImportStatus(): Promise<StripePayoutImportStatusResponse> {
  if (USE_MOCK) return (await getMock()).getStripePayoutImportStatus();
  return apiClient.get<StripePayoutImportStatusResponse>("/v1/admin/accounting/stripe/import-status");
}

export async function syncStripeBalanceTransactions(limit = 100): Promise<StripeBalanceImportResponse> {
  if (USE_MOCK) return (await getMock()).syncStripeBalanceTransactions(limit);
  const params = new URLSearchParams({ limit: String(limit) });
  return apiClient.post<StripeBalanceImportResponse>(`/v1/admin/accounting/stripe/sync?${params}`);
}

export async function importStripeBalanceCsv(file: File): Promise<StripeBalanceImportResponse> {
  if (USE_MOCK) return (await getMock()).importStripeBalanceCsv(file);
  const formData = new FormData();
  formData.append("file", file);
  return apiClient.postForm<StripeBalanceImportResponse>("/v1/admin/accounting/stripe/manual-import", formData);
}

export async function applyManualPaymentAction(
  orderId: string,
  action: ManualPaymentAction,
  note: string,
  callbackOutcome?: CallbackOutcome | null
): Promise<OrderResponse> {
  if (USE_MOCK) {
    return (await getMock()).applyManualPaymentAction(orderId, action, note, callbackOutcome);
  }
  return apiClient.post<OrderResponse>(
    `/v1/admin/orders/${encodeURIComponent(orderId)}/payment-actions`,
    { action, note, callback_outcome: callbackOutcome ?? undefined }
  );
}

export async function createReturnCase(
  orderId: string,
  data: CreateReturnCaseRequest
): Promise<ReturnCaseResponse> {
  if (USE_MOCK) return (await getMock()).createReturnCase(orderId, data);
  return apiClient.post<ReturnCaseResponse>(
    `/v1/admin/orders/${encodeURIComponent(orderId)}/returns`,
    data
  );
}

export async function receiveReturnCase(
  orderId: string,
  returnId: string
): Promise<ReturnCaseResponse> {
  if (USE_MOCK) return (await getMock()).receiveReturnCase(orderId, returnId);
  return apiClient.post<ReturnCaseResponse>(
    `/v1/admin/orders/${encodeURIComponent(orderId)}/returns/${encodeURIComponent(returnId)}/receive`
  );
}

export async function inspectReturnCase(
  orderId: string,
  returnId: string,
  data: InspectReturnCaseRequest
): Promise<ReturnCaseResponse> {
  if (USE_MOCK) return (await getMock()).inspectReturnCase(orderId, returnId, data);
  return apiClient.patch<ReturnCaseResponse>(
    `/v1/admin/orders/${encodeURIComponent(orderId)}/returns/${encodeURIComponent(returnId)}/inspect`,
    data
  );
}

export async function closeReturnCase(
  orderId: string,
  returnId: string
): Promise<ReturnCaseResponse> {
  if (USE_MOCK) return (await getMock()).closeReturnCase(orderId, returnId);
  return apiClient.post<ReturnCaseResponse>(
    `/v1/admin/orders/${encodeURIComponent(orderId)}/returns/${encodeURIComponent(returnId)}/close`
  );
}

export async function updateReturnAccounting(
  orderId: string,
  returnId: string,
  data: UpdateReturnAccountingRequest
): Promise<ReturnCaseResponse> {
  if (USE_MOCK) return (await getMock()).updateReturnAccounting(orderId, returnId, data);
  return apiClient.patch<ReturnCaseResponse>(
    `/v1/admin/orders/${encodeURIComponent(orderId)}/returns/${encodeURIComponent(returnId)}/accounting`,
    data
  );
}

export async function createStripeRefund(
  orderId: string,
  data: CreateStripeRefundRequest
): Promise<PaymentRefundResponse> {
  if (USE_MOCK) return (await getMock()).createStripeRefund(orderId, data);
  return apiClient.post<PaymentRefundResponse>(
    `/v1/admin/orders/${encodeURIComponent(orderId)}/refunds`,
    data
  );
}

export async function recordCodSettlement(
  orderId: string,
  data: RecordCodSettlementRequest
): Promise<CodSettlementResponse> {
  if (USE_MOCK) return (await getMock()).recordCodSettlement(orderId, data);
  return apiClient.post<CodSettlementResponse>(
    `/v1/admin/orders/${encodeURIComponent(orderId)}/cod-settlement`,
    data
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
