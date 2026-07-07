## 1. Models Package Setup

- [x] 1.1 Create `app/models/__init__.py` with re-exports of all public schemas
- [x] 1.2 Create `app/models/common.py` with `ErrorDetail`, `ErrorResponse`, `PaginationParams` schemas

## 2. Product Models

- [x] 2.1 Create `app/models/products.py` with `ProductResponse` (id, name, description, price, category, image_url, stock, is_active, is_featured, created_at, updated_at)
- [x] 2.2 Add `ProductListResponse` (products list, total, page, limit)
- [x] 2.3 Add `CreateProductRequest` with validation (name required, price > 0, stock >= 0, is_active default True, is_featured default False)
- [x] 2.4 Add `UpdateProductRequest` with all fields optional (partial update pattern)
- [x] 2.5 Add `ProductImportRequest` (products: list[CreateProductRequest])

## 3. Cart Models

- [x] 3.1 Create `app/models/cart.py` with `CartItemResponse` (product_id, product: ProductResponse, quantity, added_at)
- [x] 3.2 Add `CartResponse` (items list, total, item_count)
- [x] 3.3 Add `AddToCartRequest` (product_id required, quantity >= 1 default 1)
- [x] 3.4 Add `UpdateCartItemRequest` (quantity >= 0, where 0 means remove)

## 4. Order Models

- [x] 4.1 Create `app/models/orders.py` with `OrderItemResponse` (product_id, product_name, price, quantity)
- [x] 4.2 Add `OrderResponse` (id, status literal, total, customer_email, customer_name, shipping_address, items list, created_at, updated_at)
- [x] 4.3 Add `OrderListResponse` (orders list, total, page, limit)
- [x] 4.4 Add `CreateOrderRequest` with email validation (customer_email required + valid, customer_name, shipping_address, notes optional)
- [x] 4.5 Add `UpdateOrderStatusRequest` with status constrained to valid values (pending|confirmed|shipped|delivered|cancelled)

## 5. User & Auth Models

- [x] 5.1 Create `app/models/users.py` with `UserResponse` (id, email, name, avatar_url, is_admin)
- [x] 5.2 Create `app/models/auth.py` with `AuthTokenResponse` (access_token, token_type="bearer", user: UserResponse)
- [x] 5.3 Add `GoogleAuthRequest` (code required, redirect_uri required)

## 6. Config & App Factory Extensions

- [x] 6.1 Add `cors_origins: list[str]` (default `["http://localhost:3000"]`) and `static_file_path: str` (default `"./static"`) to `app/config.py` Settings class
- [x] 6.2 Add CORS middleware to `app/main.py` using `fastapi.middleware.cors.CORSMiddleware` with configured origins
- [x] 6.3 Create stub router files: `app/routes/__init__.py`, `app/routes/products.py`, `app/routes/cart.py`, `app/routes/orders.py`, `app/routes/auth.py`, `app/routes/admin.py` — each with an APIRouter and a single catch-all that returns 501 with ErrorResponse shape
- [x] 6.4 Register all routers in `app/main.py` with prefixes: /v1/products, /v1/cart, /v1/orders, /v1/auth, /v1/admin

## 7. Frontend Scaffold

- [x] 7.1 Initialize Next.js 14 project in `frontend/` with TypeScript, App Router, ESLint (use `create-next-app` or manual `package.json` + `tsconfig.json` + `next.config.js`)
- [x] 7.2 Create `frontend/lib/types.ts` with TypeScript interfaces mirroring all Pydantic response models (ProductResponse, ProductListResponse, CartItemResponse, CartResponse, OrderResponse, OrderItemResponse, OrderListResponse, UserResponse, AuthTokenResponse, ErrorResponse)
- [x] 7.3 Create `frontend/lib/api-client.ts` with typed `fetch` wrapper: base URL from `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`), error parsing into ErrorResponse, generic `get<T>()` / `post<T>()` helpers
- [x] 7.4 Create `frontend/lib/mock-api.ts` with all mock functions: getProducts, getProduct, getCart, addToCart, updateCartItem, removeFromCart, createOrder, getOrders, getOrder, getCurrentUser, login — each returning realistic hardcoded data matching the types
- [x] 7.5 Add `NEXT_PUBLIC_USE_MOCK_API` environment flag; mock-api.ts functions are used when true (default), api-client.ts functions when false
- [x] 7.6 Create `frontend/.env.local.example` documenting `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_USE_MOCK_API`

## 8. Tests & Verification

- [x] 8.1 Create `tests/test_models.py` — verify all models instantiate with valid data, reject invalid data (price <= 0, invalid email, quantity < 0, invalid order status)
- [x] 8.2 Create `tests/test_routers.py` — verify all stub routers return 501 with correct ErrorResponse shape
- [x] 8.3 Verify `app/models/__init__.py` re-exports work: `from app.models.products import ProductResponse` etc.
- [x] 8.4 Run `pytest` — all tests pass
- [x] 8.5 Run `ruff check .` — no lint errors
- [x] 8.6 Run `cd frontend && npm install && npx tsc --noEmit` — TypeScript compiles without errors
