## ADDED Requirements

### Requirement: Admin manages payment settings
The system SHALL provide `/admin/settings/payments` where admins can enable/disable
card payments, enable/disable pay on delivery, set pay-on-delivery max amount, and
view read-only Stripe configuration health/mode. This page SHALL require admin
authentication.

#### Scenario: Admin views payment settings
- **WHEN** an authenticated admin opens `/admin/settings/payments`
- **THEN** the page shows current payment toggles, pay-on-delivery max amount,
  Stripe configured/missing health, and Stripe test/live mode

#### Scenario: Both methods disabled rejected
- **WHEN** admin attempts to save settings with card payments disabled and pay on
  delivery disabled
- **THEN** the backend rejects the save and settings remain unchanged

#### Scenario: Card enable rejected when Stripe incomplete
- **WHEN** admin attempts to enable card payments but Stripe env config is
  incomplete or production uses test keys
- **THEN** the backend rejects the save and explains the missing production gate

#### Scenario: Settings audit recorded
- **WHEN** admin changes payment settings
- **THEN** the backend appends a `site_setting_events` audit entry with admin
  identity, setting key, old value, new value, timestamp, and request id

### Requirement: Public checkout receives safe payment settings
The system SHALL expose a safe public settings projection for checkout. The
projection SHALL include only enabled payment methods and pay-on-delivery max
amount. It SHALL NOT expose Stripe secret key, webhook secret, admin audit data, or
internal configuration details.

#### Scenario: Public settings omit secrets
- **WHEN** checkout fetches payment settings
- **THEN** the response contains safe availability fields only and no secrets
