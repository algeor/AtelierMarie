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

// --- Products ---

export interface ProductResponse {
  id: string;
  name: string;
  description: string | null;
  materials: string | null;
  days_to_craft: number | null;
  price_cents: number;
  category: string | null;
  image_url: string | null;
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
  total_cents: number;
  customer_email: string;
  customer_name: string | null;
  shipping_address: string | null;
  notes: string | null;
  items: OrderItemResponse[];
  created_at: string;
  updated_at: string;
}

export interface OrderListResponse {
  orders: OrderResponse[];
  total: number;
  page: number;
  limit: number;
}

export interface CreateOrderRequest {
  customer_email: string;
  customer_name?: string | null;
  shipping_address?: string | null;
  notes?: string | null;
}

export interface UpdateOrderStatusRequest {
  status: OrderStatus;
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
