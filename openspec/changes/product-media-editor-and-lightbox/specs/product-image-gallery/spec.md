## MODIFIED Requirements

### Requirement: Click-to-zoom lightbox
The product gallery SHALL provide a single, unified media lightbox that displays **all** of the product's media — every image and the video (if present) — as an ordered, navigable carousel following the gallery's existing display order (`sort_order`, primary image first). Activating any gallery item (hero or thumbnail) SHALL open the lightbox positioned on that item.

Within the lightbox:
- **Image slides** SHALL support pan and pinch/scroll zoom into detail, sourced from the high-resolution `zoom_url` derivative, falling back to `image_url` when `zoom_url` is null or absent. The zoom asset SHALL be loaded lazily — only when its slide is shown, not on initial product page load.
- The lightbox SHALL allow navigation across the entire media set (next/previous via arrow keys and swipe, and direct selection via thumbnails), so the user can move photo → video → photo without leaving the viewer.
- The lightbox SHALL be keyboard accessible: it exposes a dialog role, traps focus, and closes on Escape or backdrop interaction.

#### Scenario: Open unified media lightbox
- **WHEN** the customer activates a gallery item (hero or a thumbnail)
- **THEN** the lightbox opens positioned on that item, containing all of the product's images and video as ordered slides

#### Scenario: Pan and pinch-zoom into image detail
- **WHEN** an image slide is shown and the customer zooms in
- **THEN** the slide renders the `zoom_url` derivative and the customer can pan around the enlarged image to inspect fine detail

#### Scenario: Navigate across images and video in one flow
- **WHEN** the lightbox is open on an image slide adjacent to the video slide
- **THEN** advancing (arrow/swipe/thumbnail) moves to the video slide, and continuing advances to the next image — all within the same lightbox

#### Scenario: Zoom asset loaded lazily
- **WHEN** the product detail page first loads
- **THEN** no `zoom_url` asset is requested until its slide is displayed in the lightbox

#### Scenario: Zoom fallback when no zoom asset
- **WHEN** an image slide's `zoom_url` is null or absent
- **THEN** the slide falls back to rendering `image_url` rather than failing

#### Scenario: Lightbox is keyboard accessible
- **WHEN** the lightbox is open
- **THEN** it exposes a dialog role, traps focus, and closes on Escape or backdrop interaction
