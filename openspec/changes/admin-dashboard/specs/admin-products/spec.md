# Admin Products — Spec

## ADDED Requirements

### Requirement: Product listing with event-derived performance metrics

GET /v1/admin/products returns all products from the catalog enriched with computed metrics from event data.

The `total_views`, `total_cart_adds`, and `total_orders` metrics are read from `analytics_product_metrics` joined with the SQLite products table, rather than computed per-request from the events table.

#### Scenario: Products returned with performance metrics

WHEN an admin requests GET /v1/admin/products
THEN the response includes all products in the catalog
AND each product contains: id, name, price, stock_quantity, active (boolean), total_views, total_cart_adds, total_orders

#### Scenario: Metrics reflect actual event counts

WHEN an admin requests GET /v1/admin/products
AND product "Lavender Bliss" has 150 page_view events, 30 add_to_cart events, and appears in 12 completed orders
THEN the product entry shows total_views=150, total_cart_adds=30, total_orders=12

#### Scenario: Product with no events shows zero metrics

WHEN an admin requests GET /v1/admin/products
AND a newly added product has no associated events
THEN that product is still listed with total_views=0, total_cart_adds=0, total_orders=0

---

### Requirement: Sorting by any metric column

The product list can be sorted by any metric column to identify top or bottom performers.

#### Scenario: Sort by total views descending (default)

WHEN an admin requests GET /v1/admin/products without sort parameters
THEN products are sorted by total_views descending

#### Scenario: Sort by specific column ascending

WHEN an admin requests GET /v1/admin/products?sort_by=total_orders&sort_dir=asc
THEN products are sorted by total_orders in ascending order

#### Scenario: Sort by stock quantity to find low-stock items

WHEN an admin requests GET /v1/admin/products?sort_by=stock_quantity&sort_dir=asc
THEN products are sorted by stock_quantity ascending (lowest stock first)

#### Scenario: Invalid sort column returns 422

WHEN an admin requests GET /v1/admin/products?sort_by=nonexistent_field
THEN the response status is 422 Unprocessable Entity
AND the error message lists valid sort columns

---

### Requirement: Active/inactive product status

Each product includes its active status, allowing admins to see which products are currently available for purchase.

#### Scenario: Active products show active=true

WHEN an admin requests GET /v1/admin/products
AND a product is marked as active in the catalog
THEN that product's entry shows active=true

#### Scenario: Inactive products are included in the listing

WHEN an admin requests GET /v1/admin/products
AND some products are marked as inactive
THEN inactive products are still returned in the response with active=false
AND their metrics still reflect historical event data

#### Scenario: Filter by active status

WHEN an admin requests GET /v1/admin/products?active=true
THEN only products with active=true are returned

#### Scenario: Filter inactive products

WHEN an admin requests GET /v1/admin/products?active=false
THEN only products with active=false are returned
