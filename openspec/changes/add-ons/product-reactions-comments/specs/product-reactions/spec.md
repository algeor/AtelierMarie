## ADDED Requirements

### Requirement: Toggle reaction on a product
The system SHALL allow any session holder to toggle a reaction (heart or thumbs_up) on a product. A session MAY have at most one reaction of each type per product. Toggling an existing reaction removes it; toggling a non-existent reaction adds it. The product MUST exist and be active (is_active=1).

#### Scenario: Add a heart reaction
- **WHEN** a session sends `POST /v1/products/{product_id}/reactions` with `{"reaction_type": "heart"}`
- **THEN** the system stores the reaction and returns `201` with `{"reaction_type": "heart", "active": true}`

#### Scenario: Remove a heart reaction (toggle off)
- **WHEN** a session that already has a heart reaction on the product sends `POST /v1/products/{product_id}/reactions` with `{"reaction_type": "heart"}`
- **THEN** the system removes the reaction and returns `200` with `{"reaction_type": "heart", "active": false}`

#### Scenario: Invalid reaction type rejected
- **WHEN** a request includes a `reaction_type` value other than "heart" or "thumbs_up"
- **THEN** the system returns `422 Unprocessable Entity`

#### Scenario: Reaction on non-existent product
- **WHEN** a request targets a product_id that does not exist
- **THEN** the system returns `404 Not Found`

#### Scenario: Reaction on inactive product
- **WHEN** a request targets a product with is_active=0
- **THEN** the system returns `404 Not Found` (treat inactive as non-existent)

### Requirement: Get aggregate reaction counts for a product
The system SHALL return the total count of each reaction type for a product, along with whether the current session has reacted.

#### Scenario: Get reactions for a product with reactions
- **WHEN** a session sends `GET /v1/products/{product_id}/reactions`
- **THEN** the system returns `200` with `{"heart": {"count": N, "reacted": bool}, "thumbs_up": {"count": M, "reacted": bool}}`

#### Scenario: Get reactions for a product with no reactions
- **WHEN** a session sends `GET /v1/products/{product_id}/reactions` for a product with zero reactions
- **THEN** the system returns `200` with `{"heart": {"count": 0, "reacted": false}, "thumbs_up": {"count": 0, "reacted": false}}`

#### Scenario: Get reactions for inactive product
- **WHEN** a session sends `GET /v1/products/{product_id}/reactions` for a product with is_active=0
- **THEN** the system returns `404 Not Found`

### Requirement: Reactions are session-scoped
The system SHALL scope reactions to the session cookie. No login is required. Each session MAY have one heart and one thumbs_up per product independently.

#### Scenario: Two sessions react to the same product
- **WHEN** session A adds a heart and session B adds a heart to the same product
- **THEN** the aggregate count for heart is 2, session A sees `reacted: true`, session B sees `reacted: true`

#### Scenario: Toggle is atomic and idempotent
- **WHEN** two concurrent requests from the same session toggle the same reaction type
- **THEN** the system handles both without error (INSERT OR IGNORE + rowcount check ensures atomicity)

### Requirement: Reaction toggle rate limiting
The system SHALL enforce a maximum of 10 reaction toggles per session per minute across all products to prevent write-amplification DoS. Toggle operations are tracked in a separate `reaction_toggle_log` table (append-only) since the reactions table loses rows on toggle-off.

#### Scenario: Eleventh toggle in one minute blocked
- **WHEN** a session has toggled reactions 10 times in the last 60 seconds (counted from reaction_toggle_log)
- **THEN** the system returns `429 Too Many Requests` with message "Too many reactions. Please slow down."

#### Scenario: Toggle after one minute resets
- **WHEN** a session toggles 10 times, waits 60 seconds, then toggles again
- **THEN** the system allows the toggle (counter resets)

### Requirement: Reactions database schema
The system SHALL store reactions in a `reactions` table with columns: `session_id` (TEXT, NOT NULL — denormalized snapshot, not a FK), `product_id` (TEXT, NOT NULL, FK to products ON DELETE CASCADE), `reaction_type` (TEXT, CHECK IN ('heart', 'thumbs_up')), `created_at` (TEXT, datetime default). Primary key is `(session_id, product_id, reaction_type)`.

The system SHALL also maintain a `reaction_toggle_log` table for rate limiting with columns: `session_id` (TEXT, NOT NULL), `product_id` (TEXT, NOT NULL), `toggled_at` (TEXT, datetime default). This table is append-only; old rows (>1 hour) are cleaned up lazily.

#### Scenario: Uniqueness constraint prevents duplicates
- **WHEN** the same session attempts to insert two heart reactions for the same product
- **THEN** the database rejects the second insert with a UNIQUE constraint violation (handled via INSERT OR IGNORE)

#### Scenario: Index supports aggregate count queries
- **WHEN** the system queries reaction counts by product_id
- **THEN** an index on `(product_id, reaction_type)` ensures the query executes efficiently

#### Scenario: Index supports rate limit checks
- **WHEN** the system counts toggles by session_id within a time window
- **THEN** an index on `(session_id, created_at)` ensures efficient counting

#### Scenario: Product deletion cascades to reactions
- **WHEN** a product is deleted from the products table
- **THEN** all reactions for that product are automatically deleted via ON DELETE CASCADE
