## ADDED Requirements

### Requirement: Orders store tracking information

The system SHALL store tracking number, carrier name, and tracking URL on the orders table when an order is marked as shipped.

#### Scenario: Tracking fields added to orders schema

- **WHEN** the database schema is initialized
- **THEN** the `orders` table includes nullable columns: `tracking_number` (TEXT), `tracking_carrier` (TEXT), `tracking_url` (TEXT)

#### Scenario: Tracking data persisted on ship

- **WHEN** admin updates order status to "shipped" with tracking_number, tracking_carrier, and tracking_url
- **THEN** all three tracking fields are stored on the order row

#### Scenario: Tracking fields are NULL for non-shipped orders

- **WHEN** an order is in any status other than "shipped" or "delivered"
- **THEN** tracking_number, tracking_carrier, and tracking_url MAY be NULL

### Requirement: Tracking information required when shipping

The system SHALL require tracking_number and tracking_carrier when transitioning an order to "shipped" status. tracking_url is optional (auto-generated from carrier + number if not provided).

#### Scenario: Ship without tracking number rejected

- **WHEN** admin attempts to update status to "shipped" without providing tracking_number
- **THEN** the system returns 422 with error code "TRACKING_REQUIRED"

#### Scenario: Ship without carrier rejected

- **WHEN** admin attempts to update status to "shipped" without providing tracking_carrier
- **THEN** the system returns 422 with error code "TRACKING_REQUIRED"

#### Scenario: Ship with valid tracking accepted

- **WHEN** admin provides tracking_number="1234567" and tracking_carrier="speedy" with status="shipped"
- **THEN** the order transitions to "shipped" and tracking data is persisted

#### Scenario: Tracking URL auto-generated from known carrier

- **WHEN** admin provides tracking_number and tracking_carrier is a known carrier (speedy, econt, dhl, fedex) but no tracking_url
- **THEN** the system generates tracking_url from the carrier's URL pattern

#### Scenario: Custom tracking URL accepted

- **WHEN** admin provides an explicit tracking_url alongside tracking_number and tracking_carrier
- **THEN** the provided URL is used as-is (no auto-generation)

#### Scenario: Tracking fields ignored for non-ship transitions

- **WHEN** admin updates status to "confirmed", "delivered", or "cancelled"
- **THEN** tracking_number, tracking_carrier, and tracking_url fields in the request body are ignored

### Requirement: Supported carriers with URL patterns

The system SHALL support auto-generating tracking URLs for known carriers.

#### Scenario: Speedy tracking URL

- **WHEN** tracking_carrier is "speedy" and tracking_number is "1234567"
- **THEN** tracking_url is generated as `https://www.speedy.bg/en/track-shipment?shipmentNumber=1234567`

#### Scenario: Econt tracking URL

- **WHEN** tracking_carrier is "econt" and tracking_number is "1234567"
- **THEN** tracking_url is generated as `https://www.econt.com/services/track-shipment/1234567`

#### Scenario: DHL tracking URL

- **WHEN** tracking_carrier is "dhl" and tracking_number is "1234567"
- **THEN** tracking_url is generated as `https://www.dhl.com/en/express/tracking.html?AWB=1234567`

#### Scenario: FedEx tracking URL

- **WHEN** tracking_carrier is "fedex" and tracking_number is "1234567"
- **THEN** tracking_url is generated as `https://www.fedex.com/fedextrack/?trknbr=1234567`

#### Scenario: Unknown carrier requires explicit URL

- **WHEN** tracking_carrier is "other" or an unrecognized value and no tracking_url is provided
- **THEN** tracking_url remains NULL (no auto-generation attempted)

### Requirement: Tracking info visible in order detail API

The system SHALL include tracking_number, tracking_carrier, and tracking_url in order detail responses when present.

#### Scenario: Order detail includes tracking after ship

- **WHEN** a shipped order is fetched via `GET /v1/orders/{id}` or `GET /v1/admin/orders/{id}`
- **THEN** the response includes tracking_number, tracking_carrier, and tracking_url fields

#### Scenario: Order detail omits tracking before ship

- **WHEN** a pending or confirmed order is fetched
- **THEN** tracking_number, tracking_carrier, and tracking_url are null in the response
