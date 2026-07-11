## ADDED Requirements

### Requirement: Event type enumeration as single source of truth
The system SHALL define all valid event types in a single `EventType` string enum in `app/contracts/events.py`. All code that references event types (ingestion endpoint, analytics SQL, tests) SHALL import from this enum — no string literals.

#### Scenario: Enum contains all accepted event types
- **WHEN** the contracts module is imported
- **THEN** `EventType` contains exactly: page_view, product_view, search, click, add_to_cart, remove_from_cart, purchase, impression, session_start, session_end

#### Scenario: Adding a new event type requires enum update
- **WHEN** a developer adds a new event type to the system
- **THEN** they MUST add it to the `EventType` enum
- **AND** the coverage test fails until a corresponding payload model is mapped

#### Scenario: Invalid event type rejected at ingestion
- **WHEN** a client sends POST /v1/events with `event_type: "unknown_thing"`
- **THEN** the system returns HTTP 422 indicating invalid event type
- **AND** the error message lists valid values from the enum

---

### Requirement: Typed payload model per event type
The system SHALL define a Pydantic model for each event type's payload (the `metadata` field). Each model specifies the required and optional fields that event type carries.

#### Scenario: ProductViewPayload validates product_id
- **WHEN** a client sends a product_view event with metadata `{"product_id": "SKU-1"}`
- **THEN** the payload is validated against `ProductViewPayload` and accepted

#### Scenario: ProductViewPayload rejects missing product_id
- **WHEN** a client sends a product_view event with metadata `{}`
- **THEN** the system returns HTTP 422 indicating product_id is required for product_view events

#### Scenario: SearchPayload validates query and result_count
- **WHEN** a client sends a search event with metadata `{"query": "vanilla", "result_count": 5}`
- **THEN** the payload is validated against `SearchPayload` and accepted

#### Scenario: SearchPayload rejects missing query
- **WHEN** a client sends a search event with metadata `{"result_count": 5}` (no query)
- **THEN** the system returns HTTP 422 indicating query is required for search events

#### Scenario: PurchasePayload validates price and product_id
- **WHEN** a client sends a purchase event with metadata `{"product_id": "SKU-1", "price": 29.99, "quantity": 2}`
- **THEN** the payload is validated against `PurchasePayload` and accepted

#### Scenario: PurchasePayload rejects non-numeric price
- **WHEN** a client sends a purchase event with metadata `{"product_id": "SKU-1", "price": "free", "quantity": 1}`
- **THEN** the system returns HTTP 422 indicating price must be a number

#### Scenario: EmptyPayload accepts events with no required fields
- **WHEN** a client sends a page_view event with metadata `{}` or no metadata
- **THEN** the payload is validated against `EmptyPayload` and accepted

#### Scenario: ImpressionPayload validates product_id with optional position
- **WHEN** a client sends an impression event with metadata `{"product_id": "SKU-1", "position": 3, "source": "recommendation"}`
- **THEN** the payload is validated against `ImpressionPayload` and accepted

#### Scenario: ImpressionPayload accepts minimal fields
- **WHEN** a client sends an impression event with metadata `{"product_id": "SKU-1"}`
- **THEN** the payload is accepted (position and source are optional)

---

### Requirement: Event payload registry maps every type to a model
The system SHALL maintain an `EVENT_PAYLOAD_MAP` dictionary that maps every `EventType` value to its corresponding Pydantic payload model class. This registry is the canonical answer to "what fields does this event carry?"

#### Scenario: Every enum value has a mapping
- **WHEN** a test checks `set(EventType) == set(EVENT_PAYLOAD_MAP.keys())`
- **THEN** the assertion passes (no unmapped event types)

#### Scenario: Registry used for validation dispatch
- **WHEN** the ingestion endpoint receives an event with `event_type: "search"`
- **THEN** it looks up `EVENT_PAYLOAD_MAP[EventType.search]` to get `SearchPayload`
- **AND** validates the event's metadata against `SearchPayload`

#### Scenario: Adding event type without payload mapping fails tests
- **WHEN** a developer adds `EventType.wishlist_add` to the enum
- **AND** does NOT add a corresponding entry in `EVENT_PAYLOAD_MAP`
- **THEN** `test_every_event_type_has_payload_model` fails

---

### Requirement: Validated metadata stored in JSONL
The system SHALL write the validated (and potentially coerced) payload to JSONL, not the raw client input. This ensures that downstream consumers (analytics SQL) receive data that matches the contract.

#### Scenario: Decimal coercion preserved in storage
- **WHEN** a client sends a purchase event with `price: 29.9`
- **THEN** the JSONL stores `"price": "29.90"` (Decimal-serialized)
- **AND** analytics SQL can reliably CAST to DECIMAL

#### Scenario: Extra fields stripped before storage
- **WHEN** a client sends a product_view event with metadata `{"product_id": "SKU-1", "random_junk": true}`
- **THEN** only `{"product_id": "SKU-1"}` is written to JSONL (extra fields forbidden by model)

#### Scenario: Optional fields stored as null when absent
- **WHEN** a client sends a product_view event with metadata `{"product_id": "SKU-1"}` (no category)
- **THEN** the JSONL stores `{"product_id": "SKU-1", "category": null}`

---

### Requirement: Backward-compatible payload evolution
The system SHALL support adding new optional fields to payload models without breaking existing events in storage. New required fields constitute a breaking change that requires a migration strategy.

#### Scenario: New optional field added to existing payload
- **WHEN** `ProductViewPayload` gains a new field `referrer: str | None = None`
- **THEN** existing JSONL events without `referrer` remain valid (field defaults to None)
- **AND** new events can include `referrer` and it is validated and stored

#### Scenario: New required field requires migration plan
- **WHEN** a developer attempts to add a required field to an existing payload model
- **THEN** the contract test warns that existing stored events will not validate
- **AND** the field should be optional with a default, or the event type should fork (e.g., purchase_v2)
