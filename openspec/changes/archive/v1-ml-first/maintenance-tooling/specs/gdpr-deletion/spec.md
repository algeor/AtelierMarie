## ADDED Requirements

### Requirement: Complete user data erasure
The system SHALL delete all personally identifiable data for a specified user across all storage layers when the delete-user command is executed with `--user-id <ID>` and `--confirm`.

#### Scenario: User record deleted from SQLite
- **WHEN** the delete-user command is executed with a valid user ID and `--confirm`
- **THEN** the user's row in the SQLite users table SHALL be deleted

#### Scenario: Orders anonymized in SQLite
- **WHEN** the delete-user command is executed with a valid user ID and `--confirm` AND the user has associated orders
- **THEN** all orders with that user_id SHALL have their user_id set to NULL (order data preserved, user link removed)

#### Scenario: Session identity unlinked in DuckDB
- **WHEN** the delete-user command is executed with a valid user ID and `--confirm`
- **THEN** all rows in DuckDB session_identity with that user_id SHALL have their user_id set to NULL

#### Scenario: Events remain unchanged
- **WHEN** the delete-user command is executed with a valid user ID and `--confirm`
- **THEN** no modifications SHALL be made to the DuckDB events table (events reference session_id only; without the session_identity link they are already anonymous)

### Requirement: Confirmation required for deletion
The system SHALL NOT perform any deletion unless the `--confirm` flag is provided. Without `--confirm`, the system SHALL display what would be deleted and exit without making changes.

#### Scenario: Missing --confirm flag shows preview
- **WHEN** the delete-user command is executed with a valid user ID but WITHOUT `--confirm`
- **THEN** the system SHALL display the user record, order count, and session count that would be affected, then exit with no changes

#### Scenario: Nonexistent user ID
- **WHEN** the delete-user command is executed with a user ID that does not exist in the users table
- **THEN** the system SHALL exit with an error message indicating the user was not found

### Requirement: Deletion audit logging
The system SHALL append a record to `app/data/deletion_log.jsonl` for every user deletion, containing the user_id, timestamp, and counts of affected rows (orders anonymized, sessions unlinked).

#### Scenario: Audit log entry created on deletion
- **WHEN** a user deletion completes successfully
- **THEN** a JSON line SHALL be appended to `app/data/deletion_log.jsonl` with `user_id`, `deleted_at` (ISO 8601 timestamp), `orders_anonymized` (count), `sessions_unlinked` (count)

#### Scenario: Audit log not subject to retention cleanup
- **WHEN** the data retention cleanup command runs
- **THEN** the `deletion_log.jsonl` file SHALL NOT be modified or deleted regardless of its age

### Requirement: Mutual exclusion during deletion
The system SHALL acquire the maintenance file lock before performing deletion operations.

#### Scenario: Lock prevents concurrent deletion
- **WHEN** the delete-user command is executed AND another maintenance process holds the lock
- **THEN** the command SHALL exit with an error without making any changes
