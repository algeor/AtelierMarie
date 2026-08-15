## ADDED Requirements

### Requirement: Product and order API models include crafted-later fields
The shared API models used by backend and frontend SHALL include the crafted-later availability and fulfillment fields introduced by this change. Product models SHALL include `can_order`, `available_now`, `availability_status`, and `ships_when_complete`. Order models SHALL include `fulfillment_status`, and order-item models SHALL include `allocated_quantity` and `backordered_quantity` where the response shape supports fulfillment detail.

#### Scenario: Public product model includes availability fields
- **WHEN** a product response is serialized
- **THEN** the API model contains the crafted-later availability fields defined by this change

#### Scenario: Order model includes fulfillment status
- **WHEN** an order response is serialized
- **THEN** the API model contains `fulfillment_status`

#### Scenario: Admin order item model includes allocation detail
- **WHEN** an admin order detail response is serialized
- **THEN** each item includes `allocated_quantity` and `backordered_quantity`
