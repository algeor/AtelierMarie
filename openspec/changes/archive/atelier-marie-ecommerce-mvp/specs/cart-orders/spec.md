## ADDED Requirements

### Requirement: Get cart contents
The system SHALL expose GET /cart that returns the current cart items for the session. Each item SHALL include product_id, product name, product image_url, price, quantity, and line subtotal.

#### Scenario: Get cart with items
- **WHEN** a client with session_id "abc-123" sends GET /cart and has 2 items in cart
- **THEN** the API returns both items with product details, quantities, subtotals, and cart total

#### Scenario: Get empty cart
- **WHEN** a client with no items sends GET /cart
- **THEN** the API returns an empty items array and total of 0

### Requirement: Add item to cart
The system SHALL expose POST /cart/add accepting product_id and quantity. It SHALL validate stock availability and return the updated cart. If the product already exists in cart, quantity SHALL be incremented.

#### Scenario: Add new item to cart
- **WHEN** a client sends POST /cart/add with product_id 5 and quantity 1
- **THEN** the item is added to the cart and updated cart is returned

#### Scenario: Add existing item increments quantity
- **WHEN** a client adds product_id 5 which is already in cart with quantity 1
- **THEN** the cart item quantity becomes 2

#### Scenario: Adding exceeds stock returns error
- **WHEN** a client tries to add quantity 10 of a product with stock_quantity 3
- **THEN** the API returns HTTP 409 with message "Insufficient stock"

### Requirement: Update cart item quantity
The system SHALL expose PATCH /cart/item accepting product_id and new quantity. Setting quantity to 0 SHALL remove the item.

#### Scenario: Update quantity
- **WHEN** a client sends PATCH /cart/item with product_id 5 and quantity 3
- **THEN** the cart item quantity is updated to 3 and updated cart returned

#### Scenario: Set quantity to zero removes item
- **WHEN** a client sends PATCH /cart/item with product_id 5 and quantity 0
- **THEN** the item is removed from the cart

### Requirement: Remove item from cart
The system SHALL expose DELETE /cart/item accepting product_id. The item SHALL be removed and the updated cart returned.

#### Scenario: Remove existing item
- **WHEN** a client sends DELETE /cart/item with product_id 5
- **THEN** the item is removed and updated cart (without that item) is returned

#### Scenario: Remove non-existent item returns 404
- **WHEN** a client sends DELETE /cart/item with a product_id not in their cart
- **THEN** the API returns HTTP 404 with message "Item not in cart"

### Requirement: Checkout creates order
The system SHALL expose POST /checkout that converts the current cart into an order. It SHALL validate stock, decrement stock quantities, create order and order_items records, clear the cart, and return the order details.

#### Scenario: Successful checkout
- **WHEN** a client with 2 cart items sends POST /checkout and all items are in stock
- **THEN** an order is created with status "pending", stock is decremented, cart is cleared, and order details are returned with HTTP 201

#### Scenario: Checkout with out-of-stock item fails
- **WHEN** a client sends POST /checkout but one item's requested quantity exceeds stock
- **THEN** the API returns HTTP 409 identifying the out-of-stock item, no order is created, cart is unchanged

#### Scenario: Checkout with empty cart fails
- **WHEN** a client with an empty cart sends POST /checkout
- **THEN** the API returns HTTP 400 with message "Cart is empty"

### Requirement: Get order details
The system SHALL expose GET /orders/{id} that returns order details including items, total, status, and created_at. Access SHALL be restricted to the session or user that created the order.

#### Scenario: Owner retrieves order
- **WHEN** the session/user that created order 42 sends GET /orders/42
- **THEN** the full order details are returned

#### Scenario: Non-owner access denied
- **WHEN** a different session/user sends GET /orders/42
- **THEN** the API returns HTTP 403

### Requirement: Cart persists across page loads
The system SHALL persist cart state server-side keyed by session_id. Cart contents SHALL survive browser refresh and be available across multiple tabs.

#### Scenario: Cart survives browser refresh
- **WHEN** a user adds items to cart, refreshes the page, and opens the cart
- **THEN** all previously added items are present with correct quantities
