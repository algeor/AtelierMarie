## ADDED Requirements

### Requirement: In-memory cache with per-key-type TTL
The system SHALL provide an in-memory recommendation cache with different TTL values per key type:
- Session-keyed entries: TTL of 5 minutes
- User-keyed entries: TTL of 30 minutes
- Trending products: TTL of 30 minutes (refreshed by batch job)
- Featured products: loaded once on startup, refreshed on product catalog update

#### Scenario: Session cache expires after 5 minutes
- **WHEN** a session recommendation is cached and 5 minutes elapse
- **THEN** the next request for that session results in a cache miss

#### Scenario: User cache persists for 30 minutes
- **WHEN** a user recommendation is cached and 20 minutes elapse
- **THEN** the cache still returns the entry (within 30 min TTL)

#### Scenario: Trending cache refreshed by batch job
- **WHEN** the batch job completes
- **THEN** the trending cache entry is replaced with fresh data and TTL resets to 30 minutes

### Requirement: LRU eviction at max capacity
The cache SHALL evict the least recently used entries when the total entry count exceeds 10,000. Eviction applies to session and user entries (trending and featured are exempt).

#### Scenario: Cache at capacity
- **WHEN** the cache holds 10,000 session/user entries and a new entry is added
- **THEN** the least recently accessed entry is evicted to make room

#### Scenario: Trending not evicted
- **WHEN** LRU eviction runs
- **THEN** the trending and featured entries are never evicted (they are separate from the LRU pool)

### Requirement: Cache miss triggers on-the-fly computation
The system SHALL compute recommendations on-the-fly when a cache miss occurs, rather than returning an error or empty result.

#### Scenario: Cache miss for session
- **WHEN** no cache entry exists for a session_id
- **THEN** the system runs the recommendation pipeline and returns results (with `cached: false` in response)

#### Scenario: On-the-fly result is cached
- **WHEN** recommendations are computed on-the-fly for a cache miss
- **THEN** the computed result is stored in the cache with the appropriate TTL for future requests

### Requirement: Cache handles multi-worker deployment
The cache SHALL operate in shared-nothing mode: each worker process maintains its own independent cache. Slight inconsistency across workers is acceptable.

#### Scenario: Independent worker caches
- **WHEN** worker A caches a recommendation and worker B receives the next request for the same session
- **THEN** worker B experiences a cache miss and computes independently (no shared state required)

#### Scenario: Cache consistency after batch job
- **WHEN** the batch job runs (in one worker or a separate process)
- **THEN** other workers gradually warm their caches on subsequent requests (eventual consistency)

### Requirement: Cache exposes statistics
The cache SHALL expose metrics for monitoring: hit count, miss count, eviction count, and current entry count.

#### Scenario: Cache stats available
- **WHEN** the application is running and serving recommendations
- **THEN** cache statistics are accessible programmatically (for logging or health endpoints)

#### Scenario: Stats reset on restart
- **WHEN** the application process restarts
- **THEN** cache statistics start from zero (no persistence of stats)
