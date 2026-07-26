## Requirements

### Requirement: Managed site announcement banner
The system SHALL store a managed top-of-site announcement banner with localized message fields, optional link fields, an enabled flag, an optional active window, and a stable ID or version used for dismissal. The banner SHALL support `message_en` as required text, `message_bg` as optional text with English fallback, optional `link_label_en`, optional `link_label_bg`, optional `link_url`, `is_enabled`, `starts_at`, and `ends_at`. Datetime writes SHALL normalize timezone-aware input to canonical UTC text and SHALL reject timezone-less non-canonical input using the same rules as discount windows.

Only one banner SHALL be visible on the storefront at a time. A banner is visible when it is enabled and its active window contains the current server time, with inclusive start and end bounds. Disabled, future, and expired banners SHALL NOT be returned by the public banner endpoint.

#### Scenario: Enabled banner without dates is visible
- **WHEN** a banner has `is_enabled = true` and no start or end date
- **THEN** it is considered visible

#### Scenario: Future banner is hidden publicly
- **WHEN** a banner has `starts_at` later than the current server time
- **THEN** the public banner endpoint returns no banner

#### Scenario: Expired banner is hidden publicly
- **WHEN** a banner has `ends_at` earlier than the current server time
- **THEN** the public banner endpoint returns no banner

#### Scenario: Invalid banner window is rejected
- **WHEN** an admin submits `starts_at` later than or equal to `ends_at`
- **THEN** the request is rejected with a validation error

### Requirement: Public active banner endpoint
The system SHALL expose `GET /v1/promotions/banner` returning the currently visible banner for the requested locale, or `null` when no banner is visible. The endpoint SHALL accept `locale` (`en` or `bg`, default `en`). The response SHALL include localized `message`, optional localized `link_label`, optional `link_url`, and `dismiss_key`. The public response SHALL NOT expose future scheduled banner copy or raw inactive banner configuration.

#### Scenario: Get active banner in English
- **WHEN** an active banner has `message_en = "20% off spring candles"`
- **THEN** `GET /v1/promotions/banner?locale=en` returns that message and a dismiss key

#### Scenario: Get active banner in Bulgarian with fallback
- **WHEN** an active banner has `message_bg = NULL`
- **THEN** `GET /v1/promotions/banner?locale=bg` returns the English message

#### Scenario: No active banner
- **WHEN** no banner is currently visible
- **THEN** `GET /v1/promotions/banner` returns 200 with `banner = null`

#### Scenario: Banner link is returned when configured
- **WHEN** an active banner has `link_url` and a localized link label
- **THEN** the public response includes both values so the storefront can render a link
