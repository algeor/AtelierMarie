## REMOVED Requirements

### Requirement: Stock validation on add
**Reason**: Active products remain orderable even when on-hand stock is insufficient, so raw stock can no longer be a universal add/update blocker.
**Migration**: Cart operations should enforce active-product existence and configured quantity limits, while checkout and fulfillment snapshot allocated versus crafted-later quantities.

## MODIFIED Requirements

### Requirement: Add item to cart
The system SHALL provide `POST /v1/cart` that adds a product to the cart for the current session. If the product is already in the cart, the quantity SHALL be incremented by the requested amount. The service SHALL return a `created: bool` flag indicating whether a new cart item was created. Active products SHALL remain addable regardless of current stock.

#### Scenario: Add new item to cart
- **WHEN** `POST /v1/cart` with an active product that is not already in the cart
- **THEN** a new cart row is created and the response is the updated full cart

#### Scenario: Add existing item increases quantity
- **WHEN** `POST /v1/cart` targets an active product already in the cart
- **THEN** the stored quantity increases and the response is the updated full cart

#### Scenario: Add item for inactive product
- **WHEN** `POST /v1/cart` targets a product where `is_active = 0`
- **THEN** the response is 404 with error code `PRODUCT_NOT_FOUND`

#### Scenario: Add out-of-stock active product
- **WHEN** `POST /v1/cart` targets an active product with `stock = 0`
- **THEN** the item is added successfully

### Requirement: Update cart item quantity
The system SHALL provide `PATCH /v1/cart/{product_id}` that sets the quantity of a cart item to the specified absolute value. Setting quantity to 0 SHALL remove the item. Active products SHALL remain updatable regardless of current stock.

#### Scenario: Update quantity to valid value
- **WHEN** `PATCH /v1/cart/{product_id}` sets a quantity within configured limits for an active product
- **THEN** the cart item is updated and the response is the updated full cart

#### Scenario: Update quantity to zero removes item
- **WHEN** `PATCH /v1/cart/{product_id}` uses `quantity = 0`
- **THEN** the item is removed and the response is the updated full cart

#### Scenario: Update out-of-stock active product
- **WHEN** `PATCH /v1/cart/{product_id}` targets an active product with `stock = 0`
- **THEN** the quantity update succeeds if it stays within configured cart limits
