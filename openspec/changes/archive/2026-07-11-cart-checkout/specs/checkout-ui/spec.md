## ADDED Requirements

### Requirement: Checkout page layout
The system SHALL provide a `/checkout` page with a two-column layout on desktop (form left, order summary right) and single-column stacked layout on mobile (summary first, form below). The page SHALL be accessible only when the cart has items — if the cart is empty, it SHALL redirect to `/products`.

#### Scenario: Desktop layout
- **WHEN** user navigates to `/checkout` on a screen ≥1024px wide with items in cart
- **THEN** a contact form and shipping address form are shown on the left, and an order summary sidebar is shown on the right

#### Scenario: Mobile layout
- **WHEN** user navigates to `/checkout` on a screen <1024px with items in cart
- **THEN** the order summary is shown at the top and the form fields are stacked below

#### Scenario: Empty cart redirect
- **WHEN** user navigates to `/checkout` with an empty cart
- **THEN** they are redirected to `/products`

### Requirement: Contact information form
The system SHALL collect customer email (required) and customer name (optional but encouraged) in a contact section. The email field SHALL validate format on blur and on submit.

#### Scenario: Valid email entered
- **WHEN** user enters "marie@example.com" in the email field and blurs
- **THEN** no validation error is shown

#### Scenario: Invalid email format
- **WHEN** user enters "not-an-email" in the email field and blurs
- **THEN** an inline error message "Please enter a valid email address" appears below the field

#### Scenario: Empty email on submit
- **WHEN** user clicks "Place Order" with the email field empty
- **THEN** the email field shows "Email is required" error and the form does not submit

### Requirement: Shipping address form
The system SHALL collect a shipping address as a single multi-line textarea field (optional). The field label SHALL indicate it is optional.

#### Scenario: Address provided
- **WHEN** user enters a shipping address in the textarea
- **THEN** the value is included in the order submission as `shipping_address`

#### Scenario: Address left empty
- **WHEN** user leaves the address field empty and submits
- **THEN** the order is placed with `shipping_address: null`

### Requirement: Order summary sidebar
The system SHALL display a read-only summary of cart items (name, quantity, line total), the subtotal, and a "Place Order" button. Item details SHALL come from CartContext.

#### Scenario: Summary displays cart items
- **WHEN** the checkout page loads with 2 items in cart
- **THEN** the summary shows each item's name, quantity, unit price, line total (quantity × price), and the cart subtotal

#### Scenario: Summary updates reflect cart
- **WHEN** the cart state changes while on the checkout page (e.g., item removed via API elsewhere)
- **THEN** the summary re-renders with updated items and total

### Requirement: Order submission
The system SHALL call `POST /v1/orders` with `{customer_email, customer_name, shipping_address}` when the user clicks "Place Order" and validation passes. The `notes` field SHALL be omitted (sent as `null`). On success, the user SHALL be redirected to the order confirmation page. On failure, an error message SHALL be displayed.

#### Scenario: Successful order placement
- **WHEN** user fills valid contact info and clicks "Place Order"
- **THEN** the system calls `createOrder()`, shows a loading state on the button, and on success navigates to `/orders/{order_id}/confirmation`

#### Scenario: Order fails due to stock change
- **WHEN** the backend returns 409 (stock insufficient at checkout time)
- **THEN** an error message "Some items are no longer available. Please review your cart." is shown and the user is not redirected

#### Scenario: Order fails due to network error
- **WHEN** the `POST /v1/orders` request fails with a network error
- **THEN** an error message "Something went wrong. Please try again." is shown and the button re-enables

#### Scenario: Button disabled during submission
- **WHEN** the "Place Order" button is clicked
- **THEN** it becomes disabled and shows "Placing order..." until the request resolves

### Requirement: Form preserves input on error
The system SHALL NOT clear form fields when an order submission fails. The user's entered data SHALL remain intact so they can retry without re-entering.

#### Scenario: Input preserved after error
- **WHEN** order submission fails and user sees an error
- **THEN** all form fields retain their values and user can click "Place Order" again

### Requirement: Checkout page accessibility
The system SHALL use semantic form elements with associated labels, required field indicators, and ARIA live regions for error messages. Focus SHALL move to the first error field on failed validation.

#### Scenario: Screen reader announces errors
- **WHEN** form validation fails on submit
- **THEN** errors are announced via aria-live region and focus moves to the first invalid field

#### Scenario: Required fields indicated
- **WHEN** the checkout page renders
- **THEN** the email field has a visible required indicator (asterisk) and `aria-required="true"`
