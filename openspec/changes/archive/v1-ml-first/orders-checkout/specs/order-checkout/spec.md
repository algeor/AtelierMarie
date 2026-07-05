## ADDED Requirements

### Requirement: Create order via checkout
The system SHALL accept a checkout request containing a list of items (product_id + quantity) and an optional payment_method, and create an order with order_items in a single atomic SQLite transaction.

#### Scenario: Successful checkout with authenticated user
- **WHEN** an authenticated user sends POST /v1/orders with valid items and X-Session-ID header
- **THEN** the system creates an order with user_id set, session_id set, status "pending", payment_method set (default "cod"), and total_price calculated from current product prices; returns 201 with the order object

#### Scenario: Successful checkout as anonymous user
- **WHEN** a request without authentication sends POST /v1/orders with valid items and X-Session-ID header
- **THEN** the system creates an order with user_id NULL, session_id from header, status "pending", payment_method "cod"; returns 201

#### Scenario: Missing session ID
- **WHEN** a checkout request is sent without X-Session-ID header
- **THEN** the system returns 422 with error indicating session_id is required

#### Scenario: Empty items list
- **WHEN** a checkout request is sent with an empty items array
- **THEN** the system returns 422 with error indicating at least one item is required

#### Scenario: Invalid product ID
- **WHEN** a checkout request references a product_id that does not exist
- **THEN** the system returns 404 with error identifying the invalid product_id

#### Scenario: Inactive product
- **WHEN** a checkout request references a product_id where is_active is FALSE
- **THEN** the system returns 409 with error indicating the product is no longer available

### Requirement: Price snapshot at purchase time
The system SHALL record the product price at the moment of purchase in `price_at_purchase` on each order_item. This value MUST NOT change if the product price is subsequently updated.

#### Scenario: Price captured at checkout
- **WHEN** an order is created for a product with price 29.99
- **THEN** the order_item.price_at_purchase is 29.99 regardless of future product price changes

#### Scenario: Total calculated from current prices
- **WHEN** an order is created with items [{product_id: "A", quantity: 2, price: 10.00}, {product_id: "B", quantity: 1, price: 5.00}]
- **THEN** the order.total_price is 25.00 (server-calculated, not client-provided)

### Requirement: Purchase event emission
The system SHALL emit a `purchase` event to the JSONL buffer after successful order creation. The event MUST contain order_id, items with prices, total_price, session_id, and user_id (or null) in metadata.

#### Scenario: Event emitted after successful order
- **WHEN** an order is successfully committed to SQLite
- **THEN** a purchase event is written to the JSONL buffer with event_type "purchase" and metadata containing order_id, items array, and total_price

#### Scenario: Event failure does not fail the order
- **WHEN** an order is committed but the JSONL write fails (e.g., disk full)
- **THEN** the order creation still returns 201 success, and the failure is logged at WARNING level

### Requirement: Atomic order creation
The system SHALL create the order row and all order_items rows within a single SQLite transaction. If any insert fails, the entire operation MUST be rolled back.

#### Scenario: Transaction rollback on partial failure
- **WHEN** the order row is inserted but an order_item insert fails (e.g., FK violation on product_id)
- **THEN** the entire transaction is rolled back — no order row and no order_items rows persist

### Requirement: Duplicate quantity validation
The system SHALL reject checkout requests where the same product_id appears more than once in the items array.

#### Scenario: Duplicate product in items
- **WHEN** a checkout request contains two items with the same product_id
- **THEN** the system returns 422 with error indicating duplicate product_ids are not allowed

### Requirement: Payment method selection
The system SHALL accept an optional `payment_method` field on checkout. The field MUST be validated against the set of supported methods. For MVP, the only supported value is `"cod"` (cash on delivery). If omitted, it defaults to `"cod"`.

#### Scenario: Default payment method
- **WHEN** a checkout request does not include a payment_method field
- **THEN** the order is created with payment_method set to "cod"

#### Scenario: Explicit COD selection
- **WHEN** a checkout request includes payment_method "cod"
- **THEN** the order is created with payment_method "cod"

#### Scenario: Unsupported payment method
- **WHEN** a checkout request includes payment_method "stripe" or any unsupported value
- **THEN** the system returns 422 with error indicating the payment method is not supported and listing available methods
