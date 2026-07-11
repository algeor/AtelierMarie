# Schema Contracts — Design

## Context

AtelierMarie has three communication boundaries where data shapes are implicit: events (SDK → DuckDB → analytics SQL → Python readers), analytics tables (SQL output → ML/admin consumers), and API responses (route handlers → frontend). All rely on human memory to stay in sync. This change introduces a formal contract layer using Pydantic models as the single source of truth, validated both at runtime and at test time.

**Current state:**
- Event ingestion accepts a flat `EventIn` Pydantic model with `metadata: dict` (untyped blob)
- Analytics SQL files assume specific JSON field names inside `metadata`
- ML recommender reads analytics table rows as raw dicts from DuckDB
- API responses are Pydantic models defined per-route (no shared vocabulary)
- No test asserts that SQL output matches Python expectations

**Constraints:**
- Zero new dependencies (Pydantic + pytest already in stack)
- Zero additional latency on event ingestion (validation already happens)
- Must remain approachable for a solo developer (no codegen, no magic)
- Must fail loudly at test time when contracts drift, not silently at runtime

## Goals / Non-Goals

**Goals:**
- Define every event payload shape as a typed Pydantic model
- Define every analytics table's output schema as a Pydantic model
- Define API response shapes as shared models (route + test + OpenAPI)
- Test suite catches: missing payload models, SQL↔model drift, incomplete event_type coverage
- Make "add new event type" a mechanical checklist (enum + model + done)
- API versioning policy: additive-only in v1, breaking changes require v2

**Non-Goals:**
- Runtime schema negotiation or content-type versioning
- Cross-language schema (protobuf, Avro, JSON Schema registry)
- Event schema migration/evolution tooling
- Auto-generated TypeScript types (can layer on later)
- Backward-compatible payload decoding (v1 is the only version)

## Decisions

### 1. Discriminated union for event payloads

**Decision:** Each `event_type` maps to exactly one Pydantic payload model. The event ingestion endpoint validates `metadata` against the correct model based on `event_type`. A `Literal` type discriminator drives the union.

```python
class EventType(str, Enum):
    page_view = "page_view"
    product_view = "product_view"
    search = "search"
    click = "click"
    add_to_cart = "add_to_cart"
    remove_from_cart = "remove_from_cart"
    purchase = "purchase"
    impression = "impression"
    session_start = "session_start"
    session_end = "session_end"

class ProductViewPayload(BaseModel):
    product_id: str
    category: str | None = None

class SearchPayload(BaseModel):
    query: str
    result_count: int

class AddToCartPayload(BaseModel):
    product_id: str
    quantity: int = 1

class PurchasePayload(BaseModel):
    product_id: str
    price: Decimal
    quantity: int
    order_id: int | None = None

class ImpressionPayload(BaseModel):
    product_id: str
    position: int | None = None
    source: str | None = None  # "recommendation", "search", "listing"

class ClickPayload(BaseModel):
    product_id: str
    source: str | None = None

class EmptyPayload(BaseModel):
    """For events with no required payload (page_view, session_start, session_end)"""
    pass
```

**Alternatives considered:**
- *Single `metadata: dict` (current)*: No validation, no IDE support, silent failures when analytics SQL assumes a key. Rejected.
- *JSON Schema files + validation library*: Adds a schema registry, a validation step, and a separate language. Pydantic already IS the validator. Rejected.
- *Optional validation (warn, don't reject)*: Defeats the purpose. If you accept garbage now, you'll query garbage later. Rejected.

**Rationale:** Pydantic discriminated unions are natively supported, have zero performance penalty beyond field validation (which we already pay), and give IDE autocomplete + type checking for free. Adding a new event type forces you to define its shape — you physically cannot forget.

### 2. Event type → Payload mapping as a registry dict

**Decision:** A single `EVENT_PAYLOAD_MAP` dict maps each `EventType` to its payload model class. This is the canonical "what fields does this event carry?" answer.

```python
EVENT_PAYLOAD_MAP: dict[EventType, type[BaseModel]] = {
    EventType.page_view: EmptyPayload,
    EventType.product_view: ProductViewPayload,
    EventType.search: SearchPayload,
    EventType.click: ClickPayload,
    EventType.add_to_cart: AddToCartPayload,
    EventType.remove_from_cart: AddToCartPayload,  # same shape
    EventType.purchase: PurchasePayload,
    EventType.impression: ImpressionPayload,
    EventType.session_start: EmptyPayload,
    EventType.session_end: EmptyPayload,
}
```

**Rationale:** A dict is inspectable, iterable, and testable. The coverage test simply asserts `set(EventType) == set(EVENT_PAYLOAD_MAP.keys())`. If someone adds an enum value without a payload mapping, the test fails immediately.

### 3. Analytics row models mirror SQL output exactly

**Decision:** Each `analytics_*` table has a corresponding Pydantic model in `app/contracts/analytics.py`. Field names match SQL column names exactly. Types match DuckDB output types (after Python coercion).

```python
class ProductMetricsRow(BaseModel):
    product_id: str
    view_count: int
    cart_count: int
    purchase_count: int
    unique_sessions: int
    revenue: Decimal

class SessionMetricsRow(BaseModel):
    total_sessions: int
    anonymous_sessions: int
    authenticated_sessions: int
    converted_sessions: int
    avg_events_per_session: Decimal

class FunnelRow(BaseModel):
    total_views: int
    total_carts: int
    total_checkouts: int
    total_purchases: int
    unique_sessions: int
    conversion_rate: Decimal
    cart_rate: Decimal
    total_revenue: Decimal

class SearchTermRow(BaseModel):
    query: str
    search_count: int
    avg_result_count: Decimal

class PopularityRow(BaseModel):
    product_id: str
    popularity_score: Decimal
    view_count: int
    cart_count: int
    purchase_count: int
    unique_sessions: int
    recency_boost: Decimal

class CooccurrenceRow(BaseModel):
    product_a: str
    product_b: str
    co_count: int

class SessionSequenceRow(BaseModel):
    session_id: str
    product_sequence: list[str]
    event_sequence: list[str]

class CtrRow(BaseModel):
    product_id: str
    impressions: int
    clicks: int
    purchases: int
    ctr: Decimal
    conversion_rate: Decimal
```

**Alternatives considered:**
- *DuckDB → Python dataclass via reflection*: Requires running DuckDB to discover schema. Can't validate at import time. Rejected.
- *SQLAlchemy models*: Heavy ORM dependency for what's fundamentally a read schema. DuckDB isn't using SQLAlchemy. Rejected.
- *TypedDict instead of Pydantic*: No runtime validation, no serialization. We want both. Rejected.

**Rationale:** The model IS documentation. Any consumer that does `row = ProductMetricsRow(**raw_dict)` gets type-safe access AND immediate validation that the SQL output hasn't drifted. The analytics reader wraps DuckDB results in these models — if a column is missing or mistyped, it explodes at the point of use, not downstream in some ML calculation.

### 4. Analytics table contract registry

**Decision:** A `ANALYTICS_TABLE_MAP` connects table names to their row models, enabling programmatic testing.

```python
ANALYTICS_TABLE_MAP: dict[str, type[BaseModel]] = {
    "analytics_product_metrics": ProductMetricsRow,
    "analytics_session_metrics": SessionMetricsRow,
    "analytics_funnel": FunnelRow,
    "analytics_search_terms": SearchTermRow,
    "analytics_popularity": PopularityRow,
    "analytics_cooccurrence": CooccurrenceRow,
    "analytics_session_sequences": SessionSequenceRow,
    "analytics_ctr": CtrRow,
}
```

**Rationale:** The contract test iterates this dict, runs `SELECT * FROM {table} LIMIT 0` (or `DESCRIBE {table}`), and asserts the columns match the model fields. If someone adds a new analytics table without a contract, the test for "all `analytics_*` tables have contracts" fails.

### 5. API response contracts as shared models

**Decision:** Response models live in `app/contracts/api.py` and are imported by both route handlers (as the `response_model=`) and integration tests. FastAPI generates OpenAPI from these automatically.

```python
# Product responses
class ProductListItem(BaseModel):
    id: str
    name: str
    price: Decimal
    category: str | None
    image_url: str | None
    stock_quantity: int
    in_stock: bool
    is_featured: bool

class ProductDetail(ProductListItem):
    description: str | None
    created_at: datetime

class PaginatedProducts(BaseModel):
    items: list[ProductListItem]
    total: int
    page: int
    per_page: int

# Admin product response (extends with metrics)
class AdminProductItem(ProductListItem):
    is_active: bool
    total_views: int
    total_cart_adds: int
    total_orders: int

# Dashboard response
class DashboardMetrics(BaseModel):
    total_views: int
    unique_sessions: int
    total_orders: int
    conversion_rate: Decimal
    add_to_cart_rate: Decimal
    total_revenue: Decimal
    analytics_computed_at: datetime | None
    analytics_age_seconds: int | None
    source: str  # "analytics_layer" | "direct_query"
    # ... top products, search terms, etc.
```

**Alternatives considered:**
- *Inline models per route (current)*: Works but creates no shared vocabulary. If two routes return "a product", they might have slightly different shapes. Rejected.
- *Separate schema files (YAML/JSON Schema)*: Extra language, extra tooling, extra sync burden. FastAPI already uses Pydantic for this. Rejected.

**Rationale:** When the route handler declares `response_model=ProductDetail`, FastAPI validates the response matches that shape before sending it. The OpenAPI spec is auto-generated. If someone adds a field to the DB query but not the model, the field is stripped (explicit) or the model is updated (intentional). Either way, no silent drift.

### 6. API versioning policy (additive-only in v1)

**Decision:** Within `/v1/`, changes are additive only:
- ✅ Add a new field to a response (old clients ignore it)
- ✅ Add a new optional query parameter
- ✅ Add a new endpoint
- ❌ Remove a field from a response → requires `/v2/`
- ❌ Rename a field → requires `/v2/`
- ❌ Change a field's type → requires `/v2/`
- ❌ Make an optional request field required → requires `/v2/`

**Implementation:** Response models use `model_config = ConfigDict(extra="forbid")` to prevent accidental extra fields. A test asserts that the set of fields in the response model matches the set of fields actually returned (no phantom fields leaking from the DB layer).

**Rationale:** For a single-frontend system, this is lightweight but sufficient. The rule is simple: if a frontend would break, it's a breaking change. The contract models make this visible — you physically see the field list and can reason about what removing one does.

### 7. Contract tests as the enforcement mechanism

**Decision:** A dedicated test module (`tests/test_contracts.py`) contains structural assertions:

```python
def test_every_event_type_has_payload_model():
    """No event_type can be added without defining its shape."""
    assert set(EventType) == set(EVENT_PAYLOAD_MAP.keys())

def test_analytics_tables_match_row_models(duckdb_conn):
    """SQL output schema matches Python model fields."""
    for table_name, model_cls in ANALYTICS_TABLE_MAP.items():
        columns = duckdb_conn.execute(f"DESCRIBE {table_name}").fetchall()
        db_fields = {col[0] for col in columns}
        model_fields = set(model_cls.model_fields.keys())
        assert db_fields == model_fields, f"{table_name}: {db_fields ^ model_fields}"

def test_event_payloads_cover_analytics_assumptions():
    """Every field that analytics SQL extracts from metadata
    is present in the corresponding payload model."""
    # Parses SQL files for metadata->>'{field}' patterns
    # Asserts each extracted field exists in the payload model
    # for the event_types that SQL filters on
    ...

def test_api_responses_are_strict():
    """No response model allows extra fields."""
    for model in ALL_RESPONSE_MODELS:
        assert model.model_config.get("extra") == "forbid"
```

**Rationale:** These tests are the trip wires. They don't test business logic — they test structural consistency across system boundaries. They're cheap to run (no I/O beyond a test DuckDB), fast to write, and catch the exact class of bugs that silently corrupt data.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           app/contracts/                                          │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  events.py                                                               │    │
│  │                                                                         │    │
│  │  EventType (enum)  ─────────────┐                                       │    │
│  │  ProductViewPayload             │                                       │    │
│  │  SearchPayload                  ├── EVENT_PAYLOAD_MAP                   │    │
│  │  PurchasePayload                │   {EventType → PayloadModel}          │    │
│  │  AddToCartPayload               │                                       │    │
│  │  ImpressionPayload              │                                       │    │
│  │  ClickPayload                   │                                       │    │
│  │  EmptyPayload                  ─┘                                       │    │
│  └──────────┬──────────────────────────────────────────────────────────────┘    │
│             │                                                                    │
│             │ imported by                                                        │
│             ▼                                                                    │
│  ┌──────────────────────┐                                                       │
│  │  POST /v1/events     │  validates metadata against correct PayloadModel       │
│  │  (event ingestion)   │  based on event_type discriminator                     │
│  └──────────────────────┘                                                       │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  analytics.py                                                            │    │
│  │                                                                         │    │
│  │  ProductMetricsRow  ────────────┐                                       │    │
│  │  SessionMetricsRow              │                                       │    │
│  │  FunnelRow                      ├── ANALYTICS_TABLE_MAP                 │    │
│  │  SearchTermRow                  │   {"analytics_*" → RowModel}          │    │
│  │  PopularityRow                  │                                       │    │
│  │  CooccurrenceRow                │                                       │    │
│  │  SessionSequenceRow             │                                       │    │
│  │  CtrRow                        ─┘                                       │    │
│  └──────────┬──────────────────────────────────────────────────────────────┘    │
│             │                                                                    │
│             │ imported by                                                        │
│             ▼                                                                    │
│  ┌─────────────────────────┐    ┌──────────────────────────────┐                │
│  │  ML Recommender         │    │  Admin Dashboard routes       │                │
│  │                         │    │                              │                │
│  │  row = PopularityRow(   │    │  metrics = FunnelRow(        │                │
│  │    **raw_dict           │    │    **query_result            │                │
│  │  )                      │    │  )                           │                │
│  │  # type-safe access     │    │  # type-safe access          │                │
│  └─────────────────────────┘    └──────────────────────────────┘                │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  api.py                                                                  │    │
│  │                                                                         │    │
│  │  ProductListItem        ─── used as response_model in routes             │    │
│  │  ProductDetail          ─── FastAPI auto-generates OpenAPI from these    │    │
│  │  PaginatedProducts      ─── Frontend can codegen TypeScript types        │    │
│  │  AdminProductItem                                                        │    │
│  │  DashboardMetrics                                                        │    │
│  │  OrderResponse                                                           │    │
│  │  CartResponse                                                            │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                        tests/test_contracts.py                                    │
│                                                                                 │
│  ┌─────────────────────────────────────────────┐                                │
│  │  STRUCTURAL ASSERTIONS (trip wires)          │                                │
│  │                                             │                                │
│  │  • Every EventType has a payload model      │◄── catches: "added event type  │
│  │  • Every analytics_* table has a row model  │    but forgot payload"          │
│  │  • SQL column names match model fields      │◄── catches: "renamed column    │
│  │  • SQL metadata access matches payload      │    in SQL, forgot Python"       │
│  │    fields for that event_type               │◄── catches: "SDK sends price,  │
│  │  • All response models forbid extra fields  │    SQL expects unit_price"      │
│  │  • API endpoints validate against contracts │◄── catches: "response shape    │
│  │                                             │    drifted from contract"       │
│  └─────────────────────────────────────────────┘                                │
│                                                                                 │
│  Run: pytest tests/test_contracts.py (fast — no I/O beyond test DuckDB)          │
│  CI: Runs on every push, blocks merge if contracts drift                         │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow With Contracts

```
  BEFORE (implicit):
  ══════════════════

  SDK track("purchase", {price: 29.99})
       │
       ▼
  POST /v1/events ──── validates: "is it JSON?" ✓
       │
       ▼
  JSONL: {"event_type":"purchase","metadata":{"price":29.99}}
       │
       ▼
  DuckDB events table ──── stores blob
       │
       ▼
  analytics SQL: SUM(metadata->>'price')  ◄── BREAKS SILENTLY if SDK
                                               sends "unit_price" instead


  AFTER (contracted):
  ══════════════════

  SDK track("purchase", {price: 29.99})
       │
       ▼
  POST /v1/events ──── validates against PurchasePayload ✓
       │                (price: Decimal, product_id: str, quantity: int)
       │                REJECTS if shape doesn't match
       ▼
  JSONL: {"event_type":"purchase","metadata":{"price":"29.99","product_id":"X","quantity":1}}
       │
       ▼
  DuckDB events table ──── stores validated payload
       │
       ▼
  analytics SQL: SUM(CAST(metadata->>'price' AS DECIMAL))
       │
       │   TEST ASSERTS: "price" ∈ PurchasePayload.model_fields
       │   TEST ASSERTS: SQL output columns == ProductMetricsRow.model_fields
       ▼
  ML Recommender: row = PopularityRow(**result) ◄── EXPLODES IMMEDIATELY
                                                    if columns don't match
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| **Validation overhead on event ingestion** | Pydantic V2 is compiled (Rust-based). Field validation adds <0.1ms per event. Already paying this cost for the flat model — discriminated union adds negligible overhead. |
| **Rigid event payloads block SDK experimentation** | `EmptyPayload` allows `model_config = ConfigDict(extra="allow")` for specific event types during experimentation. Graduate fields to typed when stable. |
| **Analytics SQL test requires DuckDB fixture** | Test creates an in-memory DuckDB, runs CREATE TABLE + SQL file, validates output. Fast (~100ms per table). No external deps. |
| **Overhead of maintaining contracts alongside code** | The contract IS the code. Route handlers import the model. Analytics readers wrap results in the model. There's no separate file to "keep in sync" — the model is used directly. |
| **Breaking change detection is test-only** | Acceptable for a single-developer, single-repo system. In a multi-team setting you'd want CI to diff schemas. Here, `pytest` is sufficient. |
| **Extra payload validation rejects SDK bugs at ingestion** | This is a FEATURE, not a bug. Better to get a 422 now than silently corrupt analytics for 30 days. SDK can be fixed and events replayed. |

## Open Questions

None — the design is self-contained and uses only existing tooling (Pydantic + pytest + FastAPI response_model).
