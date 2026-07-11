## MODIFIED Requirements

### Requirement: Shipping address form
The system SHALL replace the single shipping address textarea with a structured delivery section containing: delivery method selection (office pickup or door-to-door), courier provider selection (Speedy or Econt), and either an office picker (for office method) or a structured address form (for door method). A phone number field SHALL be required for both methods.

#### Scenario: Delivery section replaces textarea
- **WHEN** user navigates to `/checkout` with items in cart
- **THEN** the shipping section shows delivery method radio buttons ("Вземи от офис" / "Доставка до врата") instead of a plain textarea

#### Scenario: Office method shows office picker
- **WHEN** user selects "Вземи от офис" and picks a courier
- **THEN** a city search field and office list appear below, along with a phone number field

#### Scenario: Door method shows address form
- **WHEN** user selects "Доставка до врата" and picks a courier
- **THEN** a structured address form appears with fields: city, postal code, street, building (optional), apartment (optional), and phone number

#### Scenario: Delivery info required for checkout
- **WHEN** user clicks "Place Order" without completing the delivery section
- **THEN** validation errors appear on the delivery section and the form does not submit

### Requirement: Order submission
The system SHALL call `POST /v1/orders` with `{customer_email, customer_name, delivery}` when the user clicks "Place Order" and validation passes. The `delivery` object SHALL contain the method, courier, and either office details or address details depending on the selected method. The `notes` field SHALL be omitted (sent as `null`). On success, the user SHALL be redirected to the order confirmation page. On failure, an error message SHALL be displayed.

#### Scenario: Successful order with office delivery
- **WHEN** user fills valid contact info, selects Speedy office pickup, chooses an office, enters phone, and clicks "Place Order"
- **THEN** the system calls `createOrder()` with delivery object `{method: "office", office: {courier: "speedy", office_id, office_name}, phone}`, shows loading state, and on success navigates to `/orders/{order_id}/confirmation`

#### Scenario: Successful order with door delivery
- **WHEN** user fills valid contact info, selects Econt door delivery, fills address fields and phone, and clicks "Place Order"
- **THEN** the system calls `createOrder()` with delivery object `{method: "door", door: {courier: "econt", city, postal_code, street, building, apartment, phone}}`, shows loading state, and on success navigates to `/orders/{order_id}/confirmation`

#### Scenario: Order fails due to stock change
- **WHEN** the backend returns 409 (stock insufficient at checkout time)
- **THEN** an error message "Some items are no longer available. Please review your cart." is shown and the user is not redirected

#### Scenario: Order fails due to network error
- **WHEN** the `POST /v1/orders` request fails with a network error
- **THEN** an error message "Something went wrong. Please try again." is shown and the button re-enables

#### Scenario: Button disabled during submission
- **WHEN** the "Place Order" button is clicked
- **THEN** it becomes disabled and shows "Placing order..." until the request resolves
