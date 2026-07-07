## ADDED Requirements

### Requirement: Post a comment on a product
The system SHALL allow any session holder to post a comment on a product. Comments consist of a display name (2–50 chars) and a body (1–500 chars). Length limits apply to the raw input after whitespace trimming (before html.escape). The product MUST exist and be active (is_active=1). Logged-in users have their display name auto-filled from their Google profile but MAY override it.

#### Scenario: Anonymous user posts a comment
- **WHEN** an anonymous session sends `POST /v1/products/{product_id}/comments` with `{"display_name": "Marie", "body": "Love this scent!"}`
- **THEN** the system sanitizes inputs (html.escape), validates lengths, stores the comment, and returns `201` with the created comment including `id`, `display_name`, `body`, `created_at`

#### Scenario: Logged-in user posts a comment without display_name
- **WHEN** a logged-in session (with non-null users.name) sends `POST /v1/products/{product_id}/comments` with `{"body": "Beautiful candle"}` (no display_name)
- **THEN** the system uses the user's Google profile name as the display name and returns `201`

#### Scenario: Logged-in user with NULL profile name posts without display_name
- **WHEN** a logged-in session with NULL users.name posts without display_name
- **THEN** the system returns `422 Unprocessable Entity` with message "display_name is required"

#### Scenario: Display name too short
- **WHEN** a request includes `display_name` that is fewer than 2 characters after whitespace trimming
- **THEN** the system returns `422 Unprocessable Entity`

#### Scenario: Display name too long
- **WHEN** a request includes `display_name` that exceeds 50 characters after whitespace trimming
- **THEN** the system returns `422 Unprocessable Entity`

#### Scenario: Comment body empty
- **WHEN** a request includes a `body` field that is empty after whitespace trimming
- **THEN** the system returns `422 Unprocessable Entity`

#### Scenario: Comment body exceeds 500 characters
- **WHEN** a request includes `body` longer than 500 characters after whitespace trimming
- **THEN** the system returns `422 Unprocessable Entity`

#### Scenario: Comment on non-existent product
- **WHEN** a request targets a product_id that does not exist
- **THEN** the system returns `404 Not Found`

#### Scenario: Comment on inactive product
- **WHEN** a request targets a product with is_active=0
- **THEN** the system returns `404 Not Found` (treat inactive as non-existent)

#### Scenario: Display name must contain at least one letter
- **WHEN** a request includes a display_name with no Unicode letter characters (e.g., "!!" or "123")
- **THEN** the system returns `422 Unprocessable Entity`

### Requirement: List comments for a product
The system SHALL return a paginated list of comments for a product, sorted by newest first (default) or oldest first. The `limit` parameter MUST NOT exceed 100.

#### Scenario: List comments sorted by newest
- **WHEN** a session sends `GET /v1/products/{product_id}/comments?sort=newest&page=1&limit=20`
- **THEN** the system returns comments ordered by `created_at DESC` with standard pagination response `{items, total, page, limit}`

#### Scenario: List comments sorted by oldest
- **WHEN** a session sends `GET /v1/products/{product_id}/comments?sort=oldest&page=1&limit=20`
- **THEN** the system returns comments ordered by `created_at ASC`

#### Scenario: Default sort is newest
- **WHEN** a session sends `GET /v1/products/{product_id}/comments` without a `sort` parameter
- **THEN** the system returns comments ordered by `created_at DESC`

#### Scenario: List comments for inactive product
- **WHEN** a session sends `GET /v1/products/{product_id}/comments` for a product with is_active=0
- **THEN** the system returns `404 Not Found`

#### Scenario: Invalid sort parameter
- **WHEN** a request includes a `sort` value other than "newest" or "oldest"
- **THEN** the system returns `422 Unprocessable Entity`

#### Scenario: Limit exceeds maximum
- **WHEN** a request includes `limit` greater than 100
- **THEN** the system clamps limit to 100

### Requirement: Rate limiting for comments
The system SHALL enforce rate limits to prevent spam: a maximum of 3 comments per session per product, and a maximum of 10 comments per session per hour across all products. Both limits are checked; if either is exceeded, the request is rejected.

#### Scenario: Fourth comment on same product blocked
- **WHEN** a session that already has 3 comments on a product attempts to post a fourth
- **THEN** the system returns `429 Too Many Requests` with message "Comment limit reached for this product"

#### Scenario: Eleventh comment in one hour blocked
- **WHEN** a session that has posted 10 comments in the last hour attempts to post another
- **THEN** the system returns `429 Too Many Requests` with message "Too many comments. Please try again later."

#### Scenario: Comments on different products within limit succeed
- **WHEN** a session posts 3 comments each on 3 different products (9 total, <10/hour)
- **THEN** all comments are accepted successfully

### Requirement: Input sanitization for comments
The system SHALL apply `html.escape()` to `display_name` and `body` before storage, converting `<>"'&` to HTML entities. The system SHALL reject comments whose body (after sanitization and trimming) consists solely of a URL. The system SHALL reject comments or display names containing words from a configurable blocklist (case-insensitive substring match).

Processing order: (1) trim whitespace → (2) validate length → (3) check letter in display_name (`any(c.isalpha() for c in name)`) → (4) check blocklist → (5) check URL-only → (6) html.escape() → (7) store.

#### Scenario: HTML entities escaped in body
- **WHEN** a comment body contains `<script>alert('xss')</script>Great candle`
- **THEN** the stored body is `&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;Great candle` (entities escaped, text preserved)

#### Scenario: HTML entities escaped in display_name
- **WHEN** a display_name contains `<b>Admin</b>`
- **THEN** the stored display_name is `&lt;b&gt;Admin&lt;/b&gt;`

#### Scenario: Legitimate comparison text preserved
- **WHEN** a comment body contains `I love candles < 8oz but > 4oz`
- **THEN** the stored body is `I love candles &lt; 8oz but &gt; 4oz` (no content lost)

#### Scenario: URL-only comment rejected
- **WHEN** a comment body (after sanitization and trimming) matches `^https?://\S+$`
- **THEN** the system returns `422 Unprocessable Entity` with message indicating URL-only comments are not allowed

#### Scenario: URL embedded in text is allowed
- **WHEN** a comment body is `Check out https://example.com for details`
- **THEN** the comment is accepted (URL is not the sole content)

#### Scenario: Blocklisted word rejected
- **WHEN** a comment body or display_name (lowercased) contains a substring from the blocklist
- **THEN** the system returns `422 Unprocessable Entity` with message indicating inappropriate content

### Requirement: Comments database schema
The system SHALL store comments in a `comments` table with columns: `id` (TEXT, PK, UUID4), `product_id` (TEXT, NOT NULL, FK to products ON DELETE CASCADE), `session_id` (TEXT, NOT NULL — denormalized snapshot, not a FK), `user_id` (TEXT, nullable, FK to users ON DELETE SET NULL), `display_name` (TEXT, NOT NULL), `body` (TEXT, NOT NULL), `created_at` (TEXT, datetime default).

#### Scenario: Index supports product listing queries
- **WHEN** the system queries comments by product_id ordered by created_at
- **THEN** an index on `(product_id, created_at)` ensures efficient retrieval

#### Scenario: Index supports rate limit checks
- **WHEN** the system counts comments by session_id within a time window
- **THEN** an index on `(session_id, created_at)` ensures efficient counting

#### Scenario: Product deletion cascades to comments
- **WHEN** a product is deleted from the products table
- **THEN** all comments for that product are automatically deleted via ON DELETE CASCADE

#### Scenario: User deletion nullifies user_id
- **WHEN** a user is deleted from the users table
- **THEN** comments by that user have user_id set to NULL (comment and display_name preserved)

### Requirement: Hybrid identity for comments
The system SHALL use the logged-in user's Google profile name as the default display name when users.name is not NULL. Anonymous users MUST provide a display_name explicitly. Logged-in users with NULL profile name MUST also provide a display_name. The system SHALL store `user_id` alongside the comment when the session is authenticated.

#### Scenario: Logged-in user has name auto-populated
- **WHEN** a logged-in session (with non-null users.name) posts a comment without specifying display_name
- **THEN** the system uses the user's `name` from the `users` table

#### Scenario: Anonymous user must provide display_name
- **WHEN** an anonymous session posts a comment without a display_name
- **THEN** the system returns `422 Unprocessable Entity` with message indicating display_name is required

#### Scenario: Logged-in user with NULL name must provide display_name
- **WHEN** a logged-in session with NULL users.name posts a comment without a display_name
- **THEN** the system returns `422 Unprocessable Entity` with message indicating display_name is required

### Requirement: Comment response model
The system SHALL return comments with the following fields only: `id` (comment UUID), `display_name` (string), `body` (string), `created_at` (string, ISO 8601). The response does NOT include `session_id`, `user_id`, or `product_id` (internal/redundant from request path).

#### Scenario: Comment response excludes internal fields
- **WHEN** a client receives a comment response (from create or list)
- **THEN** the response contains only `id`, `display_name`, `body`, `created_at`
