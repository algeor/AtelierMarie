## ADDED Requirements

### Requirement: Consent required before tracking
The SDK SHALL NOT emit any events until explicit consent is granted when initialized with `requireConsent: true`.

#### Scenario: Track called before consent
- **WHEN** the tracker is initialized with `{ requireConsent: true }` and `tracker.track()` is called before `grantConsent()`
- **THEN** the SDK silently discards the event (no-op) — no event is queued, no network request is made

#### Scenario: Default behavior (requireConsent: true)
- **WHEN** `AtelierTracker.init({ endpoint: '...' })` is called without specifying requireConsent
- **THEN** the SDK defaults to `requireConsent: true` and tracking is disabled until consent is granted

### Requirement: Grant consent enables tracking
The SDK SHALL begin tracking events when `tracker.grantConsent()` is called, and persist the consent state.

#### Scenario: User accepts cookie banner
- **WHEN** `tracker.grantConsent()` is called
- **THEN** the SDK sets its internal enabled flag to true, stores `atelier_consent: 'granted'` in localStorage, and all subsequent `track()` calls function normally

#### Scenario: Consent persists across page loads
- **WHEN** the user has previously granted consent and the page is reloaded
- **THEN** the SDK reads `atelier_consent: 'granted'` from localStorage on initialization and starts in enabled state (no need to call grantConsent() again)

### Requirement: Revoke consent stops tracking and clears data
The SDK SHALL stop tracking and clear stored data when `tracker.revokeConsent()` is called.

#### Scenario: User revokes consent
- **WHEN** `tracker.revokeConsent()` is called
- **THEN** the SDK sets enabled to false, clears the in-memory event queue (unsent events discarded), removes `atelier_consent`, `atelier_session_id`, and `atelier_session_start` from localStorage

#### Scenario: Track called after revocation
- **WHEN** consent has been revoked and `tracker.track()` is called
- **THEN** the SDK silently discards the event (same behavior as pre-consent)

### Requirement: Consent state in localStorage
The SDK SHALL persist consent state in localStorage under the key `atelier_consent`.

#### Scenario: Consent granted persistence
- **WHEN** `grantConsent()` is called
- **THEN** localStorage contains `atelier_consent` with value `'granted'`

#### Scenario: Consent revoked persistence
- **WHEN** `revokeConsent()` is called
- **THEN** localStorage item `atelier_consent` is removed (not set to 'revoked')

#### Scenario: localStorage unavailable for consent
- **WHEN** localStorage is not accessible and `grantConsent()` is called
- **THEN** consent is granted for the current page session only (in-memory flag) — on next page load, consent must be granted again
