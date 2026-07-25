## MODIFIED Requirements

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

### Requirement: Office/locker type indication
The system SHALL visually distinguish between staffed offices and automated lockers (автомати) in the office picker. Offices SHALL show an office icon; lockers SHALL show a locker icon and include a note about SMS code pickup.

#### Scenario: Office type icons
- **WHEN** office list contains both offices and lockers
- **THEN** each entry shows an appropriate icon (📦 for office, 🔐 for locker/автомат) and lockers have subtext "Вземете с SMS код"

#### Scenario: Type filter in office picker
- **WHEN** the office picker is displayed
- **THEN** filter tabs/buttons are available: "Всички" / "Офиси" / "Автомати"

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
