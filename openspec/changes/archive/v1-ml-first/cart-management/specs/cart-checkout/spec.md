# Cart Checkout — Specification

## ADDED Requirements

### Requirement: Checkout creates order from cart

POST /v1/cart/checkout (no body) reads the server-side cart for the session, creates an order with order_items, decrements stock atomically, clears the cart, and returns order details.

#### Scenario: Successful checkout with multiple items

WHEN a client sends POST /v1/cart/checkout
AND the session's cart contains product 5 (qty 2) and product 8 (qty 1)
AND both products are active and have sufficient stock
THEN the response status is 201
AND a new order is created with 2 order_items
AND product 5 stock is decremented by 2
AND product 8 stock is decremented by 1
AND all cart_items for the session are deleted
AND the response includes order_id, items, total, and status="pending"

#### Scenario: Successful checkout with single item

WHEN a client sends POST /v1/cart/checkout
AND the session's cart contains product 3 (qty 1)
AND product 3 is active with stock >= 1
THEN the response status is 201
AND a new order is created with 1 order_item
AND product 3 stock is decremented by 1
AND the cart is cleared

---

### Requirement: Checkout validates stock atomically

All items are validated in a single transaction. If any item has insufficient stock, the entire checkout fails with 409 listing problematic items. No partial orders are created.

#### Scenario: One item out of stock

WHEN a client sends POST /v1/cart/checkout
AND the cart contains product 5 (qty 2) and product 8 (qty 3)
AND product 5 has stock=2 but product 8 has stock=1
THEN the response status is 409
AND the response body lists product 8 as having insufficient stock (requested=3, available=1)
AND no order is created
AND no stock is decremented
AND the cart remains unchanged

#### Scenario: Multiple items out of stock

WHEN a client sends POST /v1/cart/checkout
AND the cart contains 3 items, 2 of which have insufficient stock
THEN the response status is 409
AND the response body lists both problematic items with requested vs available quantities
AND no order is created

#### Scenario: All items have sufficient stock

WHEN a client sends POST /v1/cart/checkout
AND all cart items have sufficient stock
THEN stock validation passes
AND the checkout proceeds to order creation

---

### Requirement: Empty cart checkout fails

POST /v1/cart/checkout with an empty cart returns HTTP 400.

#### Scenario: Cart is empty

WHEN a client sends POST /v1/cart/checkout
AND the session's cart contains no items
THEN the response status is 400
AND the response body contains error "Cart is empty"
AND no order is created

#### Scenario: Cart only contained inactive products (effectively empty)

WHEN a client sends POST /v1/cart/checkout
AND the session's cart_items all reference deactivated products
THEN the response status is 409
AND the response identifies the unavailable products

---

### Requirement: Unavailable products at checkout fail

If the cart contains deactivated products at checkout time, the checkout returns 409 identifying them.

#### Scenario: One product deactivated since adding to cart

WHEN a client sends POST /v1/cart/checkout
AND the cart contains product 5 (active) and product 8 (deactivated)
THEN the response status is 409
AND the response body identifies product 8 as unavailable
AND no order is created
AND no stock is decremented

#### Scenario: Product deleted between cart add and checkout

WHEN a client sends POST /v1/cart/checkout
AND the cart contains product 5 which no longer exists in the products table
THEN the response status is 409
AND the response body identifies product 5 as unavailable

---

### Requirement: Purchase event emitted post-checkout

After successful order creation, a purchase event is emitted to the event pipeline. Event emission is fire-and-forget — failure does not fail the order.

#### Scenario: Event emitted on successful checkout

WHEN a client sends POST /v1/cart/checkout
AND the checkout succeeds (order created)
THEN a purchase event is written to the event pipeline
AND the event contains order_id, session_id, items, and total

#### Scenario: Event emission failure does not fail checkout

WHEN a client sends POST /v1/cart/checkout
AND the checkout succeeds
AND the event pipeline write fails (e.g., disk error)
THEN the response status is still 201
AND the order is still created successfully
AND the cart is still cleared

---

### Requirement: Cart cleared on success

After successful checkout, all cart_items for the session are deleted.

#### Scenario: Cart empty after checkout

WHEN a client sends POST /v1/cart/checkout
AND the checkout succeeds
THEN all cart_items rows for the session are deleted
AND a subsequent GET /v1/cart returns an empty items array with cart_total=0

#### Scenario: Other sessions' carts unaffected

WHEN session "abc" checks out successfully
AND session "xyz" has items in their cart
THEN session "xyz" cart remains unchanged
AND only session "abc" cart_items are deleted
