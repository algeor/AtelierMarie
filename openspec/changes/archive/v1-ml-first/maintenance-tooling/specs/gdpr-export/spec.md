## ADDED Requirements

### Requirement: Complete user data export
The system SHALL export all data associated with a specified user as a single JSON file when the export-user command is executed with `--user-id <ID>` and `--output <path>`.

#### Scenario: Export produces complete JSON file
- **WHEN** the export-user command is executed with a valid user ID and output path
- **THEN** a JSON file SHALL be written to the specified path containing: `exported_at` (ISO 8601 timestamp), `user` (profile data), `sessions` (all linked sessions with event counts), `events` (all events across all user sessions), and `orders` (all orders with line items)

#### Scenario: User profile included in export
- **WHEN** the export is generated
- **THEN** the `user` object SHALL contain all columns from the SQLite users table for that user_id

#### Scenario: Sessions resolved via session_identity
- **WHEN** the export is generated AND the user has linked sessions in DuckDB session_identity
- **THEN** the `sessions` array SHALL contain each session with `session_id`, `first_seen`, `last_seen`, and `event_count`

#### Scenario: Events collected across all user sessions
- **WHEN** the export is generated AND the user has linked sessions
- **THEN** the `events` array SHALL contain all events from DuckDB where `session_id` matches any of the user's linked sessions

#### Scenario: Orders included with line items
- **WHEN** the export is generated AND the user has orders
- **THEN** the `orders` array SHALL contain each order with its items, prices, status, and timestamps

### Requirement: Export handles nonexistent user
The system SHALL exit with a clear error message if the specified user_id does not exist.

#### Scenario: Nonexistent user ID
- **WHEN** the export-user command is executed with a user ID not present in the users table
- **THEN** the system SHALL exit with a non-zero status and print an error indicating the user was not found

### Requirement: Export summary output
The system SHALL print a summary to stdout after successful export showing counts of records exported and the file size.

#### Scenario: Summary printed after export
- **WHEN** the export completes successfully
- **THEN** stdout SHALL show: profile record count, session count, event count, order count, output file path, and file size
