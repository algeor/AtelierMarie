# Admin Orders — Spec

## ADDED Requirements

### Requirement: Paginated order listing with default page size of 20

GET /v1/admin/orders returns a paginated list of orders with limit/offset support.

#### Scenario: Default pagination returns 20 orders

WHEN an admin requests GET /v1/admin/orders without pagination parameters
THEN the response returns up to 20 orders
AND the response includes total_count indicating total orders in the system
AND the response includes limit=20 and offset=0

#### Scenario: Custom pagination

WHEN an admin requests GET /v1/admin/orders?limit=10&offset=30
THEN the response returns up to 10 orders starting from the 31st order
AND total_count reflects total matching orders regardless of pagination

#### Scenario: Limit capped at maximum

WHEN an admin requests GET /v1/admin/orders?limit=200
THEN the response uses limit=100 (maximum allowed)
AND returns up to 100 orders

---

### Requirement: Order response includes required fields

Each order in the response contains identification, financial, and contextual information.

#### Scenario: Order object contains all required fields

WHEN an admin requests GET /v1/admin/orders
THEN each order in the response contains:
- id (order identifier)
- status (e.g., "pending", "completed", "cancelled")
- total_price (decimal, the order total)
- item_count (integer, number of line items)
- user_email (string: the user's email if authenticated, or "Anonymous" if guest checkout)
- session_id (the session that placed the order)
- created_at (ISO 8601 timestamp)

#### Scenario: Authenticated order shows user email

WHEN an admin requests GET /v1/admin/orders
AND an order was placed by a user with email "marie@example.com"
THEN that order's user_email field is "marie@example.com"

#### Scenario: Anonymous order shows "Anonymous"

WHEN an admin requests GET /v1/admin/orders
AND an order was placed without user authentication (guest session)
THEN that order's user_email field is "Anonymous"

---

### Requirement: Orders ordered by created_at descending

Orders are always returned newest-first to show recent activity at the top.

#### Scenario: Most recent orders appear first

WHEN an admin requests GET /v1/admin/orders
AND there are orders created at times T1 < T2 < T3
THEN the response lists orders in order T3, T2, T1

#### Scenario: Pagination preserves sort order

WHEN an admin requests GET /v1/admin/orders?limit=5&offset=5
THEN the returned orders are the 6th through 10th most recent orders
AND they are still sorted by created_at descending within the page

---

### Requirement: Filter by order status

Orders can be filtered by status to focus on specific fulfillment states.

#### Scenario: Filter by completed status

WHEN an admin requests GET /v1/admin/orders?status=completed
THEN only orders with status="completed" are returned
AND total_count reflects only completed orders

#### Scenario: Filter by pending status

WHEN an admin requests GET /v1/admin/orders?status=pending
THEN only orders with status="pending" are returned

#### Scenario: Filter by cancelled status

WHEN an admin requests GET /v1/admin/orders?status=cancelled
THEN only orders with status="cancelled" are returned

#### Scenario: No filter returns all statuses

WHEN an admin requests GET /v1/admin/orders without status parameter
THEN orders of all statuses are returned
