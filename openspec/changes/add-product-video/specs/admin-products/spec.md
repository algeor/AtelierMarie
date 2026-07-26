## ADDED Requirements

### Requirement: Admin can manage a product's video
Admin product management SHALL allow uploading, replacing, and deleting a single product video, and SHALL display its processing status and any failure reason. The upload endpoint SHALL require admin authorization. Uploading a video for a product that already has one SHALL replace the existing video.

#### Scenario: Admin uploads a video
- **WHEN** an authorized admin uploads a valid video for a product
- **THEN** the video is accepted for processing and the admin view shows status `processing`

#### Scenario: Admin sees a failure reason
- **WHEN** a product's video is in status `failed`
- **THEN** the admin product view shows the human-readable `failure_reason`
- **AND** offers a re-upload action

#### Scenario: Admin deletes a video
- **WHEN** an authorized admin deletes a product's video
- **THEN** the video row and its output files are removed and the product has no video

#### Scenario: Non-admin cannot upload
- **WHEN** an unauthenticated or non-admin caller attempts to upload a product video
- **THEN** the request is rejected with `401`/`403`

### Requirement: Admin controls the video's gallery position
Admin SHALL be able to set the video's `sort_order` so it appears at a chosen position among the product's gallery images. The image gallery ordering (`product_images`) is unaffected by this control.

#### Scenario: Admin positions the video in the gallery
- **WHEN** an admin sets the video's `sort_order`
- **THEN** the public product's `video.sort_order` reflects the new position
- **AND** the detail-page gallery renders the video slide at that position among the images
