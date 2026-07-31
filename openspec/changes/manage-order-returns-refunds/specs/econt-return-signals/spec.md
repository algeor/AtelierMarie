## ADDED Requirements

### Requirement: Econt trace refresh captures return and failure evidence
The system SHALL support refreshing Econt shipment trace/status data for Econt orders when an Econt shipment number and configured credentials are available. The system SHALL support Econt Delivery `OrdersService.getTrace` and MAY support EE `LabelService` shipment status responses when that API family is used for label creation. Trace refresh SHALL persist raw redacted courier payloads and normalized public-safe status fields.

#### Scenario: Econt trace reports returning to sender
- **WHEN** Econt trace/status reports `shortDeliveryStatusEn = "Is returning to sender"` or a tracking event type `is_returning_to_sender`
- **THEN** the system creates or updates an admin review signal for return in transit and does not change order status, payment status, refund status, or stock automatically

#### Scenario: Econt trace reports returned to sender
- **WHEN** Econt trace/status reports `shortDeliveryStatusEn = "Returned to sender"` or a tracking event type `returned_to_sender`
- **THEN** the system creates or updates an admin review signal for returned shipment and does not issue a refund or restock without admin action

#### Scenario: Econt trace reports failed delivery
- **WHEN** Econt trace/status includes tracking event type `failed_delivery`
- **THEN** the system creates or updates an admin review signal for failed delivery so an admin can decide whether this is refused, uncollected, wrong address, or another return reason

### Requirement: Econt return and reject instructions are explicit when labels are created
When the system creates Econt shipment labels, it SHALL use configured Econt return/reject instruction settings rather than relying on implicit courier defaults. Supported fields SHALL include return destination, return-payment side, days until return for unclaimed parcels, reject action, and reject-payment side fields where supported by the active Econt API.

#### Scenario: Unclaimed office parcel has return instruction
- **WHEN** an Econt office-pickup label is created with configured unclaimed-return days
- **THEN** the Econt payload includes the configured `executeIfNotTaken`/unclaimed-return instruction or equivalent supported field

#### Scenario: Rejected parcel has return-to-sender instruction
- **WHEN** an Econt label is created with reject action configured as return to sender
- **THEN** the Econt payload includes the configured reject action and return payment-side fields supported by Econt

### Requirement: Econt COD collection and payout evidence is stored
The system SHALL capture Econt COD evidence from trace/status responses when available, including collected amount/time and paid amount/time. This evidence SHALL support COD settlement reconciliation but SHALL NOT replace an explicit admin settlement record.

#### Scenario: Econt reports COD collected but not paid
- **WHEN** Econt status includes `cdCollectedAmount` and `cdCollectedTime` but no `cdPaidAmount` or `cdPaidTime`
- **THEN** the system stores the collection evidence and keeps the order in COD settlement review

#### Scenario: Econt reports COD paid to merchant
- **WHEN** Econt status includes `cdPaidAmount` and `cdPaidTime`
- **THEN** the system stores the payout evidence and shows it to the admin for settlement reconciliation

### Requirement: Econt return shipment relationships are preserved
The system SHALL preserve Econt return-related shipment metadata when present, including previous shipment number, next shipments, last processed instruction, return shipment URL, and tracking events. This data SHALL be stored as courier evidence and linked to the local return case where possible.

#### Scenario: Econt response includes return shipment URL
- **WHEN** Econt status includes `returnShipmentURL`
- **THEN** the system stores the URL as admin-visible courier evidence on the order or return case

#### Scenario: Econt response links a return shipment
- **WHEN** Econt status includes `previousShipmentNumber` or `nextShipments`
- **THEN** the system stores the relationship so admins can trace the original and return shipment numbers together

### Requirement: Manual Econt fallback remains available
The system SHALL allow admins to record Econt tracking/return evidence manually when Econt API credentials are missing, the order was fulfilled outside the app, or trace refresh fails.

#### Scenario: Econt credentials unavailable
- **WHEN** an admin handles an Econt order without configured Econt trace credentials
- **THEN** the admin can manually mark uncollected/refused/return in transit/returned and enter tracking or claim notes without using the Econt API

#### Scenario: Econt trace refresh fails
- **WHEN** Econt trace refresh fails due to auth, validation, timeout, or service outage
- **THEN** the system records an admin-safe error and leaves manual return handling available
