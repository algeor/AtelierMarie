## MODIFIED Requirements

### Requirement: Checkout converts cart to order atomically
The system SHALL expose `POST /v1/orders` accepting customer_email, customer_name (optional), delivery (required object), shipping_cents (required integer), and notes (optional). The endpoint SHALL atomically validate active products, validate delivery data, create an order with status `pending`, snapshot product names and effective prices into `order_items`, store delivery details and shipping cost, reserve available stock, record any outstanding crafted-later quantities, and clear the session's cart. Checkout SHALL capture `now` once inside the transaction and use that timestamp for all effective-price computations. The price snapshotted into `order_items.price_cents` SHALL be each product's effective price at checkout time. For each line, checkout SHALL persist `allocated_quantity` as the quantity reserved from stock and `backordered_quantity` as the remaining quantity that must be crafted later. The order SHALL be created with `fulfillment_status = awaiting_production` when any line has `backordered_quantity > 0`, otherwise `ready`. On success it SHALL return the created order with HTTP 201.

#### Scenario: Successful checkout with fully available stock
- **WHEN** a session with cart items sends `POST /v1/orders` and every item can be fully allocated from current stock
- **THEN** an order is created with `status = pending` and `fulfillment_status = ready`
- **AND** each order item stores `backordered_quantity = 0`
- **AND** the cart is cleared

#### Scenario: Successful checkout with crafted-later shortage
- **WHEN** a session orders an active product quantity larger than the current stock
- **THEN** checkout still returns HTTP 201
- **AND** allocates the currently available quantity
- **AND** stores the remaining quantity as `backordered_quantity`
- **AND** sets the order `fulfillment_status` to `awaiting_production`

#### Scenario: Mixed order ships only when complete
- **WHEN** one line is fully allocated and another line still has `backordered_quantity > 0`
- **THEN** the order is accepted
- **AND** the fully allocated line is reserved immediately
- **AND** the order remains `awaiting_production` until all lines are ready

#### Scenario: Checkout with deactivated product fails
- **WHEN** a session attempts checkout with a product that is inactive
- **THEN** the API returns HTTP 409 with `PRODUCT_UNAVAILABLE`
- **AND** no order is created

#### Scenario: Checkout with empty cart fails
- **WHEN** a session with no cart items sends `POST /v1/orders`
- **THEN** the API returns HTTP 400 with error code `EMPTY_CART`

### Requirement: Checkout reserves only allocatable stock
Checkout SHALL decrement stock only for quantities that are actually allocated at order creation. It SHALL NOT drive stock negative and SHALL NOT require the full ordered quantity to be present.

#### Scenario: Partial allocation decrements only the allocated quantity
- **WHEN** a product has stock `2` and the customer orders `5`
- **THEN** stock decreases by `2`
- **AND** the order item records `allocated_quantity = 2` and `backordered_quantity = 3`

#### Scenario: Zero on-hand stock still allows order creation
- **WHEN** a product has stock `0` and the customer orders `3`
- **THEN** checkout succeeds
- **AND** stock remains `0`
- **AND** the order item records `allocated_quantity = 0` and `backordered_quantity = 3`
