## Context

Follow-on to `shipping-courier-integration` (parent), which delivers the structured delivery picker without pricing. This change adds real-time courier pricing on top.

Refer to the parent's `design.md` decisions 10–14 (real-time calculation, free shipping, fallback, per-product weight, `shipping_cents` column) and decision 16 (server-side validation via range check) — those are hereby adopted as the design of this change. The sections below capture only what's new or specific to the pricing layer.

> **Weight data half extracted:** Decision 13's `weight_grams` data model (DB column + `DEFAULT 300 CHECK (weight_grams > 0)`, product models, admin form field, CSV import column) is delivered by the **`product-mgmt-completeness`** change and is already in the codebase. This change only **consumes** `weight_grams` when computing cart weight — the calculation endpoint reads weights server-side from the DB.

## Goals / Non-Goals

**Goals:**
- Real-time shipping cost via Speedy and Econt calculation APIs
- Two-phase UX: approximate (both couriers, for comparison) → exact (selected courier only)
- Free shipping for orders ≥ €50 (server-enforced)
- Graceful degradation: fallback flat rate when a courier API is unavailable
- Per-product weight for accurate calculation
- Checkout POST stays < 200ms (no external calls in the checkout transaction — pricing is calculated in a separate endpoint, validated by range check at checkout)

**Non-Goals (this change / Phase A):**
- Signed price tokens (parent Decision 16 chose range check for MVP)
- Shaped snapshot-table fallback and its fetch script — **deferred to Phase B** (see Phasing)
- Reconciliation of quoted vs actual courier invoice — **deferred to Phase C**
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
    is_fallback: bool  # True when a non-live tier produced the price
    price_source: Literal["live", "table", "flat"]  # provenance — see Decision 5
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

### 3. Timeout + fallback are per-courier, not global — and the fallback is *tiered*

Each courier call gets its own 3s timeout. On timeout / 5xx / auth-failure, the courier does **not** fail the endpoint — it degrades through a tiered fallback (see Decision 5). If Speedy times out but Econt returns, the response includes Econt's real price and a Speedy *fallback* quote (`is_fallback: true`, `price_source` reflecting which tier answered). The whole endpoint never fails — worst case, both couriers return flat last-resort quotes.

**Rationale:** Partial data is better than no data. Customer can still choose the courier that responded, and the fallback lets them still proceed if both are down.

> **Phase A note:** In this change the fallback is the flat last-resort tier only (`FALLBACK_SHIPPING_CENTS`). The *shaped* snapshot-table tier (Decision 5, tier 2) is a **follow-on change** — see "Phasing" below. Phase A ships live + flat, but records `price_source` from day one so we can measure how often the fallback fires before investing in the table.

### 4. Free-shipping threshold is enforced in `/calculate` AND in checkout

Both `/v1/delivery/calculate` and `order_service.checkout()` independently check `items_total_cents >= FREE_SHIPPING_THRESHOLD_CENTS` and force `shipping_cents = 0`. The calculate endpoint does it so the UI shows "Безплатна доставка" without a round-trip; checkout does it as the final source of truth (parent Decision 16 — server never trusts the frontend for this). Free shipping short-circuits the whole pricing pipeline — it is evaluated *before* the tiered fallback (Decision 5), so an outage never charges a fallback price on a qualifying order.

### 5. Tiered fallback with price provenance

When live pricing is unavailable, the price degrades through tiers rather than jumping straight to a blind flat rate. Each tier is recorded on the quote (and later on the order) via `price_source`:

```
  free shipping? items ≥ €50 ──yes──▶ 0¢        (short-circuit)
       │ no
       ▼
  TIER 1  live courier calculate   ──✓──▶  price_source="live",  is_fallback=false
       │ down / slow / 5xx / auth-fail
       ▼
  TIER 2  snapshot table           ──✓──▶  price_source="table", is_fallback=true
       │  (zone × weight_tier)                    ── FOLLOW-ON (Phase B), not this change
       │ zone unknown / table miss
       ▼
  TIER 3  flat FALLBACK_SHIPPING_CENTS  ──▶  price_source="flat",  is_fallback=true
```

**In Phase A (this change)** only tiers 1 and 3 exist — live, else flat. Tier 2 (the shaped snapshot table, mirroring how the parent stores office data in `data/*.json` refreshed by a fetch script) is deferred to Phase B. The `price_source` enum includes `"table"` now so the schema and persistence don't change when Phase B lands.

**Provenance is persisted on the order** at checkout: `price_source`, `is_fallback`, and `quoted_at`. This is the professional keystone — it lets the shop (a) measure how often live pricing actually fails before building tier 2, and (b) reconcile quoted shipping against the courier's real invoice later (Phase C). Without it, every fallback is silent and unauditable.

**Rationale:** A blind flat rate ignores weight and destination — fine as a rare last resort, wrong as the only fallback. Recording provenance turns "we guessed" from an invisible event into measurable data that justifies (or refutes) the next phase.

### 6. Fallback disclaimer shown only when the price is a genuine guess

The `is_fallback` disclaimer in the UI is shown **only** for tier 2/3 quotes (`price_source != "live"`), never for a live quote. This resolves the conflict between the parent's landed `courier-delivery` spec (which showed the flat price with *no* indicator) and an earlier draft of this change's tasks (which showed a disclaimer unconditionally): the rule is now provenance-driven — live prices carry no disclaimer, fallback prices do.

**Rationale:** Disclaiming a live, cent-exact price needlessly undermines customer confidence; not disclaiming a guessed price is dishonest. Tie the disclaimer to provenance and both cases are correct.

## Phasing

This change is **Phase A** of a three-phase professional rollout. It is independently shippable — priced checkout works end-to-end on live pricing with a flat fallback.

| Phase | Scope | Ships in |
|-------|-------|----------|
| **A — live + flat + provenance** | Live Speedy/Econt calculate, flat last-resort fallback, `price_source`/`is_fallback`/`quoted_at` persisted on orders, two-phase UX | **this change** |
| **B — shaped snapshot fallback** | `data/shipping_tariffs.json` + `data/city_zones.json`, `scripts/fetch_courier_tariffs.py` (sibling to `fetch_courier_offices.py`), tier-2 pricing in `shipping_service` | follow-on change |
| **C — reconciliation** | Admin view comparing quoted `shipping_cents` vs courier invoice; surfaces tariff drift | follow-on change |

**Why phase, not build-all-at-once:** Phase A's `price_source` instrumentation produces the evidence for whether Phase B is worth building. If `"flat"` almost never appears in real orders, the snapshot table is unnecessary complexity; if it appears often, we build it knowing it matters. Instrument first, then build on data.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| Both couriers down simultaneously | Each degrades independently through the tiered fallback (Decision 5). In Phase A both return the flat last-resort with `price_source="flat"`; order still proceeds, warning logged, and the `"flat"` count is now measurable per order. |
| Approximate → exact delta feels like bait-and-switch | Show the disclaimer prominently ("Ориентировъчна цена, финалната може да варира"). If real deltas turn out to be > ~15% commonly, revisit whether to skip the approximate phase for that route. |
| Product weights are wrong (default 300g used) | Courier APIs tolerate ±200g at these scales. Admin can refine per-product weights over time. Include a note in the admin product form. |
| Sender office assumption (single origin) | Documented as env-var config. Multi-origin is out of scope for MVP — revisit when a second atelier exists. |
| Courier API auth failures on startup | Credentials are validated lazily (per-request), not at startup. A misconfigured account produces fallback quotes with a logged warning — checkout keeps working. |

## Open Questions

- Speedy `serviceId` — which service tier to hardcode (standard vs. express)?
- Econt calculation endpoint exact request format — verify once account is created
- Whether "approximate" needs both couriers for small towns where only one operates
