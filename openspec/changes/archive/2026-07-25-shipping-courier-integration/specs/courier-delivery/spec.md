## ADDED Requirements

### Requirement: Delivery method selection
The system SHALL present the customer with a choice between two delivery methods: "Вземи от офис" (office pickup) and "Доставка до врата" (door-to-door delivery). The selection SHALL be required before the order can be placed.

#### Scenario: Customer selects office pickup
- **WHEN** customer selects "Вземи от офис" delivery method
- **THEN** the city search field becomes visible for the next step

#### Scenario: Customer selects door delivery
- **WHEN** customer selects "Доставка до врата" delivery method
- **THEN** the city field becomes visible for entering delivery city

#### Scenario: No delivery method selected on submit
- **WHEN** customer attempts to place order without selecting a delivery method
- **THEN** validation error "Моля, изберете начин на доставка" is shown and form does not submit

### Requirement: City/location entry (step 2)
The system SHALL collect the customer's city after delivery method selection. For office pickup, this is a city search field (typeahead from courier cities). For door delivery, this is a free-text city input. This step triggers the approximate price calculation for both couriers.

#### Scenario: Customer enters city for office method
- **WHEN** customer types "София" in the city search for office pickup
- **THEN** the system fetches matching cities from both couriers and shows the courier comparison with approximate prices

#### Scenario: Customer enters city for door method
- **WHEN** customer types "Пловдив" as their delivery city
- **THEN** the system calculates approximate prices for both couriers to that city and shows the courier comparison

### Requirement: Courier comparison with approximate prices (step 3)
The system SHALL display both Speedy and Econt as options with approximate shipping prices after the customer enters their city. Each option SHALL show: courier logo, courier name, approximate price (e.g., "~6.50€"), and estimated delivery time. A disclaimer SHALL be shown: "Ориентировъчна цена. Може да се промени при избор на конкретен офис/адрес."

#### Scenario: Both couriers show prices
- **WHEN** customer has entered city "София" with office method
- **THEN** two courier cards are displayed: Speedy with approximate price and Econt with approximate price, plus disclaimer text

#### Scenario: Customer selects courier based on price
- **WHEN** customer sees Speedy at ~6.50€ and Econt at ~5.99€ and clicks Econt
- **THEN** Econt is selected and the office picker (or address form) appears for the next step

#### Scenario: Free shipping threshold met
- **WHEN** customer's cart total is ≥ €50 and they enter a city
- **THEN** both courier options show "Безплатна доставка ✓" instead of a price, with the original price crossed out (e.g., "~~6.50€~~ Безплатна")

#### Scenario: Approximate price loading state
- **WHEN** the price calculation API call is in flight
- **THEN** both courier cards show a price skeleton/spinner instead of a number

#### Scenario: Courier API down for approximate price
- **WHEN** one or both courier APIs fail to respond within 5 seconds
- **THEN** the fallback price of €5.00 is shown for the failed courier(s) with no special indicator to the customer

### Requirement: Courier provider selection (step 4)
The system SHALL allow the customer to select their preferred courier after seeing the price comparison. Selecting a courier SHALL reveal the appropriate details section (office picker or address form).

#### Scenario: Customer selects Speedy
- **WHEN** customer selects Speedy as courier provider
- **THEN** the selection is highlighted, and for office method the Speedy office picker appears; for door method the address form appears

#### Scenario: Customer selects Econt
- **WHEN** customer selects Econt as courier provider
- **THEN** the selection is highlighted, and for office method the Econt office picker appears; for door method the address form appears

#### Scenario: Switching courier resets office selection
- **WHEN** customer has selected a Speedy office and then switches courier to Econt
- **THEN** the previously selected office is cleared and the office picker shows Econt offices

### Requirement: Office picker for office delivery (step 5a)
The system SHALL provide a searchable office picker when the customer has selected office pickup and a courier. The picker SHALL show offices filtered by the previously entered city. Each office SHALL display its name, address, type (office vs locker), and working hours. The picker SHALL support filtering by type (offices only, lockers only, or all).

#### Scenario: Customer sees offices for selected city and courier
- **WHEN** customer has selected Speedy and city "София"
- **THEN** the system queries `GET /v1/delivery/offices?courier=speedy&city=София` and displays matching offices and lockers

#### Scenario: Customer filters to lockers only
- **WHEN** customer clicks "Автомати" filter in the office picker
- **THEN** only automated parcel terminals (type "apt") are shown, with locker icons

#### Scenario: Customer selects an office
- **WHEN** customer clicks on "Speedy офис София Център - бул. Витоша 50" from the office list
- **THEN** the office is selected, its full details (name, address, working hours, type) are shown in a confirmation card, the exact shipping price is recalculated, and the office_id is stored for submission

#### Scenario: Customer selects a locker
- **WHEN** customer clicks on a locker (type "apt") from the office list
- **THEN** the locker is selected with a note "Ще получите SMS код за отваряне на шкафчето" and the exact price is calculated

#### Scenario: No offices match search
- **WHEN** customer's city has no offices for the selected courier
- **THEN** a message "Няма намерени офиси за този град" is displayed

#### Scenario: Office list loading state
- **WHEN** the office list request is in flight
- **THEN** a loading skeleton is shown in the office picker area

### Requirement: Structured address form for door delivery (step 5b)
The system SHALL collect a structured address when door delivery is selected: city (pre-filled from step 2, required), postal code (required), street with number (required), building/entrance (optional), apartment/floor (optional). All fields SHALL have Bulgarian labels. Completing the address SHALL trigger exact price recalculation.

#### Scenario: All required door fields filled
- **WHEN** customer fills city, postal code, street, and phone for door delivery
- **THEN** the form is valid, exact price is calculated, and order can be submitted

#### Scenario: Missing required door field
- **WHEN** customer leaves the city field empty for door delivery and attempts to submit
- **THEN** inline validation error "Градът е задължителен" appears below the city field

#### Scenario: Optional fields left empty
- **WHEN** customer fills only required fields and leaves building and apartment empty
- **THEN** the form is valid; building and apartment are submitted as null

### Requirement: Final shipping price display (step 6)
The system SHALL display the exact, final shipping price after the customer completes step 5 (office selection or address entry). This price SHALL be shown in the order summary section. For free shipping orders, it SHALL show "Безплатна доставка ✓".

#### Scenario: Exact price replaces approximate
- **WHEN** customer selects a specific Speedy office after seeing approximate price of ~6.50€
- **THEN** the order summary updates to show the exact price (e.g., "Доставка: 6.30€") replacing the approximation

#### Scenario: Free shipping in order summary
- **WHEN** cart total ≥ €50
- **THEN** the order summary shows "Доставка: Безплатна" with shipping_cents = 0

#### Scenario: Price recalculation on office change
- **WHEN** customer changes their selected office after seeing a final price
- **THEN** the price is recalculated and updated in the order summary

### Requirement: "Add more for free shipping" nudge
The system SHALL display a message when the customer's cart is below the €50 free shipping threshold, indicating how much more they need to add. Format: "Добави още за X€ за безплатна доставка".

#### Scenario: Cart below threshold
- **WHEN** cart total is €35 and delivery section is visible
- **THEN** a message "Добави още за 15€ за безплатна доставка" is shown near the shipping price

#### Scenario: Cart at or above threshold
- **WHEN** cart total is €52
- **THEN** no "add more" message is shown; free shipping is already applied

### Requirement: Phone number collection
The system SHALL collect a phone number for both office pickup and door delivery. The phone field SHALL be required and displayed with the label "Телефон за куриера". Basic format validation SHALL accept digits, optional leading +, and length between 8 and 15 characters.

#### Scenario: Valid phone number
- **WHEN** customer enters "+359888123456" in the phone field
- **THEN** validation passes and no error is shown

#### Scenario: Invalid phone number
- **WHEN** customer enters "abc" in the phone field and blurs
- **THEN** inline error "Моля, въведете валиден телефонен номер" is displayed

#### Scenario: Phone required for office pickup
- **WHEN** customer selects office pickup but leaves phone empty and submits
- **THEN** validation error "Телефонът е задължителен" is shown on the phone field

### Requirement: Delivery and shipping summary in order confirmation
The system SHALL display the selected delivery method, courier, destination (office name or full address), and shipping cost on the order confirmation page after successful checkout.

#### Scenario: Office delivery confirmation display
- **WHEN** order is placed with Speedy office pickup at "Speedy офис София Център" with shipping 6.30€
- **THEN** the confirmation page shows "Доставка: Вземи от офис на Speedy", the office name and address, and "Цена за доставка: 6.30€"

#### Scenario: Door delivery confirmation display
- **WHEN** order is placed with Econt door delivery to "ул. Витоша 100, София 1000" with shipping 7.20€
- **THEN** the confirmation page shows "Доставка: До врата с Econt", the full formatted address, and "Цена за доставка: 7.20€"

#### Scenario: Free shipping confirmation display
- **WHEN** order is placed with free shipping (cart ≥ €50)
- **THEN** the confirmation page shows "Доставка: Безплатна ✓" and shipping cost as 0.00€
