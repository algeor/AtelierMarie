## ADDED Requirements

### Requirement: Admin can configure Econt integration
The system SHALL provide an admin-only Econt settings surface where an admin can configure whether Econt fulfillment is enabled, the Econt environment (`demo` or `production`), shop id, credential source, sender origin, default shipment options, payment-side behavior, office locator behavior, and automatic status-sync behavior.

#### Scenario: Admin views Econt settings
- **WHEN** an authenticated admin opens the Econt settings page
- **THEN** the page shows current non-secret settings, whether required secrets are configured, and whether the integration is enabled

#### Scenario: Admin saves non-secret settings
- **WHEN** an admin updates shop id, sender office code, default pack count, shipment description, or feature toggles
- **THEN** the settings are persisted and subsequent fulfillment actions use the updated values

#### Scenario: Non-admin cannot access Econt settings
- **WHEN** a non-admin requests Econt settings endpoints or page data
- **THEN** the system denies access with the existing admin authorization behavior

### Requirement: Econt secrets are protected
The system SHALL never return Econt private keys, access tokens, or Authorization headers in API responses, logs, snapshots, or frontend state. If secrets are stored by the application, they SHALL be encrypted with an app-level encryption key; otherwise the system SHALL support env-backed secrets and show only configured/not configured state.

#### Scenario: Secret is saved
- **WHEN** an admin saves an Econt private key through the UI
- **THEN** later reads show only a masked/configured state and never the original value

#### Scenario: Env-backed secret is configured
- **WHEN** `ECONT_DELIVERY_PRIVATE_KEY` is configured in the environment
- **THEN** the admin settings page shows that credentials are configured without exposing the value

### Requirement: Admin can test Econt connectivity
The system SHALL provide an admin-only test connection action that validates current Econt settings without creating a real shipment. The result SHALL distinguish success, missing configuration, authentication failure, validation failure, timeout, and service outage.

#### Scenario: Test connection succeeds
- **WHEN** an admin runs the test with valid demo credentials and shop id
- **THEN** the system returns success and records a successful health check timestamp

#### Scenario: Test connection fails due to missing credentials
- **WHEN** an admin runs the test without a private key or shop id
- **THEN** the system returns an actionable configuration error and no Econt request is attempted

#### Scenario: Test connection redacts courier error details
- **WHEN** Econt returns an authentication failure
- **THEN** the admin sees a concise auth failure and no Authorization value is logged or returned
