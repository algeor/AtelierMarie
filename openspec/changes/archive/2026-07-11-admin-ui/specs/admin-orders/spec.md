## ADDED Requirements

### Requirement: Order list table
The admin order list at `/admin/orders` SHALL display orders in a table with columns: Order ID, Customer Email, Total, Status, Date, and Actions (update status).

#### Scenario: Order table renders
- **WHEN** admin navigates to `/admin/orders`
- **THEN** a table displays orders with columns: Order ID (truncated), Email, Total (EUR), Status, Date, Actions

#### Scenario: Order table shows formatted data
- **WHEN** the order table renders
- **THEN** order IDs are truncated to first 8 characters
- **AND** totals are displayed in EUR format
- **AND** dates are displayed in human-readable format (e.g., "Jul 11, 2026")
- **AND** status is displayed as a colored badge (pending=yellow, confirmed=blue, shipped=purple, delivered=green, cancelled=red)

### Requirement: Order status filter
The system SHALL provide a filter dropdown or pill buttons to filter orders by status. Selecting a status shows only orders matching that status. An "All" option shows all orders.

#### Scenario: Filter by status
- **WHEN** admin selects "Confirmed" from the status filter
- **THEN** only orders with status "confirmed" are displayed

#### Scenario: Show all orders
- **WHEN** admin selects "All" from the status filter
- **THEN** all orders are displayed regardless of status

### Requirement: Inline order status update
The system SHALL allow admins to update an order's status via a dropdown in the Actions column. Only valid state transitions SHALL be available as options.

#### Scenario: Update order status
- **WHEN** admin selects "Shipped" from the status dropdown on a "confirmed" order
- **THEN** the order status is updated via the API
- **AND** the status badge in the row updates to show "Shipped"

#### Scenario: Only valid transitions shown
- **WHEN** admin opens the status dropdown on a "pending" order
- **THEN** only "Confirmed" and "Cancelled" are available (valid transitions from pending)
- **AND** "Shipped" and "Delivered" are NOT available

#### Scenario: Update status failure
- **WHEN** the status update API call fails
- **THEN** the dropdown reverts to the previous status
- **AND** an error message is displayed
