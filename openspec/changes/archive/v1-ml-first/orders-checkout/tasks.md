## 1. Database Schema

- [ ] 1.1 Add `orders` table to SQLite schema init (id, user_id FK, session_id, payment_method DEFAULT 'cod', total_price, status, created_at, updated_at)
- [ ] 1.2 Add `order_items` table to SQLite schema init (id, order_id FK, product_id FK, quantity, price_at_purchase)
- [ ] 1.3 Add indexes on orders(user_id), orders(session_id), order_items(order_id)

## 2. Pydantic Models

- [ ] 2.1 Create `app/models/orders.py` with OrderItemCreate (product_id, quantity), OrderCreate (items list, optional payment_method)
- [ ] 2.2 Add OrderItemResponse (product_id, quantity, price_at_purchase) and OrderResponse (id, user_id, session_id, payment_method, total_price, status, items, created_at, updated_at)
- [ ] 2.3 Add OrderListResponse (paginated: items, total, page, per_page) and OrderStatusUpdate (status)

## 3. Order Service Layer

- [ ] 3.1 Create `app/services/order_service.py` with `create_order()` — validate products, validate payment_method, calculate total, atomic insert of order + items
- [ ] 3.2 Implement price snapshotting: read current product price and store as price_at_purchase
- [ ] 3.3 Implement duplicate product_id validation in items list
- [ ] 3.4 Implement purchase event emission (fire-and-forget post-commit, log on failure)
- [ ] 3.5 Implement `VALID_TRANSITIONS` map and `update_order_status()` with state machine enforcement
- [ ] 3.6 Implement `get_order()` with ownership/session validation logic
- [ ] 3.7 Implement `list_user_orders()` with offset pagination

## 4. API Routes

- [ ] 4.1 Create `app/api/v1/orders.py` with POST /v1/orders (checkout endpoint, uses get_current_user_optional)
- [ ] 4.2 Add GET /v1/orders/{id} — authenticated user ownership check OR anonymous session_id match
- [ ] 4.3 Add GET /v1/orders — authenticated user's paginated order list
- [ ] 4.4 Add PATCH /v1/orders/{id}/status — admin-only with API key auth, validates transition
- [ ] 4.5 Register orders router in FastAPI app

## 5. Integration & Testing

- [ ] 5.1 Write tests for order creation (happy path: authenticated + anonymous)
- [ ] 5.2 Write tests for validation failures (invalid product, inactive product, empty items, duplicate items, missing session, unsupported payment method)
- [ ] 5.3 Write tests for order retrieval (owner access, session match, denied access)
- [ ] 5.4 Write tests for status transitions (valid transitions, invalid transitions, terminal states)
- [ ] 5.5 Write test for purchase event emission (success + failure tolerance)
- [ ] 5.6 Verify atomic rollback: partial insert failure rolls back entire transaction
