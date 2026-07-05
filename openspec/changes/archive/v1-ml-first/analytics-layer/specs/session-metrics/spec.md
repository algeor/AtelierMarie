## ADDED Requirements

### Requirement: Session metrics materialized table
The analytics layer SHALL compute an `analytics_session_metrics` summary table in DuckDB containing aggregate session statistics for the last 30 days.

The table MUST be a single-row result containing: `total_sessions`, `anonymous_sessions`, `authenticated_sessions`, `converted_sessions`, and `avg_events_per_session`.

#### Scenario: Session breakdown by authentication state
- **WHEN** the analytics job runs
- **AND** there are 100 sessions: 60 never linked to a user, 25 linked to a user without purchase, 15 with at least one purchase event
- **THEN** `analytics_session_metrics` contains total_sessions=100, anonymous_sessions=60, authenticated_sessions=25, converted_sessions=15

#### Scenario: Average events per session
- **WHEN** the analytics job runs
- **AND** 100 sessions have a total of 500 events
- **THEN** avg_events_per_session equals 5.0

#### Scenario: No sessions exist
- **WHEN** the analytics job runs and no sessions exist in the last 30 days
- **THEN** `analytics_session_metrics` contains all zeros

#### Scenario: Session that authenticates mid-flow
- **WHEN** a session starts anonymous and later links to a user_id
- **AND** that session does not contain a purchase event
- **THEN** it counts toward authenticated_sessions (not anonymous_sessions)
