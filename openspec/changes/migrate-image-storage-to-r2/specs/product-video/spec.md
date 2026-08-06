## MODIFIED Requirements

### Requirement: Video files are removed on delete and product delete
When a video is deleted, replaced, or its product is deleted, the system SHALL remove the transcoded MP4 and the poster from R2, and remove any raw temp original from the local video-temp directory. Object/file removal SHALL be best-effort (a failure is logged, not fatal) and SHALL NOT rely solely on database cascade, which removes only the row.

#### Scenario: Deleting a video removes its objects
- **WHEN** a `ready` video is deleted
- **THEN** its MP4 and poster objects are deleted from R2 and any temp original is unlinked from the local video-temp directory

#### Scenario: Deleting a product removes its video objects
- **WHEN** a product with a `ready` video is deleted or deactivated
- **THEN** the `product_videos` row is removed (cascade/explicit) AND its MP4 and poster objects are deleted from R2

## ADDED Requirements

### Requirement: Transcoded video and poster stored in R2
The transcode pipeline SHALL, on successful transcode, upload the transcoded MP4 (`ContentType: video/mp4`) and the extracted WebP poster (`ContentType: image/webp`) to R2 under keys `products/{product_id}_{video_id}_video.mp4` and `products/{product_id}_{video_id}_poster.webp`, then set the row's `video_url` and `poster_url` to the R2 public URLs and null `source_path`. Raw uploads SHALL continue to stage locally under `video_upload_temp_path` for ffmpeg; only the transcoded outputs are stored in R2.

#### Scenario: Ready video records R2 URLs
- **WHEN** a queued video is successfully transcoded
- **THEN** the MP4 and poster are uploaded to R2 and the row transitions to `ready` with `video_url` and `poster_url` set to R2 public URLs and `source_path` nulled

#### Scenario: Raw upload staged locally, not in R2
- **WHEN** a video is uploaded and queued
- **THEN** the raw file is written to the local `video_upload_temp_path` and no object is written to R2 until transcode succeeds

#### Scenario: Upload failure leaves the video not ready
- **WHEN** the R2 upload of a transcoded MP4 or poster fails
- **THEN** the video does not transition to `ready`, no R2 URLs are recorded, and the failure is handled by the existing fail/retry path (temp/output artifacts cleaned up on failure)

#### Scenario: Poster fallback still applies
- **WHEN** poster extraction fails and a primary product image exists
- **THEN** the existing fallback sets `poster_url` to the product's primary thumbnail (already an R2 public URL after migration), unchanged by this migration
