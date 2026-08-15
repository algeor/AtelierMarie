## ADDED Requirements

### Requirement: S3-compatible object storage service
The system SHALL provide a single object storage service module (`app/services/object_storage_service.py`) that owns all writes, deletes, and public-URL generation for product media objects against a Cloudflare R2 bucket via an S3-compatible client. No other module SHALL construct an R2 client or call the S3 API directly.

#### Scenario: Object uploaded with content type
- **WHEN** a caller uploads bytes for an object key (e.g. `products/{stem}.webp`) with a MIME type
- **THEN** the service performs an S3 `PutObject` to the configured bucket with that key, body, and `ContentType`, and returns the object's public URL

#### Scenario: Object deleted
- **WHEN** a caller requests deletion of an object key
- **THEN** the service performs an S3 `DeleteObject`; a missing object is treated as success (idempotent)

#### Scenario: Client constructed from config
- **WHEN** the object storage client is created
- **THEN** it uses `r2_endpoint_url`, `r2_access_key_id`, `r2_secret_access_key`, and `r2_bucket` from configuration with S3v4 signing and `region_name="auto"`

### Requirement: Public URL generation
The system SHALL generate a public HTTPS URL for each stored object by joining the configured public base URL with the object key. The DB SHALL store this full public URL (not a relative `/static/...` path) in the media URL columns.

#### Scenario: Public URL built from base and key
- **WHEN** an object with key `products/lavender-dream-300ml_ab12.webp` is stored and `r2_public_base_url` is `https://media.example.com`
- **THEN** the returned public URL is `https://media.example.com/products/lavender-dream-300ml_ab12.webp`

#### Scenario: Base URL trailing slash normalized
- **WHEN** `r2_public_base_url` is configured with a trailing slash
- **THEN** the joined URL contains exactly one slash between the base and the key

### Requirement: Object key derivation preserves existing naming scheme
The system SHALL derive object keys under a `products/` prefix using the same filename stems as the current disk scheme so that image and video variants remain grouped and predictable: `products/{product_id}_{image_id}.webp`, `..._thumb.webp`, `..._zoom.webp`, `products/{product_id}_{video_id}_video.mp4`, `..._poster.webp`.

#### Scenario: Image variant keys grouped by stem
- **WHEN** an image with stem `{product_id}_{image_id}` is stored
- **THEN** its three variants use keys `products/{stem}.webp`, `products/{stem}_thumb.webp`, and `products/{stem}_zoom.webp`

#### Scenario: Key derivation is traversal-safe
- **WHEN** an object key is derived from a `product_id`
- **THEN** the `product_id` SHALL be validated against the slug format (`^[a-z0-9][a-z0-9-]*[a-z0-9]$`) before the key is constructed, and a non-conforming id is rejected

### Requirement: Storage failures never corrupt DB state
The system SHALL upload media objects to R2 BEFORE inserting or updating the DB row that references them, and SHALL NOT record a media URL for an object that failed to upload. S3 client errors SHALL be wrapped in a service exception so callers never see raw botocore internals.

#### Scenario: Upload fails before DB write
- **WHEN** an R2 `PutObject` fails during an image upload
- **THEN** no `product_images` row is inserted for that image and the caller receives a storage error (not a 500 leaking botocore)

#### Scenario: Delete failure is non-fatal for cleanup
- **WHEN** an R2 `DeleteObject` fails while removing media for a deleted image or video
- **THEN** the DB row removal still proceeds, and the delete failure is logged (best-effort), matching the current disk-unlink behavior

### Requirement: One-time disk-to-R2 backfill
The system SHALL provide a one-time backfill script that uploads every existing on-disk product media file referenced by `/static/products/...` URLs to R2 and rewrites the corresponding DB URL columns (`product_images.image_url/thumbnail_url/zoom_url`, `product_videos.video_url/poster_url`) to their R2 public URLs. The script SHALL be idempotent, resumable, and support a dry-run mode.

#### Scenario: Existing files uploaded and URLs rewritten
- **WHEN** the backfill runs against a DB with `/static/products/...` URLs and the corresponding files on disk
- **THEN** each file is uploaded to R2 under its derived key and the DB column is updated to the R2 public URL

#### Scenario: Idempotent re-run skips already-migrated rows
- **WHEN** the backfill is run a second time
- **THEN** rows whose URLs already point at the R2 public base are skipped and no duplicate uploads occur

#### Scenario: Absolute external URLs left untouched
- **WHEN** a row already holds an absolute `http(s)://` URL that is not a `/static/...` path (e.g. a CSV-imported external image)
- **THEN** the backfill leaves that row unchanged

#### Scenario: Missing source file reported, not fatal
- **WHEN** a DB URL points at a `/static/...` path whose file is missing on disk
- **THEN** the backfill logs the missing file and continues, reporting it in the run summary without aborting

#### Scenario: Dry run makes no changes
- **WHEN** the backfill is run in dry-run mode
- **THEN** it reports the objects it would upload and rows it would rewrite, and performs no `PutObject` or DB write

### Requirement: Object storage isolation from the critical path
The object storage service SHALL be used only by the media write/delete paths (image upload, gallery management, video transcode, about-page images) and SHALL NOT be imported by cart, checkout, order, or payment code. The R2 client dependency SHALL be imported only within the object storage service module.

#### Scenario: Media serving does not run through the app
- **WHEN** a browser requests a stored media object
- **THEN** it is served directly from R2's public domain and the request never reaches the FastAPI app

#### Scenario: Checkout unaffected by storage outage
- **WHEN** R2 is unreachable
- **THEN** cart, checkout, and order flows continue to function (only new media uploads fail); no critical-path route depends on the object storage service
