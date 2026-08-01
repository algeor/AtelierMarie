## ADDED Requirements

### Requirement: Econt office delivery stores label-ready details
For Econt office delivery, the system SHALL store both the internal office id and the Econt office code in delivery details. Label creation SHALL treat office code as required for Econt office delivery.

#### Scenario: Static Econt office selected
- **WHEN** a customer selects an Econt office from the static office picker
- **THEN** the submitted delivery office includes `office_id`, `office_code`, `office_name`, `office_type`, and phone

#### Scenario: Econt locker selected
- **WHEN** a customer selects an Econt locker/APS/MPS
- **THEN** the delivery details preserve `office_type='apt'` and include the Econt office code

### Requirement: Econt Office Locator is optional and origin-validated
When enabled, the checkout SHALL render Econt's Office Locator iframe for Econt office delivery and SHALL accept selected-office messages only from configured Econt locator origins.

#### Scenario: Locator enabled
- **WHEN** Econt office locator is enabled and the customer chooses Econt office delivery
- **THEN** checkout renders the locator iframe with configured environment URL, shop URL, city, office type, language, and geolocation allowance

#### Scenario: Message from unknown origin ignored
- **WHEN** checkout receives a `message` event from an origin not in the configured Econt locator origin list
- **THEN** the message is ignored and no delivery selection changes

### Requirement: Econt door delivery remains structured
For Econt door delivery, the system SHALL store city, postal code, street/address details, phone, and optional building/apartment fields in a format that can be mapped to Econt `CustomerInfo` without reparsing free text.

#### Scenario: Econt door details submitted
- **WHEN** a customer completes Econt door delivery fields
- **THEN** the order stores structured city, postal code, street, building, apartment, and phone values
