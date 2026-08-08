## MODIFIED Requirements

### Requirement: Image management endpoints
The system SHALL provide admin-authenticated endpoints to append, delete, reorder, and set the primary of a product's images. All SHALL require admin auth and validate the product exists. Media objects are stored in and served from R2; delete issues an R2 `DeleteObject` for each variant.

#### Scenario: Append image
- **WHEN** an admin `POST`s a valid image to `/v1/admin/products/{id}/images`
- **THEN** the image is processed, its variants uploaded to R2, and it is returned, becoming primary if it is the product's first

#### Scenario: Delete image
- **WHEN** an admin `DELETE`s `/v1/admin/products/{id}/images/{image_id}`
- **THEN** the row is removed, its main/thumbnail/zoom objects are deleted from R2 (best-effort), and primary is promoted if needed

#### Scenario: Reorder images
- **WHEN** an admin `PATCH`es `/v1/admin/products/{id}/images/reorder` with an ordered list of image ids
- **THEN** each image's `sort_order` is updated to match, without changing which image is primary

#### Scenario: Set primary
- **WHEN** an admin `PATCH`es `/v1/admin/products/{id}/images/{image_id}/primary`
- **THEN** that image becomes the sole primary for the product

#### Scenario: Non-admin rejected
- **WHEN** a non-admin calls any image-management endpoint
- **THEN** the request is rejected with 401/403

## ADDED Requirements

### Requirement: Orphaned image objects removed when a product is deactivated
The system SHALL delete a product's image objects from R2 when the product is deactivated (soft-deleted), closing the pre-existing gap where deactivating a product left its image files in storage. Object deletion SHALL be best-effort (failures logged, not fatal) and SHALL mirror the video-cleanup behavior already invoked on deactivation.

#### Scenario: Deactivation removes image objects
- **WHEN** an admin deactivates a product that has gallery images
- **THEN** each image's main/thumbnail/zoom object is deleted from R2 (best-effort) in addition to the existing video cleanup

#### Scenario: Deactivation succeeds despite storage errors
- **WHEN** an R2 delete fails during product deactivation
- **THEN** the product is still deactivated and the failure is logged
