## ADDED Requirements

### Requirement: Econt office data preserves office code
The normalized Econt office catalog SHALL preserve the courier-native `code` field from Econt nomenclature data. Public office responses SHALL include `code` for Econt offices so checkout can store the value needed by later Econt label creation.

#### Scenario: Normalize Econt office code
- **WHEN** raw Econt office data contains `{id: 1029, code: "1127"}`
- **THEN** the normalized office record includes `id: "econt-1029"` and `code: "1127"`

#### Scenario: Office response includes Econt code
- **WHEN** `GET /v1/delivery/offices?courier=econt&city=София` returns offices
- **THEN** each Econt office response includes its `code` value when known

#### Scenario: Legacy office records without code remain readable
- **WHEN** an old normalized office JSON record has no `code`
- **THEN** office list endpoints still return the office with `code: null` or omitted according to the response model compatibility decision

### Requirement: Office locator selections normalize to the office schema
The system SHALL normalize Econt Office Locator message payloads into the same office-selection shape used by the static office picker, including `office_id`, `office_code`, name, type, city, address, and working-hour fallback.

#### Scenario: Locator office selected
- **WHEN** the Econt Office Locator posts an office object with `id`, `code`, `name`, and address data
- **THEN** checkout stores an Econt office selection containing both `office_id` and `office_code`
