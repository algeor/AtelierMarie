## ADDED Requirements

### Requirement: Admin dashboard overview metrics
The system SHALL expose GET /admin/dashboard returning aggregate metrics: total product views, total unique sessions, total orders, conversion rate (orders / sessions), add-to-cart rate (cart events / sessions), and revenue total.

#### Scenario: Dashboard metrics returned
- **WHEN** an admin calls GET /admin/dashboard
- **THEN** the API returns total_views, unique_sessions, total_orders, conversion_rate, add_to_cart_rate, and total_revenue

#### Scenario: Metrics filtered by date range
- **WHEN** an admin calls GET /admin/dashboard?from=2025-01-01&to=2025-01-31
- **THEN** only events and orders within that range are included in metrics

### Requirement: Top products report
The system SHALL include in dashboard metrics the top 10 products by views, top 10 by add-to-cart, and top 10 by purchases.

#### Scenario: Top products by views
- **WHEN** the dashboard is loaded
- **THEN** the top 10 most-viewed products are listed with view counts

### Requirement: Popular search terms
The system SHALL expose GET /admin/events/searches returning the top 20 search queries by frequency with their result counts.

#### Scenario: Search terms aggregated
- **WHEN** an admin views search analytics
- **THEN** the top 20 queries are returned sorted by frequency, each with avg_result_count

### Requirement: Session analytics
The system SHALL provide anonymous vs. authenticated session breakdown showing: total anonymous sessions, total authenticated sessions, sessions that converted (anonymous → logged in), and average events per session.

#### Scenario: Session breakdown returned
- **WHEN** an admin views session analytics
- **THEN** counts for anonymous, authenticated, and converted sessions are displayed

### Requirement: Recommendation performance metrics
The system SHALL track and expose recommendation click-through rate: how often recommended products are clicked vs. displayed.

#### Scenario: Recommendation CTR calculated
- **WHEN** recommendations were shown 1000 times and clicked 50 times
- **THEN** the recommendation CTR is reported as 5%

### Requirement: Admin events log
The system SHALL expose GET /admin/events with pagination and filtering by event_type, returning recent events with session_id, user_id, product_id, event_type, metadata, and timestamp.

#### Scenario: Events listed with filters
- **WHEN** an admin calls GET /admin/events?event_type=purchase&limit=50
- **THEN** the 50 most recent purchase events are returned

### Requirement: Admin product list
The system SHALL expose GET /admin/products returning all products with stock levels, total views, and total orders for each product.

#### Scenario: Product list with metrics
- **WHEN** an admin calls GET /admin/products
- **THEN** each product includes stock_quantity, total_views, and total_orders counts

### Requirement: Admin order list
The system SHALL expose GET /admin/orders with pagination returning orders with status, total, user/session info, and item count.

#### Scenario: Orders listed
- **WHEN** an admin calls GET /admin/orders?limit=20
- **THEN** the 20 most recent orders are returned with status, total_price, and item_count

### Requirement: Admin authentication
The admin dashboard endpoints SHALL require admin-level authentication. The first registered user SHALL be auto-promoted to admin (bootstrap flow).

#### Scenario: Non-admin access denied
- **WHEN** a regular user calls GET /admin/dashboard
- **THEN** the API returns HTTP 403

#### Scenario: First user becomes admin
- **WHEN** the first Google sign-in occurs with no existing users
- **THEN** that user is created with admin role
