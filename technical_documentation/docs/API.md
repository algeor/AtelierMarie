# API Reference — AtelierMarie

> Complete endpoint reference for Layer 1 (Production E-Commerce). Layer 2 (analytics) endpoints documented in separate section. All times are UTC; prices in EUR cents unless otherwise noted.

**Base URL:** `/v1`  
**Authentication:** Session cookie (UUID) OR JWT Bearer token for admin API key  
**Response envelope:** All responses are JSON; errors use standard `{"error": {"code": "...", "message": "..."}}` format.

---

## Products & Catalog

### List/Search Products

```http
GET /v1/products?search=<query>&category=<slug>&type=<slug>&page=1&limit=20
```

**Query Parameters:**
- `search` (optional): Full-text search on product names/descriptions (both locales supported)
- `category` (optional): Filter by category slug
- `type` (optional): Filter by product type slug
- `is_featured` (optional): `1` to show featured only
- `page` (optional, default `1`): Pagination page
- `limit` (optional, default `20`, max `100`): Items per page
- `locale` (optional, default from Accept-Language or NEXT_LOCALE cookie): `en` or `bg`

**Response:**
```json
{
  "items": [
    {
      "id": "lavender-dream-300ml",
      "name": "Lavender Dream",
      "description": "...",
      "price_cents": 3500,
      "discount_percent": null,
      "stock": 12,
      "image_url": "/static/products/lavender-dream.png",
      "is_featured": true,
      "product_type_slug": "candles",
      "category_slug": "classic",
      "reactions_count": { "heart": 42, "thumbs_up": 8 },
      "comments_count": 3,
      "rating_avg": 4.5,
      "weight_grams": 300,
      "materials": "Soy wax, essential oils"
    }
  ],
  "total": 123,
  "page": 1,
  "limit": 20
}
```

**Status Codes:**
- `200 OK` — Success
- `400 Bad Request` — Invalid filter or pagination

---

### Get Product Detail

```http
GET /v1/products/{product_id}
```

**Path Parameters:**
- `product_id`: Product SKU/slug (e.g., `lavender-dream-300ml`)

**Response:**
```json
{
  "id": "lavender-dream-300ml",
  "name": "Lavender Dream",
  "description": "Handcrafted lavender candle for relaxation",
  "price_cents": 3500,
  "discount_percent": 10,
  "discount_starts_at": "2026-08-01T00:00:00Z",
  "discount_ends_at": "2026-08-15T23:59:59Z",
  "stock": 12,
  "weight_grams": 300,
  "materials": "Soy wax, essential oils",
  "safety_warnings": "Keep away from drafts. Do not leave burning unattended.",
  "care_instructions": "Trim wick to 1/4 inch before each use.",
  "days_to_craft": 3,
  "is_active": true,
  "is_featured": true,
  "product_type_slug": "candles",
  "category_slug": "classic",
  "images": [
    {
      "id": "img-1",
      "image_url": "/static/products/lavender-dream.jpg",
      "thumbnail_url": "/static/products/lavender-dream-thumb.jpg",
      "zoom_url": "/static/products/lavender-dream-zoom.jpg",
      "is_primary": true,
      "sort_order": 0
    }
  ],
  "video": {
    "id": "vid-1",
    "video_url": "/static/products/lavender-dream.mp4",
    "poster_url": "/static/products/lavender-dream-poster.jpg",
    "duration_secs": 45,
    "status": "ready"
  },
  "reactions_count": { "heart": 42, "thumbs_up": 8 },
  "comments_count": 3,
  "comments_sample": [
    {
      "id": "c-1",
      "display_name": "Alice",
      "body": "Absolutely love this candle!",
      "created_at": "2026-07-15T10:30:00Z"
    }
  ]
}
```

**Status Codes:**
- `200 OK` — Product found
- `404 Not Found` — Product not found or inactive

---

## Cart

### Get Cart

```http
GET /v1/cart
```

**Authentication:** Session cookie required

**Response:**
```json
{
  "items": [
    {
      "product_id": "lavender-dream-300ml",
      "product_name": "Lavender Dream",
      "quantity": 2,
      "price_cents": 3500,
      "subtotal_cents": 7000,
      "image_url": "/static/products/lavender-dream.png"
    }
  ],
  "subtotal_cents": 7000,
  "item_count": 2
}
```

---

### Add to Cart

```http
POST /v1/cart
Content-Type: application/json

{
  "product_id": "lavender-dream-300ml",
  "quantity": 2
}
```

**Request Body:**
- `product_id` (required): Product SKU
- `quantity` (required): Quantity (1-10)

**Response:**
```json
{
  "items": [...],
  "subtotal_cents": 7000,
  "item_count": 2
}
```

**Status Codes:**
- `201 Created` — Item added
- `400 Bad Request` — Invalid quantity (must be 1-10)
- `409 Conflict` — Product out of stock: `{"error": {"code": "OUT_OF_STOCK", "available": 2}}`

---

### Update Cart Item

```http
PATCH /v1/cart/{product_id}
Content-Type: application/json

{
  "quantity": 3
}
```

**Request Body:**
- `quantity` (required): New quantity (0 = remove item, 1-10 = update)

**Status Codes:**
- `200 OK` — Updated
- `400 Bad Request` — Invalid quantity
- `404 Not Found` — Item not in cart

---

### Remove from Cart

```http
DELETE /v1/cart/{product_id}
```

**Status Codes:**
- `204 No Content` — Removed
- `404 Not Found` — Item not in cart

---

## Checkout & Orders

### Get Live Courier Quote

```http
GET /v1/delivery/quote?delivery_method=<door|office>&delivery_courier=<speedy|econt>
```

**Query Parameters:**
- `delivery_method` (required): `door` or `office`
- `delivery_courier` (required): `speedy` or `econt`

**Response:**
```json
{
  "courier": "speedy",
  "delivery_method": "door",
  "quote_cents": 1200,
  "estimated_days": 2,
  "office_info": null,
  "address_required": true
}
```

**Status Codes:**
- `200 OK` — Quote retrieved
- `400 Bad Request` — Invalid method/courier
- `503 Service Unavailable` — Courier API offline (returns fallback quote)

---

### Create Order (COD/Bank Transfer)

```http
POST /v1/orders
Content-Type: application/json

{
  "customer_name": "Alice Smith",
  "customer_email": "alice@example.com",
  "delivery_method": "door",
  "delivery_courier": "speedy",
  "payment_method": "cod",
  "shipping_address": "123 Main St, Sofia, 1000, Bulgaria"
}
```

**Request Body:**
- `customer_name` (required): Full name
- `customer_email` (required): Email address
- `delivery_method` (required): `door` or `office`
- `delivery_courier` (required): `speedy` or `econt`
- `payment_method` (required): `cod` or `bank_transfer`
- `shipping_address` (conditional): Required if delivery_method=`door`; optional for office delivery

**Response:**
```json
{
  "id": "ord-uuid-12345",
  "order_number": "AM-K9X2P7",
  "status": "pending",
  "payment_method": "cod",
  "payment_status": "cod_pending",
  "total_cents": 8200,
  "shipping_cents": 1200,
  "items": [
    {
      "product_id": "lavender-dream-300ml",
      "product_name": "Lavender Dream",
      "quantity": 2,
      "price_cents": 3500
    }
  ],
  "created_at": "2026-08-08T12:34:56Z"
}
```

**Status Codes:**
- `201 Created` — Order created
- `400 Bad Request` — Cart empty or invalid input
- `409 Conflict` — Stock validation failed: `{"error": {"code": "OUT_OF_STOCK", "product_id": "..."}}`

---

### Create Stripe Checkout Order

```http
POST /v1/orders/stripe
Content-Type: application/json

{
  "customer_name": "Alice Smith",
  "customer_email": "alice@example.com",
  "delivery_method": "door",
  "delivery_courier": "speedy",
  "shipping_address": "123 Main St, Sofia, 1000, Bulgaria"
}
```

**Response:**
```json
{
  "order_id": "ord-uuid-12345",
  "order_number": "AM-K9X2P7",
  "checkout_session_id": "cs_test_...",
  "client_secret": "pi_1234_secret_...",
  "checkout_url": "https://checkout.stripe.com/..."
}
```

**Status Codes:**
- `201 Created` — Checkout session created, order reserved for 15 minutes
- `400 Bad Request` — Cart empty or card payments disabled
- `409 Conflict` — Stock validation failed

---

### List User's Orders

```http
GET /v1/orders?page=1&limit=10&status=pending
```

**Authentication:** JWT cookie or session required

**Query Parameters:**
- `page` (optional, default `1`): Pagination page
- `limit` (optional, default `10`, max `50`): Items per page
- `status` (optional): Filter by status (`pending`, `confirmed`, `shipped`, `delivered`, `cancelled`)

**Response:**
```json
{
  "items": [
    {
      "id": "ord-uuid",
      "order_number": "AM-K9X2P7",
      "status": "pending",
      "payment_method": "cod",
      "payment_status": "cod_pending",
      "total_cents": 8200,
      "created_at": "2026-08-08T12:34:56Z"
    }
  ],
  "total": 5,
  "page": 1,
  "limit": 10
}
```

---

### Get Order Detail

```http
GET /v1/orders/{order_id}
```

**Authentication:** JWT/session (must own order or be admin)

**Response:**
```json
{
  "id": "ord-uuid",
  "order_number": "AM-K9X2P7",
  "status": "pending",
  "payment_method": "cod",
  "payment_status": "cod_pending",
  "total_cents": 8200,
  "shipping_cents": 1200,
  "items": [
    {
      "product_id": "lavender-dream-300ml",
      "product_name": "Lavender Dream",
      "quantity": 2,
      "price_cents": 3500
    }
  ],
  "customer_name": "Alice Smith",
  "customer_email": "alice@example.com",
  "delivery_method": "door",
  "delivery_courier": "speedy",
  "shipping_address": "123 Main St, Sofia",
  "tracking_number": "SPDY123456789",
  "tracking_url": "https://tracking.speedy.bg/...",
  "courier_status": "in_transit",
  "timeline": [
    {
      "event": "placed",
      "timestamp": "2026-08-08T12:34:56Z",
      "status": "pending"
    },
    {
      "event": "confirmed",
      "timestamp": "2026-08-08T14:15:00Z",
      "status": "confirmed"
    }
  ],
  "created_at": "2026-08-08T12:34:56Z",
  "updated_at": "2026-08-08T14:15:00Z"
}
```

---

## Authentication

### Google OAuth Login

```http
GET /v1/auth/login?redirect_uri=http://localhost:3000/en
```

**Query Parameters:**
- `redirect_uri` (optional): Where to redirect after OAuth callback (must be whitelisted)

**Response:** Redirect to Google OAuth consent screen

---

### OAuth Callback

```http
GET /v1/auth/callback?code=<auth_code>&state=<state>
```

Handled by frontend via `/auth/callback` route. Backend sets JWT cookie on success.

**Response (on frontend):**
- JWT cookie set (HttpOnly, Secure, SameSite=Lax, 7 day expiry)
- Redirect to referrer or `/en`

---

### Get Current User

```http
GET /v1/auth/me
```

**Authentication:** JWT cookie required

**Response:**
```json
{
  "id": "user-uuid",
  "email": "alice@example.com",
  "name": "Alice Smith",
  "is_admin": false,
  "avatar_url": "https://...",
  "created_at": "2026-07-01T00:00:00Z"
}
```

---

### Logout

```http
POST /v1/auth/logout
```

**Authentication:** JWT cookie required

**Response:**
- JWT cookie cleared
- Session ID rotated (old ID invalidated, new one issued)

---

## Social Features

### Toggle Product Reaction

```http
POST /v1/products/{product_id}/reactions
Content-Type: application/json

{
  "reaction_type": "heart"
}
```

**Request Body:**
- `reaction_type` (required): `heart` or `thumbs_up`

**Response:**
```json
{
  "reaction_type": "heart",
  "reacted": true,
  "reaction_count": 43
}
```

**Status Codes:**
- `200 OK` — Reaction toggled
- `429 Too Many Requests` — Rate limited (5 reactions per minute per session)
- `404 Not Found` — Product not found

---

### Post Product Comment

```http
POST /v1/products/{product_id}/comments
Content-Type: application/json

{
  "display_name": "Alice",
  "body": "Absolutely love this candle!"
}
```

**Request Body:**
- `display_name` (required): Public display name (1-50 chars)
- `body` (required): Comment text (1-500 chars, HTML stripped)

**Response:**
```json
{
  "id": "c-uuid",
  "product_id": "lavender-dream-300ml",
  "display_name": "Alice",
  "body": "Absolutely love this candle!",
  "created_at": "2026-08-08T12:34:56Z"
}
```

---

### Get Product Comments

```http
GET /v1/products/{product_id}/comments?page=1&limit=20
```

**Response:**
```json
{
  "items": [
    {
      "id": "c-uuid",
      "display_name": "Alice",
      "body": "Absolutely love this candle!",
      "created_at": "2026-08-08T12:34:56Z"
    }
  ],
  "total": 8,
  "page": 1,
  "limit": 20
}
```

---

## Admin

### Admin Dashboard

```http
GET /v1/admin/dashboard
```

**Authentication:** Admin JWT or API key

**Response:**
```json
{
  "stats": {
    "total_orders": 142,
    "pending_orders": 8,
    "revenue_cents": 425300,
    "average_order_value_cents": 2994,
    "top_products": [
      {
        "product_id": "lavender-dream-300ml",
        "name": "Lavender Dream",
        "sales": 23,
        "revenue_cents": 80500
      }
    ]
  },
  "recent_orders": [
    {
      "id": "ord-uuid",
      "order_number": "AM-K9X2P7",
      "status": "pending",
      "total_cents": 8200,
      "created_at": "2026-08-08T12:34:56Z"
    }
  ]
}
```

---

### List All Orders (Admin)

```http
GET /v1/admin/orders?page=1&limit=20&status=pending&payment_status=cod_pending
```

**Query Parameters:**
- `status` (optional): `pending`, `confirmed`, `shipped`, `delivered`, `cancelled`
- `payment_status` (optional): `pending`, `paid`, `cod_pending`, `failed`, `refunded`
- `page`, `limit`: Pagination

**Response:**
```json
{
  "items": [
    {
      "id": "ord-uuid",
      "order_number": "AM-K9X2P7",
      "status": "pending",
      "payment_status": "cod_pending",
      "customer_email": "alice@example.com",
      "total_cents": 8200,
      "created_at": "2026-08-08T12:34:56Z"
    }
  ],
  "total": 142,
  "page": 1,
  "limit": 20
}
```

---

### Update Order Status

```http
PATCH /v1/admin/orders/{order_id}/status
Content-Type: application/json

{
  "status": "confirmed"
}
```

**Valid transitions:**
- `pending` → `confirmed`, `cancelled`
- `confirmed` → `shipped`, `cancelled`
- `shipped` → `delivered`

**Response:**
```json
{
  "id": "ord-uuid",
  "status": "confirmed",
  "updated_at": "2026-08-08T14:00:00Z"
}
```

**Status Codes:**
- `200 OK` — Updated
- `400 Bad Request` — Invalid transition
- `404 Not Found` — Order not found

---

### Update Order Payment Status

```http
PATCH /v1/admin/orders/{order_id}/payment-status
Content-Type: application/json

{
  "payment_status": "collected"
}
```

**Valid for COD:** `cod_pending` → `collected`

**Response:**
```json
{
  "id": "ord-uuid",
  "payment_status": "collected",
  "updated_at": "2026-08-08T14:00:00Z"
}
```

---

### Create Product

```http
POST /v1/admin/products
Content-Type: application/json

{
  "id": "new-candle-300ml",
  "name_en": "New Candle",
  "name_bg": "Нова Свещ",
  "description_en": "A new candle product",
  "price_cents": 3500,
  "stock": 100,
  "weight_grams": 300,
  "product_type_slug": "candles",
  "category_slug": "classic"
}
```

**Response:**
```json
{
  "id": "new-candle-300ml",
  "name_en": "New Candle",
  "price_cents": 3500,
  "stock": 100,
  "created_at": "2026-08-08T12:34:56Z"
}
```

---

### Bulk Import Products (CSV)

```http
POST /v1/admin/products/import
Content-Type: multipart/form-data

file=products.csv
```

**CSV Format:**
```
id,name_en,name_bg,description_en,price_cents,stock,weight_grams
lavender-dream,Lavender Dream,Лавандово Мечта,Relaxing lavender candle,3500,100,300
rose-bliss,Rose Bliss,Розово Блаженство,Romantic rose candle,4000,50,300
```

**Response:**
```json
{
  "total": 2,
  "created": 2,
  "updated": 0,
  "failed": 0,
  "errors": []
}
```

---

## Error Handling

All errors follow a standard envelope:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": { "field": "reason" }
  }
}
```

**Common error codes:**
- `VALIDATION_ERROR` — Input validation failed
- `OUT_OF_STOCK` — Product not in stock
- `NOT_FOUND` — Resource not found
- `UNAUTHORIZED` — Missing/invalid authentication
- `FORBIDDEN` — Insufficient permissions
- `RATE_LIMITED` — Too many requests
- `INTERNAL_SERVER_ERROR` — Server error (logged, should be rare)

---

## Pagination

All list endpoints support offset pagination:

```json
{
  "items": [...],
  "total": 142,
  "page": 1,
  "limit": 20
}
```

**Query Parameters:**
- `page` (default `1`): Page number (1-indexed)
- `limit` (default varies by endpoint, max `100`): Items per page

---

## Rate Limiting

- Reactions: 5 per minute per session
- Comments: 10 per minute per session
- Contact form submissions: 5 per minute per IP
- Login attempts: 10 per hour per email

Responses include:
- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-RateLimit-Reset`

---

## Webhooks (Stripe)

**Endpoint:** `POST /v1/webhooks/stripe`

**Expected headers:**
- `stripe-signature`: HMAC signature

**Idempotency:** All webhook events are deduplicated by `event_id`; safe to retry.

**Event types handled:**
- `checkout.session.completed` — Payment completed, update payment_status
- `charge.refunded` — Refund processed, update payment_status

---

## Locale Support

All endpoints support bilingual content via:
- `Accept-Language` header (preferred)
- `NEXT_LOCALE` cookie
- Query parameter `?locale=en` or `?locale=bg` (overrides both)

Default: `en`
