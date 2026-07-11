## 1. Backend — Pydantic Models & Schema Migration

- [ ] 1.1 Create `app/models/delivery.py` with `DeliveryOffice`, `DeliveryDoor`, and `DeliveryInfo` Pydantic models (method literal, courier literal, phone validation regex)
- [ ] 1.2 Update `app/models/orders.py` — replace `shipping_address: str | None` with `delivery: DeliveryInfo` in `CreateOrderRequest`; add `delivery_method`, `delivery_courier`, `delivery_details` to `OrderResponse`
- [ ] 1.3 Add migration columns to `orders` table in `app/database.py`: `delivery_method TEXT`, `delivery_courier TEXT`, `delivery_details TEXT` (JSON)

## 2. Backend — Office Data & Delivery Endpoints

- [ ] 2.1 Create `data/speedy_offices.json` and `data/econt_offices.json` with sample office data (10-20 offices each across major Bulgarian cities)
- [ ] 2.2 Create `app/services/delivery_service.py` — load JSON at module level, expose `get_offices(courier, city)` and `get_cities(courier, query)` functions
- [ ] 2.3 Create `app/routes/delivery.py` — `GET /v1/delivery/offices` and `GET /v1/delivery/cities` endpoints with query parameter validation
- [ ] 2.4 Register delivery router in `app/main.py`

## 3. Backend — Order Service Update

- [ ] 3.1 Update `app/services/order_service.py` `checkout()` — accept `delivery: DeliveryInfo` parameter, store `delivery_method`, `delivery_courier`, `delivery_details` (JSON-serialized) in INSERT
- [ ] 3.2 Update `app/services/order_service.py` query functions — include delivery columns in SELECT, parse `delivery_details` JSON in `OrderData` TypedDict
- [ ] 3.3 Update `OrderData` TypedDict — add `delivery_method: str | None`, `delivery_courier: str | None`, `delivery_details: dict | None` fields
- [ ] 3.4 Update `app/routes/orders.py` — destructure `delivery` from request and pass to service; map service response to updated `OrderResponse`

## 4. Backend — Tests

- [ ] 4.1 Test delivery models: valid office/door payloads, invalid phone, missing required fields, invalid courier/method literals
- [ ] 4.2 Test delivery endpoints: offices by city, cities search, empty results, invalid courier param
- [ ] 4.3 Test checkout with office delivery: successful order, delivery fields persisted correctly
- [ ] 4.4 Test checkout with door delivery: successful order, all address fields stored
- [ ] 4.5 Test checkout validation: missing delivery object → 422, invalid method → 422, office method without office details → 422
- [ ] 4.6 Test legacy order retrieval: orders with shipping_address (no delivery columns) still return correctly

## 5. Frontend — Delivery Components

- [ ] 5.1 Create `DeliveryMethodSelector` component — radio group for office/door with Bulgarian labels
- [ ] 5.2 Create `CourierPicker` component — radio cards for Speedy/Econt with courier logos
- [ ] 5.3 Create `OfficePicker` component — city search input + office list (calls `/v1/delivery/cities` and `/v1/delivery/offices`), selected office confirmation card
- [ ] 5.4 Create `DoorAddressForm` component — structured form fields (city, postal code, street, building, apartment, phone) with inline validation
- [ ] 5.5 Create `DeliverySection` component — orchestrates method/courier/details flow, manages delivery state

## 6. Frontend — Checkout Integration

- [ ] 6.1 Update checkout page — replace shipping textarea with `DeliverySection` component
- [ ] 6.2 Update `lib/types.ts` — add `DeliveryInfo`, `DeliveryOffice`, `DeliveryDoor` TypeScript interfaces; update `CreateOrderRequest` type
- [ ] 6.3 Update `lib/api-client.ts` — add `getDeliveryOffices(courier, city)` and `getDeliveryCities(courier, query)` functions
- [ ] 6.4 Update `lib/mock-api.ts` — mock delivery endpoints with sample office data
- [ ] 6.5 Update checkout form submission — build `delivery` object from component state, remove `shipping_address` field
- [ ] 6.6 Update order confirmation page — display delivery method, courier, and office/address details

## 7. Frontend — Admin Order View

- [ ] 7.1 Update admin order detail view — render structured delivery info (method, courier, office or address) instead of plain text shipping_address
- [ ] 7.2 Handle legacy orders — display `shipping_address` string for orders without delivery columns
