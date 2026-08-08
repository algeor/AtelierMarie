# Developer Workflows

Common patterns for adding features, fixing bugs, and debugging.

## Workflow 1: Add a New Product Attribute

**Goal:** Add a product field (e.g., `origin_country`)

**Steps:**

1. **Decide:** Does this need a DB column? If yes → file Alembic migration
   ```bash
   .venv/bin/alembic revision --autogenerate -m "add product origin_country"
   # Edit alembic/versions/...py
   ```

2. **Backend model:** Add field to `app/models/products.py`
   ```python
   class ProductResponse(BaseModel):
       origin_country: str | None = None
   ```

3. **Backend service:** Update `app/services/product_service.py`
4. **Backend tests:** Add test in `tests/test_products.py`
5. **Frontend model:** Add to `frontend/lib/types.ts` ProductResponse interface
6. **Frontend component:** Update product card/detail to display
7. **Frontend mock:** Update `frontend/lib/mock-api.ts` with sample data
8. **I18n:** Add label in `frontend/messages/en.json` + `bg.json`
9. **Test:** Run `make test`
10. **Manual verify:** Create product via admin, see it on storefront

**Commit:** One commit per logical layer (model → service → route → frontend)

---

## Workflow 2: Fix a Bug

**Goal:** User reports checkout fails silently

**Steps:**

1. **Reproduce:** Can you hit it locally? In mock or real mode?
2. **Locate:** Search codebase for symptom
   ```bash
   grep -r "checkout" app/routes app/services --include="*.py"
   ```
3. **Understand:** Read the service code; check data flow in `ARCHITECTURE.md`
4. **Fix:** Make the *smallest* change that fixes it
5. **Add test:** Write a test that would have caught this bug
6. **Verify:** Manually test the fixed flow end-to-end
7. **Commit:** Describe what broke and why the fix works

---

## Workflow 3: Add an Admin Feature

**Goal:** Admins need to bulk edit product descriptions

**Steps:**

1. **Frontend first:**
   - Add page: `frontend/app/[locale]/admin/bulk-edit.tsx`
   - Create component: `frontend/components/admin/BulkEditForm.tsx`
   - Use mock API first: update `frontend/lib/mock-api.ts`

2. **Backend:**
   - Add route: `app/routes/admin.py` (or new module)
   - Add service: `app/services/admin_service.py`
   - Add model: `app/models/admin.py`

3. **Test:**
   - Backend: `make test-backend`
   - Frontend: `make test-frontend`
   - Manual: Switch frontend to real mode, test the flow

4. **Verify admin auth:** Use `require_admin` dependency on backend

---

## Workflow 4: Debug Stripe Payments

**Goal:** Card checkout returns error

**Steps:**

1. **Get local webhook secret:**
   ```bash
   make stripe-webhook-secret
   ```

2. **Set in `.env`:**
   ```
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_WEBHOOK_SECRET=whsec_...
   ```

3. **Start webhook forwarder:**
   ```bash
   make dev-stripe-webhook
   ```

4. **Restart backend:** `make dev-backend`

5. **Add logs:** In `app/services/payment_service.py`, add structured logging

6. **Trigger order:** Create order with card payment in frontend

7. **Inspect DB:** Check `stripe_events` table:
   ```bash
   .venv/bin/psql postgresql://atelier:atelier@localhost:5432/atelier_marie
   SELECT * FROM stripe_events ORDER BY received_at DESC LIMIT 5;
   ```

8. **Check logs:** Look at backend terminal for errors

---

## Workflow 5: Test Courier Integration (Speedy/Econt)

**Goal:** Verify live pricing works

**Steps:**

1. **Set credentials in `.env`:**
   ```
   SPEEDY_API_USERNAME=username
   SPEEDY_API_PASSWORD=password
   SPEEDY_CLIENT_ID=12345
   ```

2. **Health check:** Go to `/admin/delivery/speedy` → Click "Check Connection"

3. **Create test order:** Checkout with Speedy door delivery

4. **Inspect:** Check `order_courier_events` table:
   ```bash
   SELECT * FROM order_courier_events ORDER BY created_at DESC LIMIT 5;
   ```

5. **Debug:** If quote fails, check `courier_last_error` in orders table

---

## Workflow 6: Add Backend Tests

**Pattern: Arrange → Act → Assert**

```python
# tests/test_cart_service.py

def test_add_to_cart_out_of_stock(db):
    # Arrange: Set up test data
    product = add_product(db, id="test-candle", stock=0)
    session = add_session(db)
    
    # Act & Assert: Verify behavior
    with pytest.raises(OutOfStockError):
        cart_service.add_to_cart(
            session_id=session.id,
            product_id="test-candle",
            quantity=1
        )
```

**Run tests:**
```bash
make test-backend
.venv/bin/pytest tests/test_cart_service.py::test_add_to_cart_out_of_stock -v
```

---

## Workflow 7: Add Frontend Tests

**Pattern: Arrange → Render → Assert**

```typescript
// frontend/__tests__/components/ProductCard.test.tsx

test('renders product card with reaction count', () => {
  const { getByText } = render(
    <ProductCard product={mockProduct} />
  )
  expect(getByText('42')).toBeInTheDocument() // heart count
})
```

**Run tests:**
```bash
make test-frontend
npm --prefix frontend run vitest run
```

---

## Workflow 8: Review Database Changes

**Goal:** Verify schema migration is safe

**Steps:**

1. **Check migration:** `alembic/versions/...py`
2. **Verify downgrade:** Does `downgrade()` exist?
3. **Test locally:**
   ```bash
   .venv/bin/alembic upgrade head
   make test
   ```
4. **Check data:** Will existing rows break?
5. **Commit:** Include migration number in commit message

---

## Key Patterns

### Thin Routes, Fat Services
```
Route layer:    HTTP parsing → call service → HTTP response
Service layer:  Business logic (testable, no HTTP)
```

### Session-First Identity
```
Anonymous user → Session UUID
Optional login → Session.user_id + JWT
Cart follows session, not user
```

### Layer Separation (e-commerce vs analytics)
```
Layer 1 (Postgres):  Checkout, orders, payments
Layer 2 (DuckDB):    Events, analytics, ML
Layer 1 NEVER imports Layer 2
```

---

## Safety Constraints

1. **Layer 1 code NEVER imports Layer 2 modules**
2. **Cart stock validated at add, not just checkout**
3. **Transactional email must work offline**
4. **Order items are immutable** (never update after creation)
5. **Tests must clean up** between runs
6. **API responses are JSON only**
7. **Admin routes require authentication**

---

## Good First Tasks

- Add/improve a component test
- Add a service test for edge case
- Improve empty/loading/error states
- Tighten copy in `en.json` + `bg.json`
- Update stale docs
- Fix a type warning (`npm --prefix frontend run typecheck`)

---

## Avoid These First

- Payment provider behavior
- Session/auth rotation
- Schema migrations
- Analytics consent/legal
- Product video processing
- Cross-stack checkout changes
