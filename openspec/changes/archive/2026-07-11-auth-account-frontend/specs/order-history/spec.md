## ADDED Requirements

### Requirement: My Orders page lists past orders
The system SHALL have a page at `/orders` that displays a paginated list of the user's past orders, sorted by most recent first. Each order entry SHALL show the order ID (truncated), date, status badge, item count, and total.

#### Scenario: Authenticated user with orders
- **WHEN** an authenticated user with past orders navigates to `/orders`
- **THEN** the page SHALL display a list of their orders sorted by `created_at` DESC, each showing: order date (formatted), status badge (colored by status), number of items, and total price

#### Scenario: Authenticated user with no orders
- **WHEN** an authenticated user with no orders navigates to `/orders`
- **THEN** the page SHALL display a friendly empty state: "No orders yet" with a "Start Shopping" link to `/products`

#### Scenario: Anonymous user with session orders
- **WHEN** an anonymous user who placed orders in this session navigates to `/orders`
- **THEN** the page SHALL display orders from the current session (session-keyed endpoint), plus a message encouraging login to see all past orders

#### Scenario: Pagination
- **WHEN** the user has more than 20 orders
- **THEN** the page SHALL show pagination controls (Next/Previous) and display 20 orders per page

### Requirement: Order status badges show visual state
The system SHALL display order status as a colored badge component. Each status SHALL have a distinct color for quick visual scanning.

#### Scenario: Status-to-color mapping
- **WHEN** an order has status "pending"
- **THEN** the badge SHALL be amber/yellow with text "Pending"

#### Scenario: All status colors
- **WHEN** orders with different statuses are displayed
- **THEN** pending SHALL be amber, confirmed SHALL be blue, shipped SHALL be indigo, delivered SHALL be green, and cancelled SHALL be red

### Requirement: Order detail page shows full order information
The system SHALL have a page at `/orders/[id]` that displays the complete order: items with prices, total, customer info, and a status timeline.

#### Scenario: View order detail
- **WHEN** a user navigates to `/orders/{orderId}`
- **THEN** the page SHALL display: order ID, order date, current status badge, all items (name, quantity, unit price, line total), order total, and customer email

#### Scenario: Order not found
- **WHEN** a user navigates to `/orders/{invalid-id}` (non-existent or not owned by user)
- **THEN** the page SHALL display "Order not found" with a link back to the orders list

#### Scenario: Order detail loading state
- **WHEN** the order detail page is fetching data
- **THEN** it SHALL display skeleton placeholders for all content areas

### Requirement: Status timeline shows order progress
The system SHALL display a vertical timeline/stepper on the order detail page showing the progression of order states.

#### Scenario: Order in confirmed state
- **WHEN** an order has status "confirmed"
- **THEN** the timeline SHALL show "Pending" and "Confirmed" as completed steps (filled/colored), and "Shipped" and "Delivered" as future steps (gray/unfilled)

#### Scenario: Delivered order
- **WHEN** an order has status "delivered"
- **THEN** the timeline SHALL show all four steps (Pending → Confirmed → Shipped → Delivered) as completed

#### Scenario: Cancelled order timeline
- **WHEN** an order has status "cancelled"
- **THEN** the timeline SHALL show completed steps up to the point of cancellation, then a "Cancelled" indicator branching off (e.g., red X or strikethrough on remaining steps)

### Requirement: Order list page accessible from header menu
The My Orders page SHALL be accessible from the authenticated user's header dropdown menu under "My Orders".

#### Scenario: Navigate to orders from menu
- **WHEN** an authenticated user clicks "My Orders" in the header dropdown
- **THEN** they SHALL be navigated to `/orders`

### Requirement: Orders page handles loading and error states
The system SHALL handle loading and error states gracefully on the orders page.

#### Scenario: Orders loading
- **WHEN** the orders page is fetching the order list
- **THEN** it SHALL display skeleton placeholders (list of order-shaped cards)

#### Scenario: Orders fetch error
- **WHEN** the orders API call fails (network error, server error)
- **THEN** the page SHALL display "Something went wrong loading your orders" with a "Try again" button that retries the fetch
