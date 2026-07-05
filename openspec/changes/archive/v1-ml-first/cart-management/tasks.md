# Cart Management — Tasks

## 1. Database & Models

- [ ] 1.1 Create cart_items table in SQLite (session_id TEXT NOT NULL, product_id INTEGER NOT NULL REFERENCES products, quantity INTEGER NOT NULL DEFAULT 1, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (session_id, product_id))
- [ ] 1.2 Create SQLAlchemy model for cart_items
- [ ] 1.3 Create Pydantic schemas for cart request/response (CartItem, CartResponse with items + totals)

## 2. Cart State API

- [ ] 2.1 Implement GET /v1/cart — return cart items with product name, image_url, price, quantity, line_subtotal, and cart_total
- [ ] 2.2 Implement POST /v1/cart/items — add item (product_id, quantity). Validate: product exists, is_active, stock >= requested quantity. If already in cart, increment quantity.
- [ ] 2.3 Implement PATCH /v1/cart/items/{product_id} — update quantity. If quantity=0, remove item. Validate stock for increases.
- [ ] 2.4 Implement DELETE /v1/cart/items/{product_id} — remove item from cart. Return 404 if not in cart.
- [ ] 2.5 Implement cart service layer (reusable by checkout)
- [ ] 2.6 Emit add_to_cart event on POST (product_id, quantity, source)
- [ ] 2.7 Emit remove_from_cart event on DELETE and quantity-to-zero PATCH

## 3. Cart Checkout

- [ ] 3.1 Implement POST /v1/cart/checkout — no request body. Read cart for session, validate all items in stock, create order + order_items atomically, decrement stock, clear cart, emit purchase event.
- [ ] 3.2 Handle partial stock failure (identify which items are insufficient, return 409 with details)
- [ ] 3.3 Handle empty cart (return 400 "Cart is empty")
- [ ] 3.4 Handle inactive/deleted products in cart at checkout time (return 409 identifying unavailable items)
- [ ] 3.5 Return created order details on success (order_id, items, total, status)
