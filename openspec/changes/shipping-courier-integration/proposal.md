## Why

The current checkout shipping address is a single optional textarea — too minimalist for Bulgaria where most deliveries go through Speedy or Econt courier services. Customers expect to choose between office pickup and door-to-door delivery, select their courier, and pick from a list of offices. Without this, customers must manually look up and type office addresses, leading to errors, failed deliveries, and support overhead.

## What Changes

- Replace the single `shipping_address` textarea with a structured delivery method selector
- Add a delivery method choice: **office pickup** (Speedy/Econt office) or **to-door delivery** (courier brings it to an address)
- Add courier selection (Speedy or Econt) — both supported for office and to-door
- Add office picker: searchable dropdown of courier offices (filtered by city)
- For to-door: structured address form (city, postal code, street, building/apartment, phone)
- Store delivery details as structured JSON in the order (courier, method, office/address details)
- Backend accepts the structured delivery payload in `POST /v1/orders` instead of a plain string
- Admin order view displays delivery details clearly (courier, method, full address or office name)
- **BREAKING**: `shipping_address` field in `CreateOrderRequest` changes from `string | null` to a structured `delivery` object

## Capabilities

### New Capabilities
- `courier-delivery`: Delivery method selection (office pickup vs door-to-door), courier provider choice (Speedy/Econt), office search/picker, structured address form, and order delivery details storage
- `courier-offices-data`: Static/cached office list for Speedy and Econt (city-filtered searchable data source for the office picker)

### Modified Capabilities
- `checkout-ui`: Shipping section replaced with courier delivery method selector, office picker, and structured address form
- `checkout-flow`: `POST /v1/orders` accepts structured delivery object instead of plain `shipping_address` string

## Impact

- **Backend**: `CreateOrderRequest` schema changes (breaking), `orders` table schema adds `delivery_method`, `courier`, `delivery_details_json` columns (migration), order service checkout logic updated
- **Frontend**: Checkout page shipping section rewritten — new components (DeliveryMethodSelector, CourierPicker, OfficePicker, AddressForm)
- **Database**: Schema migration for orders table, new `courier_offices` table or JSON data file
- **API contract**: Breaking change to `POST /v1/orders` request body — frontend and backend must deploy together
- **Admin UI**: Order detail view updated to render structured delivery info
