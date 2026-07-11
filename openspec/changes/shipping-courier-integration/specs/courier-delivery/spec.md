## ADDED Requirements

### Requirement: Delivery method selection
The system SHALL present the customer with a choice between two delivery methods: "Вземи от офис" (office pickup) and "Доставка до врата" (door-to-door delivery). The selection SHALL be required before the order can be placed.

#### Scenario: Customer selects office pickup
- **WHEN** customer selects "Вземи от офис" delivery method
- **THEN** the courier selection and office picker sections become visible, and the door-delivery address form is hidden

#### Scenario: Customer selects door delivery
- **WHEN** customer selects "Доставка до врата" delivery method
- **THEN** the courier selection and structured address form become visible, and the office picker is hidden

#### Scenario: No delivery method selected on submit
- **WHEN** customer attempts to place order without selecting a delivery method
- **THEN** validation error "Моля, изберете начин на доставка" is shown and form does not submit

### Requirement: Courier provider selection
The system SHALL present the customer with a choice between Speedy and Econt courier providers. Both options SHALL be available for both office pickup and door delivery. Each option SHALL display the courier logo and name.

#### Scenario: Customer selects Speedy
- **WHEN** customer selects Speedy as courier provider
- **THEN** the selection is highlighted, and subsequent office/address fields filter by Speedy data

#### Scenario: Customer selects Econt
- **WHEN** customer selects Econt as courier provider
- **THEN** the selection is highlighted, and subsequent office/address fields filter by Econt data

#### Scenario: Switching courier resets office selection
- **WHEN** customer has selected a Speedy office and then switches courier to Econt
- **THEN** the previously selected office is cleared and the office picker shows Econt offices

### Requirement: Office picker for office delivery
The system SHALL provide a searchable office picker when the customer has selected office pickup. The picker SHALL filter offices by city first, then allow text search within that city's offices. The selected office SHALL display its name, address, and working hours.

#### Scenario: Customer searches for office by city
- **WHEN** customer types "София" in the city filter with Speedy selected
- **THEN** the system queries `GET /v1/delivery/offices?courier=speedy&city=София` and displays matching offices

#### Scenario: Customer selects an office
- **WHEN** customer clicks on "Speedy офис София Център - бул. Витоша 50" from the office list
- **THEN** the office is selected, its full details (name, address, working hours) are shown in a confirmation card, and the office_id is stored for submission

#### Scenario: No offices match search
- **WHEN** customer searches for a city that has no offices for the selected courier
- **THEN** a message "Няма намерени офиси за този град" is displayed

#### Scenario: Office list loading state
- **WHEN** the office list request is in flight
- **THEN** a loading skeleton is shown in the office picker area

### Requirement: Structured address form for door delivery
The system SHALL collect a structured address when door delivery is selected: city (required), postal code (required), street with number (required), building/entrance (optional), apartment/floor (optional). All fields SHALL have Bulgarian labels.

#### Scenario: All required door fields filled
- **WHEN** customer fills city, postal code, street, and phone for door delivery
- **THEN** the form is valid and order can be submitted

#### Scenario: Missing required door field
- **WHEN** customer leaves the city field empty for door delivery and attempts to submit
- **THEN** inline validation error "Градът е задължителен" appears below the city field

#### Scenario: Optional fields left empty
- **WHEN** customer fills only required fields and leaves building and apartment empty
- **THEN** the form is valid; building and apartment are submitted as null

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

### Requirement: Delivery summary in order confirmation
The system SHALL display the selected delivery method, courier, and destination (office name or full address) on the order confirmation page after successful checkout.

#### Scenario: Office delivery confirmation display
- **WHEN** order is placed with Speedy office pickup at "Speedy офис София Център"
- **THEN** the confirmation page shows "Доставка: Вземи от офис на Speedy" and the office name and address

#### Scenario: Door delivery confirmation display
- **WHEN** order is placed with Econt door delivery to "ул. Витоша 100, София 1000"
- **THEN** the confirmation page shows "Доставка: До врата с Econt" and the full formatted address
