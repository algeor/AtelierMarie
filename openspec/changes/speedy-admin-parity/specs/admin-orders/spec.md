## ADDED Requirements

### Requirement: Admin orders link Speedy fulfillment to Speedy admin
Admin order list and order detail surfaces SHALL keep existing Speedy fulfillment behavior while linking Speedy-specific operations to the dedicated Speedy admin page. Existing `confirmed -> shipped` automation SHALL remain available from the order list and order detail.

#### Scenario: Speedy order links to Speedy admin context
- **WHEN** an admin views a Speedy order in the admin order list or detail page
- **THEN** the UI provides a path to the Speedy admin page filtered or focused on that order where practical

#### Scenario: Existing Speedy ship automation remains
- **WHEN** an admin marks a confirmed Speedy order shipped from the order list or detail page without manual tracking
- **THEN** the system still creates a Speedy waybill through the existing shipped transition

### Requirement: Admin order detail shows Speedy fulfillment state
Admin order detail SHALL show Speedy shipment number, tracking URL, display courier status, label action, latest Speedy operation error where available, and links to Speedy admin diagnostics for Speedy orders.

#### Scenario: Speedy shipment metadata visible
- **WHEN** an admin opens a Speedy order that has a tracking number
- **THEN** the order detail shows the tracking number, tracking URL, courier status if present, print label action, and Speedy diagnostics link

#### Scenario: No Speedy controls on non-Speedy order
- **WHEN** an admin opens an order whose delivery courier and tracking carrier are not Speedy
- **THEN** Speedy-specific order detail controls are hidden
