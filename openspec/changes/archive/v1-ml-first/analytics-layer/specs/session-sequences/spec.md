## ADDED Requirements

### Requirement: Session sequences materialized table
The analytics layer SHALL compute an `analytics_session_sequences` table containing ordered product interaction sequences per session from the last 7 days.

Each row MUST contain: `session_id`, `product_sequence` (list of product_ids ordered by timestamp), and `event_sequence` (list of corresponding event types).

#### Scenario: Session with multiple product interactions
- **WHEN** a session views product A, then adds product B to cart, then views product C
- **THEN** the table contains product_sequence=[A, B, C] and event_sequence=[product_view, add_to_cart, product_view]

#### Scenario: Events without product_id excluded
- **WHEN** a session has events with and without product_id
- **THEN** only events with a non-NULL product_id appear in the sequences

#### Scenario: 7-day window (shorter than other tables)
- **WHEN** the analytics job runs
- **THEN** only sessions with activity in the last 7 days are included (sequences older than 7 days are dropped)

#### Scenario: Sequence ordering is deterministic
- **WHEN** two events in the same session have the same timestamp
- **THEN** ordering falls back to event_id for determinism
