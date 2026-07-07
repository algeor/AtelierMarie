## ADDED Requirements

### Requirement: Next.js project initializes with TypeScript
The frontend SHALL be a Next.js 14 application using the App Router with TypeScript strict mode enabled, located in the `frontend/` directory.

#### Scenario: Fresh install and dev server
- **WHEN** a developer runs `npm install && npm run dev` in `frontend/`
- **THEN** the Next.js development server starts without TypeScript errors

#### Scenario: Strict TypeScript
- **WHEN** `tsconfig.json` is inspected
- **THEN** `strict: true` is set and no `any` types exist in the type definitions

### Requirement: TypeScript types mirror Pydantic models exactly
The frontend SHALL have a `frontend/lib/types.ts` file containing TypeScript interfaces that match every Pydantic response model field-for-field, including nullability.

#### Scenario: ProductResponse type matches Python model
- **WHEN** the Python `ProductResponse` has `price_cents: int` and `description: str | None`
- **THEN** the TypeScript `ProductResponse` has `price_cents: number` and `description: string | null`

#### Scenario: All response types covered
- **WHEN** `frontend/lib/types.ts` is inspected
- **THEN** it contains interfaces for: ProductResponse, ProductListResponse, CartItemResponse, CartResponse, OrderResponse, OrderItemResponse, OrderListResponse, UserResponse, AuthTokenResponse, ErrorResponse

### Requirement: Mock API provides typed async functions
The frontend SHALL have a `frontend/lib/mock-api.ts` file that exports async functions returning hardcoded data conforming to the TypeScript types.

#### Scenario: getProducts returns typed data
- **WHEN** `getProducts()` is called
- **THEN** it returns a `Promise<ProductListResponse>` with realistic mock product data (at least 3 products)

#### Scenario: getCart returns typed data
- **WHEN** `getCart()` is called
- **THEN** it returns a `Promise<CartResponse>` with mock cart items and correct total calculation

#### Scenario: All API functions present
- **WHEN** `frontend/lib/mock-api.ts` is inspected
- **THEN** it exports functions for: getProducts, getProduct, getCart, addToCart, updateCartItem, removeFromCart, createOrder, getOrders, getOrder, getCurrentUser, login

### Requirement: Mock API flag enables switching to real API
The frontend SHALL have a `USE_MOCK_API` configuration flag (environment variable) that controls whether API calls use mock data or real fetch requests.

#### Scenario: Mock mode (default in development)
- **WHEN** `NEXT_PUBLIC_USE_MOCK_API=true` (or unset)
- **THEN** all API functions return mock data without network requests

#### Scenario: Real mode
- **WHEN** `NEXT_PUBLIC_USE_MOCK_API=false`
- **THEN** API functions make HTTP requests to the configured backend URL

### Requirement: API client centralizes backend communication
The frontend SHALL have a `frontend/lib/api-client.ts` that wraps `fetch` with the backend base URL, error handling, and type casting. Mock and real implementations share the same function signatures.

#### Scenario: Base URL configuration
- **WHEN** `NEXT_PUBLIC_API_URL` environment variable is set
- **THEN** all real API requests target that base URL (default: `http://localhost:8000`)

#### Scenario: Error responses parsed
- **WHEN** the backend returns a non-2xx response
- **THEN** the client parses the ErrorResponse body and throws a typed error
