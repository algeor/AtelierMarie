## Context

AtelierMarie currently stores shipping as a single optional text field (`shipping_address TEXT` in the orders table). The checkout UI renders it as a textarea. This works for a prototype but is completely impractical for Bulgaria, where ~90% of e-commerce deliveries go through Speedy or Econt courier services. Customers expect to choose a delivery method (office pickup or door delivery), select their courier provider, and—for office pickup—search and select from a list of courier offices.

The existing `POST /v1/orders` accepts `shipping_address: str | None`. The frontend checkout-ui spec defines it as a single textarea. The orders-checkout design doc explicitly marks shipping cost calculation as a non-goal for MVP. The order service uses a single SQLite transaction for checkout.

Speedy and Econt both have public APIs for office listings, but for MVP we'll use static office data (periodically refreshed) to avoid runtime API dependencies on checkout.

## Goals / Non-Goals

**Goals:**
- Let customers choose delivery method: office pickup or to-door delivery
- Let customers select courier provider: Speedy or Econt
- For office pickup: provide a city-filtered, searchable office picker (offices + lockers/автомати)
- For to-door: collect structured address (city, postal code, street, building/apt, phone)
- Calculate shipping price dynamically from courier APIs (two-phase: approximate then exact)
- Show both courier options with prices for comparison before customer commits
- Free shipping for orders ≥ €50
- Store structured delivery data + shipping cost in orders (queryable by admin)
- Display delivery details and shipping breakdown clearly in admin order view
- Keep checkout POST still under 200ms (no external API calls during the checkout transaction itself)

**Non-Goals:**
- Live courier API integration for tracking or label generation (future enhancement)
- Address validation against courier APIs (trust user input for MVP)
- Automated office list sync from courier APIs (manual script-based refresh for now)
- Multiple delivery addresses per order
- International shipping (Bulgaria only)
- Express/same-day delivery options (standard service only for MVP)

## Decisions

### 1. Structured delivery object replaces shipping_address string

**Decision:** Replace the flat `shipping_address: str | None` field with a structured `delivery` object in `CreateOrderRequest`:

```python
class DeliveryOffice(BaseModel):
    courier: Literal["speedy", "econt"]
    office_id: str  # Courier's own office identifier
    office_name: str  # Display name for confirmation/admin
    office_type: Literal["office", "apt"]  # Staffed office or automated locker (автомат)

class DeliveryDoor(BaseModel):
    courier: Literal["speedy", "econt"]
    city: str
    postal_code: str
    street: str
    building: str | None = None  # Building/entrance
    apartment: str | None = None  # Floor/apartment
    phone: str  # Required for courier contact

class DeliveryInfo(BaseModel):
    method: Literal["office", "door"]
    office: DeliveryOffice | None = None  # Required when method="office"
    door: DeliveryDoor | None = None  # Required when method="door"
```

**Alternatives considered:**
- *Keep single string, parse on display:* Unstructured data leads to delivery errors. Rejected.
- *Multiple flat fields on CreateOrderRequest:* Doesn't model the office-vs-door distinction cleanly. Rejected.
- *Polymorphic discriminated union:* Python's discriminated union (`Annotated[... | ..., Field(discriminator=...)]`) — more complex, harder to document in OpenAPI. The nested optional approach is simpler for this case.

**Rationale:** Explicit structure prevents data entry errors. The `office_id` allows future integration with courier tracking APIs. Courier name stored with the order enables admin to know which company to contact.

### 2. Office data stored as static JSON, served via API endpoint

**Decision:** Courier office lists are stored as JSON files in the backend (`data/speedy_offices.json`, `data/econt_offices.json`). A `GET /v1/delivery/offices?courier=speedy&city=Sofia` endpoint serves them filtered. No database table for offices.

Office data structure:
```json
{
  "id": "speedy-sf-001",
  "name": "Speedy офис София Център - бул. Витоша 50",
  "city": "София",
  "address": "бул. Витоша 50",
  "working_hours": "Mon-Fri 09:00-18:00, Sat 09:00-14:00"
}
```

**Alternatives considered:**
- *Database table with admin CRUD:* Over-engineered for data that changes rarely and comes from courier companies. Rejected.
- *Call courier APIs live:* Adds external dependency to checkout flow, risks latency/failures. Rejected for MVP.
- *Hardcode in frontend:* Makes updates require frontend deploy. Rejected.

**Rationale:** Static JSON is simplest to maintain (copy from courier website/API periodically). Backend endpoint allows filtering without sending full list to client. Easy to upgrade to live API later.

### 3. Database schema: JSON column for delivery details

**Decision:** Add columns to `orders` table:
```sql
ALTER TABLE orders ADD COLUMN delivery_method TEXT;  -- "office" | "door" | NULL (legacy)
ALTER TABLE orders ADD COLUMN delivery_courier TEXT;  -- "speedy" | "econt" | NULL
ALTER TABLE orders ADD COLUMN delivery_details TEXT;  -- JSON blob with full details
```

The `delivery_details` column stores the full `DeliveryOffice` or `DeliveryDoor` object as JSON. `delivery_method` and `delivery_courier` are denormalized for easy querying/filtering without JSON parsing.

**Alternatives considered:**
- *Separate delivery_addresses table:* Normalized but adds JOIN complexity for a 1:1 relationship. Rejected.
- *All fields as individual columns:* Too many columns, half NULL depending on method. Rejected.
- *Pure JSON (no denormalized columns):* Makes admin filtering by courier/method require JSON functions. Rejected.

**Rationale:** Hybrid approach — queryable top-level fields for filtering, JSON blob for full details. SQLite has `json_extract()` if we ever need to query inside the blob.

### 4. Cities endpoint for typeahead

**Decision:** Add `GET /v1/delivery/cities?courier=speedy&q=Со` — returns distinct cities from the office data where the courier has offices. Used by the frontend for the city search/filter before showing offices.

For to-door delivery, the city field is a free-text input (no restriction to cities with offices — couriers deliver to all cities).

**Rationale:** Office picker needs city filtering. Sending all cities upfront in the offices payload bloats initial load. A lightweight endpoint keeps the UI responsive.

### 5. Frontend: step-based delivery section in checkout

**Decision:** The checkout shipping section becomes a multi-step flow within the same page (not separate pages):
1. **Choose method** — Radio: "Вземи от офис" (office) / "Доставка до врата" (door)
2. **Choose courier** — Radio: Speedy / Econt (with logos)
3. **Choose details** — Office picker (for office method) OR address form (for door method)

All steps visible/collapsible on the same checkout page. No separate routing.

**Alternatives considered:**
- *Multi-page wizard:* Too many clicks for a simple choice. Rejected.
- *Single dropdown with all options:* Doesn't scale to hundreds of offices. Rejected.

**Rationale:** Keeps checkout as a single page (no navigation changes). Progressive disclosure — show relevant fields based on prior selection.

### 6. Backward compatibility: shipping_address field deprecated

**Decision:** The `shipping_address` field is removed from `CreateOrderRequest`. Existing orders with `shipping_address` data retain it (column stays in DB). The new `delivery` field is required for new orders. Admin view handles both old-format (plain string) and new-format (structured JSON) orders.

**Migration path:** Since this is pre-launch (no live customers), there's no data migration needed — existing test orders can be deleted or ignored.

**Rationale:** Clean break is acceptable pre-launch. No backward compat shim needed.

### 7. Phone number required for all delivery methods

**Decision:** Phone number is required for both office pickup and door delivery. Couriers always need a contact number. For office pickup, phone is stored in the `DeliveryOffice` model (added field). For door delivery, it's in `DeliveryDoor`.

**Rationale:** Speedy and Econt both require a recipient phone number regardless of delivery method. Better to collect it upfront than have the courier contact fail.

### 8. Office type distinguishes staffed offices from lockers (автомати)

**Decision:** The `DeliveryOffice` model includes `office_type: Literal["office", "apt"]`. Both Speedy and Econt expose this distinction in their APIs (`"OFFICE"` vs `"APT"` for automated parcel terminals). The office picker UI can show different icons/labels and the office data JSON includes the type field.

The office data schema becomes:
```json
{
  "id": "speedy-sf-001",
  "name": "Speedy офис София Център - бул. Витоша 50",
  "type": "office",
  "city": "София",
  "address": "бул. Витоша 50",
  "working_hours": "Mon-Fri 09:00-18:00, Sat 09:00-14:00"
}
```

**Alternatives considered:**
- *Ignore type, treat all as "office":* Customers expect to know if it's a locker (different pickup flow — SMS code vs counter). Rejected.
- *Separate endpoints for offices vs lockers:* Unnecessary complexity. Single list with a type filter is simpler. Rejected.

**Rationale:** Lockers are increasingly popular (especially in Sofia). Customers choosing an автомат know the pickup is self-service (code-based). The UI can show a locker icon, filter by type, and potentially show different instructions on the order confirmation.

### 9. Office data sourced from courier APIs via fetch script

**Decision:** Office data is fetched from official courier APIs using a script (`scripts/fetch_courier_offices.py`), not scraped or manually compiled:
- Econt: `POST /Nomenclatures/NomenclaturesService.getOffices` (HTTP Basic auth)
- Speedy: `POST /location/office` (credentials in JSON body)

The script normalizes both responses into the unified schema and writes `data/speedy_offices.json` and `data/econt_offices.json`. For MVP, run manually when needed. Future: nightly cron job.

**Rationale:** Both couriers provide official APIs for this exact purpose. A fetch script is reproducible, fast, and trivial to automate later. Eliminates manual data entry errors and makes quarterly refresh a one-command operation.

### 10. Real-time shipping price calculation from courier APIs

**Decision:** Shipping cost is calculated dynamically using official courier APIs, not hardcoded. The calculation uses:
- **Sender:** Your configured drop-off office (stored in app config as `SPEEDY_SENDER_OFFICE_ID` and `ECONT_SENDER_OFFICE_ID`)
- **Recipient:** Customer's selected office/address
- **Weight:** Sum of `weight_grams` across cart items × quantities + `PACKAGING_WEIGHT_GRAMS` buffer

Two-phase calculation:
1. **Approximate (both couriers):** Triggered when customer selects city/method. Calls both courier APIs, returns estimates for comparison. Shown with disclaimer "Ориентировъчна цена. Може да се промени при избор на конкретен офис/адрес."
2. **Exact (selected courier):** Triggered when customer picks specific office/address. Updates the displayed price to final.

A new backend endpoint: `POST /v1/delivery/calculate` accepts courier(s), method, destination (city for approximate, office_id/full address for exact), and cart weight. Returns price per courier.

API details:
- Speedy: `POST https://api.speedy.bg/v1/calculate` — accepts `sender.dropoffOfficeId`, `recipient.pickupOfficeId` (or `recipient.addressLocation`), `content.totalWeight`, `service.serviceIds`
- Econt: Shipment calculation endpoint via their Shipments service (similar structure)

**Alternatives considered:**
- *Calculate only after courier selection (one API call):* Customer can't compare prices before choosing. Loses a key decision signal. Rejected.
- *Hardcoded flat rates:* Inaccurate, doesn't reflect distance/weight. Rejected.
- *Calculate during checkout POST:* Adds external dependency to the atomic checkout transaction. Rejected — keep calculation separate.

**Rationale:** Customers expect to see shipping cost before committing. Showing both courier prices lets them choose based on value. The two-phase approach balances UX (fast initial estimates) with accuracy (exact price before final submit).

### 11. Free shipping above €50 threshold

**Decision:** Orders with `items_total_cents >= 5000` (€50) get free shipping. When free shipping applies:
- Skip courier API calculation (or still show crossed-out price for psychology: "~~6.50€~~ Безплатна")
- `shipping_cents = 0`
- UI shows: "Безплатна доставка ✓"

When below threshold, UI shows: "Добави още за X€ за безплатна доставка"

Constants:
```python
FREE_SHIPPING_THRESHOLD_CENTS = 5000  # €50
```

**Rationale:** Standard e-commerce incentive. Encourages larger orders. €50 is achievable with 2-3 candles.

### 12. Fallback flat rate when courier API is unavailable

**Decision:** When a courier's calculation API is down (timeout, 5xx, network error), use a fixed fallback price:

```python
FALLBACK_SHIPPING_CENTS = 500  # €5.00 flat fallback
```

The fallback is intentionally on the low side (real price is often €5-7). Rationale: better to slightly undercharge on the rare API-down case than to block checkout or show an inflated price. The margin loss on a few orders is acceptable.

UI shows the fallback price normally (no special indicator to customer). Backend logs a warning when fallback is used. Calculation endpoint returns a `is_estimate: true` flag so the frontend could optionally indicate it, but this is not required.

**Alternatives considered:**
- *Block checkout when API is down:* Lost sales are worse than €1-2 margin loss. Rejected.
- *Show "Price TBD, we'll contact you":* Bad UX, cart abandonment risk. Rejected.
- *Cached last-known price per city:* Over-engineering for an edge case. Rejected.

**Rationale:** Courier APIs are generally reliable, but the store must never be blocked by a third-party dependency. Fixed fallback is simple and the financial risk is bounded.

### 13. Product weight field for shipping calculation

**Decision:** Add `weight_grams INTEGER NOT NULL DEFAULT 300` to the `products` table. Each product stores its shipping weight (product + container, e.g., wax + glass jar + lid). A flat packaging buffer is added at order level:

```python
PACKAGING_WEIGHT_GRAMS = 200  # box, bubble wrap, filler
```

Calculation: `order_weight = Σ(product.weight_grams × quantity) + PACKAGING_WEIGHT_GRAMS`

The weight doesn't need to be perfectly accurate — courier APIs are forgiving within ~100-200g at these scales (candles are small parcels). Weights can be refined over time.

**Impact:**
- Products table: new `weight_grams` column (default 300g — safe middle for candles)
- `ProductResponse` model: add `weight_grams: int`
- CSV import: optional `weight_grams` column (uses default if missing)
- Admin product form: weight input field (grams)

**Rationale:** Candles range from ~150g (travel tin) to ~800g (large three-wick in glass). A single flat weight for all products would consistently over/under-charge. Per-product weight with a packaging buffer gives reasonable accuracy with minimal effort.

### 14. Order stores shipping cost separately; total includes shipping

**Decision:** The `orders` table gains a `shipping_cents INTEGER NOT NULL DEFAULT 0` column. The `total_cents` field becomes `items_total_cents + shipping_cents`:

```python
class OrderResponse(BaseModel):
    items_total_cents: int   # sum of (price × qty) across order items
    shipping_cents: int      # 0 when free, otherwise courier-calculated
    total_cents: int         # items_total_cents + shipping_cents
    delivery_method: str | None
    delivery_courier: str | None
    delivery_details: dict | None
```

The checkout flow:
1. Calculate `items_total_cents` from cart
2. If `items_total_cents >= FREE_SHIPPING_THRESHOLD_CENTS`: `shipping_cents = 0`
3. Else: `shipping_cents` = pre-calculated courier price (passed from frontend, validated server-side)
4. `total_cents = items_total_cents + shipping_cents`

**Rationale:** Separating shipping from items total gives clear breakdown in receipts, admin views, and future reporting. Customer always sees what they're paying for.

### 15. Checkout UX reordered: city/method first, then courier comparison with prices

**Decision:** The delivery section flow changes from the original Decision #5. New order:

1. **Choose method** — Radio: "Вземи от офис" / "Доставка до врата"
2. **Enter location** — City search (for office method) or city field (for door)
3. **See courier comparison** — Both Speedy and Econt shown with approximate price + estimated delivery time. Disclaimer: "Ориентировъчна цена"
4. **Choose courier** — Customer picks based on price/preference
5. **Choose specifics** — Office picker (for office) or full address form (for door)
6. **See final price** — Exact price calculated, replaces approximation. Shown in order summary.

This supersedes the original Decision #5 ordering (which had courier choice at step 2, before location). The key insight: customers want to compare prices, and price depends on destination — so destination must come first.

**Rationale:** Price is the #1 decision factor for courier choice in Bulgaria. Showing both options with prices lets the customer make an informed decision without guessing.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| **Stale office data** | Include "last updated" date in JSON files. Add admin note to refresh quarterly. Future: automated sync from courier APIs. |
| **Office removed but referenced in old order** | Office name stored in order (snapshot). Order is always readable even if office no longer exists in current data. |
| **Large office list (~3000 Econt + ~1500 Speedy offices)** | City filtering reduces payload to ~50-100 per request. Client-side search within city results. |
| **Bulgarian text in office names** | UTF-8 throughout. Frontend uses proper Cyrillic rendering. Search is case-insensitive with Bulgarian locale. |
| **Breaking API change** | Pre-launch, no live consumers. Frontend and backend deploy together. Document in changelog. |
| **Courier adds new delivery methods** | `delivery_method` is a Literal type — adding a new method requires code change. Acceptable at this scale. |
| **Phone validation** | Basic format check (digits, optional +, 8-15 chars). Not validating against carrier databases. |
| **Courier API latency** | Calculation is a separate async step (not in checkout transaction). UI shows loading state. Timeout at 5s → fallback price. |
| **Courier API downtime** | Fallback flat rate (€5). Logged as warning. Customer experience unaffected. |
| **Inaccurate product weights** | Weights don't need to be exact — courier APIs tolerate ±200g for small parcels. Refineable over time. |
| **Free shipping threshold gaming** | €50 is 2-3 candles — legitimate purchase size. Not a concern at this scale. |

## Open Questions

- **Econt calculation endpoint** — need to verify exact request format once account is created (similar to Speedy's `/calculate` but via their Shipments service).
- **Courier service IDs** — Speedy requires a `serviceId` in the calculation request (e.g., standard vs express). Need to determine which service types to offer once account is active.
- **Approximate calculation strategy** — For the city-level estimate, does Speedy's API accept just a `siteId` without a specific office? Needs testing with real credentials.
