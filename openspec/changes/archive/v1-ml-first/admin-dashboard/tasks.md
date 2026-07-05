# Admin Dashboard — Tasks

## 1. Admin Access Control

- [ ] 1.1 Add is_admin boolean column to users table (default FALSE)
- [ ] 1.2 Implement first-user-as-admin bootstrap logic (on first Google sign-in, auto-set is_admin=TRUE)
- [ ] 1.3 Implement admin auth dependency (check is_admin flag from JWT or API key from X-Admin-API-Key header)
- [ ] 1.4 Add ATELIER_ADMIN_API_KEY env var support for programmatic admin access

## 2. Dashboard Metrics API

- [ ] 2.1 Implement GET /v1/admin/dashboard endpoint returning aggregate metrics
- [ ] 2.2 Implement metrics computation service (DuckDB queries for views, sessions, conversion, add-to-cart rate)
- [ ] 2.3 Implement revenue computation from SQLite orders
- [ ] 2.4 Implement top-10 products by views/carts/purchases
- [ ] 2.5 Implement popular search terms aggregation (top 20 by frequency)
- [ ] 2.6 Implement session breakdown (anonymous vs authenticated vs converted)
- [ ] 2.7 Implement recommendation CTR computation
- [ ] 2.8 Add optional date range filtering (?from=&to=)
- [ ] 2.9 Implement 5-minute in-memory cache for dashboard metrics

## 3. Admin Data Endpoints

- [ ] 3.1 Implement GET /v1/admin/events (paginated, filterable by event_type, date range)
- [ ] 3.2 Implement GET /v1/admin/products (all products with view_count, cart_count, order_count)
- [ ] 3.3 Implement GET /v1/admin/orders (paginated, includes status, total, item_count, session/user info)

## 4. Admin Frontend

- [ ] 4.1 Create /(admin)/dashboard page with admin auth gate
- [ ] 4.2 Implement metrics cards row (total views, sessions, orders, conversion %, revenue)
- [ ] 4.3 Implement top products table (sortable by views/carts/orders)
- [ ] 4.4 Implement search terms table
- [ ] 4.5 Implement recent orders table with status badges
- [ ] 4.6 Implement session breakdown display
- [ ] 4.7 Implement recommendation performance card (CTR %)
