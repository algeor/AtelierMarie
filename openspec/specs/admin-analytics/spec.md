# admin-analytics Specification

## Purpose
TBD - created by archiving change first-party-funnel-analytics. Update Purpose after archive.
## Requirements
### Requirement: Admin analytics panel
The system SHALL provide an admin-only analytics panel at `/admin/analytics`. The panel SHALL show funnel, product, cart, checkout, delivery, payment, purchase, event delivery health, and order coverage metrics for a selected date range.

#### Scenario: Admin opens analytics panel
- **WHEN** an authenticated admin navigates to `/admin/analytics`
- **THEN** the analytics panel renders with date range controls and metric sections

#### Scenario: Non-admin cannot access analytics panel
- **WHEN** an unauthenticated visitor or non-admin user navigates to `/admin/analytics`
- **THEN** the system denies access using the existing admin protection behavior

### Requirement: Admin analytics API
The system SHALL expose admin-only analytics APIs for summary metrics, funnel metrics, product metrics, event delivery health, and optional paginated event debugging. All analytics admin endpoints SHALL require admin authentication.

#### Scenario: Admin summary request succeeds
- **WHEN** an admin requests analytics summary for a valid date range
- **THEN** the API returns sessions with analytics consent, total accepted events, conversion rate, order count, revenue, and event delivery health

#### Scenario: Non-admin summary request denied
- **WHEN** a non-admin requests an analytics admin API endpoint
- **THEN** the API returns HTTP 403 or the existing admin-auth failure response

### Requirement: Funnel report
The analytics panel SHALL show counts and conversion percentages for `product_view`, `listing_filter`, `add_to_cart`, `cart_open`, `checkout_start`, `delivery_selected`, `shipping_quote_selected`, `order_submit`, `payment_redirect`, and `purchase_confirmed` in the selected date range. Counts SHALL be shown beside percentages.

#### Scenario: Funnel counts render
- **WHEN** the selected date range contains accepted analytics events
- **THEN** each funnel step displays count and conversion percentage from the prior step

#### Scenario: Empty funnel renders safely
- **WHEN** the selected date range contains no accepted analytics events
- **THEN** the panel displays zero counts without division-by-zero errors

### Requirement: Product analytics report
The analytics panel SHALL show product-level views, add-to-cart counts, purchase counts, revenue, and conversion rates. Product metrics SHALL join analytics events with current product records by stable product ID.

#### Scenario: Product metrics render
- **WHEN** a product has views, add-to-cart events, and purchases in the selected date range
- **THEN** the product analytics table displays those counts, revenue, and conversion rate

### Requirement: Checkout and delivery analytics report
The analytics panel SHALL show checkout starts, delivery selections by method/courier, shipping quote selections, order submissions, payment redirects, and purchase confirmations. Delivery and shipping metrics SHALL use only non-PII properties such as delivery method, courier, quote cents, and currency.

#### Scenario: Delivery method metrics render
- **WHEN** accepted events include office and door delivery selections
- **THEN** the dashboard reports counts for each delivery method without storing or displaying addresses or phone numbers

### Requirement: Dashboard order coverage against backend orders
The analytics panel SHALL show authoritative backend order counts and revenue for the selected date range, consented analytics `purchase_confirmed` counts and revenue for the same date range, and the resulting analytics coverage percentage. The panel SHALL label backend order data as business truth and consented analytics data as measured behavioral coverage.

#### Scenario: Order coverage renders
- **WHEN** the selected date range contains backend orders and consented analytics purchases
- **THEN** the panel displays backend order count/revenue, analytics purchase count/revenue, and coverage percentage

#### Scenario: Low coverage is labelled clearly
- **WHEN** analytics purchase count is lower than backend order count because some customers did not consent to analytics
- **THEN** the panel labels the difference as analytics coverage rather than a data error

#### Scenario: Consented-order delivery check detects missing events
- **WHEN** backend records show consented orders that should have produced `purchase_confirmed` events but analytics events are missing beyond the configured tolerance
- **THEN** the panel displays a delivery-health warning with both consented-order and analytics-purchase values

### Requirement: Analytics export
The admin panel SHALL allow admins to export aggregate analytics reports as CSV for the selected date range. Exports SHALL contain aggregate metrics only and SHALL NOT include customer PII.

#### Scenario: Admin exports funnel CSV
- **WHEN** an admin clicks export for the funnel report
- **THEN** the downloaded CSV contains funnel step names, counts, and conversion percentages for the selected date range

