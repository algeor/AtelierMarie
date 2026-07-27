## ADDED Requirements

### Requirement: Return notification templates in both locales
The system SHALL provide plain-text templates for the return events in both `en/` and
`bg/`, named `order_return_approved.txt`, `order_return_rejected.txt`,
`order_return_refunded.txt`, and `admin_return_requested.txt`, following the existing
`order_{event}.txt` convention. Customer templates SHALL render in the order's stored
`locale`. Templates SHALL include the order number, affected items, and — for the
refund template — the refunded amount; they SHALL NOT include payment card data.

#### Scenario: Refund template renders in the order locale
- **WHEN** the `return_refunded` email renders for an order with `locale = "bg"`
- **THEN** the Bulgarian `order_return_refunded.txt` template is used and includes the refunded amount

#### Scenario: Missing locale falls back
- **WHEN** a template is requested for a locale without a specific file
- **THEN** the renderer falls back per the existing locale-fallback rule
