## Why

The current checkout shipping address is a single optional textarea — too minimalist for Bulgaria where most deliveries go through Speedy or Econt courier services. Customers expect to choose between office pickup and door-to-door delivery, select their courier, and pick from a list of offices. Without this, customers must manually look up and type office addresses, leading to errors, failed deliveries, and support overhead.

This change delivers the structured delivery **picker** — method, courier, office/door specifics, phone. Real-time shipping **price calculation** (courier APIs, per-product weight, free-shipping threshold, two-phase pricing UX) is intentionally scoped to a follow-on change: `shipping-pricing`. That split lets the picker ship independently, without waiting on live Speedy/Econt API accounts.

## What Changes

- Replace the single `shipping_address` textarea with a structured delivery method selector
- Add a delivery method choice: **office pickup** (Speedy/Econt office or locker/автомат) or **to-door delivery** (courier brings it to an address)
- Add courier selection (Speedy or Econt) — both supported for office and to-door
- Add office picker: searchable dropdown of courier offices and lockers (filtered by city, distinguishes offices from автомати)
- For to-door: structured address form (city, postal code, street, building/apartment, phone)
- Store delivery details as structured data in the order
- Backend accepts the structured delivery payload in `POST /v1/orders` instead of a plain string
- Admin order view displays delivery details clearly
- **Shipping cost is a placeholder** in this change — `shipping_cents = 0` is stored and returned. The `shipping-pricing` follow-on adds the calculation, free-shipping threshold, and fallback.
- **BREAKING**: `shipping_address` field in `CreateOrderRequest` changes from `string | null` to a structured `delivery` object

## Capabilities

### New Capabilities
- `courier-delivery`: Delivery method selection (office pickup vs door-to-door), courier provider choice (Speedy/Econt), office search/picker (offices + lockers), structured address form, and order delivery details storage
- `courier-offices-data`: Static/cached office list for Speedy and Econt (city-filtered searchable data source for the office picker), sourced via official courier APIs

### Modified Capabilities
- `checkout-ui`: Shipping section replaced with multi-step delivery flow — method → courier → specifics (office picker or address form)
- `checkout-flow`: `POST /v1/orders` accepts structured delivery object

## Impact

- **Backend**: `CreateOrderRequest` schema changes (breaking), `orders` table schema adds delivery columns (`delivery_method`, `delivery_courier`, `delivery_details`), new delivery service (offices/cities from JSON), new delivery endpoints
- **Frontend**: Checkout page shipping section rewritten — new components (DeliveryMethodSelector, CourierPicker, OfficePicker, AddressForm, DeliverySection). All customer-facing strings plumbed through `useTranslations` (see design Decision 17)
- **Database**: Schema migration for orders table (delivery columns)
- **External dependencies**: Speedy and Econt accounts required only to run the office-fetch script — not needed at runtime
- **API contract**: Breaking change to `POST /v1/orders` request body — frontend and backend must deploy together
- **Admin UI**: Order detail view updated to render structured delivery info
- **Follow-on**: `shipping-pricing` change adds real-time cost calculation, per-product weight, free-shipping threshold, fallback, and courier-comparison UI on top of this picker
