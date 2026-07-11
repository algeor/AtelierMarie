## Context

AtelierMarie has an event pipeline (JSONL → DuckDB), a product catalog (SQLite CRUD with soft delete), a session/identity system, and Google OAuth. The platform needs to close the conversion loop: capture actual purchases as transactional records while feeding purchase signals into the ML layer.

**Current state:** Products exist in SQLite (`app/data/atelier.db`). Events flow via JSONL buffer to DuckDB. Users authenticate via Google OAuth with JWT tokens. Sessions are tracked via `X-Session-ID` header.

**Constraints:**
- Zero budget — no payment processors, no managed queues
- SQLite is the transactional store (WAL mode, same `atelier.db`)
- DuckDB is ML/analytics only — purchase events are behavioral, not transactional truth
- Must support anonymous checkout (session-only, no auth required)
- Must not fail the order if event emission fails

## Goals / Non-Goals

**Goals:**
- Capture orders as ACID-guaranteed transactional records in SQLite
- Emit purchase events to ML pipeline (fire-and-forget, post-commit)
- Support both cart-based checkout (POST /v1/cart/checkout, primary user flow) and direct order creation (POST /v1/orders, programmatic/API use)
- Enforce valid order status transitions via state machine
- Snapshot price at purchase time (immutable once ordered)
- Allow anonymous checkout with session_id linkage
- Provide order retrieval for authenticated users and session-matched anonymous users

**Non-Goals:**
- Online payment processing (no Stripe, PayPal, Google Pay, Apple Pay)
- Inventory tracking or stock validation (delegated to product-catalog and cart-management)
- Order notifications (email, push)
- Discount codes or pricing rules
- Multi-currency or tax calculation
- Order editing after creation (cancel/refund only)

## Decisions

### 1. Orders in the same SQLite database as products

**Decision:** `orders` and `order_items` tables go in `app/data/atelier.db` alongside `products` and `users`.

**Alternatives considered:**
- *Separate SQLite database for orders*: Complicates joins with products table and FK enforcement. Rejected.
- *DuckDB for orders*: Single-writer model conflicts with event batch loader. DuckDB is OLAP, not OLTP. Rejected.

**Rationale:** Same database means atomic transactions spanning orders + order_items with FK validation against products. SQLite WAL mode handles the read-heavy pattern (many order lookups, few order creates).

### 2. Auto-increment integer order IDs (not UUIDs)

**Decision:** `orders.id` is `INTEGER PRIMARY KEY AUTOINCREMENT`.

**Alternatives considered:**
- *UUID*: Better obscurity for anonymous access pattern. Adds complexity (TEXT PK, 36-char strings, no natural ordering). Rejected for MVP.
- *ULID*: Sortable + random, but overkill for MVP. Rejected.

**Rationale:** Simple, compact, naturally ordered (newest = highest). The anonymous access pattern (session_id match required) provides sufficient security for MVP. Migration to UUIDs is trivial if the platform goes public.

### 3. Dual checkout paths (cart-based + direct)

**Decision:** Two ways to create orders:
1. `POST /v1/cart/checkout` — primary user flow. Reads items from server-side cart (managed by cart-management change). No request body needed.
2. `POST /v1/orders` — programmatic/API flow. Accepts items array directly in request body.

Both use the same `order_service.create_order()` function underneath. The difference is only in where items come from.

**Alternatives considered:**
- *Cart-only checkout*: Forces all order creation through cart. Blocks programmatic bulk ordering, testing, and admin operations. Rejected.
- *Stateless-only (no server cart)*: Frontend holds all cart state; checkout sends full items list. Loses cart persistence across tabs/devices, requires client-side stock validation. Rejected for luxury UX.

**Rationale:** The server-side cart (from cart-management) gives the luxury UX expected — persistent, multi-tab, server-validated. The direct endpoint keeps the API flexible for future integrations (POS, wholesale, admin order creation).

### 4. Fire-and-forget event emission with structured logging

**Decision:** After order commit, build and emit a `purchase` event to the JSONL buffer. If the event write fails, log the error at WARNING level and return success to the client.

**Alternatives considered:**
- *Transactional outbox*: Write event to SQLite in the same transaction, background worker pushes to JSONL. Guarantees delivery but adds a table + worker. Overkill for MVP. Rejected.
- *Fail the order if event fails*: Violates the principle that SQLite is business truth. Rejected.

**Rationale:** The purchase event is supplementary ML data. The order record is the source of truth. A failed event write means one missing data point in DuckDB — acceptable for a zero-budget platform where the JSONL writer almost never fails (it's an append to a local file).

### 5. Order status as a state machine with explicit transitions

**Decision:** Status transitions are validated in the service layer against an allowed-transitions map. Invalid transitions return 422.

```python
VALID_TRANSITIONS = {
    "pending": ["confirmed", "cancelled"],
    "confirmed": ["shipped", "cancelled", "refunded"],
    "shipped": ["delivered"],
    "delivered": [],
    "cancelled": [],
    "refunded": [],
}
```

**Alternatives considered:**
- *Free-form status updates*: No protection against nonsensical transitions (delivered → pending). Rejected.
- *Separate status history table*: Good for audit trail but overkill for MVP. Rejected for now.

**Rationale:** Explicit transitions prevent data corruption and serve as documentation of the order lifecycle. Terminal states (cancelled, refunded, delivered) are enforced at the code level.

### 6. Session-based access for anonymous orders

**Decision:** Anonymous order retrieval requires both the order ID and a matching `X-Session-ID` header. No auth token needed.

**Alternatives considered:**
- *Signed order URL / access token*: More secure but adds token generation and storage. Rejected for MVP.
- *No anonymous access*: Forces login to view order. Bad UX for anonymous checkout flow. Rejected.

**Rationale:** Security-through-obscurity (must know order ID + session ID) is acceptable for MVP. The order ID alone is insufficient — the session_id provides a second factor.

### 7. Service layer for order logic (not in route handlers)

**Decision:** `order_service.py` handles order creation, status transitions, and event emission. Route handlers are thin — validate input, call service, return response.

**Rationale:** Order creation involves product validation, price calculation, transactional insert, and event emission. Putting this in the route handler creates an untestable monolith. Service layer enables unit testing without HTTP overhead.

### 8. Payment method as enum field (COD for MVP)

**Decision:** Orders have a `payment_method TEXT NOT NULL DEFAULT 'cod'` column. MVP supports only `"cod"` (cash on delivery). The checkout request may optionally include `payment_method`; if omitted, defaults to `"cod"`. Validation rejects unknown values.

**Alternatives considered:**
- *No payment_method field (implicit COD)*: Simpler now, but adding a second method later requires a schema migration to add the column + backfill. Rejected.
- *Separate payment table*: Overkill for a single enum field. Would make sense if we needed to track payment attempts, partial payments, etc. Rejected for MVP.
- *Online payment integration*: Zero-budget constraint. Google Pay/Apple Pay require a processor (Stripe, Adyen). Rejected.

**Rationale:** A single TEXT column with enum validation in the service layer costs almost nothing but makes the system trivially extensible. Adding `"bank_transfer"` or `"online"` later means adding one string to the allowed values — no migration needed. COD is the natural fit for zero-budget: payment happens at delivery, order confirmation is immediate (no webhook to wait for).

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| **Float price precision** → $0.01 rounding errors | Acceptable for MVP (same decision as products table). Document as known limitation. |
| **Auto-increment IDs** → enumerable by attackers | Session_id match required for anonymous access. Authenticated access restricted to own orders. Admin access restricted by API key. |
| **No inventory validation** → overselling possible | Out of scope. This is an ML platform, not a fulfillment system. |
| **Race condition: product deactivated between validation and insert** | Extremely unlikely (admin action during checkout). If it happens, FK constraint catches it. Return 409. |
| **Large order (100+ items)** → slow checkout | Unlikely for this platform type. Single transaction with batch insert handles it in <10ms. |
| **Lost purchase events** → ML data gap | Log at WARNING. Re-derivable from SQLite orders if needed (future backfill script). |

## Open Questions

None — all decisions resolved.
