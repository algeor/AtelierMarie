/**
 * TypeScript types mirroring the backend Pydantic models.
 * Source of truth: app/models/*.py
 */

// --- Common ---

export interface ErrorDetail {
  code: string;
  message: string;
  details: Record<string, unknown> | null;
}

export interface ErrorResponse {
  error: ErrorDetail;
}

// --- Contact ---

export interface ContactRequest {
  name: string;
  email: string;
  message: string;
  locale: "en" | "bg";
  website?: string;
}

export interface ContactResponse {
  status: "received";
  message_id: number | null;
}

// --- Products ---

export interface ProductImage {
  id: string;
  image_url: string;
  thumbnail_url: string;
  zoom_url: string | null;
  sort_order: number;
  is_primary: boolean;
}

export interface ProductVideo {
  id: string;
  product_id: string;
  status: "queued" | "transcoding" | "ready" | "failed";
  video_url: string | null;
  poster_url: string | null;
  sort_order: number;
  duration_secs: number | null;
  failure_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProductLabelRef {
  slug: string;
  name: string;
}

export interface ProductResponse {
  id: string;
  name: string;
  description: string | null;
  safety_warnings: string | null;
  care_instructions: string | null;
  materials: string | null;
  days_to_craft: number | null;
  price_cents: number;
  // Discount display fields. effective_price_cents == price_cents when no
  // discount is active; discount_percent is the active display percent or null.
  // Window timestamps are never exposed publicly.
  effective_price_cents: number;
  discount_percent: number | null;
  discount_active: boolean;
  category: string | null;
  category_name: string | null;
  product_type: string;
  product_type_name: string;
  labels: ProductLabelRef[];
  images: ProductImage[];
  video?: ProductVideo | null;
  primary_image_url: string | null;
  primary_thumbnail_url: string | null;
  stock: number;
  is_active: boolean;
  is_featured: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProductListResponse {
  products: ProductResponse[];
  total: number;
  page: number;
  limit: number;
}

export interface SavedProductListResponse extends ProductListResponse {
  product_ids: string[];
}

export interface SavedProductStatusResponse {
  product_id: string;
  saved: boolean;
}

// --- Taxonomy ---

export type TaxonomyKind = "product-types" | "categories" | "labels";

export interface TaxonomyTerm {
  slug: string;
  name: string;
  sort_order: number;
}

export interface TaxonomyResponse {
  product_types: TaxonomyTerm[];
  categories: TaxonomyTerm[];
  labels: TaxonomyTerm[];
}

// --- Atelier Story / About ---

export type AboutSectionType =
  | "hero"
  | "text_image"
  | "text_band"
  | "cards"
  | "timeline"
  | "collections"
  | "cta_band";

export interface AboutCta {
  label: string;
  href: string;
}

export interface AboutItem {
  id: number;
  title: string;
  text: string | null;
  image: string | null;
  link: string | null;
}

export interface AboutSection {
  slug: string;
  type: AboutSectionType;
  heading: string;
  subheading: string | null;
  body: string | null;
  cta: AboutCta | null;
  image: string | null;
  items: AboutItem[];
}

export interface AboutPublicResponse {
  sections: AboutSection[];
}

export interface AboutItemAdmin {
  id: number;
  section: string;
  title_en: string;
  title_bg: string | null;
  text_en: string | null;
  text_bg: string | null;
  image_id: string | null;
  image: string | null;
  link_href: string | null;
  sort_order: number;
  is_published: boolean;
  created_at: string;
  updated_at: string;
}

export interface AboutSectionAdmin {
  slug: string;
  type: AboutSectionType;
  heading_en: string;
  heading_bg: string | null;
  subheading_en: string | null;
  subheading_bg: string | null;
  body_en: string | null;
  body_bg: string | null;
  cta_label_en: string | null;
  cta_label_bg: string | null;
  cta_href: string | null;
  image_id: string | null;
  image: string | null;
  sort_order: number;
  is_published: boolean;
  created_at: string;
  updated_at: string;
  items: AboutItemAdmin[];
}

export interface AboutAdminResponse {
  sections: AboutSectionAdmin[];
}

// --- Site Media ---

export type SiteMediaKey =
  | "home_hero"
  | "home_hero_fallback"
  | "atelier_hero_fallback"
  | "atelier_story_fallback"
  | "atelier_atelier_fallback"
  | "atelier_collections_fallback"
  | "atelier_process_fallback"
  | "error_page_image"
  | "page_background";

export type SiteMediaMap = Record<SiteMediaKey, string | null>;

export interface SiteMediaAssetAdmin {
  key: SiteMediaKey;
  label: string;
  description: string;
  default_url: string | null;
  image_id: string | null;
  image_url: string | null;
  thumbnail_url: string | null;
  zoom_url: string | null;
  effective_url: string | null;
  updated_at: string;
}

export interface SiteMediaAdminResponse {
  assets: SiteMediaAssetAdmin[];
}

export interface PublicSiteMediaResponse {
  assets: SiteMediaMap;
}

export type PatchAboutSectionRequest = Partial<
  Pick<
    AboutSectionAdmin,
    | "heading_en"
    | "heading_bg"
    | "subheading_en"
    | "subheading_bg"
    | "body_en"
    | "body_bg"
    | "cta_label_en"
    | "cta_label_bg"
    | "cta_href"
  >
>;

export interface CreateAboutItemRequest {
  title_en: string;
  title_bg?: string | null;
  text_en?: string | null;
  text_bg?: string | null;
  link_href?: string | null;
  is_published?: boolean;
}

export type PatchAboutItemRequest = Partial<CreateAboutItemRequest>;

// --- FAQ ---

export interface FaqItemResponse {
  id: number;
  question: string;
  answer: string;
}

export interface FaqSectionResponse {
  slug: string;
  title: string;
  icon: string | null;
  items: FaqItemResponse[];
}

export interface FaqResponse {
  sections: FaqSectionResponse[];
}

export interface FaqItemAdminResponse {
  id: number;
  section: string;
  question_en: string;
  question_bg: string | null;
  answer_en: string;
  answer_bg: string | null;
  sort_order: number;
  is_published: boolean;
  created_at: string;
  updated_at: string;
}

export interface FaqSectionAdminResponse {
  slug: string;
  title_en: string;
  title_bg: string | null;
  icon: string | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
  items: FaqItemAdminResponse[];
}

export interface FaqAdminResponse {
  sections: FaqSectionAdminResponse[];
}

export interface CreateFaqItemRequest {
  section: string;
  question_en: string;
  answer_en: string;
  question_bg?: string | null;
  answer_bg?: string | null;
  sort_order?: number | null;
}

export interface UpdateFaqItemRequest {
  section?: string;
  question_en?: string;
  question_bg?: string | null;
  answer_en?: string;
  answer_bg?: string | null;
  sort_order?: number;
  is_published?: boolean;
}

export interface ReorderFaqItemsRequest {
  section: string;
  ordered_ids: number[];
}

export interface UpdateFaqSectionRequest {
  title_en?: string;
  title_bg?: string | null;
  icon?: string | null;
  sort_order?: number;
}

// --- Terms & Conditions ---

export interface TermsSectionResponse {
  id: string;
  title: string;
  nav: string;
  body: string[];
  model_form_title: string | null;
  model_form_intro: string | null;
  model_form_lines: string[] | null;
}

export interface TermsResponse {
  meta_title: string;
  meta_description: string;
  eyebrow: string;
  title: string;
  subtitle: string;
  last_updated: string;
  identity_intro: string;
  policy_links_title: string;
  privacy_link: string;
  cookies_link: string;
  nav_label: string;
  back_to_top: string;
  sections: TermsSectionResponse[];
}

export interface TermsPageAdminResponse {
  id: string;
  meta_title_en: string;
  meta_title_bg: string | null;
  meta_description_en: string;
  meta_description_bg: string | null;
  eyebrow_en: string;
  eyebrow_bg: string | null;
  title_en: string;
  title_bg: string | null;
  subtitle_en: string;
  subtitle_bg: string | null;
  last_updated_en: string;
  last_updated_bg: string | null;
  identity_intro_en: string;
  identity_intro_bg: string | null;
  policy_links_title_en: string;
  policy_links_title_bg: string | null;
  privacy_link_en: string;
  privacy_link_bg: string | null;
  cookies_link_en: string;
  cookies_link_bg: string | null;
  nav_label_en: string;
  nav_label_bg: string | null;
  back_to_top_en: string;
  back_to_top_bg: string | null;
  created_at: string;
  updated_at: string;
}

export interface TermsSectionAdminResponse {
  slug: string;
  title_en: string;
  title_bg: string | null;
  nav_en: string;
  nav_bg: string | null;
  body_en: string[];
  body_bg: string[] | null;
  model_form_title_en: string | null;
  model_form_title_bg: string | null;
  model_form_intro_en: string | null;
  model_form_intro_bg: string | null;
  model_form_lines_en: string[] | null;
  model_form_lines_bg: string[] | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface TermsAdminResponse {
  page: TermsPageAdminResponse;
  sections: TermsSectionAdminResponse[];
}

export type UpdateTermsPageRequest = Partial<
  Pick<
    TermsPageAdminResponse,
    | "meta_title_en"
    | "meta_title_bg"
    | "meta_description_en"
    | "meta_description_bg"
    | "eyebrow_en"
    | "eyebrow_bg"
    | "title_en"
    | "title_bg"
    | "subtitle_en"
    | "subtitle_bg"
    | "last_updated_en"
    | "last_updated_bg"
    | "identity_intro_en"
    | "identity_intro_bg"
    | "policy_links_title_en"
    | "policy_links_title_bg"
    | "privacy_link_en"
    | "privacy_link_bg"
    | "cookies_link_en"
    | "cookies_link_bg"
    | "nav_label_en"
    | "nav_label_bg"
    | "back_to_top_en"
    | "back_to_top_bg"
  >
>;

export type UpdateTermsSectionRequest = Partial<
  Pick<
    TermsSectionAdminResponse,
    | "title_en"
    | "title_bg"
    | "nav_en"
    | "nav_bg"
    | "body_en"
    | "body_bg"
    | "model_form_title_en"
    | "model_form_title_bg"
    | "model_form_intro_en"
    | "model_form_intro_bg"
    | "model_form_lines_en"
    | "model_form_lines_bg"
  >
>;

// --- Privacy Policy ---

export interface PrivacySectionResponse {
  id: string;
  title: string;
  nav: string;
  body: string[];
}

export interface PrivacyResponse {
  meta_title: string;
  meta_description: string;
  eyebrow: string;
  title: string;
  subtitle: string;
  last_updated: string;
  controller_title: string;
  sections: PrivacySectionResponse[];
}

export interface PrivacyPageAdminResponse {
  id: string;
  meta_title_en: string;
  meta_title_bg: string | null;
  meta_description_en: string;
  meta_description_bg: string | null;
  eyebrow_en: string;
  eyebrow_bg: string | null;
  title_en: string;
  title_bg: string | null;
  subtitle_en: string;
  subtitle_bg: string | null;
  last_updated_en: string;
  last_updated_bg: string | null;
  controller_title_en: string;
  controller_title_bg: string | null;
  created_at: string;
  updated_at: string;
}

export interface PrivacySectionAdminResponse {
  slug: string;
  title_en: string;
  title_bg: string | null;
  nav_en: string;
  nav_bg: string | null;
  body_en: string[];
  body_bg: string[] | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface PrivacyAdminResponse {
  page: PrivacyPageAdminResponse;
  sections: PrivacySectionAdminResponse[];
}

export type UpdatePrivacyPageRequest = Partial<
  Pick<
    PrivacyPageAdminResponse,
    | "meta_title_en"
    | "meta_title_bg"
    | "meta_description_en"
    | "meta_description_bg"
    | "eyebrow_en"
    | "eyebrow_bg"
    | "title_en"
    | "title_bg"
    | "subtitle_en"
    | "subtitle_bg"
    | "last_updated_en"
    | "last_updated_bg"
    | "controller_title_en"
    | "controller_title_bg"
  >
>;

export type UpdatePrivacySectionRequest = Partial<
  Pick<
    PrivacySectionAdminResponse,
    "title_en" | "title_bg" | "nav_en" | "nav_bg" | "body_en" | "body_bg"
  >
>;

// --- Cookie Policy ---

export interface CookieHeadersResponse {
  name: string;
  purpose: string;
  type: string;
  duration: string;
}

export interface CookieInventoryResponse {
  name: string;
  purpose: string;
  type: string;
  duration: string;
}

export interface CookieSectionResponse {
  id: string;
  title: string;
  body: string[];
}

export interface CookiesResponse {
  meta_title: string;
  meta_description: string;
  eyebrow: string;
  title: string;
  subtitle: string;
  last_updated: string;
  inventory_title: string;
  headers: CookieHeadersResponse;
  cookies: CookieInventoryResponse[];
  sections: CookieSectionResponse[];
}

export interface CookiesPageAdminResponse {
  id: string;
  meta_title_en: string;
  meta_title_bg: string | null;
  meta_description_en: string;
  meta_description_bg: string | null;
  eyebrow_en: string;
  eyebrow_bg: string | null;
  title_en: string;
  title_bg: string | null;
  subtitle_en: string;
  subtitle_bg: string | null;
  last_updated_en: string;
  last_updated_bg: string | null;
  inventory_title_en: string;
  inventory_title_bg: string | null;
  header_name_en: string;
  header_name_bg: string | null;
  header_purpose_en: string;
  header_purpose_bg: string | null;
  header_type_en: string;
  header_type_bg: string | null;
  header_duration_en: string;
  header_duration_bg: string | null;
  created_at: string;
  updated_at: string;
}

export interface CookieInventoryAdminResponse {
  name: string;
  purpose_en: string;
  purpose_bg: string | null;
  type_en: string;
  type_bg: string | null;
  duration_en: string;
  duration_bg: string | null;
  source: string;
  first_seen_at: string | null;
  last_seen_at: string | null;
  last_audited_at: string | null;
  observed_on: string[];
  is_active: boolean;
  auto_detected: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface CookieSectionAdminResponse {
  slug: string;
  title_en: string;
  title_bg: string | null;
  body_en: string[];
  body_bg: string[] | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface CookiesAdminResponse {
  page: CookiesPageAdminResponse;
  cookies: CookieInventoryAdminResponse[];
  sections: CookieSectionAdminResponse[];
}

export type UpdateCookiesPageRequest = Partial<
  Pick<
    CookiesPageAdminResponse,
    | "meta_title_en"
    | "meta_title_bg"
    | "meta_description_en"
    | "meta_description_bg"
    | "eyebrow_en"
    | "eyebrow_bg"
    | "title_en"
    | "title_bg"
    | "subtitle_en"
    | "subtitle_bg"
    | "last_updated_en"
    | "last_updated_bg"
    | "inventory_title_en"
    | "inventory_title_bg"
    | "header_name_en"
    | "header_name_bg"
    | "header_purpose_en"
    | "header_purpose_bg"
    | "header_type_en"
    | "header_type_bg"
    | "header_duration_en"
    | "header_duration_bg"
  >
>;

export type UpdateCookieInventoryRequest = Partial<
  Pick<
    CookieInventoryAdminResponse,
    | "purpose_en"
    | "purpose_bg"
    | "type_en"
    | "type_bg"
    | "duration_en"
    | "duration_bg"
  >
>;

export type UpdateCookieSectionRequest = Partial<
  Pick<
    CookieSectionAdminResponse,
    "title_en" | "title_bg" | "body_en" | "body_bg"
  >
>;

export interface AdminTaxonomyTerm {
  slug: string;
  name_en: string;
  name_bg: string | null;
  sort_order: number;
  is_active: boolean;
  product_count: number;
  created_at: string;
  updated_at: string;
}

export interface CreateTaxonomyTermRequest {
  name_en: string;
  name_bg?: string | null;
  sort_order?: number;
}

export interface UpdateTaxonomyTermRequest {
  name_en?: string;
  name_bg?: string | null;
  sort_order?: number;
  is_active?: boolean;
}

// --- Cart ---

export interface CartItemResponse {
  product_id: string;
  product: ProductResponse;
  quantity: number;
  added_at: string;
}

export interface UnavailableCartItem {
  product_id: string;
  product_name: string;
  reason: string;
}

export interface CartResponse {
  items: CartItemResponse[];
  total_cents: number;
  item_count: number;
  unavailable_items: UnavailableCartItem[];
}

// --- Orders ---

export type OrderStatus =
  | "pending"
  | "confirmed"
  | "shipped"
  | "delivered"
  | "return_in_transit"
  | "returned"
  | "cancelled";

export type PaymentMethod = "cod" | "card" | "bank_transfer";
export type PaymentStatus =
  | "pending"
  | "paid"
  | "cod_pending"
  | "failed"
  | "review_required"
  | "refund_pending"
  | "partially_refunded"
  | "refunded"
  | "dispute_open"
  | "dispute_won"
  | "dispute_lost";

export interface OrderItemResponse {
  product_id: string;
  product_name: string;
  price_cents: number;
  quantity: number;
}

export interface AdminOrderItemResponse extends OrderItemResponse {
  inventory_mode?: "legacy" | "fallback" | "ledger_managed";
  ledger_managed?: boolean;
  stock_issue_status?: "legacy" | "issued" | "missing" | "reversed";
  inventory_movement_ids?: string[];
  source_movement_id?: string | null;
  finished_batch_id?: string | null;
  finished_batch_number?: string | null;
  cogs_row_id?: string | null;
  cogs_readiness?: string;
  valuation_method?: string | null;
  source_valuation_layer_id?: string | null;
  inventory_exception_ids?: string[];
  inventory_exception_count?: number;
}

export interface InvoiceProfile {
  customer_type: "individual" | "business";
  legal_name: string;
  vat_identification_number?: string | null;
  business_registration_number?: string | null;
  billing_address: string;
  billing_country: string;
  invoice_email: string;
  purchase_reference_note?: string | null;
}

export type AccountingClassificationState =
  | "unreviewed"
  | "domestic_default"
  | "business_vat_id_provided"
  | "cross_border_candidate"
  | "manual_review_required";

export type AccountingReadinessStatus =
  "unreviewed" | "ready" | "review_required" | "blocked";

export type AccountingDocumentReferenceStatus =
  "not_required" | "missing" | "recorded" | "review_required";

export type AccountingReconciliationStatus =
  | "not_applicable"
  | "pending"
  | "matched"
  | "mismatch"
  | "unmatched"
  | "review_required";

export type CodSettlementStatus =
  "not_applicable" | "pending" | "settled" | "mismatch";

export interface AccountingFinanceHubLinks {
  period_id?: string | null;
  period_href?: string | null;
  exceptions_href?: string | null;
  ledger_href?: string | null;
  documents_href?: string | null;
}

export interface OrderInventoryContext {
  valuation_method?: string | null;
  official_cogs_required?: boolean;
  missing_inventory_movement_count?: number;
  missing_cogs_count?: number;
  inventory_exception_count?: number;
  inventory_exception_ids?: string[];
  links?: Record<string, string | null> | null;
}

export interface OrderResponse {
  id: string;
  internal_sequence?: number | null;
  order_number?: string | null;
  status: OrderStatus;
  payment_method: PaymentMethod;
  payment_status: PaymentStatus;
  reserved_until?: string | null;
  paid_at?: string | null;
  collected_at?: string | null;
  payment_return_token?: string | null;
  stripe_checkout_session_id?: string | null;
  stripe_checkout_url: string | null;
  invoice_profile?: InvoiceProfile | null;
  accounting_currency?: string;
  seller_legal_profile_version_id?: number | null;
  vat_fiscal_settings_version_id?: number | null;
  accounting_classification_state?: AccountingClassificationState;
  accounting_snapshot?: Record<string, unknown> | null;
  accounting_readiness_status?: AccountingReadinessStatus;
  finance_period_id?: string | null;
  document_reference_status?: AccountingDocumentReferenceStatus;
  payment_reconciliation_status?: AccountingReconciliationStatus;
  payout_reconciliation_status?: AccountingReconciliationStatus;
  cod_settlement_status?: CodSettlementStatus;
  blocking_exception_count?: number;
  finance_hub_links?: AccountingFinanceHubLinks | null;
  analytics_consent?: boolean;
  items_total_cents: number;
  shipping_cents: number;
  shipping_price_source: ShippingPriceSource;
  shipping_is_fallback: boolean;
  total_cents: number;
  customer_email: string;
  customer_name: string | null;
  delivery_method: "office" | "door" | null;
  delivery_courier: "speedy" | "econt" | null;
  delivery_details: DeliveryOffice | DeliveryDoor | null;
  notes: string | null;
  items: OrderItemResponse[];
  tracking_number: string | null;
  tracking_carrier: string | null;
  tracking_url: string | null;
  courier_status: string | null;
  label_url: string | null;
  courier_provider?: string | null;
  courier_order_id?: string | null;
  courier_shipment_number?: string | null;
  courier_label_url?: string | null;
  courier_label_created_at?: string | null;
  courier_sync_status?: string | null;
  courier_last_error?: string | null;
  courier_last_synced_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface OrderListResponse {
  items: OrderResponse[];
  total: number;
  page: number;
  limit: number;
}

export type CustomerOrderView = "all" | "active" | "needs_action" | "delivered";
export type CustomerOrderDateRange = "all" | "last_30_days" | "last_6_months";
export type CustomerOrderSort = "newest" | "oldest" | "highest";

export interface CustomerOrderFilters {
  q?: string;
  view?: CustomerOrderView;
  date_range?: CustomerOrderDateRange;
  sort?: CustomerOrderSort;
}

// --- Accounting & Finance Hub ---

export type VatMode =
  "unknown" | "not_registered" | "registered" | "oss_registered";
export type OssMode =
  "not_applicable" | "not_registered" | "registered" | "review_required";
export type FiscalDocumentMode =
  | "external_reference"
  | "app_invoice_reference"
  | "fiscal_device_reference"
  | "alternative_sales_document"
  | "not_configured";
export type CloseBehavior = "warn" | "block";
export type CostingBasis =
  "manual_snapshot" | "recipe_bom" | "imported_estimate";
export type MissingCostPolicy = "none" | "warning" | "blocking";
export type FinancePeriodStatus =
  "open" | "review" | "closed" | "exported" | "accepted" | "reopened";
export type FinanceExceptionStatus = "open" | "resolved" | "waived";
export type FinanceExceptionSeverity = "blocking" | "warning";
export type AccountingLedgerName =
  | "sales"
  | "payments"
  | "stripe_payouts"
  | "cod_settlements"
  | "refunds"
  | "courier_claims"
  | "return_reasons"
  | "inventory_adjustments"
  | "inventory_movements"
  | "documents"
  | "expenses"
  | "product_costs";
export type AccountingDocumentType =
  | "invoice"
  | "credit_note"
  | "fiscal_receipt"
  | "alternative_sales_document"
  | "external_document";
export type AccountingDocumentStatus =
  "draft" | "recorded" | "void" | "corrected" | "missing" | "review_required";
export type ExpensePaymentStatus =
  "unpaid" | "paid" | "partially_paid" | "reimbursed" | "cancelled";
export type ExpenseReviewStatus =
  "unreviewed" | "reviewed" | "missing_document" | "waived" | "rejected";
export type ProductCostReviewStatus =
  "estimate" | "reviewed" | "accountant_reviewed" | "archived";
export type ProductCostComponentType =
  "material" | "packaging" | "labor" | "overhead" | "waste" | "other";
export type AdminOrderAccountingFilter =
  | "missing_document_reference"
  | "unresolved_exception"
  | "payout_mismatch"
  | "cod_settlement_pending"
  | "refund_document_missing"
  | "vat_review_required"
  | "missing_batch_assignment"
  | "missing_inventory_movement"
  | "missing_cogs_row"
  | "valuation_exception"
  | "return_inventory_review_pending";

// --- Inventory, recipes, production, valuation ---

export type MaterialUom =
  "g" | "kg" | "ml" | "l" | "piece" | "pcs" | "unit" | "m" | "cm";
export type MaterialMovementType =
  "adjustment" | "spoilage" | "write_off" | "stock_count_correction";
export type InventoryReviewState =
  "unreviewed" | "reviewed" | "estimate" | "official" | "reversed";
export type MaterialReviewState =
  "draft" | "needs_review" | "reviewed" | "rejected";
export type RecipeStatus = "draft" | "active" | "archived";
export type RecipeReviewState =
  "estimate" | "reviewed" | "accountant_reviewed" | "invalid";
export type QuantityBasis = "per_unit" | "per_batch";
export type ProductionBatchStatus = "draft" | "produced" | "cancelled";
export type ValuationMethod = "weighted_average" | "fifo";
export type CogsDateBasis =
  | "order_date"
  | "payment_date"
  | "shipment_date"
  | "delivery_date"
  | "period_close";

export interface InventoryExceptionResponse {
  id: string;
  exception_type: string;
  severity: FinanceExceptionSeverity;
  target_type?: string | null;
  target_id?: string | null;
  source_type?: string | null;
  source_id?: string | null;
  status: FinanceExceptionStatus;
  message: string;
  created_at: string;
}

export interface InventoryMovementResponse {
  id: string;
  item_type: "material" | "finished_good";
  item_id: string;
  movement_type: string;
  quantity_delta: number;
  uom: string;
  source_type?: string | null;
  source_id?: string | null;
  material_lot_id?: string | null;
  actor_user_id?: string | null;
  actor_email?: string | null;
  reason?: string | null;
  notes?: string | null;
  review_state: InventoryReviewState;
  occurred_at: string;
  created_at: string;
}

export interface InventoryMovementListResponse {
  movements: InventoryMovementResponse[];
  total: number;
}

export interface MaterialRequest {
  sku?: string | null;
  name: string;
  category?: string;
  stock_uom: MaterialUom;
  purchase_uom?: MaterialUom | null;
  purchase_to_stock_factor?: number | null;
  preferred_supplier_name?: string | null;
  preferred_supplier_sku?: string | null;
  reorder_threshold?: number | null;
  active?: boolean;
  lot_tracked?: boolean;
  expiry_tracked?: boolean;
  evidence_required?: boolean;
  notes?: string | null;
}

export type MaterialUpdateRequest = Partial<MaterialRequest>;

export interface MaterialResponse {
  id: string;
  sku?: string | null;
  name: string;
  category: string;
  stock_uom: string;
  purchase_uom?: string | null;
  purchase_to_stock_factor?: number | null;
  preferred_supplier_name?: string | null;
  preferred_supplier_sku?: string | null;
  reorder_threshold?: number | null;
  active: boolean;
  lot_tracked: boolean;
  expiry_tracked: boolean;
  evidence_required: boolean;
  on_hand_quantity: number;
  reorder_status: "ok" | "below_threshold" | "not_configured" | "inactive";
  open_exception_count: number;
  latest_movement_at?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface MaterialLotResponse {
  id: string;
  material_id: string;
  receipt_id?: string | null;
  supplier_lot?: string | null;
  expiry_date?: string | null;
  use_by_date?: string | null;
  received_quantity: number;
  stock_uom: string;
  remaining_quantity_snapshot?: number | null;
  unit_cost_amount?: string | null;
  currency: string;
  supplier_name?: string | null;
  review_state: MaterialReviewState;
  lot_status: "ok" | "near_expiry" | "expired" | "unknown";
  created_at: string;
  updated_at: string;
}

export interface MaterialDetailResponse extends MaterialResponse {
  lots: MaterialLotResponse[];
  recent_movements: InventoryMovementResponse[];
  exceptions: InventoryExceptionResponse[];
}

export interface MaterialListResponse {
  materials: MaterialResponse[];
  total: number;
}

export interface MaterialLotListResponse {
  lots: MaterialLotResponse[];
  total: number;
}

export interface MaterialReceiptRequest {
  receipt_date?: string | null;
  quantity: number;
  uom: MaterialUom;
  unit_cost_amount?: string | null;
  total_cost_cents?: number | null;
  currency?: string;
  supplier_name?: string | null;
  supplier_lot?: string | null;
  expiry_date?: string | null;
  use_by_date?: string | null;
  expense_evidence_id?: string | null;
  document_reference?: string | null;
  notes?: string | null;
}

export interface MaterialReceiptResponse extends MaterialReceiptRequest {
  id: string;
  material_id: string;
  receipt_date: string;
  quantity: number;
  uom: MaterialUom;
  stock_quantity: number;
  stock_uom: string;
  currency: string;
  review_state: MaterialReviewState;
  movement_id?: string | null;
  lot_id?: string | null;
  exceptions: InventoryExceptionResponse[];
  created_at: string;
  updated_at: string;
}

export interface MaterialAdjustmentRequest {
  movement_type: MaterialMovementType;
  quantity_delta: number;
  uom?: MaterialUom | null;
  reason: string;
  notes?: string | null;
  occurred_at?: string | null;
}

export interface RecipeComponentRequest {
  material_id: string;
  quantity: number;
  uom: MaterialUom;
  quantity_basis?: QuantityBasis;
  wastage_percent?: number;
  required?: boolean;
  substitute_group?: string | null;
  sort_order?: number;
}

export interface RecipeVersionRequest {
  product_id: string;
  version_label: string;
  effective_date: string;
  output_quantity: number;
  output_uom?: string;
  notes?: string | null;
  components?: RecipeComponentRequest[];
}

export type RecipeVersionUpdateRequest = Partial<
  Omit<RecipeVersionRequest, "product_id">
>;

export interface RecipeReviewRequest {
  review_state?: RecipeReviewState;
  review_note?: string | null;
}

export interface RecipeCostSnapshotRequest {
  labor_cost_cents?: number;
  overhead_cost_cents?: number;
  currency?: string;
}

export interface RecipeDiagnosticResponse {
  code: string;
  severity: FinanceExceptionSeverity;
  message: string;
  target_type?: string | null;
  target_id?: string | null;
}

export interface RecipeComponentResponse {
  id: string;
  recipe_version_id: string;
  material_id: string;
  material_name?: string | null;
  material_active?: boolean | null;
  material_category?: string | null;
  quantity: number;
  uom: string;
  quantity_basis: QuantityBasis;
  wastage_percent: number;
  required: boolean;
  substitute_group?: string | null;
  sort_order: number;
  review_state: "valid" | "warning" | "invalid";
  created_at: string;
  updated_at: string;
}

export interface RecipeCostSnapshotResponse {
  id: string;
  recipe_version_id: string;
  currency: string;
  material_cost_cents: number;
  packaging_cost_cents: number;
  labor_cost_cents: number;
  overhead_cost_cents: number;
  batch_cost_cents: number;
  expected_unit_cost_cents: number;
  source_cost_references_json?: string | null;
  missing_cost_count: number;
  estimate_label: string;
  review_state: "estimate" | "incomplete" | "reviewed" | "accountant_reviewed";
  calculated_at: string;
  created_by_admin_id?: string | null;
  created_at: string;
}

export interface RecipeVersionResponse {
  id: string;
  product_id: string;
  version_label: string;
  status: RecipeStatus;
  effective_date: string;
  output_quantity: number;
  output_uom: string;
  review_state: RecipeReviewState;
  accountant_reviewed: boolean;
  reviewed_by_admin_id?: string | null;
  reviewed_at?: string | null;
  notes?: string | null;
  created_by_admin_id?: string | null;
  updated_by_admin_id?: string | null;
  components: RecipeComponentResponse[];
  latest_cost_snapshot?: RecipeCostSnapshotResponse | null;
  diagnostics: RecipeDiagnosticResponse[];
  created_at: string;
  updated_at: string;
}

export interface RecipeVersionListResponse {
  recipes: RecipeVersionResponse[];
  total: number;
}

export interface RecipeDiagnosticsListResponse {
  diagnostics: RecipeDiagnosticResponse[];
}

export interface ProductionBatchRequest {
  batch_number: string;
  product_id: string;
  recipe_version_id?: string | null;
  planned_output_quantity: number;
  output_uom?: string;
  production_date: string;
  ready_date?: string | null;
  notes?: string | null;
}

export interface ProductionBatchUpdateRequest {
  planned_output_quantity?: number;
  production_date?: string;
  ready_date?: string | null;
  notes?: string | null;
}

export interface ProductionBatchActualConsumptionRequest {
  batch_consumption_id?: string | null;
  material_id: string;
  material_lot_id?: string | null;
  actual_quantity: number;
  waste_quantity?: number;
  uom?: MaterialUom | null;
}

export interface ProductionBatchPostRequest {
  actual_output_quantity: number;
  actual_consumption?: ProductionBatchActualConsumptionRequest[];
  variance_tolerance_percent?: number;
  notes?: string | null;
}

export interface ProductionBatchCorrectionRequest {
  item_type: "material" | "finished_good";
  item_id: string;
  quantity_delta: number;
  uom: string;
  reason: string;
  notes?: string | null;
}

export interface ProductionBatchConsumptionResponse {
  id: string;
  production_batch_id: string;
  recipe_component_id?: string | null;
  material_id: string;
  material_name?: string | null;
  material_lot_id?: string | null;
  expected_quantity?: number | null;
  actual_quantity?: number | null;
  waste_quantity: number;
  uom: string;
  unit_cost_amount?: string | null;
  currency: string;
  movement_id?: string | null;
  review_state: MaterialReviewState;
  created_at: string;
  updated_at: string;
}

export interface ProductionBatchOutputResponse {
  id: string;
  production_batch_id: string;
  product_id: string;
  batch_number: string;
  quantity: number;
  uom: string;
  unit_cost_amount?: string | null;
  currency: string;
  movement_id?: string | null;
  remaining_quantity_snapshot?: number | null;
  valuation_review_state: "estimate" | "reviewed" | "official";
  created_at: string;
}

export interface ProductionBatchResponse {
  id: string;
  batch_number: string;
  product_id: string;
  recipe_version_id?: string | null;
  planned_output_quantity: number;
  actual_output_quantity?: number | null;
  output_uom: string;
  status: ProductionBatchStatus;
  production_date: string;
  ready_date?: string | null;
  cost_snapshot_id?: string | null;
  variance_review_state: "not_reviewed" | "warning" | "reviewed";
  actor_user_id?: string | null;
  notes?: string | null;
  consumption: ProductionBatchConsumptionResponse[];
  outputs: ProductionBatchOutputResponse[];
  exceptions: InventoryExceptionResponse[];
  created_by_admin_id?: string | null;
  updated_by_admin_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProductionBatchListResponse {
  batches: ProductionBatchResponse[];
  total: number;
}

export interface ProductionTraceabilityResponse extends ProductionBatchResponse {
  source_movements: InventoryMovementResponse[];
  finished_movements: InventoryMovementResponse[];
  linked_order_lines: Record<string, unknown>[];
}

export interface InventoryValuationSettingsRequest {
  ledger_mode?: "legacy" | "setup" | "ledger_managed";
  valuation_enabled?: boolean;
  valuation_method?: ValuationMethod;
  effective_date: string;
  cogs_date_basis?: CogsDateBasis;
  rounding_policy?: "half_up_2dp" | "half_up_4dp";
  missing_cost_behavior?: "allow_estimate" | "warn" | "block_official";
  included_cost_components?: Record<string, unknown> | null;
  write_off_mapping?: Record<string, unknown> | null;
  currency?: string;
  accountant_reviewed?: boolean;
  reviewed_by_name?: string | null;
  review_notes?: string | null;
}

export interface InventoryValuationSettingsResponse {
  id: string;
  ledger_mode: "legacy" | "setup" | "ledger_managed";
  valuation_enabled: boolean;
  valuation_method: ValuationMethod;
  effective_date: string;
  cogs_date_basis: CogsDateBasis;
  rounding_policy: string;
  missing_cost_behavior: string;
  included_cost_components?: Record<string, unknown> | null;
  write_off_mapping?: Record<string, unknown> | null;
  currency: string;
  settings_version: number;
  accountant_reviewed: boolean;
  reviewed_by_admin_id?: string | null;
  reviewed_by_name?: string | null;
  reviewed_at?: string | null;
  review_notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface OpeningBalanceRequest {
  item_type: "material" | "finished_good";
  item_id: string;
  quantity: number;
  uom: string;
  unit_value_amount?: string | null;
  total_value_cents?: number | null;
  reviewed?: boolean;
  notes?: string | null;
}

export interface ValuationLayerResponse {
  id: string;
  movement_id?: string | null;
  item_type: "material" | "finished_good";
  item_id: string;
  quantity: number;
  unit_value_amount?: string | null;
  total_value_cents?: number | null;
  currency: string;
  valuation_method: ValuationMethod | "revaluation";
  source_type?: string | null;
  source_id?: string | null;
  valuation_date: string;
  review_state: "estimate" | "reviewed" | "official" | "reversed";
  method_metadata_json?: string | null;
  reversal_layer_id?: string | null;
  created_at: string;
}

export interface ValuationLayerListResponse {
  layers: ValuationLayerResponse[];
  total: number;
}

export interface CogsLedgerResponse {
  id: string;
  order_id?: string | null;
  order_number?: string | null;
  order_item_key?: string | null;
  product_id?: string | null;
  quantity_sold: number;
  cogs_date: string;
  unit_cost_amount?: string | null;
  total_cost_cents: number;
  currency: string;
  valuation_method: ValuationMethod;
  source_movement_id?: string | null;
  source_valuation_layer_id?: string | null;
  source_finished_batch_id?: string | null;
  review_state: "estimate" | "reviewed" | "official" | "reversed";
  reversal_cogs_id?: string | null;
  created_at: string;
}

export interface CogsLedgerListResponse {
  rows: CogsLedgerResponse[];
  total: number;
}

export interface InventoryClosePreviewResponse {
  period_start: string;
  period_end: string;
  currency: string;
  valuation_method: ValuationMethod;
  official: boolean;
  opening_value_cents: number;
  receipts_value_cents: number;
  production_consumption_value_cents: number;
  finished_output_value_cents: number;
  sales_cogs_value_cents: number;
  returns_value_cents: number;
  adjustments_value_cents: number;
  ending_value_cents: number;
  exception_count: number;
  policy_snapshot: Record<string, unknown>;
}

export interface LegalIdentityResponse {
  trading_name: string;
  legal_name: string;
  country: string;
  geographic_address: string;
  contact_email: string;
  registration_number: string;
  vat_number: string;
  responsible_party_name: string;
  responsible_party_address: string;
  responsible_party_email: string;
}

export interface SellerLegalProfileRequest {
  effective_date: string;
  reviewed?: boolean;
  company_display_name?: string | null;
  legal_name?: string | null;
  uic_eik?: string | null;
  vat_identification_number?: string | null;
  registered_address?: Record<string, unknown> | null;
  contact_email?: string | null;
  bank_details?: Record<string, unknown> | null;
  default_currency?: string;
}

export interface SellerLegalProfileResponse extends SellerLegalProfileRequest {
  id: number;
  reviewed: boolean;
  default_currency: string;
  bank_details_configured: boolean;
  created_by_admin_id?: string | null;
  created_at: string;
}

export interface VatFiscalSettingsRequest {
  effective_date: string;
  reviewed?: boolean;
  vat_mode?: VatMode;
  oss_mode?: OssMode;
  default_domestic_vat_treatment?: string | null;
  fiscal_document_mode?: FiscalDocumentMode;
  document_rules?: Record<string, unknown> | null;
  threshold_warnings?: Record<string, unknown> | null;
  tolerance_cents?: number;
  warning_text?: string | null;
}

export interface VatFiscalSettingsResponse extends VatFiscalSettingsRequest {
  id: number;
  reviewed: boolean;
  vat_mode: VatMode;
  oss_mode: OssMode;
  fiscal_document_mode: FiscalDocumentMode;
  tolerance_cents: number;
  created_by_admin_id?: string | null;
  created_at: string;
}

export interface CategoryMappingRequest {
  category_code?: string | null;
  category_label: string;
  is_required?: boolean;
  reviewed?: boolean;
}

export interface CategoryMappingResponse extends CategoryMappingRequest {
  id: number;
  mapping_key: string;
  is_required: boolean;
  reviewed: boolean;
  created_at: string;
  updated_at: string;
}

export interface ExportSchemaSettingsRequest {
  workbook_language?: "en" | "bg";
  date_format?: string;
  decimal_separator?: "." | ",";
  default_period_range?: string;
  included_tabs?: string[];
  custom_columns?: Record<string, unknown> | null;
  reviewed?: boolean;
}

export interface ExportSchemaSettingsResponse extends ExportSchemaSettingsRequest {
  id: string;
  workbook_language: "en" | "bg";
  date_format: string;
  decimal_separator: "." | ",";
  default_period_range: string;
  included_tabs: string[];
  reviewed: boolean;
  updated_at: string;
}

export interface ExpenseEvidenceSettingsRequest {
  required_document_categories?: string[];
  allowed_payment_statuses?: string[];
  default_category_mappings?: Record<string, string>;
  close_behavior?: CloseBehavior;
  reviewed?: boolean;
}

export interface ExpenseEvidenceSettingsResponse extends ExpenseEvidenceSettingsRequest {
  id: string;
  required_document_categories: string[];
  allowed_payment_statuses: string[];
  default_category_mappings: Record<string, string>;
  close_behavior: CloseBehavior;
  reviewed: boolean;
  updated_at: string;
}

export interface ProductCostSettingsRequest {
  enabled?: boolean;
  costing_basis?: CostingBasis;
  include_labor?: boolean;
  include_overhead?: boolean;
  missing_cost_policy?: MissingCostPolicy;
  reviewed?: boolean;
  estimate_label?: string;
}

export interface ProductCostSettingsResponse extends ProductCostSettingsRequest {
  id: string;
  enabled: boolean;
  costing_basis: CostingBasis;
  include_labor: boolean;
  include_overhead: boolean;
  missing_cost_policy: MissingCostPolicy;
  reviewed: boolean;
  estimate_label: string;
  updated_at: string;
}

export interface AccountingSetupException {
  code: string;
  severity: FinanceExceptionSeverity;
  message: string;
}

export interface AccountingConfigurationResponse {
  seller_profile: SellerLegalProfileResponse | null;
  vat_fiscal_settings: VatFiscalSettingsResponse | null;
  category_mappings: CategoryMappingResponse[];
  export_schema: ExportSchemaSettingsResponse;
  expense_settings: ExpenseEvidenceSettingsResponse;
  product_cost_settings: ProductCostSettingsResponse;
  setup_exceptions: AccountingSetupException[];
}

export interface FinancePeriodCreateRequest {
  period_start: string;
  period_end: string;
  currency?: string;
}

export interface FinancePeriodActionRequest {
  reason?: string | null;
  accountant_name?: string | null;
  accountant_reference?: string | null;
}

export interface FinancePeriodResponse {
  id: string;
  period_start: string;
  period_end: string;
  currency: string;
  status: FinancePeriodStatus;
  summary_totals: Record<string, unknown> | null;
  open_exception_count: number;
  blocking_exception_count: number;
  created_by_admin_id?: string | null;
  updated_by_admin_id?: string | null;
  closed_by_admin_id?: string | null;
  closed_at?: string | null;
  accepted_at?: string | null;
  reopened_from_export_id?: string | null;
  reopen_reason?: string | null;
  created_at: string;
  updated_at: string;
}

export interface FinancePeriodListResponse {
  items: FinancePeriodResponse[];
  total: number;
}

export interface FinanceExceptionResponse {
  id: string;
  period_id?: string | null;
  exception_type: string;
  severity: FinanceExceptionSeverity;
  target_type?: string | null;
  target_id?: string | null;
  status: FinanceExceptionStatus;
  message: string;
  details?: Record<string, unknown> | null;
  waived_by_admin_id?: string | null;
  waiver_reason?: string | null;
  waived_at?: string | null;
  resolved_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface FinanceExceptionActionRequest {
  reason: string;
}

export interface FinanceExceptionListResponse {
  items: FinanceExceptionResponse[];
  total: number;
}

export interface AccountingLedgerResponse {
  period_id: string;
  ledger: AccountingLedgerName;
  date_basis: string;
  rows: Record<string, unknown>[];
  totals: Record<string, number>;
  total: number;
  page: number;
  limit: number;
}

export interface StripePayoutImportStatusResponse {
  total_rows: number;
  matched: number;
  unmatched: number;
  mismatched: number;
  duplicate: number;
  ignored: number;
  latest_imported_at?: string | null;
}

export interface StripeBalanceImportResponse {
  imported: number;
  updated: number;
  duplicate_provider_ids: number;
  matched: number;
  unmatched: number;
  mismatched: number;
  ignored: number;
  errors: string[];
}

export interface AccountingDocumentRequest {
  document_type: AccountingDocumentType;
  source_system?: string;
  document_number?: string | null;
  issue_date: string;
  order_id?: string | null;
  refund_id?: string | null;
  period_id?: string | null;
  currency?: string;
  net_amount_cents?: number | null;
  tax_amount_cents?: number | null;
  gross_amount_cents?: number | null;
  vat_summary?: Record<string, unknown> | null;
  original_document_id?: string | null;
  file_reference?: string | null;
  status?: AccountingDocumentStatus;
  notes?: string | null;
}

export interface AccountingDocumentResponse extends AccountingDocumentRequest {
  id: string;
  source_system: string;
  currency: string;
  status: AccountingDocumentStatus;
  created_by_admin_id?: string | null;
  updated_by_admin_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AccountingDocumentListResponse {
  items: AccountingDocumentResponse[];
  total: number;
}

export interface ExpenseEvidenceRequest {
  supplier_name: string;
  supplier_identifier?: string | null;
  document_number?: string | null;
  document_date?: string | null;
  purchase_date: string;
  payment_date?: string | null;
  payment_status?: ExpensePaymentStatus;
  category_key?: string | null;
  net_amount_cents?: number | null;
  tax_amount_cents?: number;
  gross_amount_cents: number;
  currency?: string;
  attachment_reference?: string | null;
  linked_product_id?: string | null;
  linked_material_name?: string | null;
  linked_courier?: "speedy" | "econt" | null;
  linked_order_id?: string | null;
  review_status?: ExpenseReviewStatus;
  notes?: string | null;
}

export interface ExpenseEvidenceResponse extends ExpenseEvidenceRequest {
  id: string;
  payment_status: ExpensePaymentStatus;
  tax_amount_cents: number;
  currency: string;
  review_status: ExpenseReviewStatus;
  created_by_admin_id?: string | null;
  updated_by_admin_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExpenseEvidenceListResponse {
  items: ExpenseEvidenceResponse[];
  total: number;
}

export interface ExpensePaymentStatusRequest {
  payment_status: ExpensePaymentStatus;
  payment_date?: string | null;
  reason: string;
}

export interface ProductCostComponentRequest {
  component_type: ProductCostComponentType;
  description: string;
  quantity?: number | null;
  unit?: string | null;
  unit_cost_cents?: number | null;
  total_cost_cents: number;
  source_expense_id?: string | null;
}

export interface ProductCostComponentResponse extends ProductCostComponentRequest {
  id: string;
  cost_version_id: string;
  created_at: string;
}

export interface ProductCostVersionRequest {
  product_id?: string | null;
  sku?: string | null;
  product_name: string;
  effective_date: string;
  costing_basis?: CostingBasis;
  material_cost_cents?: number;
  packaging_cost_cents?: number;
  labor_cost_cents?: number;
  overhead_cost_cents?: number;
  estimated_unit_cost_cents?: number | null;
  currency?: string;
  reviewed?: boolean;
  accountant_reviewed?: boolean;
  review_status?: ProductCostReviewStatus;
  source_expense_ids?: string[];
  notes?: string | null;
  components?: ProductCostComponentRequest[];
}

export interface ProductCostVersionResponse extends ProductCostVersionRequest {
  id: string;
  estimated_unit_cost_cents: number;
  costing_basis: CostingBasis;
  material_cost_cents: number;
  packaging_cost_cents: number;
  labor_cost_cents: number;
  overhead_cost_cents: number;
  currency: string;
  reviewed: boolean;
  accountant_reviewed: boolean;
  review_status: ProductCostReviewStatus;
  source_expense_ids: string[];
  components: ProductCostComponentResponse[];
  created_by_admin_id?: string | null;
  updated_by_admin_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProductCostVersionListResponse {
  items: ProductCostVersionResponse[];
  total: number;
}

export interface MissingProductCostDiagnostic {
  order_id: string;
  order_number?: string | null;
  order_date: string;
  product_id: string;
  product_name: string;
}

export interface MissingProductCostDiagnosticsResponse {
  items: MissingProductCostDiagnostic[];
  total: number;
}

export interface FinanceExportPackageResponse {
  id: string;
  period_id: string;
  version: number;
  schema_version: string;
  xlsx_path?: string | null;
  csv_dir_path?: string | null;
  manifest_path?: string | null;
  manifest?: Record<string, unknown> | null;
  generated_by_admin_id?: string | null;
  generated_at: string;
  accepted_by_admin_id?: string | null;
  accepted_at?: string | null;
  accountant_name?: string | null;
  accountant_reference?: string | null;
  acceptance_note?: string | null;
  current_final: boolean;
}

export interface FinanceExportPackageListResponse {
  items: FinanceExportPackageResponse[];
  total: number;
}

export interface AccountantAcceptanceRequest {
  accountant_name?: string | null;
  accountant_reference?: string | null;
  note?: string | null;
}

// --- Econt admin settings ---

export type EcontEnvironment = "demo" | "production";
export type EcontCredentialSource = "env" | "stored";
export type EcontDeliveryMode = "office" | "door";
export type EcontPaymentSide = "sender" | "receiver";
export type EcontCurrency = "EUR" | "BGN";
export type EcontConnectionStatus =
  | "success"
  | "missing_configuration"
  | "authentication_failed"
  | "validation_failed"
  | "timeout"
  | "service_outage";

export interface EcontSecretState {
  credential_source: EcontCredentialSource;
  private_key_configured: boolean;
  shop_id_configured: boolean;
  encryption_key_configured: boolean;
}

export interface EcontSettingsResponse {
  enabled: boolean;
  environment: EcontEnvironment;
  shop_id: string | null;
  credential_source: EcontCredentialSource;
  sender_delivery_mode: EcontDeliveryMode;
  sender_office_code: string | null;
  sender_city: string | null;
  sender_post_code: string | null;
  sender_address: string | null;
  sender_quarter: string | null;
  sender_street: string | null;
  sender_num: string | null;
  sender_other: string | null;
  default_pack_count: number;
  shipment_description: string;
  declared_value_enabled: boolean;
  default_payment_side: EcontPaymentSide;
  return_parcel_destination: string;
  days_until_return: number;
  return_parcel_payment_side: EcontPaymentSide;
  reject_action: string;
  reject_payment_side: EcontPaymentSide;
  reject_return_payment_side: EcontPaymentSide;
  courier_currency: EcontCurrency;
  currency_conversion_rate: number | null;
  office_locator_enabled: boolean;
  auto_confirm_on_label: boolean;
  auto_delivered_on_trace: boolean;
  base_url: string;
  office_locator_url: string;
  office_locator_origins: string[];
  secret_state: EcontSecretState;
  last_health_status: string | null;
  last_health_checked_at: string | null;
  last_health_error: string | null;
  updated_at: string;
}

export type EcontSettingsUpdate = Partial<
  Pick<
    EcontSettingsResponse,
    | "enabled"
    | "environment"
    | "shop_id"
    | "credential_source"
    | "sender_delivery_mode"
    | "sender_office_code"
    | "sender_city"
    | "sender_post_code"
    | "sender_address"
    | "sender_quarter"
    | "sender_street"
    | "sender_num"
    | "sender_other"
    | "default_pack_count"
    | "shipment_description"
    | "declared_value_enabled"
    | "default_payment_side"
    | "return_parcel_destination"
    | "days_until_return"
    | "return_parcel_payment_side"
    | "reject_action"
    | "reject_payment_side"
    | "reject_return_payment_side"
    | "courier_currency"
    | "currency_conversion_rate"
    | "office_locator_enabled"
    | "auto_confirm_on_label"
    | "auto_delivered_on_trace"
  >
>;

export interface EcontConnectionTestResponse {
  status: EcontConnectionStatus;
  ok: boolean;
  message: string;
  checked_at: string;
  details: Record<string, unknown> | null;
}

export interface EcontOrderFulfillmentResponse {
  order_id: string;
  ready: boolean;
  blockers: string[];
  courier_provider: string | null;
  courier_order_id: string | null;
  courier_shipment_number: string | null;
  courier_label_url: string | null;
  courier_sync_status: string | null;
  courier_last_error: string | null;
  courier_last_synced_at: string | null;
  tracking_number: string | null;
  tracking_url: string | null;
}

export interface EcontFulfillmentActionResponse {
  order_id: string;
  action: string;
  status: string;
  courier_order_id: string | null;
  shipment_number: string | null;
  label_url: string | null;
  tracking_url: string | null;
  courier_status: string | null;
  status_updated_to?: OrderStatus | null;
  ready?: boolean | null;
  blockers?: string[] | null;
}

// --- Speedy admin operations ---

export type SpeedyHealthStatus =
  "healthy" | "blocked" | "warning" | "unavailable";

export interface SpeedyCircuitState {
  name: string;
  state: string;
  failure_count: number;
  failure_threshold: number;
  recovery_remaining_seconds?: number | null;
}

export interface SpeedyHealthResponse {
  status: SpeedyHealthStatus;
  ok: boolean;
  message: string;
  username_configured: boolean;
  password_configured: boolean;
  client_id_configured: boolean;
  client_id_numeric: boolean;
  configured_client_id: string | null;
  verified_client_id: string | null;
  client_id_matches: boolean | null;
  blockers: string[];
  circuit: SpeedyCircuitState;
  last_failure_category: string | null;
  last_successful_check_at: string | null;
  checked_at: string;
}

export interface SpeedyOrderSummary {
  order_id: string;
  order_number: string | null;
  status: string;
  customer_email: string;
  customer_name: string | null;
  delivery_method: string | null;
  delivery_label: string | null;
  total_cents: number;
  tracking_number: string | null;
  tracking_url: string | null;
  courier_status: string | null;
  courier_sync_status: string | null;
  courier_last_error: string | null;
  courier_last_synced_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SpeedyQueuesResponse {
  ready_to_ship: SpeedyOrderSummary[];
  shipped: SpeedyOrderSummary[];
}

export interface SpeedyEventResponse {
  id: number;
  order_id: string;
  action: string;
  status: string;
  request: Record<string, unknown> | null;
  response: Record<string, unknown> | null;
  error: Record<string, unknown> | null;
  actor_user_id: string | null;
  created_at: string;
}

export interface SpeedyMetricsResponse {
  recent_successes: number;
  recent_failures: number;
  failures_by_category: Record<string, number>;
  cancellation_count: number;
  pickup_request_count: number;
  last_successful_health_check_at: string | null;
}

export interface SpeedyOfficeRefreshStatusResponse {
  status: string | null;
  refreshed_at: string | null;
  records: number | null;
  error: string | null;
}

export interface SpeedyAdminOverviewResponse {
  health: SpeedyHealthResponse;
  queues: SpeedyQueuesResponse;
  events: SpeedyEventResponse[];
  metrics: SpeedyMetricsResponse;
  office_refresh: SpeedyOfficeRefreshStatusResponse;
}

export interface SpeedyActionResponse {
  order_id: string;
  action: string;
  status: string;
  shipment_number: string | null;
  tracking_url: string | null;
  courier_status: string | null;
  status_updated_to: string | null;
  details: Record<string, unknown> | null;
}

export interface SpeedyShipmentSearchRequest {
  reference: string;
  include_returns?: boolean;
  shipments_only?: boolean;
}

export interface SpeedyShipmentSearchResponse {
  reference: string;
  barcodes: string[];
}

export interface SpeedyShipmentInfoRequest {
  shipment_ids: string[];
}

export interface SpeedyShipmentInfoResponse {
  shipments: Record<string, unknown>[];
}

export interface SpeedyCancelShipmentRequest {
  comment?: string | null;
}

export interface SpeedyPickupTermsRequest {
  shipment_ids: string[];
  starting_date_utc_ms?: number | null;
}

export interface SpeedyPickupTermsResponse {
  cutoffs: string[];
}

export interface SpeedyPickupRequest {
  shipment_ids: string[];
  pickup_datetime: string;
  visit_end_time: string;
  contact_name: string;
  phone: string;
}

export interface SpeedyPickupResponse {
  orders: Record<string, unknown>[];
}

export interface EcontOrderRepairRequest {
  office_code?: string | null;
  recipient_phone?: string | null;
  pack_count?: number | null;
  shipment_description?: string | null;
  payment_side?: EcontPaymentSide | null;
}

export interface EcontManualStatusRequest {
  courier_status: string;
  tracking_number?: string | null;
  tracking_url?: string | null;
  notes?: string | null;
}

// --- Delivery ---

export type DeliveryMethod = "office" | "door";
export type Courier = "speedy" | "econt";
export type OfficeType = "office" | "apt";

export interface DeliveryOffice {
  courier: Courier;
  office_id: string;
  office_code?: string | null;
  office_name: string;
  office_type: OfficeType;
  city: string;
  phone: string;
}

export interface DeliveryDoor {
  courier: Courier;
  city: string;
  postal_code: string;
  street: string;
  building?: string | null;
  apartment?: string | null;
  phone: string;
}

export interface DeliveryInfo {
  method: DeliveryMethod;
  office?: DeliveryOffice | null;
  door?: DeliveryDoor | null;
}

export interface DeliverySettingsResponse {
  speedy_office_enabled: boolean;
  speedy_door_enabled: boolean;
  econt_office_enabled: boolean;
  econt_door_enabled: boolean;
  cod_enabled: boolean;
  card_enabled: boolean;
  bank_transfer_enabled: boolean;
  updated_at: string;
}

export interface DeliverySettingsUpdate {
  speedy_office_enabled: boolean;
  speedy_door_enabled: boolean;
  econt_office_enabled: boolean;
  econt_door_enabled: boolean;
  cod_enabled: boolean;
  card_enabled: boolean;
  bank_transfer_enabled: boolean;
}

export interface EcontCheckoutConfig {
  office_locator_enabled: boolean;
  office_locator_url: string;
  office_locator_origins: string[];
}

export interface DeliveryConfigResponse {
  econt: EcontCheckoutConfig;
}

export interface StripeConfigHealth {
  mode: "not_configured" | "test" | "live" | "unknown";
  secret_key_configured: boolean;
  webhook_secret_configured: boolean;
  publishable_key_configured: boolean;
  ready_for_card_payments: boolean;
  problems: string[];
}

export interface PaymentSettingsUpdate {
  card_payments_enabled: boolean;
  pay_on_delivery_enabled: boolean;
  pay_on_delivery_max_cents: number;
}

export interface PaymentSettingsResponse extends PaymentSettingsUpdate {
  stripe: StripeConfigHealth;
}

export interface PublicPaymentSettingsResponse {
  card_payments_enabled: boolean;
  pay_on_delivery_enabled: boolean;
  pay_on_delivery_max_cents: number;
  bank_transfer_enabled: boolean;
  available_payment_methods: PaymentMethod[];
}

export interface PaymentEventResponse {
  id: string;
  order_id?: string | null;
  payment_id?: string | null;
  event_type: string;
  source: "stripe" | "admin" | "system" | "customer";
  stripe_event_id?: string | null;
  stripe_event_type?: string | null;
  provider?: string | null;
  provider_status?: string | null;
  processing_status: string;
  details?: string | null;
  admin_email?: string | null;
  admin_note?: string | null;
  request_id?: string | null;
  created_at: string;
}

export type ReturnSource =
  "admin" | "speedy" | "econt" | "customer" | "stripe" | "system";
export type ReturnStatus =
  | "requested"
  | "return_in_transit"
  | "received"
  | "inspected"
  | "rejected"
  | "closed";
export type ReturnReason =
  | "not_picked_up"
  | "refused_delivery"
  | "customer_return"
  | "wrong_address"
  | "unreachable_customer"
  | "damaged_by_courier"
  | "lost_by_courier"
  | "merchant_error"
  | "other";
export type ReturnCreateStatus = "requested" | "return_in_transit";
export type RestockDecision = "restock" | "do_not_restock" | "partial";
export type ReturnRestockDecision = "pending" | RestockDecision;
export type CourierClaimStatus =
  "none" | "filed" | "approved" | "rejected" | "paid";
export type RefundStatus = "pending" | "succeeded" | "failed" | "cancelled";

export interface ReturnCaseResponse {
  id: string;
  order_id: string;
  reason: ReturnReason;
  source: ReturnSource;
  status: ReturnStatus;
  refund_amount_cents: number | null;
  courier_return_fee_cents: number;
  courier_claim_id: string | null;
  courier_claim_status: CourierClaimStatus;
  courier_claim_amount_cents: number | null;
  restock_decision: ReturnRestockDecision;
  returned_at: string | null;
  received_at: string | null;
  inspected_at: string | null;
  closed_at: string | null;
  notes: string | null;
  created_by_admin_id: string | null;
  updated_by_admin_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReturnEventResponse {
  id: string;
  order_return_id: string | null;
  order_id: string;
  event_type: string;
  source: ReturnSource;
  payload_json: string | null;
  admin_user_id: string | null;
  admin_email: string | null;
  created_at: string;
}

export interface PaymentRefundResponse {
  id: string;
  order_id: string;
  payment_id: string | null;
  provider: "stripe" | "manual" | "bank_transfer" | "cod_adjustment";
  provider_refund_id: string | null;
  amount_cents: number;
  status: RefundStatus;
  reason: string | null;
  idempotency_key: string | null;
  failure_reason: string | null;
  created_by_admin_id: string | null;
  created_at: string;
  confirmed_at: string | null;
}

export interface CodSettlementResponse {
  id: string;
  order_id: string;
  amount_cents: number;
  settlement_date: string;
  courier_reference: string | null;
  notes: string | null;
  mismatch_review: boolean;
  created_by_admin_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateReturnCaseRequest {
  reason: ReturnReason;
  source?: "admin";
  status?: ReturnCreateStatus;
  notes?: string | null;
  refund_amount_cents?: number | null;
  courier_return_fee_cents?: number;
  courier_claim_id?: string | null;
  courier_claim_status?: CourierClaimStatus;
  courier_claim_amount_cents?: number | null;
}

export interface InspectReturnCaseRequest {
  restock_decision: RestockDecision;
  restock_quantities?: Record<string, number> | null;
  notes?: string | null;
}

export interface UpdateReturnAccountingRequest {
  courier_return_fee_cents?: number | null;
  courier_claim_id?: string | null;
  courier_claim_status?: CourierClaimStatus | null;
  courier_claim_amount_cents?: number | null;
  notes?: string | null;
}

export interface CreateStripeRefundRequest {
  amount_cents?: number | null;
  reason?: string | null;
  idempotency_key: string;
}

export interface RecordCodSettlementRequest {
  amount_cents: number;
  settlement_date: string;
  courier_reference?: string | null;
  notes?: string | null;
}

export interface EcontCodEvidence {
  collected_amount: number | null;
  collected_time: string | null;
  paid_amount: number | null;
  paid_time: string | null;
  source_event_id: number;
  source_action: string;
  recorded_at: string;
}

export interface AdminOrderDetailResponse extends OrderResponse {
  items: AdminOrderItemResponse[];
  payment_events: PaymentEventResponse[];
  return_cases: ReturnCaseResponse[];
  return_events: ReturnEventResponse[];
  refund_records: PaymentRefundResponse[];
  cod_settlement: CodSettlementResponse | null;
  cod_settlement_required: boolean;
  econt_cod_evidence: EcontCodEvidence | null;
  inventory_context?: OrderInventoryContext | null;
}

export type ManualPaymentAction =
  | "mark_paid"
  | "mark_collected"
  | "mark_refunded"
  | "mark_failed"
  | "mark_review"
  | "record_callback"
  | "convert_to_cod"
  | "cancel";

export type CallbackOutcome =
  "confirmed" | "declined" | "unreachable" | "needs_follow_up";

export interface OfficeResponse {
  id: string;
  code?: string | null;
  name: string;
  type: OfficeType;
  city: string;
  address: string;
  working_hours: string;
}

// --- Shipping pricing (Phase A) ---

export type ShippingPriceSource = "live" | "table" | "flat";

export interface ShippingQuote {
  courier: Courier;
  cents: number;
  estimated_delivery_days: number | null;
  is_fallback: boolean;
  price_source: ShippingPriceSource;
  quoted_at: string | null;
}

export interface CalculateShippingRequest {
  method: DeliveryMethod;
  city: string;
  office_id?: string | null;
  address?: ShippingAddress | null;
  items_total_cents: number;
  couriers: Courier[];
}

// Preview address for /calculate — looser than the checkout DeliveryDoor: only
// `city` is required and there is no `phone` (a price preview must not force the
// shopper to enter one). Mirrors app/models/shipping.py:ShippingAddress.
export interface ShippingAddress {
  courier: Courier;
  city: string;
  postal_code?: string | null;
  street?: string | null;
  building?: string | null;
}

export interface CalculateShippingResponse {
  quotes: ShippingQuote[];
}

// A specific courier-served delivery place. Same-named towns are distinct
// entries disambiguated by region + postcode — the postcode flows into pricing
// so ambiguous towns quote live. Mirrors app/models/shipping.py:CityPlace.
export interface CityPlace {
  name: string;
  region: string | null;
  postal_code: string | null;
}

export interface CreateOrderRequest {
  customer_email: string;
  customer_name: string;
  delivery: DeliveryInfo;
  notes?: string | null;
  payment_method?: PaymentMethod;
  analytics_consent?: boolean;
  shipping_cents?: number;
  shipping_price_source?: ShippingPriceSource;
  shipping_is_fallback?: boolean;
  shipping_quoted_at?: string | null;
  invoice_profile?: InvoiceProfile | null;
}

// --- Analytics ---

export type AnalyticsEventType =
  | "product_view"
  | "listing_filter"
  | "add_to_cart"
  | "cart_open"
  | "checkout_start"
  | "delivery_selected"
  | "shipping_quote_selected"
  | "order_submit"
  | "payment_redirect"
  | "purchase_confirmed";

export interface AnalyticsHealthResponse {
  accepted: number;
  rejected: number;
  duplicate: number;
  validation_failure: number;
  last_successful_flush_at: string | null;
  duckdb_load_status: string;
  retention_days: number;
}

export interface AnalyticsSummaryResponse {
  start_date: string;
  end_date: string;
  consented_sessions: number;
  accepted_events: number;
  conversion_rate: number;
  backend_order_count: number;
  backend_revenue_cents: number;
  analytics_purchase_count: number;
  analytics_purchase_revenue_cents: number;
  coverage_percent: number;
  consented_order_count: number;
  consented_order_delta: number;
  delivery_warning: boolean;
  health: AnalyticsHealthResponse;
}

export interface AnalyticsFunnelStep {
  event_type: AnalyticsEventType;
  count: number;
  conversion_from_previous: number;
}

export interface AnalyticsFunnelResponse {
  steps: AnalyticsFunnelStep[];
}

export interface ProductAnalyticsRow {
  product_id: string;
  product_name: string | null;
  views: number;
  add_to_cart: number;
  purchases: number;
  revenue_cents: number;
  conversion_rate: number;
}

export interface ProductAnalyticsResponse {
  products: ProductAnalyticsRow[];
}

export interface CheckoutAnalyticsResponse {
  checkout_starts: number;
  order_submits: number;
  payment_redirects: number;
  purchase_confirmed: number;
  delivery_methods: Record<string, number>;
  delivery_couriers: Record<string, number>;
  payment_methods: Record<string, number>;
}

export interface UpdateOrderStatusRequest {
  status: OrderStatus;
  tracking_number?: string;
  tracking_carrier?: string;
  tracking_url?: string;
}

// --- Users ---

export interface UserResponse {
  id: string;
  email: string;
  name: string | null;
  avatar_url: string | null;
  is_admin: boolean;
}

// --- Auth ---

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  user: UserResponse;
}

// --- Admin ---

export interface AdminStats {
  orders_today: number;
  revenue_this_week_cents: number;
  active_product_count: number;
  low_stock_count: number;
  contact_messages_needing_attention: number;
  orders: {
    total: number;
    revenue_cents: number;
    by_status: Partial<Record<OrderStatus, number>>;
    by_payment_status: Partial<Record<PaymentStatus, number>>;
  };
  products: {
    total: number;
    active: number;
  };
}

export interface AdminProductResponse {
  id: string;
  name_en: string;
  name_bg: string | null;
  description_en: string | null;
  description_bg: string | null;
  safety_warnings_en: string | null;
  safety_warnings_bg: string | null;
  care_instructions_en: string | null;
  care_instructions_bg: string | null;
  materials: string | null;
  days_to_craft: number | null;
  price_cents: number;
  // Raw discount config + computed preview (effective_price_cents/discount_active).
  discount_percent: number | null;
  discount_starts_at: string | null;
  discount_ends_at: string | null;
  effective_price_cents: number;
  discount_active: boolean;
  category: string | null;
  product_type: string;
  labels: string[];
  images: ProductImage[];
  video?: ProductVideo | null;
  primary_image_url: string | null;
  primary_thumbnail_url: string | null;
  stock: number;
  inventory_mode?: "legacy" | "fallback" | "ledger_managed";
  stock_source?: "product_stock" | "inventory_ledger" | "mixed";
  ledger_managed?: boolean;
  valuation_readiness?:
    "setup_required" | "estimate_only" | "ready" | "blocked";
  active_recipe_id?: string | null;
  active_recipe_status?: "missing" | "draft" | "active" | "archived";
  active_recipe_review_state?: string | null;
  latest_batch_id?: string | null;
  latest_batch_number?: string | null;
  latest_batch_status?: string | null;
  latest_batch_date?: string | null;
  inventory_exception_count?: number;
  inventory_exceptions?: InventoryExceptionResponse[];
  inventory_links?: Record<string, string | null> | null;
  weight_grams?: number;
  is_active: boolean;
  is_featured: boolean;
  translation_stale_bg: boolean;
  translation_stale_en: boolean;
  created_at: string;
  updated_at: string;
}

export interface AdminProductListResponse {
  products: AdminProductResponse[];
  total: number;
  page: number;
  limit: number;
  applied_filters?: Record<string, string | number | boolean | string[] | null>;
}

export type AdminProductStatusFilter = "all" | "active" | "inactive";
export type AdminProductMediaFilter =
  "any" | "ready" | "missing_image" | "has_video" | "missing_video";
export type AdminProductStockFilter =
  "any" | "in_stock" | "out_of_stock" | "low";
export type AdminProductDiscountFilter =
  "any" | "active" | "scheduled" | "none";
export type AdminProductInventoryModeFilter =
  "legacy" | "fallback" | "ledger_managed";
export type AdminProductRecipeStatusFilter =
  "active" | "missing" | "draft" | "archived";
export type AdminProductSort =
  | "created_desc"
  | "created_asc"
  | "updated_desc"
  | "updated_asc"
  | "name_asc"
  | "name_desc"
  | "price_asc"
  | "price_desc"
  | "stock_asc"
  | "stock_desc";

export interface AdminProductFilters {
  q?: string;
  status?: AdminProductStatusFilter;
  media?: AdminProductMediaFilter;
  stock?: AdminProductStockFilter;
  product_type?: string;
  category?: string;
  label?: string[];
  featured?: boolean | null;
  discount?: AdminProductDiscountFilter;
  inventory_mode?: AdminProductInventoryModeFilter | "";
  recipe_status?: AdminProductRecipeStatusFilter | "";
  has_inventory_exceptions?: boolean | null;
  low_stock_threshold?: number;
  sort?: AdminProductSort;
}

export interface CreateProductRequest {
  id: string;
  name_en: string;
  name_bg?: string | null;
  description_en?: string | null;
  description_bg?: string | null;
  safety_warnings_en?: string | null;
  safety_warnings_bg?: string | null;
  care_instructions_en?: string | null;
  care_instructions_bg?: string | null;
  materials?: string | null;
  days_to_craft?: number | null;
  price_cents: number;
  category?: string | null;
  product_type: string;
  labels?: string[];
  stock: number;
  weight_grams?: number;
  is_active?: boolean;
  is_featured?: boolean;
  discount_percent?: number | null;
  discount_starts_at?: string | null;
  discount_ends_at?: string | null;
}

export interface UpdateProductRequest {
  name_en?: string;
  name_bg?: string | null;
  description_en?: string | null;
  description_bg?: string | null;
  safety_warnings_en?: string | null;
  safety_warnings_bg?: string | null;
  care_instructions_en?: string | null;
  care_instructions_bg?: string | null;
  materials?: string | null;
  days_to_craft?: number | null;
  price_cents?: number;
  category?: string | null;
  product_type?: string;
  labels?: string[];
  stock?: number;
  weight_grams?: number;
  is_active?: boolean;
  is_featured?: boolean;
  discount_percent?: number | null;
  discount_starts_at?: string | null;
  discount_ends_at?: string | null;
}

export type ImageUploadResponse = ProductImage;
export type VideoUploadResponse = ProductVideo;

// --- Promotions (campaigns, bulk discount, managed banner) ---

/** Admin product-list filter descriptor used as a bulk/campaign target. */
export interface ProductFilter {
  q?: string | null;
  category?: string | null;
  is_active?: boolean | null;
  in_stock?: boolean | null;
}

export type BulkOperation = "apply" | "remove";
export type BulkItemStatus = "updated" | "skipped" | "failed";

export interface BulkResultItem {
  id: string;
  status: BulkItemStatus;
  error?: string | null;
}

export interface BulkDiscountResponse {
  success_count: number;
  failure_count: number;
  results: BulkResultItem[];
}

export interface BulkDiscountRequest {
  operation: BulkOperation;
  product_ids?: string[] | null;
  filter?: ProductFilter | null;
  discount_percent?: number | null;
  discount_starts_at?: string | null;
  discount_ends_at?: string | null;
}

export type CampaignStatus =
  "draft" | "scheduled" | "active" | "ended" | "removed";

export interface CampaignResponse {
  id: string;
  name: string;
  note: string | null;
  discount_percent: number;
  discount_starts_at: string | null;
  discount_ends_at: string | null;
  target_type: "ids" | "filter";
  target_count: number;
  target_ids: string[] | null;
  target_filter: ProductFilter | null;
  status: CampaignStatus;
  applied_at: string | null;
  removed_at: string | null;
  created_at: string;
  updated_at: string;
  last_result: BulkDiscountResponse | null;
}

export interface CampaignListResponse {
  items: CampaignResponse[];
  total: number;
}

export interface CampaignCreateRequest {
  name: string;
  note?: string | null;
  discount_percent: number;
  discount_starts_at?: string | null;
  discount_ends_at?: string | null;
  product_ids?: string[] | null;
  filter?: ProductFilter | null;
}

export interface CampaignUpdateRequest {
  name?: string | null;
  note?: string | null;
  discount_percent?: number | null;
  discount_starts_at?: string | null;
  discount_ends_at?: string | null;
  product_ids?: string[] | null;
  filter?: ProductFilter | null;
}

export interface BannerAdminResponse {
  message_en: string | null;
  message_bg: string | null;
  link_label_en: string | null;
  link_label_bg: string | null;
  link_url: string | null;
  is_enabled: boolean;
  starts_at: string | null;
  ends_at: string | null;
  version: number;
  updated_at: string;
}

export interface BannerUpdateRequest {
  message_en?: string | null;
  message_bg?: string | null;
  link_label_en?: string | null;
  link_label_bg?: string | null;
  link_url?: string | null;
  is_enabled: boolean;
  starts_at?: string | null;
  ends_at?: string | null;
}

/** The single active banner, localized for the requested locale. */
export interface PublicBanner {
  message: string;
  link_label: string | null;
  link_url: string | null;
  dismiss_key: string;
}

export interface PublicBannerResponse {
  banner: PublicBanner | null;
}

// --- Reactions ---

export interface ReactionTypeCount {
  count: number;
  reacted: boolean;
}

export interface ReactionCountsResponse {
  heart: ReactionTypeCount;
  thumbs_up: ReactionTypeCount;
}

export interface ReactionToggleRequest {
  reaction_type: "heart" | "thumbs_up";
}

export interface ReactionToggleResponse {
  reaction_type: string;
  active: boolean;
}

// --- Comments ---

export interface CommentResponse {
  id: string;
  display_name: string;
  body: string;
  created_at: string;
}

export interface CommentListResponse {
  items: CommentResponse[];
  total: number;
  page: number;
  limit: number;
}

export interface CommentCreateRequest {
  display_name?: string | null;
  body: string;
}

export type CommentSort = "newest" | "oldest";
