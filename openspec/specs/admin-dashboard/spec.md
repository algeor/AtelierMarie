## ADDED Requirements

### Requirement: Dashboard stats cards
The admin dashboard SHALL display stats cards showing: orders today (count), revenue this week (formatted as EUR), and active product count. Each card SHALL show the metric label, value, and a simple icon.

#### Scenario: Dashboard displays all stats
- **WHEN** an admin navigates to `/admin`
- **THEN** the page displays three stats cards: "Orders Today", "Revenue This Week", "Active Products"
- **AND** each card shows a numeric value

#### Scenario: Stats reflect current data
- **WHEN** admin views the dashboard
- **THEN** "Orders Today" shows the count of orders placed today
- **AND** "Revenue This Week" shows the sum of order totals this week formatted as currency (EUR)
- **AND** "Active Products" shows the count of products where `is_active` is true

### Requirement: Dashboard loading state
The system SHALL display skeleton placeholders while stats are loading.

#### Scenario: Stats loading
- **WHEN** admin navigates to the dashboard and stats are being fetched
- **THEN** skeleton cards are shown in place of the stats
- **AND** once data loads, skeleton cards are replaced with actual values
