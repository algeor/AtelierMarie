# Cart State — Specification

## ADDED Requirements

### Requirement: Get cart contents

GET /v1/cart returns the current session's cart items with product details and computed totals.

#### Scenario: Retrieve cart with items

WHEN a client sends GET /v1/cart with a valid X-Session-ID header
AND the session has 2 items in the cart
THEN the response status is 200
AND the response body contains an `items` array with 2 entries
AND each item includes product_id, name, image_url, price, quantity, and line_subtotal
AND the response includes a cart_total equal to the sum of all line_subtotals

#### Scenario: Retrieve empty cart

WHEN a client sends GET /v1/cart with a valid X-Session-ID header
AND the session has no items in the cart
THEN the response status is 200
AND the response body contains an empty `items` array
AND cart_total is 0

#### Scenario: Cart excludes inactive products

WHEN a client sends GET /v1/cart
AND one of the cart items references a product that has been deactivated
THEN the response status is 200
AND the deactivated product is excluded from the `items` array
AND the response includes a `removed_unavailable` flag set to true

---

### Requirement: Add item to cart

POST /v1/cart/items adds a product to the cart with stock validation. Increments quantity if already present.

#### Scenario: Add new item to cart

WHEN a client sends POST /v1/cart/items with product_id=5 and quantity=2
AND product 5 exists, is active, and has stock >= 2
AND the item is not already in the cart
THEN the response status is 201
AND the cart_items table contains a row with session_id, product_id=5, quantity=2
AND the response body contains the updated cart
AND an add_to_cart event is emitted with product_id=5, quantity=2

#### Scenario: Add item already in cart (increment)

WHEN a client sends POST /v1/cart/items with product_id=5 and quantity=1
AND product 5 is already in the cart with quantity=2
AND product 5 has stock >= 3
THEN the response status is 200
AND the cart item quantity is updated to 3
AND an add_to_cart event is emitted with product_id=5, quantity=1

#### Scenario: Add item with insufficient stock

WHEN a client sends POST /v1/cart/items with product_id=5 and quantity=10
AND product 5 has stock of 3
THEN the response status is 409
AND the response body contains "Insufficient stock" with available_quantity=3
AND no cart_items row is created or updated

---

### Requirement: Update cart item quantity

PATCH /v1/cart/items/{product_id} updates the quantity of an item in the cart. Setting quantity to 0 removes the item.

#### Scenario: Increase item quantity

WHEN a client sends PATCH /v1/cart/items/5 with quantity=4
AND product 5 is in the cart with quantity=2
AND product 5 has stock >= 4
THEN the response status is 200
AND the cart item quantity is updated to 4
AND the response body contains the updated cart

#### Scenario: Set quantity to zero (remove)

WHEN a client sends PATCH /v1/cart/items/5 with quantity=0
AND product 5 is in the cart
THEN the response status is 200
AND the cart item for product 5 is deleted
AND a remove_from_cart event is emitted with product_id=5

#### Scenario: Update quantity exceeds stock

WHEN a client sends PATCH /v1/cart/items/5 with quantity=20
AND product 5 has stock of 8
THEN the response status is 409
AND the response body contains "Insufficient stock" with available_quantity=8
AND the cart item quantity remains unchanged

---

### Requirement: Remove item from cart

DELETE /v1/cart/items/{product_id} removes an item from the cart entirely.

#### Scenario: Remove existing item

WHEN a client sends DELETE /v1/cart/items/5
AND product 5 is in the session's cart
THEN the response status is 200
AND the cart_items row for product 5 is deleted
AND a remove_from_cart event is emitted with product_id=5

#### Scenario: Remove item not in cart

WHEN a client sends DELETE /v1/cart/items/99
AND product 99 is not in the session's cart
THEN the response status is 404
AND the response body contains an error message indicating the item is not in the cart

---

### Requirement: Cart persists across page loads

Cart state is stored server-side keyed by session_id. It survives browser refresh and works across tabs sharing the same session.

#### Scenario: Cart survives page refresh

WHEN a client adds product 5 to the cart
AND the client sends a new GET /v1/cart request (simulating page reload) with the same X-Session-ID
THEN the response contains product 5 in the items array

#### Scenario: Cart accessible from multiple tabs

WHEN tab A adds product 5 to the cart with session_id "abc-123"
AND tab B sends GET /v1/cart with session_id "abc-123"
THEN tab B's response contains product 5 in the items array

---

### Requirement: Inactive products filtered from cart display

If a product is deactivated after being added to the cart, GET /v1/cart excludes it with a flag indicating items were removed.

#### Scenario: Product deactivated after adding to cart

WHEN a client added product 5 to the cart while it was active
AND product 5 is subsequently deactivated (is_active=false)
AND the client sends GET /v1/cart
THEN the response does not include product 5 in the items array
AND the response includes removed_unavailable=true

#### Scenario: All products active

WHEN all products in the cart are active
AND the client sends GET /v1/cart
THEN removed_unavailable is false or absent

---

### Requirement: Stock validation on add

Adding more than the available stock returns HTTP 409 with the available quantity.

#### Scenario: Request exceeds available stock

WHEN a client sends POST /v1/cart/items with product_id=5 and quantity=15
AND product 5 has stock_quantity=7
THEN the response status is 409
AND the response body includes error "Insufficient stock"
AND the response body includes available_quantity=7

#### Scenario: Request exactly equals available stock

WHEN a client sends POST /v1/cart/items with product_id=5 and quantity=7
AND product 5 has stock_quantity=7
THEN the response status is 201
AND the item is added to the cart with quantity=7

#### Scenario: Increment would exceed stock

WHEN product 5 is already in the cart with quantity=5
AND the client sends POST /v1/cart/items with product_id=5 and quantity=4
AND product 5 has stock_quantity=7
THEN the response status is 409
AND the response body includes "Insufficient stock" with available_quantity=7
AND the cart item quantity remains at 5

---

### Requirement: Cart state is never cached

The system SHALL always read cart state directly from SQLite on every request. Cart data is highly mutable and personal — caching introduces correctness risks (stale quantities, phantom items after removal) that outweigh any latency benefit given SQLite WAL reads complete in <5ms. This is an intentional architectural decision, not an oversight.

#### Scenario: Concurrent cart modifications reflect immediately

WHEN a user adds an item via POST /v1/cart/items
AND immediately sends GET /v1/cart
THEN the added item appears in the response with no stale delay

#### Scenario: No in-memory caching layer applied to cart endpoints

WHEN the application serves GET /v1/cart, POST /v1/cart/items, PATCH /v1/cart/items/{id}, or DELETE /v1/cart/items/{id}
THEN every request reads from and writes to SQLite directly
AND no TTL cache, response cache, or memoization layer is applied
