## ADDED Requirements

### Requirement: View cart contents
The system SHALL provide `GET /v1/cart` that returns all cart items for the current session with embedded product details and computed totals. Inactive/deactivated products SHALL be excluded from the main `items` list but reported in an `unavailable_items` list with human-readable details.

#### Scenario: View cart with items
- **WHEN** the session has 2 items in the cart (both products active)
- **THEN** the response is 200 with `items` (array of 2 CartItemResponse with embedded ProductResponse), `total_cents` (sum of price_cents × quantity), and `item_count` (sum of quantities)

#### Scenario: View empty cart
- **WHEN** the session has no items in the cart
- **THEN** the response is 200 with `items: []`, `total_cents: 0`, `item_count: 0`, `unavailable_items: []`

#### Scenario: Cart item references deactivated product
- **WHEN** a cart item references a product with `is_active = 0`
- **THEN** that item is excluded from `items` and reported in `unavailable_items` as `{"product_id": "...", "product_name": "...", "reason": "deactivated"}`

**Design note:** Including `product_name` in `unavailable_items` is an intentional UX choice — users need to know which of their saved items became unavailable. The information was already visible when the product was active. For a family candle business, deactivation reasons are benign (seasonal rotation, sold out permanently). If catalog secrecy ever becomes a concern, `product_name` can be replaced with a generic label without breaking the contract shape.

### Requirement: Add item to cart
The system SHALL provide `POST /v1/cart` that adds a product to the cart for the current session. If the product is already in the cart, the quantity SHALL be incremented by the requested amount. The service SHALL return a `created: bool` flag indicating whether a new cart item was created (for the route to select 201 vs 200 status).

#### Scenario: Add new item to cart
- **WHEN** `POST /v1/cart` with `{"product_id": "lavender-dream-300ml", "quantity": 2}` and the product is not already in the cart
- **THEN** a new cart_items row is created with quantity 2, and the response is 201 with the updated full cart

#### Scenario: Add existing item increases quantity
- **WHEN** `POST /v1/cart` with `{"product_id": "lavender-dream-300ml", "quantity": 1}` and the product is already in the cart with quantity 2
- **THEN** the cart_items quantity is updated to 3, and the response is 200 with the updated full cart

#### Scenario: Add item for non-existent product
- **WHEN** `POST /v1/cart` with a `product_id` that does not exist in the products table
- **THEN** the response is 404 with error code `PRODUCT_NOT_FOUND`

#### Scenario: Add item for inactive product
- **WHEN** `POST /v1/cart` with a `product_id` where `is_active = 0`
- **THEN** the response is 404 with error code `PRODUCT_NOT_FOUND`

### Requirement: Stock validation on add
The system SHALL validate available stock when adding to cart. If `products.stock < requested_total_quantity` (existing cart quantity + new quantity), the system SHALL reject with 409 Conflict and include the available stock count. The `available` field reports the total warehouse stock (not "remaining after cart").

**Advisory nature:** Stock validation on cart-add is best-effort. Multiple sessions may simultaneously hold items that exceed total stock. The atomic `CHECK (stock >= 0)` constraint enforced within the checkout transaction is the authoritative guard. This check provides immediate user feedback, not a reservation guarantee.

**Information disclosure note:** The `available` count in the 409 response intentionally exposes exact stock levels to anonymous sessions. This is a deliberate UX choice — users see how many they can actually add. At the scale of a small family candle business, this does not represent a meaningful competitive intelligence risk. If the threat model changes (e.g., wholesale competitors), the response can be degraded to a boolean or banded indicator without API contract breakage (the field remains, just capped).

#### Scenario: Sufficient stock
- **WHEN** product has stock = 5 and user adds quantity 3 (no existing cart item)
- **THEN** the item is added successfully

#### Scenario: Insufficient stock on new add
- **WHEN** product has stock = 2 and user adds quantity 5
- **THEN** the response is 409 with `{"error": {"code": "INSUFFICIENT_STOCK", "message": "...", "details": {"product_id": "...", "requested": 5, "available": 2}}}`

#### Scenario: Insufficient stock with existing cart quantity
- **WHEN** product has stock = 5, user already has 3 in cart, and adds 4 more (total would be 7)
- **THEN** the response is 409 with `available: 5` (total stock, not remaining after cart). The frontend computes max addable as `available - current_cart_quantity`.

### Requirement: Quantity limits enforced
The system SHALL enforce a maximum quantity of 10 per item (configurable) and a maximum of 20 distinct items per cart. These limits SHALL be validated on add and update operations. The Pydantic model uses a wider bound (`le=99`) because the per-item limit is configurable; the service layer is the authoritative enforcement point.

#### Scenario: Per-item quantity limit exceeded on add
- **WHEN** adding quantity that would bring total for one product above 10 (e.g., existing qty 8, add 4 → total 12)
- **THEN** the response is 422 with error code `QUANTITY_LIMIT_EXCEEDED` and `max_quantity: 10`

#### Scenario: Cart full (max distinct items)
- **WHEN** the cart already has 20 distinct products and user tries to add a new product
- **THEN** the response is 422 with error code `CART_FULL` and `max_items: 20`

#### Scenario: Adding more of an existing item when cart is full
- **WHEN** the cart has 20 distinct products and user adds more quantity of an already-in-cart product
- **THEN** the operation succeeds (not adding a new distinct item)

### Requirement: Update cart item quantity
The system SHALL provide `PATCH /v1/cart/{product_id}` that sets the quantity of a cart item to the specified absolute value. Setting quantity to 0 SHALL remove the item. Stock validation on update compares `products.stock` against the new absolute `quantity` value (not the difference from current quantity), since the quantity is being SET, not incremented.

#### Scenario: Update quantity to valid value
- **WHEN** `PATCH /v1/cart/lavender-dream-300ml` with `{"quantity": 5}` and product has stock >= 5
- **THEN** the cart_items row is updated to quantity 5, response is 200 with updated full cart

#### Scenario: Update quantity to zero removes item
- **WHEN** `PATCH /v1/cart/lavender-dream-300ml` with `{"quantity": 0}`
- **THEN** the cart_items row is deleted, response is 200 with updated full cart

#### Scenario: Update quantity exceeds stock
- **WHEN** `PATCH /v1/cart/lavender-dream-300ml` with `{"quantity": 8}` but product has stock = 5
- **THEN** the response is 409 with `INSUFFICIENT_STOCK` and `available: 5`

#### Scenario: Update quantity exceeds per-item limit
- **WHEN** `PATCH /v1/cart/lavender-dream-300ml` with `{"quantity": 15}`
- **THEN** the response is 422 with `QUANTITY_LIMIT_EXCEEDED`

#### Scenario: Update non-existent cart item
- **WHEN** `PATCH /v1/cart/some-product` but that product is not in the session's cart
- **THEN** the response is 404 with error code `CART_ITEM_NOT_FOUND`

### Requirement: Remove item from cart
The system SHALL provide `DELETE /v1/cart/{product_id}` that removes an item from the cart entirely.

#### Scenario: Remove existing item
- **WHEN** `DELETE /v1/cart/lavender-dream-300ml` and the item exists in the cart
- **THEN** the cart_items row is deleted, response is 200 with updated full cart

#### Scenario: Remove non-existent item
- **WHEN** `DELETE /v1/cart/some-product` but that product is not in the session's cart
- **THEN** the response is 404 with error code `CART_ITEM_NOT_FOUND`

### Requirement: Path parameter validation on cart endpoints
The `{product_id}` path parameter in PATCH and DELETE endpoints SHALL be validated with the same format constraints as the `product_id` field in `AddToCartRequest`: pattern `^[a-z0-9]+(-[a-z0-9]+)*$`, max length 100 characters. Invalid path parameters SHALL return 422.

#### Scenario: Malformed product_id in path rejected
- **WHEN** `DELETE /v1/cart/UPPER_CASE` or `PATCH /v1/cart/has spaces`
- **THEN** the response is 422 (FastAPI path validation)

#### Scenario: Oversized product_id in path rejected
- **WHEN** `DELETE /v1/cart/{101-character-string}`
- **THEN** the response is 422

### Requirement: Cart keyed by session (anonymous-first)
The system SHALL key all cart operations by `session_id` from `request.state.session_id`. No authentication SHALL be required to use the cart. Cart items persist for the lifetime of the session (30 days sliding).

#### Scenario: Anonymous user adds to cart
- **WHEN** an unauthenticated user (no login, just session cookie) adds an item
- **THEN** the item is stored in cart_items keyed by their session_id

#### Scenario: Different sessions have independent carts
- **WHEN** two different sessions each add items
- **THEN** `GET /v1/cart` for each session returns only their own items

### Requirement: Database constraints as safety net
The `products` table SHALL have `CHECK (stock >= 0)` and the `cart_items` table SHALL have `CHECK (quantity >= 1)`. These constraints serve as last-resort defense — service logic prevents violations, but the DB catches bugs. The cart_items FK to sessions SHALL use `ON DELETE CASCADE` so expired session cleanup also removes orphaned cart items.

#### Scenario: CHECK constraint prevents negative stock
- **WHEN** a bug or race condition attempts to set `products.stock` to a negative value
- **THEN** the database rejects the operation with a constraint violation error

#### Scenario: CHECK constraint prevents zero quantity in cart
- **WHEN** a bug attempts to update `cart_items.quantity` to 0 without deleting the row
- **THEN** the database rejects the operation with a constraint violation error

#### Scenario: Session cleanup cascades to cart_items
- **WHEN** an expired session row is deleted by the cleanup job
- **THEN** all associated cart_items rows are automatically deleted via ON DELETE CASCADE

### Requirement: Cart response is intentionally unpaginated
The `GET /v1/cart` endpoint does NOT paginate results. This is intentional: the 20-item distinct cap guarantees a bounded response size (max 20 items with embedded product details). If the max-items limit is ever raised above 50, pagination should be reconsidered.

#### Scenario: Full cart returns all items in one response
- **WHEN** a session has 20 items in the cart
- **THEN** all 20 items are returned in a single response (no pagination needed)
