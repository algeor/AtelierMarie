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
  sort_order: number;
  is_primary: boolean;
}

export interface ProductResponse {
  id: string;
  name: string;
  description: string | null;
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
  images: ProductImage[];
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

// --- Cart ---

export interface CartItemResponse {
  product_id: string;
  product: ProductResponse;
  quantity: number;
  added_at: string;
}

export interface CartResponse {
  items: CartItemResponse[];
  total_cents: number;
  item_count: number;
}

// --- Orders ---

export type OrderStatus =
  | "pending"
  | "confirmed"
  | "shipped"
  | "delivered"
  | "cancelled";

export interface OrderItemResponse {
  product_id: string;
  product_name: string;
  price_cents: number;
  quantity: number;
}

export interface OrderResponse {
  id: string;
  status: OrderStatus;
  items_total_cents: number;
  shipping_cents: number;
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
  created_at: string;
  updated_at: string;
}

export interface OrderListResponse {
  items: OrderResponse[];
  total: number;
  page: number;
  limit: number;
}

// --- Delivery ---

export type DeliveryMethod = "office" | "door";
export type Courier = "speedy" | "econt";
export type OfficeType = "office" | "apt";

export interface DeliveryOffice {
  courier: Courier;
  office_id: string;
  office_name: string;
  office_type: OfficeType;
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

export interface OfficeResponse {
  id: string;
  name: string;
  type: OfficeType;
  city: string;
  address: string;
  working_hours: string;
}

export interface CreateOrderRequest {
  customer_email: string;
  customer_name?: string | null;
  delivery: DeliveryInfo;
  notes?: string | null;
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
}

export interface AdminProductResponse {
  id: string;
  name_en: string;
  name_bg: string | null;
  description_en: string | null;
  description_bg: string | null;
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
  images: ProductImage[];
  primary_image_url: string | null;
  primary_thumbnail_url: string | null;
  stock: number;
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
}

export interface CreateProductRequest {
  id: string;
  name_en: string;
  name_bg?: string | null;
  description_en?: string | null;
  description_bg?: string | null;
  materials?: string | null;
  days_to_craft?: number | null;
  price_cents: number;
  category: string;
  stock: number;
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
  materials?: string | null;
  days_to_craft?: number | null;
  price_cents?: number;
  category?: string;
  stock?: number;
  is_active?: boolean;
  is_featured?: boolean;
  discount_percent?: number | null;
  discount_starts_at?: string | null;
  discount_ends_at?: string | null;
}

export type ImageUploadResponse = ProductImage;

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
  | "draft"
  | "scheduled"
  | "active"
  | "ended"
  | "removed";

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
