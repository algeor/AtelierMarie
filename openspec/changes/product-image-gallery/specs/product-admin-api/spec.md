## ADDED Requirements

### Requirement: Admin product response exposes the image gallery
The admin product response SHALL include the ordered `images` array (id, image_url, thumbnail_url, sort_order, is_primary) and `primary_image_url`, replacing the single `image_url` field, so the admin UI can manage the gallery.

#### Scenario: Admin detail includes images
- **WHEN** an admin fetches a product via the admin endpoint
- **THEN** the response includes the ordered `images` array with the primary flagged
