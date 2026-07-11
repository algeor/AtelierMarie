## ADDED Requirements

### Requirement: FTS5 search input is sanitized against operator injection
The system SHALL sanitize user search input before passing it to FTS5 queries. Each whitespace-separated token SHALL be wrapped in double quotes to prevent interpretation as FTS5 operators (AND, OR, NOT, NEAR, *, ^, column filters). Empty queries and whitespace-only queries SHALL return an empty result without executing FTS5.

#### Scenario: Search with FTS5 operators treated as literal text
- **WHEN** a user searches for `lavender OR poison`
- **THEN** the FTS5 query searches for the literal words "lavender", "OR", and "poison" — not using OR as a boolean operator

#### Scenario: Search with wildcard operator treated as literal
- **WHEN** a user searches for `*` or `lav*`
- **THEN** the system treats the asterisk as a literal character (quoted), not as a prefix wildcard

#### Scenario: Search with parentheses does not group
- **WHEN** a user searches for `(rose OR lavender) NOT vanilla`
- **THEN** each token including parentheses is quoted — no grouping or negation occurs

#### Scenario: Empty or whitespace-only search returns empty
- **WHEN** a user searches for `""` or `"   "`
- **THEN** the system returns an empty result list without executing an FTS5 query

### Requirement: Pagination has upper bounds
The system SHALL enforce a maximum page number and maximum limit (page size) on all paginated endpoints. The maximum page SHALL be 10,000 and the maximum limit SHALL be 100. Requests exceeding these bounds SHALL be clamped to the maximum (not rejected) to maintain backward compatibility.

#### Scenario: Excessive page number is clamped
- **WHEN** a request specifies `?page=9999999&limit=20`
- **THEN** the system uses `page=10000` (the maximum), which produces `OFFSET=199,980` — not `OFFSET=199,999,980`

#### Scenario: Excessive limit is clamped
- **WHEN** a request specifies `?limit=5000`
- **THEN** the system uses `limit=100` (the maximum)

#### Scenario: Normal pagination is unaffected
- **WHEN** a request specifies `?page=3&limit=20`
- **THEN** the system uses the provided values unchanged

### Requirement: CSV import validates value bounds
The system SHALL validate that numeric values in CSV import rows fall within acceptable ranges. `price_cents` SHALL be between 1 and 9,999,999 (€0.01 to €99,999.99). `stock` SHALL be between 0 and 999,999. Values outside these ranges SHALL be rejected as row-level errors (not swallowed silently).

#### Scenario: Extreme price value rejected
- **WHEN** a CSV row contains `price_cents=99999999999999`
- **THEN** the row is rejected with error "price_cents must be between 1 and 9999999" and the row is not imported

#### Scenario: Negative stock rejected
- **WHEN** a CSV row contains `stock=-5`
- **THEN** the row is rejected with error "stock must be between 0 and 999999"

#### Scenario: Valid boundary values accepted
- **WHEN** a CSV row contains `price_cents=1` or `price_cents=9999999`
- **THEN** the row is accepted (boundary values are inclusive)

### Requirement: Row data access is defensive with context
The system SHALL access database row fields using a helper function that provides meaningful error context on failure. When a field is missing from a row (due to schema mismatch or query error), the error SHALL include the expected field name, the available fields, and the operation being performed.

#### Scenario: Missing column produces diagnostic error
- **WHEN** service code attempts to read `row["nonexistent_field"]` via the defensive accessor
- **THEN** a `DataAccessError` is raised with message containing the field name, available columns, and operation context — not a bare `KeyError`

#### Scenario: Valid row access works without overhead
- **WHEN** service code reads `row["name"]` and the field exists
- **THEN** the value is returned with no additional overhead (fast path)
