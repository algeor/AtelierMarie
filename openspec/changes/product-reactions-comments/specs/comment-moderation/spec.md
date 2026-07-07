## ADDED Requirements

### Requirement: Admin can delete any comment
The system SHALL allow authenticated admin users to delete any comment by ID. Deletion is a hard delete (row removed from database). No "[deleted]" placeholder remains.

#### Scenario: Admin deletes a comment
- **WHEN** an admin sends `DELETE /v1/admin/comments/{comment_id}`
- **THEN** the system removes the comment from the database and returns `204 No Content`

#### Scenario: Non-admin attempts to delete a comment
- **WHEN** a non-admin session sends `DELETE /v1/admin/comments/{comment_id}`
- **THEN** the system returns `403 Forbidden`

#### Scenario: Delete non-existent comment
- **WHEN** an admin sends `DELETE /v1/admin/comments/{comment_id}` for an ID that does not exist
- **THEN** the system returns `404 Not Found`

#### Scenario: Unauthenticated user attempts to delete
- **WHEN** an unauthenticated request (no admin JWT or API key) sends `DELETE /v1/admin/comments/{comment_id}`
- **THEN** the system returns `401 Unauthorized`

### Requirement: Admin can list all comments with moderation context
The system SHALL provide an admin endpoint to list all comments across products, sorted by newest first, with product context for moderation review. The `limit` parameter MUST NOT exceed 100. The endpoint JOINs comments with products to include product_name (always available since comments cascade-delete with products).

#### Scenario: Admin lists all comments
- **WHEN** an admin sends `GET /v1/admin/comments?page=1&limit=50`
- **THEN** the system returns a paginated list of all comments including `id`, `product_id`, `product_name`, `display_name`, `body`, `created_at`, sorted by newest first

#### Scenario: Admin filters comments by product
- **WHEN** an admin sends `GET /v1/admin/comments?product_id={product_id}`
- **THEN** the system returns only comments for that product

#### Scenario: Non-admin cannot access admin comments list
- **WHEN** a non-admin session sends `GET /v1/admin/comments`
- **THEN** the system returns `403 Forbidden`

#### Scenario: Limit exceeds maximum
- **WHEN** an admin sends `GET /v1/admin/comments?limit=500`
- **THEN** the system clamps limit to 100
