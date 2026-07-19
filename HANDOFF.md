# shipping-courier-integration — session handoff

**Date:** 2026-07-19 (session 2)
**Branch:** fix-language-flags (uncommitted work)
**Progress:** 10/33 tasks done — Milestones 1, 2, 3 complete ✅

## What's done since last handoff

### Milestone 2 — Office data + delivery API
- **2.1 (Econt half)** — `data/econt_offices.json` normalized (628 offices, bilingual: `name`/`name_en`, `city`/`city_en`, `working_hours`/`working_hours_en`). Speedy half deferred (no source data yet — will be produced by 2.2).
- **2.3** — `app/services/delivery_service.py` created. Module-level load from `COURIER_FILES` dict, missing files log a warning and return `[]` (no startup failure). `get_offices(courier, city, office_type, locale)` and `get_cities(courier, query, locale)` with cross-language matching (`city="Sofia"` matches `София`).
- **2.4** — `app/routes/delivery.py` created. `GET /v1/delivery/offices` and `GET /v1/delivery/cities`. Strict Literal validation on `courier`/`type`, cross-language city matching, `q`-prefixed cities endpoint (spec-compliant param name).
- **2.5** — Router registered in `app/main.py` line 165 (`prefix="/v1/delivery"`, tag `delivery`).

### Milestone 3 — Order service (app unblocked ✅)
- **3.1** — `checkout()` rewritten: takes `delivery: DeliveryInfo`, JSON-serializes the sub-object with `ensure_ascii=False`, INSERTs `delivery_method`/`delivery_courier`/`delivery_details`. Computes `items_total_cents = sum(price*qty)`, `shipping_cents = 0`, `total_cents = items_total + shipping`.
- **3.2** — `_fetch_order_with_items()`: `json.loads` details (bad JSON → warn + `None`), defensive `"col" in row.keys()` for `shipping_cents` (added later by `shipping-pricing`).
- **3.3** — `OrderData` TypedDict: dropped `shipping_address`, added `items_total_cents`, `shipping_cents`, `delivery_method`, `delivery_courier`, `delivery_details`.
- **3.4** — `app/routes/orders.py` line ~66: passes `delivery=body.delivery`, dropped `shipping_address=body.shipping_address`.

## ⚠️ App is likely bootable but untested

`make dev-backend` should now start. `make test-backend` will fail because legacy tests reference `shipping_address` in checkout payloads and `OrderData` (see task 4.6 — cleanup grep).

## Uncommitted changes on disk

Beyond the previous session's list:
- `app/services/order_service.py` (MODIFIED) — checkout rewritten, TypedDict updated, `_fetch_order_with_items` updated, `import json`, `import DeliveryInfo`
- `app/services/delivery_service.py` (NEW) — bilingual-aware office/city lookup
- `app/routes/delivery.py` (NEW) — `/offices` and `/cities` endpoints
- `app/routes/orders.py` (MODIFIED) — `delivery=body.delivery` in checkout call
- `app/main.py` (MODIFIED) — delivery router registered (import out of alphabetical order — nit, run `ruff check --fix`)
- `app/models/delivery.py` (MODIFIED) — added `OfficeResponse` model (6-field API-shape response)
- `scripts/normalize_econt_office_data.py` (MODIFIED) — user added `_working_hours_en`, English fields renamed to `_en` suffix
- `data/econt_offices.json` — normalized, bilingual
- `openspec/changes/shipping-courier-integration/tasks.md` — 1.1–1.3, 2.3–2.5, 3.1–3.4 checked

## Where to pick up

**Next action:** Milestone 4 (tests) — start with task 4.6 (legacy cleanup grep) so the suite runs, then 4.1–4.5.

### Milestone 4 — Tests
- [ ] **4.6 (do FIRST)** — `grep -rn "shipping_address" tests/ app/` — rip references out of existing tests and any lingering app code. Pre-launch: safe to delete legacy branches entirely (Decision 6).
- [ ] 4.1 `tests/test_models_delivery.py` — parametrized model validation (phone regex, missing sub-object, wrong method/details combo)
- [ ] 4.2 `tests/test_routes_delivery.py` — endpoint coverage matching the 8 spec scenarios (Sofia BG/EN, lockers-only, unknown city, missing file, invalid courier, missing params, invalid type)
- [ ] 4.3 `tests/test_orders_checkout_office.py` — office delivery checkout, delivery fields persisted, Cyrillic round-trip
- [ ] 4.4 Door delivery checkout test — full address stored + JSON roundtrip
- [ ] 4.5 Validation errors — missing `delivery`, bad `method`, `office` method with no `office` object → 422

### Milestone 5 — Frontend components (`frontend/components/checkout/`)
- [ ] 5.1 `DeliveryMethodSelector.tsx` — radio group, `useTranslations("checkout.delivery.method")`
- [ ] 5.2 `CourierPicker.tsx` — radio cards for Speedy/Econt
- [ ] 5.3 `OfficePicker.tsx` — city typeahead → office list, `type` filter (office/apt)
- [ ] 5.4 `DoorAddressForm.tsx`
- [ ] 5.5 `DeliverySection.tsx` orchestrator

### Milestone 6 — Checkout integration
- [ ] 6.1–6.6 as before (see tasks.md)

### Milestone 7 — Admin + i18n
- [ ] 7.1 Admin order detail — structured delivery display
- [ ] 7.2 Legacy handling (mirror 4.6 decision)
- [ ] 8.1 Add `checkout.delivery.*` keys to `frontend/messages/{bg,en}.json` per design.md Decision 17
- [ ] 8.2 Verify `i18n-rendering.test.tsx` passes

### Milestone 2 leftover
- [ ] 2.1 (Speedy half) — produce `data/speedy_offices.json` (blocked on source data / task 2.2)
- [ ] 2.2 `scripts/fetch_courier_offices.py` — end-to-end fetch+normalize+atomic-write. Design pattern: `CourierSource` dataclass with `fetch`/`normalize` callables + `SOURCES` list; per-courier try/except (Speedy stub raises `NotImplementedError`, main loop logs "skipped" and moves on).

## Key architectural decisions in play

1. **Static JSON, not live API proxy.** Runtime reads from `data/*.json`.
2. **Unified 6-field schema is the contract.** `id, name, type, city, address, working_hours`. Bilingual on disk (`_en` variants); `delivery_service` resolves per locale.
3. **`shipping_cents = 0` throughout this change.** Real courier pricing is `shipping-pricing` follow-on.
4. **Pre-launch = clean break.** Legacy `shipping_address` gets ripped out in 4.6.
5. **Cross-language city matching.** `city="Sofia"` and `city="София"` both find Sofia offices (case-insensitive, checks both `city` and `city_en`).

## Gotchas already discovered

- Econt `fullAddress` has leading space + duplicates city → compose from `quarter/street/num/other`.
- Econt working hours: Unix ms in `Europe/Sofia`; `from == to` means closed (Saturday) → omit that half.
- `delivery_service` uses `Path(__file__).resolve().parent.parent.parent / "data"` — repo-rooted, works from any cwd. Tests may need to `chdir` or override `_DATA_DIR`.
- `_fetch_order_with_items` uses defensive `"col" in row.keys()` for `shipping_cents` — this column doesn't exist yet (added by `shipping-pricing`). Remove that guard when the sibling change lands.
- `app/main.py` import line 20: `delivery` tacked at end alphabetically — Ruff will complain. One-line fix.
- Tests reference `shipping_address` in payloads. Suite will fail until 4.6 runs. **Do 4.6 first.**
- `ensure_ascii=False` on the delivery-details JSON so Cyrillic stays readable in the DB.
- `OrderResponse` in `app/models/orders.py` already has `items_total_cents`, `shipping_cents=0` defaults, and the three delivery fields. Response validation should just work.

## Reference files

- `openspec/changes/shipping-courier-integration/proposal.md`
- `openspec/changes/shipping-courier-integration/design.md` — decisions 1–9 in scope, 10–14 belong to `shipping-pricing`
- `openspec/changes/shipping-courier-integration/specs/*/spec.md` — 4 spec files
- `openspec/changes/shipping-courier-integration/tasks.md` — source of truth
- `CLAUDE.md` — project coding standards

## To resume

```bash
cd /Users/i748006/Desktop/Learning/Aleks/AtelierMarie
# Verify boot
make dev-backend
# Then smoke test the delivery endpoints
curl 'http://localhost:8001/v1/delivery/cities?courier=econt&q=Со'
curl 'http://localhost:8001/v1/delivery/offices?courier=econt&city=София&type=apt'
# Fresh Claude session:
/opsx:apply shipping-courier-integration
# Start with 4.6 (grep + cleanup), then 4.1
```
