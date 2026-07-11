## ADDED Requirements

### Requirement: Google OAuth calls use a circuit breaker
The system SHALL wrap all HTTP calls to Google OAuth endpoints (token exchange, JWKS fetch, userinfo) with a circuit breaker. The circuit breaker SHALL have three states: CLOSED (normal operation), OPEN (fast-fail all requests), and HALF_OPEN (allow one probe request). Transition thresholds: 3 consecutive failures within 30 seconds → OPEN; after 60 seconds in OPEN → HALF_OPEN; one success in HALF_OPEN → CLOSED; one failure in HALF_OPEN → OPEN.

#### Scenario: Circuit trips after consecutive failures
- **WHEN** Google's token endpoint returns 3 consecutive 5xx errors within 30 seconds
- **THEN** the circuit opens and subsequent login attempts fail immediately with "Authentication service temporarily unavailable" (HTTP 503) without making HTTP requests to Google

#### Scenario: Circuit recovers after cooldown
- **WHEN** the circuit has been OPEN for 60 seconds
- **THEN** the next login attempt is allowed through as a probe; if it succeeds, the circuit closes and normal operation resumes

#### Scenario: Timeouts count as failures
- **WHEN** a Google OAuth HTTP call times out (exceeds the configured timeout)
- **THEN** it counts as a failure toward the circuit breaker threshold

#### Scenario: Non-5xx errors do not trip the circuit
- **WHEN** Google returns HTTP 400 (invalid grant — user error) or HTTP 401
- **THEN** the failure is NOT counted toward the circuit breaker threshold (client errors are not service outages)

### Requirement: Circuit breaker state is observable
The system SHALL expose circuit breaker state via `GET /v1/admin/health/oauth` (admin-only). The response SHALL include: current state (CLOSED/OPEN/HALF_OPEN), failure count, last failure timestamp, and time until next probe (if OPEN).

#### Scenario: Admin checks circuit breaker health
- **WHEN** an admin calls `GET /v1/admin/health/oauth` while the circuit is OPEN
- **THEN** the response includes `{"state": "OPEN", "failures": 3, "last_failure": "2026-07-11T14:30:00Z", "next_probe_in_seconds": 45}`

### Requirement: Login fails gracefully when circuit is open
The system SHALL return a user-friendly error when the OAuth circuit breaker is open. The error SHALL indicate that the authentication service is temporarily unavailable and suggest trying again later. Admin API key authentication SHALL remain functional regardless of circuit state.

#### Scenario: User login attempt while circuit is open
- **WHEN** a user attempts Google OAuth login and the circuit is OPEN
- **THEN** the system returns HTTP 503 with `{"error": {"code": "AUTH_SERVICE_UNAVAILABLE", "message": "Login is temporarily unavailable. Please try again in a few minutes."}}` — without attempting any HTTP call to Google

#### Scenario: Admin API key auth unaffected by circuit state
- **WHEN** the OAuth circuit is OPEN and an admin authenticates via API key header
- **THEN** authentication succeeds normally (API key validation is local, not affected by Google outage)
