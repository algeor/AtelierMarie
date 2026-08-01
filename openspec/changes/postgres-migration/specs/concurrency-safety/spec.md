## REMOVED Requirements

### Requirement: Checkout transaction uses BEGIN IMMEDIATE
**Reason**: `BEGIN IMMEDIATE` is SQLite-specific and does not exist in Postgres.
**Migration**: Checkout and reservation flows use Postgres transactions with row-level locks or atomic conditional updates.

## ADDED Requirements

### Requirement: Checkout transaction uses Postgres row-level locking
The checkout service SHALL protect stock validation and stock mutation with a single Postgres transaction using row-level locks or atomic conditional update predicates.

#### Scenario: Concurrent checkouts for last item are serialized
- **WHEN** two concurrent requests attempt to check out the last unit of product X
- **THEN** only one transaction succeeds
- **AND** the other transaction observes the updated stock state and fails with a conflict response
- **AND** stock never becomes negative

#### Scenario: Read-only operations are not blocked by checkout
- **WHEN** a checkout transaction is open for a product stock mutation
- **THEN** ordinary product and cart read requests complete using Postgres MVCC semantics without waiting for the write transaction to finish

### Requirement: Background claim workers lock rows explicitly
Background jobs that claim queued or due work SHALL use Postgres row-locking patterns that prevent two workers from processing the same row.

#### Scenario: Two workers claim queued email work
- **WHEN** two email outbox workers run at the same time
- **THEN** each claimed email row is processed by at most one worker
- **AND** unclaimed rows remain available for another worker or retry

#### Scenario: Courier polling leases are exclusive
- **WHEN** two courier polling loops attempt to lease due shipments concurrently
- **THEN** each due shipment is leased by at most one loop for the lease interval

