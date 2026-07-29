## MODIFIED Requirements

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
