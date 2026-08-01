## ADDED Requirements

### Requirement: Econt API calls use timeout and circuit breaker protection
The system SHALL wrap Econt API calls with configured HTTP timeouts and a dedicated circuit breaker. Timeouts and 5xx responses SHALL count as transient failures; validation and authentication failures SHALL be classified separately and SHALL NOT be treated as courier outage.

#### Scenario: Econt timeout trips failure count
- **WHEN** an Econt API call times out
- **THEN** the Econt circuit breaker records a transient failure and the admin action returns a retryable error

#### Scenario: Econt circuit open
- **WHEN** the Econt circuit breaker is open
- **THEN** fulfillment actions fail fast with a service-unavailable message and no HTTP request is made

#### Scenario: Econt validation error does not trip circuit
- **WHEN** Econt returns a 4xx validation error for an invalid payload
- **THEN** the system records an order-data error without incrementing the outage circuit failure count

### Requirement: Econt logs and snapshots are redacted
The system SHALL redact Econt private keys, Authorization headers, access tokens, and customer-sensitive fields beyond what is needed for fulfillment audit before writing logs or stored payload snapshots.

#### Scenario: Authorization header redacted
- **WHEN** an Econt request fails and is logged
- **THEN** logs and stored event payloads do not contain the raw Authorization header

#### Scenario: Stored payload keeps operational context
- **WHEN** an Econt validation error is stored
- **THEN** the stored event includes endpoint, action, status class, field-level error hints, and redacted request shape sufficient for debugging
