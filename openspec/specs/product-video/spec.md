# product-video Specification

## Purpose
TBD - created by archiving change add-product-video. Update Purpose after archive.
## Requirements
### Requirement: One transcoded video per product
The system SHALL support at most one video per product. The `product_videos` store SHALL enforce uniqueness per `product_id`. Every uploaded video SHALL be transcoded to a normalized MP4 (H.264 High profile, `yuv420p` pixel format, `+faststart`, capped at 1080p, AAC audio retained) before being served; the system SHALL NOT serve the raw uploaded file.

#### Scenario: Upload a valid video
- **WHEN** the owner uploads a 20-second 1080p MP4 for a product with no existing video
- **THEN** the original is stored, a `product_videos` row is created with status `queued`, and the request returns `202` with a `processing` status

#### Scenario: Second upload replaces, never duplicates
- **WHEN** the owner uploads a video for a product that already has a `ready` or `failed` video
- **THEN** the existing video is replaced (the product still has exactly one video)
- **AND** the store never holds two video rows for one product
- **AND** the replaced video's output files are removed from disk

#### Scenario: Upload rejected while processing
- **WHEN** the owner uploads a video for a product whose video is `queued` or `transcoding`
- **THEN** the request is rejected with `409 Conflict` (`video is still processing`)
- **AND** the in-flight transcode is left untouched

#### Scenario: Served video is the normalized output
- **WHEN** a video reaches status `ready`
- **THEN** `video_url` points to the transcoded normalized MP4, not the uploaded source
- **AND** the uploaded source file has been deleted

### Requirement: Duration and format validated before queuing
The upload request SHALL validate the source with `ffprobe` before queuing any transcode. A video whose duration exceeds 30 seconds, whose codec is unsupported, or which is unreadable SHALL be rejected synchronously with HTTP `422` and a human-readable reason; no transcode job is queued for it.

#### Scenario: Video too long is rejected instantly
- **WHEN** the owner uploads a 42-second video
- **THEN** the request returns `422` with reason `duration 42s exceeds 30s limit`
- **AND** no `product_videos` row is created

#### Scenario: Corrupted upload is rejected instantly
- **WHEN** the owner uploads a file that ffprobe cannot read as video
- **THEN** the request returns `422` with reason `file corrupted or unreadable`
- **AND** no transcode job is queued

#### Scenario: Oversized upload is rejected
- **WHEN** the owner uploads a source file larger than the configured maximum
- **THEN** the request returns `422` (or `413`) with a size-limit reason and nothing is queued

### Requirement: Asynchronous fail-fast transcode pipeline
Transcoding SHALL run asynchronously in a background sweeper, not in the upload request. The lifecycle SHALL be `queued → transcoding → ready | failed`. On any transcode error the video SHALL move to status `failed` with a detailed `failure_reason`; the system SHALL NOT automatically retry. The owner re-uploads to try again.

#### Scenario: Successful transcode
- **WHEN** the sweeper processes a `queued` video successfully
- **THEN** its status becomes `ready`, `video_url` and `poster_url` are populated, and the source original is deleted

#### Scenario: Transcode failure surfaces a reason
- **WHEN** ffmpeg exits non-zero while transcoding a video
- **THEN** the video's status becomes `failed` with a `failure_reason` describing the failure
- **AND** the video is NOT retried automatically

#### Scenario: Crash mid-transcode is recovered as failed
- **WHEN** the server restarts while a video is in status `transcoding` and its lease has expired
- **THEN** the next sweep marks it `failed` with reason `processing interrupted`
- **AND** it is not retried automatically

### Requirement: Transcoding must not starve the store
Transcoding SHALL NOT degrade Layer 1 request latency below its budget. At most one transcode SHALL run at a time. The ffmpeg process SHALL run off the event loop (as a subprocess) and SHALL be de-prioritized for CPU and IO (`nice`/`ionice`) so store requests take precedence. A transcode failure SHALL never cause a store request to error.

#### Scenario: Only one transcode at a time
- **WHEN** two videos are `queued` and a sweep runs
- **THEN** only one is moved to `transcoding` per the concurrency limit; the other waits

#### Scenario: Store stays responsive during transcode
- **WHEN** a transcode is running
- **THEN** product, cart, and checkout requests continue to serve within the Layer 1 latency budget

### Requirement: Missing ffmpeg degrades gracefully
When `ffmpeg`/`ffprobe` are not available on the host, video upload SHALL be rejected with a clear operator-facing message, and all non-video functionality SHALL continue to work unaffected.

#### Scenario: Upload without ffmpeg installed
- **WHEN** the owner attempts to upload a video on a host without ffmpeg
- **THEN** the request is rejected with a message indicating video processing is unavailable
- **AND** browsing products, cart, and checkout are unaffected

### Requirement: Public product exposes a ready video only
The public product API SHALL include a `video` object only when the product has a video in status `ready`. The object SHALL include the video URL, poster URL, `sort_order` (its position among gallery images), and duration. Products with no video, or a video still `queued`/`transcoding`/`failed`, SHALL omit the `video` object (or return it null).

#### Scenario: Product with a ready video
- **WHEN** a public client GETs a product whose video is `ready`
- **THEN** the response includes a `video` object with the normalized MP4 URL, poster URL, sort_order, and duration

#### Scenario: Product with a processing video hides it publicly
- **WHEN** a public client GETs a product whose video is `queued` or `transcoding`
- **THEN** the response omits the `video` object

#### Scenario: Product with no video
- **WHEN** a public client GETs a product that has never had a video
- **THEN** the response omits the `video` object

### Requirement: Video plays inline muted and enlarges with sound
On the product detail gallery, the video slide SHALL autoplay muted and loop inline (`playsinline`), positioned among the images by `sort_order`. Clicking it SHALL enlarge it **into the shared unified media lightbox** (the same viewer used for images), where it plays with sound and native controls and is navigable to and from the adjacent image slides. The product grid/listing SHALL show only the poster still and SHALL NOT autoplay. Autoplay SHALL be suppressed (poster shown) when the user prefers reduced motion or the browser blocks autoplay.

The standalone video-only lightbox (`VideoLightbox`) is retired; video enlargement is served by the unified lightbox defined in the `product-image-gallery` capability.

#### Scenario: Inline autoplay on detail page
- **WHEN** a visitor opens a product detail page whose video is `ready`
- **THEN** the video slide autoplays muted and loops inline at its gallery position

#### Scenario: Click to enlarge with sound in the unified lightbox
- **WHEN** the visitor clicks the inline video
- **THEN** the unified media lightbox opens on the video slide and it plays with sound and controls

#### Scenario: Navigate from the enlarged video to adjacent images
- **WHEN** the video slide is shown in the unified lightbox
- **THEN** advancing or going back (arrow/swipe/thumbnail) moves to the adjacent image slides without closing the viewer

#### Scenario: Grid shows poster only
- **WHEN** a product with a video appears in the product grid
- **THEN** only the poster still is shown and no video autoplays

#### Scenario: Reduced motion shows poster
- **WHEN** a visitor with `prefers-reduced-motion` opens a product detail page
- **THEN** the poster still is shown instead of autoplaying video

### Requirement: Video slot position is unambiguous
The video's `sort_order` SHALL be interpreted as an insertion index into the image sequence (images sorted by their own `sort_order`). The video slide SHALL be inserted at that index (0 = before the first image; a value ≥ the image count = after the last). When the index collides with an image position, the video SHALL sort before that image. The resulting gallery order SHALL be deterministic.

#### Scenario: Video inserted between images
- **WHEN** a product has 4 images and a video with `sort_order` = 2
- **THEN** the detail gallery renders image, image, video, image, image in that order

#### Scenario: Video after all images
- **WHEN** a product has 3 images and a video with `sort_order` = 10
- **THEN** the video renders as the last slide

### Requirement: Video files are removed on delete and product delete
When a video is deleted, replaced, or its product is deleted, the system SHALL remove the transcoded MP4, the poster, and any temp original from disk. File removal SHALL be best-effort (a failure is logged, not fatal) and SHALL NOT rely solely on database cascade, which removes only the row.

#### Scenario: Deleting a video unlinks its files
- **WHEN** a `ready` video is deleted
- **THEN** its MP4 and poster files are removed from `/static`

#### Scenario: Deleting a product removes its video files
- **WHEN** a product with a `ready` video is deleted
- **THEN** the `product_videos` row is removed (cascade) AND its MP4 and poster files are unlinked from disk

