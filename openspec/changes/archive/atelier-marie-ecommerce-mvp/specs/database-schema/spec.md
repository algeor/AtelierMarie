## ADDED Requirements

### Requirement: SQLite users table
The system SHALL maintain a users table with columns: id (INTEGER PRIMARY KEY AUTOINCREMENT), google_id (TEXT UNIQUE NOT NULL), email (TEXT NOT NULL), name (TEXT NOT NULL), avatar_url (TEXT), is_admin (BOOLEAN DEFAULT FALSE), created_at (TIMESTAMP DEFAULT CURRENT_TIMESTAMP).

#### Scenario: User created on Google sign-in
- **WHEN** a new Google user authenticates
- **THEN** a record is inserted with google_id, email, name, avatar_url from the Google profile

#### Scenario: Duplicate google_id rejected
- **WHEN** a user with the same google_id already exists
- **THEN** the existing record is returned (upsert behavior), no duplicate created

### Requirement: SQLite products table
The system SHALL maintain a products table with columns: id (INTEGER PRIMARY KEY AUTOINCREMENT), name (TEXT NOT NULL), slug (TEXT UNIQUE NOT NULL), description (TEXT), price (REAL NOT NULL), category (TEXT NOT NULL), scent (TEXT), wax_type (TEXT), burn_time (TEXT), stock_quantity (INTEGER NOT NULL DEFAULT 0), image_url (TEXT), created_at (TIMESTAMP DEFAULT CURRENT_TIMESTAMP).

#### Scenario: Slug uniqueness enforced
- **WHEN** an admin creates a product with a slug that already exists
- **THEN** the system appends a numeric suffix to ensure uniqueness (e.g., "vanilla-dream-2")

### Requirement: SQLite orders table
The system SHALL maintain an orders table with columns: id (INTEGER PRIMARY KEY AUTOINCREMENT), user_id (INTEGER NULLABLE REFERENCES users), session_id (TEXT NOT NULL), total_price (REAL NOT NULL), status (TEXT NOT NULL DEFAULT 'pending'), created_at (TIMESTAMP DEFAULT CURRENT_TIMESTAMP).

#### Scenario: Anonymous order has null user_id
- **WHEN** an unauthenticated user checks out
- **THEN** the order is created with user_id NULL and session_id populated

#### Scenario: Authenticated order has user_id
- **WHEN** an authenticated user checks out
- **THEN** the order is created with both user_id and session_id populated

### Requirement: SQLite order_items table
The system SHALL maintain an order_items table with columns: id (INTEGER PRIMARY KEY AUTOINCREMENT), order_id (INTEGER NOT NULL REFERENCES orders), product_id (INTEGER NOT NULL REFERENCES products), quantity (INTEGER NOT NULL), price (REAL NOT NULL).

#### Scenario: Order items capture price at time of purchase
- **WHEN** an order is created
- **THEN** order_items.price reflects the product price at checkout time (not a live reference)

### Requirement: SQLite session_identity table
The system SHALL maintain a session_identity table with columns: session_id (TEXT PRIMARY KEY), user_id (INTEGER NULLABLE REFERENCES users), first_seen (TIMESTAMP DEFAULT CURRENT_TIMESTAMP), last_seen (TIMESTAMP DEFAULT CURRENT_TIMESTAMP).

#### Scenario: New session recorded
- **WHEN** a session_start event is received for a new session_id
- **THEN** a session_identity record is created with user_id NULL

#### Scenario: Session linked to user on login
- **WHEN** a user authenticates and their session_id exists in session_identity
- **THEN** the user_id field is updated to the authenticated user's ID

#### Scenario: last_seen updated on activity
- **WHEN** any event is received for an existing session_id
- **THEN** the last_seen timestamp is updated

### Requirement: DuckDB events table
The system SHALL maintain a DuckDB events table with columns: event_id (UUID), session_id (VARCHAR NOT NULL), user_id (INTEGER), event_type (VARCHAR NOT NULL), product_id (INTEGER), metadata (JSON), timestamp (TIMESTAMP NOT NULL).

#### Scenario: Event with full metadata stored
- **WHEN** an add_to_cart event is ingested with metadata {"quantity": 2, "source": "product_page"}
- **THEN** the event is stored with all fields including the JSON metadata

#### Scenario: Analytical query on events
- **WHEN** querying "top 10 products by view count in last 7 days"
- **THEN** DuckDB returns results efficiently using columnar aggregation

### Requirement: SQLite WAL mode enabled
The system SHALL configure SQLite in WAL (Write-Ahead Logging) mode to support concurrent reads during writes without blocking.

#### Scenario: Concurrent reads not blocked by writes
- **WHEN** a write operation is in progress on SQLite
- **THEN** read operations complete without waiting for the write to finish

### Requirement: Database migrations
The system SHALL include migration scripts that create all tables on first run. Migrations SHALL be idempotent (safe to run multiple times).

#### Scenario: Fresh database initialized
- **WHEN** the application starts with no existing database files
- **THEN** all SQLite and DuckDB tables are created automatically

#### Scenario: Re-running migration is safe
- **WHEN** migrations are run on an existing database
- **THEN** no errors occur and no data is lost (CREATE TABLE IF NOT EXISTS)
