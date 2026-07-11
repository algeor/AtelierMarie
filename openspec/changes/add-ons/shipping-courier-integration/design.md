## Context

AtelierMarie currently stores shipping as a single optional text field (`shipping_address TEXT` in the orders table). The checkout UI renders it as a textarea. This works for a prototype but is completely impractical for Bulgaria, where ~90% of e-commerce deliveries go through Speedy or Econt courier services. Customers expect to choose a delivery method (office pickup or door delivery), select their courier provider, and—for office pickup—search and select from a list of courier offices.

The existing `POST /v1/orders` accepts `shipping_address: str | None`. The frontend checkout-ui spec defines it as a single textarea. The orders-checkout design doc explicitly marks shipping cost calculation as a non-goal for MVP. The order service uses a single SQLite transaction for checkout.

Speedy and Econt both have public APIs for office listings, but for MVP we'll use static office data (periodically refreshed) to avoid runtime API dependencies on checkout.

## Goals / Non-Goals

**Goals:**
- Let customers choose delivery method: office pickup or to-door delivery
- Let customers select courier provider: Speedy or Econt
- For office pickup: provide a city-filtered, searchable office picker
- For to-door: collect structured address (city, postal code, street, building/apt, phone)
- Store structured delivery data in orders (queryable by admin)
- Display delivery details clearly in admin order view
- Keep checkout still under 200ms (no external API calls during checkout)

**Non-Goals:**
- Real-time shipping cost calculation (flat-rate or free shipping remains — pricing is out of scope)
- Live courier API integration for tracking or label generation (future enhancement)
- Address validation against courier APIs (trust user input for MVP)
- Automated office list sync from courier APIs (manual JSON refresh for now)
- Multiple delivery addresses per order
- International shipping (Bulgaria only)

## Decisions

### 1. Structured delivery object replaces shipping_address string

**Decision:** Replace the flat `shipping_address: str | None` field with a structured `delivery` object in `CreateOrderRequest`:

```python
class DeliveryOffice(BaseModel):
    courier: Literal["speedy", "econt"]
    office_id: str  # Courier's own office identifier
    office_name: str  # Display name for confirmation/admin

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

## Open Questions

None — all decisions are straightforward for pre-launch MVP. Future enhancements (live API, tracking, shipping cost calculation) are explicitly deferred.
