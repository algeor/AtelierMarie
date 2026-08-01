## ADDED Requirements

### Requirement: Courier statuses are polled on a schedule
The system SHALL poll courier shipment statuses on a configurable schedule for active orders with courier tracking identifiers. Polling SHALL support Speedy and Econt providers and SHALL not require courier push notifications/webhooks to detect delivered, failed, returning, or returned shipments. The poller SHALL be implemented as async code using async courier clients and MUST NOT use worker threads or `asyncio.to_thread`.

#### Scenario: Poll active shipped orders
- **WHEN** the scheduled courier status poll runs
- **THEN** the system selects eligible active shipped or return-in-transit orders with tracking/shipment identifiers and polls their configured courier provider

#### Scenario: Do not poll terminal orders indefinitely
- **WHEN** an order is cancelled, returned and closed, or otherwise no longer operationally active
- **THEN** the scheduled poll excludes that order unless an admin explicitly requests a manual refresh

### Requirement: Polling uses leases and backoff
The system SHALL use database-backed leases or equivalent durable coordination so concurrent app workers or repeated cron invocations do not poll the same order at the same time. The system SHALL record last poll time, next poll time, attempt count, and last safe error. Failed polls SHALL use bounded backoff.

#### Scenario: Concurrent pollers do not duplicate work
- **WHEN** two polling loops run at the same time
- **THEN** only one poller acquires the lease for a given order and the other skips it

#### Scenario: Failed poll backs off
- **WHEN** a courier poll fails due to timeout, outage, auth, or validation error
- **THEN** the system records an admin-safe error and schedules the next poll using backoff instead of retrying immediately in a tight loop

### Requirement: Polling stores evidence and review signals only
The system SHALL store normalized courier status, raw redacted courier payloads, and audit events from polling. Polling MUST NOT automatically refund, restock, close return cases, or force order/payment transitions.

#### Scenario: Poll detects returned parcel
- **WHEN** a scheduled poll detects a returned parcel from Speedy or Econt
- **THEN** the system stores the courier evidence, creates or updates an admin review signal, and leaves order status, payment status, refund status, and stock unchanged

#### Scenario: Poll detects delivered COD order
- **WHEN** a scheduled poll detects delivery for a COD order
- **THEN** the system stores the courier evidence but does not mark COD paid or settled unless an explicit business rule/admin action does so

### Requirement: Polling cadence is configurable and provider-safe
The system SHALL expose operational settings for polling interval, batch size, maximum attempts/backoff, and provider enablement. Polling SHALL respect provider availability and configured credentials.

#### Scenario: Provider disabled for polling
- **WHEN** Econt polling is disabled in settings
- **THEN** the scheduled poll skips Econt orders but manual admin updates remain available

#### Scenario: Batch limit enforced
- **WHEN** more eligible orders exist than the configured batch size
- **THEN** one poll run processes no more than the configured batch size and leaves the rest eligible for future runs

### Requirement: Admin can request a manual status refresh
The system SHALL allow admins to manually refresh courier status for an individual order. Manual refresh SHALL use the same provider-specific normalization and review-signal logic as scheduled polling.

#### Scenario: Admin refreshes status now
- **WHEN** an admin requests a courier status refresh for a shipped Speedy or Econt order
- **THEN** the system polls the courier immediately, stores the result, and displays updated courier evidence or an admin-safe error

### Requirement: Polling runs through an async service
The system SHALL implement the polling logic as an idempotent async service called by the existing in-app async background loop. Manual admin refresh SHALL call the same async service path. Any future externally triggered invocation MUST enter through an async endpoint or async runner and MUST NOT introduce a separate synchronous polling implementation.

#### Scenario: In-app loop awaits poll service
- **WHEN** the FastAPI app background polling loop reaches its interval
- **THEN** it awaits the same async courier polling service used by manual refresh

#### Scenario: Manual refresh uses same async path
- **WHEN** an admin requests a manual courier status refresh
- **THEN** the system awaits the same async provider polling and normalization path used by the scheduled poller
