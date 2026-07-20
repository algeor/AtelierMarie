> **Scope note:** Pricing tasks (weight, calculate endpoint, courier API clients, courier-comparison UI, free-shipping threshold, fallback) have moved to the sibling `shipping-pricing` change. This file covers only the picker.

## 1. Backend — Pydantic Models & Schema Migration

- [x] 1.1 Create `app/models/delivery.py` with `DeliveryOffice`, `DeliveryDoor`, and `DeliveryInfo` Pydantic models (method literal, courier literal, office_type literal, phone validation regex)
- [x] 1.2 Update `app/models/orders.py` — replace `shipping_address: str | None` with `delivery: DeliveryInfo` in `CreateOrderRequest`; add `delivery_method`, `delivery_courier`, `delivery_details` to `OrderResponse`
- [x] 1.3 Add migration columns to `orders` table in `app/database.py`: `delivery_method TEXT`, `delivery_courier TEXT`, `delivery_details TEXT` (JSON)

## 2. Backend — Office Data & Delivery Endpoints

- [x] 2.1 Create `data/speedy_offices.json` and `data/econt_offices.json` with sample office data (10-20 offices each across major Bulgarian cities), including `type: "office" | "apt"` field
- [x] 2.2 Create `scripts/fetch_courier_offices.py` — one-off script that calls Speedy `/location/office` and Econt `Nomenclatures.getOffices`, normalizes to unified schema, writes JSON files
- [x] 2.3 Create `app/services/delivery_service.py` — load JSON at module level, expose `get_offices(courier, city)` and `get_cities(courier, query)` functions
- [x] 2.4 Create `app/routes/delivery.py` — `GET /v1/delivery/offices` and `GET /v1/delivery/cities` endpoints with query parameter validation
- [x] 2.5 Register delivery router in `app/main.py`

## 3. Backend — Order Service Update

- [x] 3.1 Update `app/services/order_service.py` `checkout()` — accept `delivery: DeliveryInfo` parameter, store `delivery_method`, `delivery_courier`, `delivery_details` (JSON-serialized) in INSERT. `shipping_cents` remains 0 in this change (added by `shipping-pricing`)
- [x] 3.2 Update `app/services/order_service.py` query functions — include delivery columns in SELECT, parse `delivery_details` JSON in `OrderData` TypedDict
- [x] 3.3 Update `OrderData` TypedDict — add `delivery_method: str | None`, `delivery_courier: str | None`, `delivery_details: dict | None` fields
- [x] 3.4 Update `app/routes/orders.py` — destructure `delivery` from request and pass to service; map service response to updated `OrderResponse`

## 4. Backend — Tests

- [x] 4.1 Test delivery models: valid office/door payloads, invalid phone, missing required fields, invalid courier/method/office_type literals
- [x] 4.2 Test delivery endpoints: offices by city, cities search, empty results, invalid courier param, office_type filtering
- [x] 4.3 Test checkout with office delivery: successful order, delivery fields persisted correctly
- [x] 4.4 Test checkout with door delivery: successful order, all address fields stored
- [x] 4.5 Test checkout validation: missing delivery object → 422, invalid method → 422, office method without office details → 422
- [x] 4.6 Ripped out `shipping_address` per design Decision 6 (pre-launch clean break): dropped column from `orders` schema, removed docstring references, deleted the length-limit tests, rewrote admin detail test to assert structured `delivery_*` fields, added `delivery` fixture to `test_order_service.py`. `grep -rn shipping_address tests/ app/` → 0 hits. Full suite: 561 passed.

## 5. Frontend — Delivery Components

- [x] 5.1 Create `DeliveryMethodSelector` component — radio group for office/door, labels via `useTranslations("checkout.delivery.method")` (implemented inside `frontend/components/checkout/DeliverySection.tsx`)
- [x] 5.2 Create `CourierPicker` component — radio cards for Speedy/Econt with courier logos (implemented inside `DeliverySection.tsx`)
- [x] 5.3 Create `OfficePicker` component — city search input + office list (calls `/v1/delivery/cities` and `/v1/delivery/offices`), office/автомат filter toggle, selected office confirmation card (implemented inside `DeliverySection.tsx`)
- [x] 5.4 Create `DoorAddressForm` component — structured form fields (city, postal code, street, building, apartment, phone) with inline validation (implemented inside `DeliverySection.tsx`)
- [x] 5.5 Create `DeliverySection` component — orchestrates method/courier/details flow, manages delivery state (`frontend/components/checkout/DeliverySection.tsx`)

## 6. Frontend — Checkout Integration

- [x] 6.1 Update checkout page — replace shipping textarea with `DeliverySection` component (`frontend/app/[locale]/checkout/page.tsx`)
- [x] 6.2 Update `lib/types.ts` — add `DeliveryInfo`, `DeliveryOffice`, `DeliveryDoor` TypeScript interfaces; update `CreateOrderRequest` type
- [x] 6.3 Update `lib/api.ts` — add `getDeliveryOffices(courier, city, type?)` and `getDeliveryCities(courier, query?)` functions (facade delegates to real client or mock)
- [x] 6.4 Update `lib/mock-api.ts` — mock delivery endpoints with sample office data across Sofia, Plovdiv, Varna, Burgas (offices + автомати for each courier)
- [x] 6.5 Update checkout form submission — build `delivery` object from component state, remove `shipping_address` field (delivery is validated via `validateDelivery` and sent as normalized `DeliveryInfo`)
- [x] 6.6 Update order confirmation page — display delivery method, courier, and office/address details via `DeliveryDetails` component

## 7. Frontend — Admin Order View

- [x] 7.1 Update admin order detail view — render structured delivery info (method, courier, office or address). Admin orders table shows a dedicated Delivery column with method · courier and office/address snippet (`frontend/app/[locale]/admin/orders/page.tsx`)
- [x] 7.2 Handle legacy orders per Decision 6 outcome (task 4.6): legacy `shipping_address` was ripped out server-side; frontend renders `tDisplay("none")` fallback when `delivery_method` is null. No legacy string branch remains.

## 8. i18n Keys (per Decision 17)

- [x] 8.1 Added `checkout.delivery.{sectionTitle,method,courier,officeType,office,door,phoneLabel,phonePlaceholder,phoneRequired,phoneInvalid,display}` and all validation-error keys to both `frontend/messages/bg.json` and `frontend/messages/en.json` (Bulgarian primary, English mirror)
- [x] 8.2 `i18n-rendering.test.tsx` completeness test auto-covers new keys via generic iteration over the message tree — no test edits required
