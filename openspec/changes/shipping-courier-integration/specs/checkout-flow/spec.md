## MODIFIED Requirements

### Requirement: Checkout converts cart to order atomically
The system SHALL expose `POST /v1/orders` accepting customer_email, customer_name (optional), delivery (required object), shipping_cents (required integer), and notes (optional). The `delivery` object SHALL contain: method ("office" or "door"), and either an `office` sub-object (courier, office_id, office_name, office_type, phone) or a `door` sub-object (courier, city, postal_code, street, building, apartment, phone). The endpoint SHALL atomically validate stock, validate delivery data, validate shipping_cents against server-side recalculation (tolerance ±50 cents for rounding), create an order with status "pending", snapshot product names and prices into order_items, store delivery details and shipping cost, decrement product stock, and clear the session's cart — all within a single database transaction. On success it SHALL return the created order with HTTP 201.

#### Scenario: Successful checkout with office delivery
- **WHEN** a session with cart items sends `POST /v1/orders` with valid email, delivery `{method: "office", office: {courier: "speedy", office_id: "speedy-sf-001", office_name: "Speedy офис София Център", office_type: "office", phone: "+359888123456"}}`, and shipping_cents 630
- **THEN** an order is created with status "pending", delivery_method "office", delivery_courier "speedy", delivery_details containing the full office object, items_total_cents computed from items, shipping_cents 630, total_cents = items_total_cents + 630, cart cleared, and response is HTTP 201

#### Scenario: Successful checkout with door delivery
- **WHEN** a session with cart items sends `POST /v1/orders` with valid email, delivery `{method: "door", door: {courier: "econt", city: "София", postal_code: "1000", street: "бул. Витоша 100", building: "А", apartment: "12", phone: "+359877654321"}}`, and shipping_cents 720
- **THEN** an order is created with status "pending", delivery_method "door", delivery_courier "econt", delivery_details containing the full door object, items_total_cents computed from items, shipping_cents 720, total_cents = items_total_cents + 720, cart cleared, and response is HTTP 201

#### Scenario: Successful checkout with free shipping
- **WHEN** a session with cart items totaling ≥ 5000 cents (€50) sends `POST /v1/orders` with valid delivery and shipping_cents 0
- **THEN** an order is created with shipping_cents 0, total_cents = items_total_cents, and the response confirms free shipping

#### Scenario: Checkout with empty cart fails
- **WHEN** a session with no cart items sends `POST /v1/orders`
- **THEN** the API returns HTTP 400 with error code "EMPTY_CART" and message "Cart is empty", no order is created

#### Scenario: Checkout with insufficient stock fails
- **WHEN** a session has product X with quantity 5 in cart but product X has only 2 in stock
- **THEN** the API returns HTTP 409 with error details identifying product X, requested quantity 5, and available quantity 2; no order is created, cart is unchanged, stock is unchanged

#### Scenario: Checkout with missing delivery object fails
- **WHEN** a session sends `POST /v1/orders` with valid email but no delivery object
- **THEN** the API returns HTTP 422 with validation error "delivery field is required"

#### Scenario: Checkout with invalid delivery method fails
- **WHEN** a session sends `POST /v1/orders` with delivery `{method: "drone"}`
- **THEN** the API returns HTTP 422 with validation error indicating method must be "office" or "door"

#### Scenario: Office delivery missing office details fails
- **WHEN** a session sends `POST /v1/orders` with delivery `{method: "office"}` but no office sub-object
- **THEN** the API returns HTTP 422 with validation error "office details required when method is office"

#### Scenario: Door delivery missing required address fields fails
- **WHEN** a session sends `POST /v1/orders` with delivery `{method: "door", door: {courier: "speedy"}}` (missing city, postal_code, street, phone)
- **THEN** the API returns HTTP 422 with validation errors for each missing required field

#### Scenario: Shipping cents mismatch rejected
- **WHEN** a session sends `POST /v1/orders` with shipping_cents 100 but server recalculation yields 650 (difference > 50 cents tolerance)
- **THEN** the API returns HTTP 409 with error "shipping price has changed, please refresh" and the correct shipping_cents value

### Requirement: Checkout validates request input
The system SHALL validate that customer_email is a valid email format, customer_name is at most 200 characters, delivery.office.phone or delivery.door.phone is 8-15 characters (digits and optional leading +), delivery.door.city is at most 100 characters, delivery.door.street is at most 200 characters, delivery.door.postal_code is at most 10 characters, shipping_cents is a non-negative integer, and notes is at most 2000 characters. Invalid input SHALL return HTTP 422.

#### Scenario: Invalid email format rejected
- **WHEN** a session sends `POST /v1/orders` with customer_email "not-an-email"
- **THEN** the API returns HTTP 422 with validation error details for the email field

#### Scenario: Invalid phone format rejected
- **WHEN** a session sends `POST /v1/orders` with delivery phone "abc"
- **THEN** the API returns HTTP 422 with validation error for the phone field

#### Scenario: Valid phone with country code accepted
- **WHEN** a session sends `POST /v1/orders` with delivery phone "+359888123456"
- **THEN** phone validation passes

#### Scenario: Negative shipping_cents rejected
- **WHEN** a session sends `POST /v1/orders` with shipping_cents -100
- **THEN** the API returns HTTP 422 with validation error for shipping_cents

### Requirement: Order response includes delivery details and shipping breakdown
The system SHALL include delivery and shipping information in the order response: delivery_method ("office", "door", or null for legacy orders), delivery_courier ("speedy", "econt", or null), delivery_details (full structured object or null), items_total_cents (sum of item prices), shipping_cents (shipping cost, 0 for free shipping), and total_cents (items + shipping). Legacy orders with only shipping_address SHALL have delivery fields as null and shipping_cents as 0, with shipping_address still returned.

#### Scenario: New order response has structured delivery and shipping
- **WHEN** a new order is retrieved via `GET /v1/orders/{id}`
- **THEN** the response includes delivery_method, delivery_courier, delivery_details, items_total_cents, shipping_cents, and total_cents = items_total_cents + shipping_cents

#### Scenario: Free shipping order response
- **WHEN** an order with free shipping is retrieved via `GET /v1/orders/{id}`
- **THEN** the response includes shipping_cents: 0 and total_cents = items_total_cents

#### Scenario: Legacy order response has shipping_address
- **WHEN** a legacy order (pre-migration) is retrieved via `GET /v1/orders/{id}`
- **THEN** the response includes shipping_address as a string, shipping_cents as 0, and delivery_method/delivery_courier/delivery_details as null
