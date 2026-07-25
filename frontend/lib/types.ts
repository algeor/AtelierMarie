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

export interface ProductLabelRef {
  slug: string;
  name: string;
}

export interface ProductResponse {
  id: string;
  name: string;
  description: string | null;
  materials: string | null;
  days_to_craft: number | null;
  price_cents: number;
  category: string | null;
  category_name: string | null;
  product_type: string;
  product_type_name: string;
  labels: ProductLabelRef[];
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
  category: string | null;
  product_type: string;
  labels: string[];
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
  category?: string | null;
  product_type: string;
  labels?: string[];
  stock: number;
  is_featured?: boolean;
}

export interface UpdateProductRequest {
  name_en?: string;
  name_bg?: string | null;
  description_en?: string | null;
  description_bg?: string | null;
  materials?: string | null;
  days_to_craft?: number | null;
  price_cents?: number;
  category?: string | null;
  product_type?: string;
  labels?: string[];
  stock?: number;
  is_active?: boolean;
  is_featured?: boolean;
}

export type ImageUploadResponse = ProductImage;

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
