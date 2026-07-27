## ADDED Requirements

### Requirement: Admin-triggered erasure endpoint

The system SHALL expose an admin-only endpoint that triggers erasure for a data subject and reports
what was affected. The endpoint SHALL require admin authorization (JWT `is_admin` claim OR API key)
and SHALL require at least one of email or `user_id` as the primary identifier.

#### Scenario: Admin erases a subject by email

- **WHEN** an authenticated admin POSTs an erasure request with a customer email
- **THEN** the erasure service runs and the response reports counts of rows anonymized and deleted
  per table

#### Scenario: Reject request with no primary identifier

- **WHEN** an erasure request is submitted with only a `session_id` and no email or `user_id`
- **THEN** the endpoint returns 422 and no data is changed

#### Scenario: Reject unauthenticated caller

- **WHEN** a caller without admin authorization POSTs to the erasure endpoint
- **THEN** the endpoint returns 401/403 and no data is changed

#### Scenario: Subject not found

- **WHEN** an admin submits an erasure request for an email that matches no records
- **THEN** the endpoint returns success with zero affected counts (idempotent, no error)
