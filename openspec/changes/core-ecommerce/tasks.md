# Core E-Commerce — Tasks

## Setup (Day 1)

- [ ] Create `pyproject.toml` with dependencies (fastapi, uvicorn, pydantic, pyjwt, httpx)
- [ ] Create `app/` package structure
- [ ] Create `app/config.py` (pydantic-settings: DB path, JWT secret, OAuth credentials, admin API key)
- [ ] Create `app/database.py` (SQLite connection, WAL mode, schema init)
- [ ] Create `app/main.py` (app factory, lifespan, router registration)
- [ ] Create `conftest.py` with test database fixture

## Product Catalog (Day 2)

- [ ] Define `products` table schema (text PK as SKU/slug, price_cents, stock CHECK >= 0)
- [ ] Create `app/models/products.py` (ProductCreate, ProductUpdate, ProductResponse, ProductList)
- [ ] Create `app/services/product_service.py` (list, get, create, update, deactivate, search)
- [ ] Create `app/routes/products.py` (public GET endpoints with category filter, search, pagination)
- [ ] Create `app/routes/admin.py` (admin CRUD + CSV bulk import endpoint)
- [ ] Implement CSV import: streaming parse, upsert semantics, error reporting per row
- [ ] Write tests for product service
- [ ] Seed script with ~10 sample candle products

## Session + Cart (Day 3)

- [ ] Define `sessions` and `cart_items` table schemas
- [ ] Upgrade `app/middleware/session.py` to eager DB sessions: INSERT row on new visit, validate + UPDATE expires_at on returning visit, import `get_db()`, handle expired/invalid cookies as new visitors
- [ ] Create `app/models/cart.py` (CartItem, CartResponse, AddToCartRequest)
- [ ] Create `app/services/cart_service.py` (get_cart, add_item, update_quantity, remove_item)
- [ ] Stock validation on add (immediate 409 if out of stock, not just at checkout)
- [ ] Quantity limits (max 10 per item, max 20 distinct items)
- [ ] Create `app/routes/cart.py` (GET/POST/PATCH/DELETE)
- [ ] Write tests for cart service (stock validation, quantity limits, update-to-zero = remove)

## Checkout + Orders (Day 4)

- [ ] Define `orders` and `order_items` table schemas (stock CHECK constraint >= 0)
- [ ] Create `app/models/orders.py` (OrderCreate, OrderResponse, OrderItemResponse)
- [ ] Create `app/services/order_service.py` (checkout, list_orders, get_order, update_status)
- [ ] Implement order state machine (valid transitions only, 422 on invalid)
- [ ] Implement stock restoration on cancellation
- [ ] Create `app/routes/orders.py` (POST /orders, GET /orders, GET /orders/{id})
- [ ] Add admin order routes to `app/routes/admin.py` (list all, update status)
- [ ] Write tests for checkout flow (happy path, out-of-stock, empty cart, race condition, cancellation restores stock)

## Authentication (Day 5)

- [ ] Define `users` table schema
- [ ] Create `app/models/users.py` (UserResponse)
- [ ] Create `app/services/auth_service.py` (OAuth flow via httpx, JWT create/verify, first-admin logic)
- [ ] Create `app/routes/auth.py` (login redirect, callback, me, logout)
- [ ] Implement JWKS verification with 6-hour cache
- [ ] Implement first-user-as-admin bootstrap (no manual DB edits needed)
- [ ] Add `get_current_user` dependency (optional + required variants)
- [ ] Add dual admin auth: JWT is_admin OR Bearer API key
- [ ] Session rotation on logout (new session ID, old one cleared, X-Session-Rotated header)
- [ ] Link session to user on login (update sessions.user_id)
- [ ] Write tests for auth (mock Google OAuth, first-admin, session rotation)

## Product Images (Day 5, alongside auth)

- [ ] Add Pillow dependency
- [ ] Create `app/services/image_service.py` (validate, resize to 1200×1500 + 400×500 thumb, convert to WebP)
- [ ] Create `POST /v1/admin/products/{id}/image` endpoint (multipart upload, max 5MB)
- [ ] Create `/static/products/` directory, configure Nginx to serve it with 30-day cache
- [ ] Styled CSS placeholder for products without images (brand gradient + product name)
- [ ] Write tests (upload JPEG, verify WebP output, reject oversized/wrong type)

## Frontend (Days 6–9)

- [ ] Init Next.js project in `frontend/`
- [ ] Create API client (`lib/api.ts`) with session cookie handling
- [ ] Product listing page (grid, category filter)
- [ ] Product detail page (image, description, price, add-to-cart button)
- [ ] Cart page/drawer (items, quantities, total, checkout button)
- [ ] Checkout page (email, name, address form → submit)
- [ ] Order confirmation page
- [ ] Login/account button (Google OAuth)
- [ ] My orders page
- [ ] Admin: product list + create/edit form
- [ ] Admin: order list + status update
- [ ] Mobile responsive (all pages)
- [ ] Basic design system (colors, typography — luxury candle aesthetic)

## Deployment (Day 10)

- [ ] Create `deploy/nginx.conf` (proxy /v1/ → FastAPI:8000, / → Next.js:3000, /static/ → disk, SSL)
- [ ] Create `deploy/atelier-api.service` (systemd unit, uvicorn --workers 2)
- [ ] Create `deploy/atelier-frontend.service` (systemd unit, next start)
- [ ] Create `deploy/setup.sh` (provision VPS: Python 3.11, Node.js, Nginx, certbot, app user)
- [ ] Create `deploy/deploy.sh` (git pull, pip install, next build, restart services)
- [ ] Create `.github/workflows/ci.yml` (lint, test, deploy on push to main)
- [ ] Create `deploy/backup.sh` (daily SQLite backup, 7-day retention)
- [ ] Add Nginx rate limiting on /v1/auth/* and /v1/orders
- [ ] Verify full deployment end-to-end

---

**Total: ~55 tasks, 2 weeks, 1 developer.**
