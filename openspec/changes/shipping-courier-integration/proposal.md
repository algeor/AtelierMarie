## Why

The current checkout shipping address is a single optional textarea — too minimalist for Bulgaria where most deliveries go through Speedy or Econt courier services. Customers expect to choose between office pickup and door-to-door delivery, select their courier, and pick from a list of offices. Without this, customers must manually look up and type office addresses, leading to errors, failed deliveries, and support overhead.

Additionally, customers expect to see shipping cost before placing an order. The current system has no shipping price — it's either flat-rate or free with no visibility. Integrating with courier APIs enables real-time price calculation and a free-shipping incentive above €50.

## What Changes

- Replace the single `shipping_address` textarea with a structured delivery method selector
- Add a delivery method choice: **office pickup** (Speedy/Econt office or locker/автомат) or **to-door delivery** (courier brings it to an address)
- Add courier selection (Speedy or Econt) — both supported for office and to-door, shown with price comparison
- Add office picker: searchable dropdown of courier offices and lockers (filtered by city, distinguishes offices from автомати)
- For to-door: structured address form (city, postal code, street, building/apartment, phone)
- **Real-time shipping price calculation** via courier APIs (Speedy `/calculate`, Econt Shipments service)
- **Two-phase pricing**: approximate prices for both couriers shown after city selection, exact price after specific office/address selection
- **Free shipping** for orders ≥ €50
- **Fallback flat rate** (€5) when courier API is unavailable
- Store delivery details + shipping cost as structured data in the order
- Backend accepts the structured delivery payload in `POST /v1/orders` instead of a plain string
- Products gain a `weight_grams` field for accurate shipping calculation
- Admin order view displays delivery details and shipping breakdown clearly
- **BREAKING**: `shipping_address` field in `CreateOrderRequest` changes from `string | null` to a structured `delivery` object

## Capabilities

### New Capabilities
- `courier-delivery`: Delivery method selection (office pickup vs door-to-door), courier provider choice (Speedy/Econt), office search/picker (offices + lockers), structured address form, and order delivery details storage
- `courier-offices-data`: Static/cached office list for Speedy and Econt (city-filtered searchable data source for the office picker), sourced via official courier APIs
- `shipping-pricing`: Real-time shipping cost calculation via courier APIs, free shipping threshold, fallback pricing, product weight management

### Modified Capabilities
- `checkout-ui`: Shipping section replaced with multi-step delivery flow — method → city → courier comparison with prices → specifics → final price
- `checkout-flow`: `POST /v1/orders` accepts structured delivery object and shipping_cents; order total includes shipping cost

## Impact

- **Backend**: `CreateOrderRequest` schema changes (breaking), `orders` table schema adds delivery + shipping columns, products table adds `weight_grams`, new delivery service with courier API integration, new pricing calculation endpoint
- **Frontend**: Checkout page shipping section rewritten — new components (DeliveryMethodSelector, CourierComparison, OfficePicker, AddressForm, ShippingPriceSummary)
- **Database**: Schema migration for orders table (delivery + shipping_cents), products table (weight_grams)
- **External dependencies**: Speedy API account + credentials, Econt API account + credentials (for price calculation and office data fetch)
- **API contract**: Breaking change to `POST /v1/orders` request body — frontend and backend must deploy together
- **Admin UI**: Order detail view updated to render structured delivery info + shipping cost breakdown
- **Config**: New env vars for courier API credentials, sender office IDs, shipping constants
