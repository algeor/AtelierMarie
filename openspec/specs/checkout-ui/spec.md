## Purpose

Defines the storefront checkout user interface, delivery selection, order summary, and submission behavior.
## Requirements
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

### Requirement: Delivery section in checkout page
The system SHALL replace the single shipping address textarea with a multi-step delivery section. The steps are: (1) delivery method selection, (2) city/location entry, (3) courier comparison with approximate prices, (4) courier selection, (5) office picker or address form, (6) final price display. All steps SHALL be visible/collapsible on the same checkout page — no separate routing.

#### Scenario: Delivery section replaces textarea
- **WHEN** user navigates to `/checkout` with items in cart
- **THEN** the shipping section shows delivery method radio buttons ("Вземи от офис" / "Доставка до врата") instead of a plain textarea

#### Scenario: Progressive disclosure of steps
- **WHEN** user selects a delivery method
- **THEN** the next step (city entry) appears below, and subsequent steps remain hidden until their prerequisites are completed

#### Scenario: Office method full flow
- **WHEN** user selects "Вземи от офис", enters city, selects courier from comparison, and picks an office
- **THEN** all steps are completed, final price is shown in order summary, and the "Place Order" button is enabled

#### Scenario: Door method full flow
- **WHEN** user selects "Доставка до врата", enters city, selects courier from comparison, and fills the address form
- **THEN** all steps are completed, final price is shown in order summary, and the "Place Order" button is enabled

#### Scenario: Delivery info required for checkout
- **WHEN** user clicks "Place Order" without completing the delivery section
- **THEN** validation errors appear on the incomplete delivery step and the form does not submit

### Requirement: Courier comparison cards
The system SHALL display courier options as cards showing: courier logo, courier name, approximate price, and estimated delivery time. Cards SHALL be selectable (radio-style). The cheaper option MAY be subtly highlighted.

#### Scenario: Both couriers rendered as cards
- **WHEN** the courier comparison step is reached after city entry
- **THEN** two cards are shown side by side: one for Speedy and one for Econt, each with logo, name, and approximate price

#### Scenario: Free shipping display in comparison
- **WHEN** cart total ≥ €50
- **THEN** both cards show "Безплатна" with original price crossed out (e.g., "~~6.50€~~ Безплатна")

### Requirement: Office/locker type indication
The system SHALL visually distinguish between staffed offices and automated lockers (автомати) in the office picker. Offices SHALL show an office icon; lockers SHALL show a locker icon and include a note about SMS code pickup.

#### Scenario: Office type icons
- **WHEN** office list contains both offices and lockers
- **THEN** each entry shows an appropriate icon (📦 for office, 🔐 for locker/автомат) and lockers have subtext "Вземете с SMS код"

#### Scenario: Type filter in office picker
- **WHEN** the office picker is displayed
- **THEN** filter tabs/buttons are available: "Всички" / "Офиси" / "Автомати"

### Requirement: Order summary sidebar
The system SHALL display a read-only summary of cart items (name, quantity, line total), the subtotal, and a "Place Order" button. Item details SHALL come from CartContext.

#### Scenario: Summary displays cart items
- **WHEN** the checkout page loads with 2 items in cart
- **THEN** the summary shows each item's name, quantity, unit price, line total (quantity × price), and the cart subtotal

#### Scenario: Summary updates reflect cart
- **WHEN** the cart state changes while on the checkout page (e.g., item removed via API elsewhere)
- **THEN** the summary re-renders with updated items and total

### Requirement: Shipping price in order summary
The system SHALL display shipping cost in the checkout order summary section, separate from the items subtotal. Format: "Междинна сума: X€ / Доставка: Y€ / Общо: Z€". The total SHALL update when shipping price changes.

#### Scenario: Order summary with shipping
- **WHEN** delivery is configured and price calculated
- **THEN** the order summary shows items subtotal, shipping cost, and total (items + shipping)

#### Scenario: Order summary with free shipping
- **WHEN** cart total ≥ €50
- **THEN** the order summary shows items subtotal, "Доставка: Безплатна", and total = items subtotal

#### Scenario: Order summary updates on courier change
- **WHEN** customer switches courier selection
- **THEN** shipping price recalculates and order summary total updates

### Requirement: Free shipping nudge
The system SHALL display a progress-style message when cart is below the €50 free shipping threshold: "Добави още за X€ за безплатна доставка". This SHALL appear near the delivery/shipping section.

#### Scenario: Below threshold
- **WHEN** cart total is €35
- **THEN** message "Добави още за 15€ за безплатна доставка" is shown

#### Scenario: At or above threshold
- **WHEN** cart total is €50 or more
- **THEN** no nudge message is shown; "Безплатна доставка ✓" appears instead

### Requirement: Order submission with shipping
The system SHALL call `POST /v1/orders` with `{customer_email, customer_name, delivery, shipping_cents, notes}` when the user clicks "Place Order" and validation passes. The `shipping_cents` SHALL be the final calculated price (0 for free shipping). On success, the user SHALL be redirected to the order confirmation page.

#### Scenario: Successful order with office delivery and shipping cost
- **WHEN** user completes delivery flow with Speedy office, final price 6.30€, and clicks "Place Order"
- **THEN** the system calls `createOrder()` with delivery object and shipping_cents: 630, shows loading state, and on success navigates to `/orders/{order_id}/confirmation`

#### Scenario: Successful order with free shipping
- **WHEN** user has cart ≥ €50, completes delivery, and clicks "Place Order"
- **THEN** the system calls `createOrder()` with shipping_cents: 0

#### Scenario: Order fails due to shipping price change
- **WHEN** the backend returns 409 with "shipping price has changed"
- **THEN** the new price is displayed, the user is asked to confirm, and the form does not auto-submit

#### Scenario: Order fails due to stock change
- **WHEN** the backend returns 409 (stock insufficient at checkout time)
- **THEN** an error message "Some items are no longer available. Please review your cart." is shown

#### Scenario: Button disabled during submission
- **WHEN** the "Place Order" button is clicked
- **THEN** it becomes disabled and shows "Поръчката се обработва..." until the request resolves

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

### Requirement: Checkout legal disclosure
The checkout page SHALL display a small legal disclosure near every visible Place Order button. The disclosure SHALL link to `/[locale]/terms` and SHALL state that placing an order means the customer agrees to the Terms & Conditions, including delivery, withdrawal, and returns information.

#### Scenario: Desktop checkout shows disclosure
- **WHEN** a customer views checkout on a desktop viewport with items in cart
- **THEN** a legal disclosure is visible near the desktop Place Order button
- **AND** the Terms & Conditions text links to the localized terms page

#### Scenario: Mobile checkout shows disclosure
- **WHEN** a customer views checkout on a mobile viewport with items in cart
- **THEN** a legal disclosure is visible near the mobile Place Order button
- **AND** the Terms & Conditions text links to the localized terms page

#### Scenario: Disclosure remains quiet
- **WHEN** the checkout page renders
- **THEN** the disclosure uses subdued styling compared with form labels and the primary order button
- **AND** it does not advertise returns as a commercial benefit

#### Scenario: Disclosure is present before submit
- **WHEN** a customer is ready to place an order
- **THEN** the disclosure is visible before order submission without requiring a separate modal or hidden accordion

### Requirement: Checkout legal and privacy disclosure
The checkout page SHALL display a small legal/privacy disclosure near every visible Place Order button. The disclosure SHALL link to localized Terms & Conditions and Privacy Policy pages and SHALL state that order submission involves processing the provided contact and delivery data.

#### Scenario: Desktop checkout disclosure includes policy links
- **WHEN** checkout renders on desktop
- **THEN** the disclosure near the desktop Place Order button links to Terms & Conditions and Privacy Policy

#### Scenario: Mobile checkout disclosure includes policy links
- **WHEN** checkout renders on mobile
- **THEN** the disclosure near the mobile Place Order button links to Terms & Conditions and Privacy Policy

### Requirement: Checkout order summary uses charged item prices
The checkout order summary SHALL use each cart item's effective charged price for line totals and subtotal display. If a product has an active discount, the summary SHALL NOT calculate line totals from the original list price.

#### Scenario: Discounted cart item summary uses effective price
- **WHEN** a cart item has `price_cents = 4000`, `effective_price_cents = 3000`, and quantity 2
- **THEN** checkout displays the line total as 6000 cents equivalent
- **AND** the subtotal matches the cart total returned by the cart API

### Requirement: Checkout shipping and total clarity
Checkout SHALL show shipping cost information only when it is known and included in the order total. If shipping pricing is not implemented or shipping is zero, the UI SHALL avoid implying that a paid courier delivery charge is included.

#### Scenario: Known shipping is shown before submission
- **WHEN** checkout has a known `shipping_cents` value
- **THEN** the order summary displays item subtotal, shipping, and final total before order submission

#### Scenario: Unknown shipping is not misrepresented
- **WHEN** checkout does not have a real shipping price
- **THEN** the UI does not present a paid shipping amount as included in the order total

