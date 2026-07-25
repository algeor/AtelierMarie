## MODIFIED Requirements

### Requirement: Session stores preferred locale
The `sessions` table SHALL include a `preferred_locale` column (`TEXT` NOT NULL, allowed values `'bg'` or `'en'`, default `'en'`) enforced via a `CHECK` constraint. The locale preference SHALL be persisted when detected or manually changed by the user.

#### Scenario: New session gets default locale
- **WHEN** a new session is created for a user with no cookie
- **THEN** `preferred_locale` is set based on `Accept-Language` detection (or `en` if no `bg` detected)

#### Scenario: Locale preference updated on toggle
- **WHEN** a user switches language via the toggle and the frontend sends a preference update
- **THEN** the session's `preferred_locale` is updated to the new locale

#### Scenario: Locale persisted for order context
- **WHEN** an order is placed
- **THEN** the order can reference the session's `preferred_locale` for future email localization

#### Scenario: Invalid locale rejected at DB level
- **WHEN** any code path attempts to write a `preferred_locale` value outside `{'bg', 'en'}`
- **THEN** Postgres raises a check-violation error (`23514`) and the write fails

## ADDED Requirements

### Requirement: Expired session cleanup uses SQL-native delete
The session cleanup task SHALL execute `DELETE FROM sessions WHERE expires_at < NOW()` against the Postgres `TIMESTAMPTZ expires_at` column with the supporting index `idx_sessions_expires_at`. The task SHALL run hourly during application lifetime and SHALL log the number of rows deleted at INFO level.

#### Scenario: Hourly cleanup deletes expired sessions
- **WHEN** the cleanup task fires and 3 sessions have `expires_at < NOW()`
- **THEN** exactly those 3 rows are deleted, their `cart_items` are cascade-removed, and one INFO log records `rows_deleted=3`

#### Scenario: Cleanup uses the expires_at index
- **WHEN** `EXPLAIN` is run on the cleanup DELETE against a table with many expired sessions
- **THEN** the query plan uses an index scan on `idx_sessions_expires_at`, not a sequential scan

#### Scenario: Cleanup runs safely under load
- **WHEN** the cleanup task fires while checkout transactions are actively running
- **THEN** the cleanup DELETE does not conflict with checkout `FOR UPDATE` locks on products, and both operations complete without error
