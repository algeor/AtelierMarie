## MODIFIED Requirements

### Requirement: Checkout converts cart to order atomically
The system SHALL expose `POST /v1/orders` accepting customer_email, customer_name (optional), delivery (required object), and notes (optional). The `delivery` object SHALL contain: method ("office" or "door"), and either an `office` sub-object (courier, office_id, office_name, phone) or a `door` sub-object (courier, city, postal_code, street, building, apartment, phone). The endpoint SHALL atomically validate stock, validate delivery data, create an order with status "pending", snapshot product names and prices into order_items, store delivery details, decrement product stock, and clear the session's cart — all within a single database transaction. On success it SHALL return the created order with HTTP 201.

#### Scenario: Successful checkout with office delivery
- **WHEN** a session with cart items sends `POST /v1/orders` with valid email and delivery `{method: "office", office: {courier: "speedy", office_id: "speedy-sf-001", office_name: "Speedy офис София Център", phone: "+359888123456"}}`
- **THEN** an order is created with status "pending", delivery_method "office", delivery_courier "speedy", delivery_details containing the full office object, total_cents computed from items, cart cleared, and response is HTTP 201

#### Scenario: Successful checkout with door delivery
- **WHEN** a session with cart items sends `POST /v1/orders` with valid email and delivery `{method: "door", door: {courier: "econt", city: "София", postal_code: "1000", street: "бул. Витоша 100", building: "А", apartment: "12", phone: "+359877654321"}}`
- **THEN** an order is created with status "pending", delivery_method "door", delivery_courier "econt", delivery_details containing the full door object, total_cents computed from items, cart cleared, and response is HTTP 201

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

### Requirement: Checkout validates request input
The system SHALL validate that customer_email is a valid email format, customer_name is at most 200 characters, delivery.office.phone or delivery.door.phone is 8-15 characters (digits and optional leading +), delivery.door.city is at most 100 characters, delivery.door.street is at most 200 characters, delivery.door.postal_code is at most 10 characters, and notes is at most 2000 characters. Invalid input SHALL return HTTP 422.

#### Scenario: Invalid email format rejected
- **WHEN** a session sends `POST /v1/orders` with customer_email "not-an-email"
- **THEN** the API returns HTTP 422 with validation error details for the email field

#### Scenario: Invalid phone format rejected
- **WHEN** a session sends `POST /v1/orders` with delivery phone "abc"
- **THEN** the API returns HTTP 422 with validation error for the phone field

#### Scenario: Valid phone with country code accepted
- **WHEN** a session sends `POST /v1/orders` with delivery phone "+359888123456"
- **THEN** phone validation passes

### Requirement: Order response includes delivery details
The system SHALL include delivery information in the order response: delivery_method ("office", "door", or null for legacy orders), delivery_courier ("speedy", "econt", or null), and delivery_details (full structured object or null). Legacy orders with only shipping_address SHALL have delivery_method and delivery_courier as null and delivery_details as null, with shipping_address still returned.

#### Scenario: New order response has structured delivery
- **WHEN** a new order is retrieved via `GET /v1/orders/{id}`
- **THEN** the response includes delivery_method, delivery_courier, and delivery_details with the full office or address object

#### Scenario: Legacy order response has shipping_address
- **WHEN** a legacy order (pre-migration) is retrieved via `GET /v1/orders/{id}`
- **THEN** the response includes shipping_address as a string and delivery_method/delivery_courier/delivery_details as null
