## ADDED Requirements

### Requirement: Speedy operational calls use consistent resilience controls
All new Speedy operational calls SHALL use bounded timeouts, typed error categories, redacted logs/events, and a dedicated observable circuit breaker where failures indicate Speedy service unavailability. Validation/auth errors SHALL be classified separately from transient outages.

#### Scenario: Speedy transient failures trip operational circuit
- **WHEN** Speedy operational endpoints repeatedly time out or return 5xx responses
- **THEN** the Speedy operational circuit opens and subsequent non-critical admin operations fail fast with an admin-safe unavailable response

#### Scenario: Speedy validation errors do not trip outage circuit
- **WHEN** Speedy rejects a request because of invalid shipment data, invalid client identity, or inaccessible shipment id
- **THEN** the error is shown as validation/configuration/actionable admin feedback and is not counted as a Speedy outage

#### Scenario: Speedy secrets are redacted
- **WHEN** any Speedy operational call succeeds or fails
- **THEN** stored audit events and logs do not include `speedy_api_password` or raw request payloads containing credentials

### Requirement: Speedy health state is observable
The system SHALL expose admin-only Speedy health state that includes configuration presence, client-id verification result, circuit state, last failure category, and timestamp of last successful safe health check.

#### Scenario: Admin reads Speedy health
- **WHEN** an admin opens the Speedy admin page or calls the Speedy health endpoint
- **THEN** the response includes safe health fields and excludes credentials
