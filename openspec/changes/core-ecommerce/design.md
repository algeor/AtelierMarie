# Core E-Commerce — Design

## Data Model

All data lives in a single SQLite database (`atelier.db`, WAL mode).

### Tables

| Table | Purpose | Key Columns |
|-------|---------|------------|
| `products` | Product catalog | id (SKU/slug), name, price_cents, stock, is_active, category, image_url |
| `users` | Google OAuth accounts | id, google_id, email, name, is_admin |
| `sessions` | Cookie-based sessions | id (UUID), user_id (nullable), expires_at |
| `cart_items` | Shopping cart | session_id, product_id, quantity |
| `orders` | Placed orders | id, session_id, user_id, status, total_cents, customer_email |
| `order_items` | Order line items (snapshots) | order_id, product_id, product_name, price_cents, quantity |

### Key Constraints

- Prices stored as **integers (cents)** — no floating point
- Product `id` is a business identifier (SKU or slug, e.g. `lavender-dream-300ml`) — not auto-increment
- `order_items` snapshots product name + price at purchase time (immutable after creation)
- `cart_items` keyed by session (works for anonymous users)
- Soft delete via `is_active` flag on products (never hard-delete — preserves event/order referential integrity)

---

## Order State Machine

```
                  ┌──────────┐
                  │ pending  │ ← created at checkout
                  └────┬─────┘
                       │ admin confirms
                       ▼
                  ┌──────────┐
                  │confirmed │
                  └────┬─────┘
                       │ admin marks shipped
                       ▼
                  ┌──────────┐
                  │ shipped  │
                  └────┬─────┘
                       │ admin marks delivered
                       ▼
                  ┌──────────┐
                  │delivered │
                  └──────────┘

  From pending or confirmed only:
                  ┌──────────┐
                  │cancelled │
                  └──────────┘
```

**Valid transitions:**
| From | To | Who |
|------|----|-----|
| `pending` | `confirmed` | Admin |
| `pending` | `cancelled` | Admin or Customer |
| `confirmed` | `shipped` | Admin |
| `confirmed` | `cancelled` | Admin |
| `shipped` | `delivered` | Admin |

Any other transition → 422 Unprocessable Entity. Once `delivered` or `cancelled`, the order is terminal.

On cancellation: stock is restored (`UPDATE products SET stock = stock + quantity`).

---

## Cart Behavior

### Stock Validation on Add (not just at checkout)

When a customer adds an item to cart:
1. Check `products.stock >= requested_quantity`
2. If out of stock → return 409 Conflict immediately (don't wait until checkout)
3. If stock is low (e.g., only 2 left, user wants 5) → return 409 with `available: 2`

**Note:** Stock is not *reserved* on cart add — only decremented at checkout. Between add and checkout, another customer could buy the last item. This is handled at checkout with a clear error.

### Quantity Limits

- Min quantity per item: 1
- Max quantity per item: 10 (configurable)
- Max distinct items in cart: 20
- Update to quantity 0 → treated as remove

### Cart Expiry

Cart items live as long as the session (30 days). No separate cart expiry timer.

---

## Checkout Flow (Detailed)

```
1. Validate cart is not empty → 400 if empty
2. Validate all items still in stock:
   SELECT id, stock FROM products WHERE id IN (cart product ids) AND is_active = 1
   - Product deactivated since add? → 409 with "product no longer available"
   - Stock insufficient? → 409 with {product_id, requested, available}
3. BEGIN TRANSACTION
   a. INSERT INTO orders (id=uuid, total_cents computed from cart, status='pending')
   b. For each cart item:
      - INSERT INTO order_items (snapshot current product name + price)
      - UPDATE products SET stock = stock - quantity
   c. DELETE FROM cart_items WHERE session_id = ?
4. COMMIT
5. Return order confirmation {order_id, total, items, status}
6. AFTER RESPONSE: fire-and-forget analytics event (Layer 2, if enabled)
```

Edge cases:
- Race condition (two checkouts for last item): Transaction fails on stock going negative (CHECK constraint: `stock >= 0`) → rollback → retry with fresh stock check → 409 to second customer
- Empty cart at step 1: Early return, no transaction opened

---

## Session Handling

### Session Lifecycle

- **Creation:** On first request without valid `atelier_session` cookie → create session row (UUID v4), set cookie
- **Cookie:** `atelier_session`, httponly, secure, samesite=lax, path=/
- **Expiry:** 30-day sliding window. Each request extends `expires_at` by 30 days.
- **Cleanup:** Expired sessions cleaned up by a periodic query (daily, or on-read check)

#### Decision: Eager DB Row Creation (Option A)

The session middleware creates the `sessions` DB row **on first request** (not lazily on first cart action). Rationale:

- FK constraint `cart_items.session_id → sessions.id` requires the row to exist before any cart insert
- Sliding expiry needs the row to UPDATE `expires_at` on every request
- SQLite INSERT is <1ms — negligible cost at this scale (~100 customers, not millions of bots)
- Downstream code can always assume `request.state.session_id` has a matching DB row

The middleware imports `get_db()` directly. On each request:
1. **No cookie / cookie not in DB / expired row** → generate UUID, INSERT session row, set cookie
2. **Valid cookie, row exists** → UPDATE `expires_at` to now+30 days (sliding window)
3. Always set `request.state.session_id`

Stale/bot sessions are handled by periodic cleanup (DELETE WHERE expires_at < now).

### Session Rotation on Logout

When a user logs out:
1. Current session's `user_id` is cleared (set to NULL)
2. A **new session** is created with a fresh UUID
3. The old session cookie is replaced with the new one
4. Response includes `X-Session-Rotated: <new_session_id>` header (for frontend to update local state)

This prevents the old session ID from being reused to access user-specific data after logout.

### Login Linking

On Google OAuth callback:
1. `sessions.user_id` = authenticated user's ID
2. Cart items remain (they're keyed by session_id, which hasn't changed)
3. Any orders placed with this session_id become visible in "My Orders"

---

## Auth Flow (Detailed)

### Google OAuth Implementation

Direct HTTP calls to Google (no authlib dependency):
1. `GET /v1/auth/login` → generate state token (contains session_id + CSRF nonce), redirect to Google
2. Google consent → redirect to `GET /v1/auth/callback?code=...&state=...`
3. Backend validates state token, exchanges code for Google tokens via `httpx.post()`
4. Verify ID token (RS256 via Google JWKS — cached 6 hours)
5. Upsert user row (google_id, email, name, avatar)
6. Set JWT cookie

### First-User-as-Admin Bootstrap

```python
# On first successful OAuth login ever:
user_count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
if user_count == 0:
    # This is the first user — make them admin
    is_admin = True
```

No manual database editing needed to set up the store.

### Dual Admin Auth

Admin routes accept EITHER:
1. **JWT cookie** with `is_admin: true` (for browser-based admin UI)
2. **`Authorization: Bearer <ATELIER_ADMIN_API_KEY>`** header (for scripts, automation, CI)

```python
async def require_admin(request: Request):
    # Try JWT first
    user = get_current_user_from_jwt(request)
    if user and user.is_admin:
        return user
    # Try API key
    api_key = request.headers.get("Authorization", "").removeprefix("Bearer ")
    if api_key == settings.admin_api_key:
        return AdminKeyUser()  # synthetic admin identity
    raise HTTPException(403)
```

### JWT Structure

```json
{
  "user_id": "abc123",
  "email": "user@example.com",
  "is_admin": true,
  "session_id": "session-uuid",
  "exp": 1720000000
}
```

- Signed with HS256 (symmetric, server-only secret)
- 7-day expiry
- `session_id` embedded for cross-validation (JWT is invalid if session doesn't exist)

---

## Product Catalog

### CSV Bulk Import

For initial catalog setup, admin can upload a CSV:

```
POST /v1/admin/products/import
Content-Type: multipart/form-data

CSV columns: id, name, description, price_cents, category, stock, image_url
```

- Upsert semantics: existing products updated, new products created
- Streaming parse (no full file in memory)
- Returns: `{created: N, updated: N, errors: [{row, message}]}`
- Skips rows with validation errors, continues processing

### Product Image Upload

Admin uploads product photos through the admin panel (or API):

```
POST /v1/admin/products/{id}/image
Content-Type: multipart/form-data
Body: file (JPEG or PNG, max 5MB)
```

**Processing pipeline:**
1. Validate file type (JPEG/PNG only) and size (≤5MB)
2. Resize to standard dimensions:
   - **Main image:** max 1200×1500px (preserving aspect ratio)
   - **Thumbnail:** 400×500px (for product grid cards)
3. Convert to WebP (smaller file size, modern browser support) with JPEG fallback
4. Save to disk:
   - `/opt/atelier/static/products/{product_id}.webp` (main)
   - `/opt/atelier/static/products/{product_id}_thumb.webp` (thumbnail)
5. Update `products.image_url` → `/static/products/{product_id}.webp`

**Serving:**
- Nginx serves `/static/` directly from disk (no Python involvement)
- `Cache-Control: public, max-age=2592000` (30 days — images rarely change)
- Next.js `<Image>` component handles lazy loading + responsive `srcset`

**If no image uploaded:** Show a styled placeholder (CSS gradient in brand colors with product name overlaid). No broken image icons ever.

**Dependencies:** Pillow (Python image library) for resize + WebP conversion.

### Product Search

`GET /v1/products?q=lavender&category=dessert&sort=price_asc&page=1&limit=20`

- Full-text search on name + description (SQLite FTS5 or LIKE fallback)
- Filter: category, price range, in-stock only
- Sort: price_asc, price_desc, name, newest
- Pagination: offset-based (simple, good enough for <1000 products)

---

## Frontend Architecture

### Next.js App Structure

```
frontend/
├── app/
│   ├── layout.tsx              (global shell: header + footer)
│   ├── page.tsx                (homepage: hero + featured)
│   ├── products/
│   │   ├── page.tsx            (product grid + filters)
│   │   └── [id]/page.tsx       (product detail)
│   ├── cart/page.tsx           (full cart view)
│   ├── checkout/page.tsx       (checkout form)
│   ├── orders/
│   │   ├── page.tsx            (order history)
│   │   └── [id]/page.tsx       (order detail + confirmation)
│   ├── account/page.tsx        (profile / login prompt)
│   ├── (admin)/
│   │   ├── dashboard/page.tsx  (stats + recent orders)
│   │   ├── products/page.tsx   (product management)
│   │   └── orders/page.tsx     (order management)
│   └── (static)/
│       ├── candle-care/page.tsx
│       ├── faq/page.tsx
│       └── contact/page.tsx
├── components/
│   ├── layout/                 (Header, Footer, Navigation, AnnouncementBar)
│   ├── product/                (ProductCard, ProductGrid, ProductDetail)
│   ├── cart/                   (CartDrawer, CartItem, CartSummary)
│   ├── checkout/               (CheckoutForm, OrderConfirmation)
│   ├── ui/                     (Button, Input, Badge, Accordion, Skeleton)
│   └── admin/                  (ProductForm, OrderTable, StatsCard)
├── lib/
│   ├── api.ts                  (fetch wrapper — session cookie auto-included)
│   ├── types.ts                (TypeScript interfaces matching backend models)
│   └── utils.ts                (formatPrice, formatDate, etc.)
├── styles/
│   └── globals.css             (Tailwind + custom design tokens)
└── package.json
```

### API Client (`lib/api.ts`)

```typescript
// Wraps fetch with:
// - Credentials: 'include' (sends session cookie)
// - Base URL from env (NEXT_PUBLIC_API_URL)
// - Automatic JSON parse
// - Error handling (non-2xx → throw with status + body)
// - Handles X-Session-Rotated header (updates local reference)

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) throw new ApiError(res.status, await res.json());
  return res.json();
}
```

### Cart State Management

- **React Context** wraps cart state (items, total, count)
- **Optimistic updates:** UI updates immediately on add/remove, reverts on API error
- **Server sync:** Cart fetched on page load, re-fetched after mutations for consistency
- **Badge:** Header cart icon shows live item count from context

---

## Deployment Architecture

### Nginx Configuration

```
server {
    listen 443 ssl;
    server_name ateliermarie.com;

    # API → FastAPI
    location /v1/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Everything else → Next.js
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
    }

    # Static assets (product images)
    location /static/ {
        alias /opt/atelier/static/;
        expires 30d;
    }
}
```

### Process Management

- **FastAPI:** systemd service, 2 uvicorn workers (`--workers 2`)
- **Next.js:** systemd service, `next start` (port 3000)
- **Workers:** 2 uvicorn workers is safe — SQLite WAL supports concurrent readers, and writes are fast enough to not contend

### Backup Strategy

- **Daily at 3am:** `sqlite3 atelier.db ".backup /opt/atelier/backups/atelier-$(date +%F).db"`
- **Retention:** 7 days (cron deletes older backups)
- **Restore:** Stop service → copy backup over → restart

---

## Performance Targets

| Operation | Target | How |
|-----------|--------|-----|
| Product list | <50ms | Single indexed query, pagination |
| Product detail | <30ms | Primary key lookup |
| Add to cart | <50ms | Stock check + insert (2 queries) |
| Checkout | <200ms | Single atomic transaction |
| Full page load (frontend) | <2s mobile 4G | React Server Components, image optimization |
| Admin dashboard | <200ms | Simple COUNT/SUM queries on small tables |

---

## Security Considerations

- **CSRF:** SameSite=Lax cookie + origin checking for state-changing requests
- **SQL injection:** Parameterized queries only (never string interpolation)
- **XSS:** HTTP-only cookies, Content-Security-Policy headers via Nginx
- **Rate limiting:** Nginx `limit_req` on login and checkout endpoints
- **Admin:** API key rotatable via env var; JWT revocable by removing user's admin flag
- **GDPR:** User data deletion = NULL-ify PII fields (email, name, address), preserve order history structure for accounting
