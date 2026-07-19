## Context

Follow-on to `shipping-courier-integration` (parent), which delivers the structured delivery picker without pricing. This change adds real-time courier pricing on top.

Refer to the parent's `design.md` decisions 10–14 (real-time calculation, free shipping, fallback, per-product weight, `shipping_cents` column) and decision 16 (server-side validation via range check) — those are hereby adopted as the design of this change. The sections below capture only what's new or specific to the pricing layer.

## Goals / Non-Goals

**Goals:**
- Real-time shipping cost via Speedy and Econt calculation APIs
- Two-phase UX: approximate (both couriers, for comparison) → exact (selected courier only)
- Free shipping for orders ≥ €50 (server-enforced)
- Graceful degradation: fallback flat rate when a courier API is unavailable
- Per-product weight for accurate calculation
- Checkout POST stays < 200ms (no external calls in the checkout transaction — pricing is calculated in a separate endpoint, validated by range check at checkout)

**Non-Goals:**
- Signed price tokens (parent Decision 16 chose range check for MVP)
- Cached prices per city / warm-cache strategies
- Live label generation, tracking numbers, courier webhooks
- Address validation against courier APIs
- Multi-parcel splits

## Decisions specific to this change

### 1. Courier API client is a thin per-courier module

Two isolated modules — `app/services/speedy_client.py` and `app/services/econt_client.py` — each exposing `async calculate(...)` with a normalized return shape:

```python
class ShippingQuote(BaseModel):
    courier: Literal["speedy", "econt"]
    cents: int
    estimated_delivery_days: int | None
    is_fallback: bool  # True when the flat fallback was used
```

`shipping_service.py` orchestrates: fans out to both clients in parallel for the approximate phase, calls one for the exact phase, applies the free-shipping override, and returns `list[ShippingQuote]`.

**Rationale:** Each courier has a different API shape, auth, and error surface. Keeping them separate makes each one independently testable and swappable. The orchestrator is the only place that knows about both.

### 2. Approximate vs. exact are the same endpoint, different arguments

Single endpoint `POST /v1/delivery/calculate` with:
```
{
  "method": "office" | "door",
  "city": "София",
  "office_id": "speedy-sf-001" | null,   # null → approximate
  "address": { ... } | null,             # null for office method
  "cart_weight_grams": 1400,
  "items_total_cents": 4200,
  "couriers": ["speedy", "econt"]        # 1 or 2
}
```

When `office_id` and `address` are both null → approximate mode (city-level estimate). When one is provided → exact mode for that courier.

**Rationale:** One endpoint keeps the frontend logic simple ("fetch quotes with whatever I know so far"). The backend already has the branching, so exposing two endpoints would just duplicate the surface.

### 3. Timeout + fallback are per-courier, not global

Each courier call gets its own 3s timeout. If Speedy times out but Econt returns, the response includes Econt's real price and a Speedy fallback quote with `is_fallback: true`. The whole endpoint never fails — worst case, both couriers return fallback quotes.

**Rationale:** Partial data is better than no data. Customer can still choose the courier that responded, and the fallback lets them still proceed if both are down.

### 4. Free-shipping threshold is enforced in `/calculate` AND in checkout

Both `/v1/delivery/calculate` and `order_service.checkout()` independently check `items_total_cents >= FREE_SHIPPING_THRESHOLD_CENTS` and force `shipping_cents = 0`. The calculate endpoint does it so the UI shows "Безплатна доставка" without a round-trip; checkout does it as the final source of truth (parent Decision 16 — server never trusts the frontend for this).

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| Both couriers down simultaneously | Fallback returned for both. Customer sees a fixed price, order still proceeds. Backend logs a warning. |
| Approximate → exact delta feels like bait-and-switch | Show the disclaimer prominently ("Ориентировъчна цена, финалната може да варира"). If real deltas turn out to be > ~15% commonly, revisit whether to skip the approximate phase for that route. |
| Product weights are wrong (default 300g used) | Courier APIs tolerate ±200g at these scales. Admin can refine per-product weights over time. Include a note in the admin product form. |
| Sender office assumption (single origin) | Documented as env-var config. Multi-origin is out of scope for MVP — revisit when a second atelier exists. |
| Courier API auth failures on startup | Credentials are validated lazily (per-request), not at startup. A misconfigured account produces fallback quotes with a logged warning — checkout keeps working. |

## Open Questions

- Speedy `serviceId` — which service tier to hardcode (standard vs. express)?
- Econt calculation endpoint exact request format — verify once account is created
- Whether "approximate" needs both couriers for small towns where only one operates
