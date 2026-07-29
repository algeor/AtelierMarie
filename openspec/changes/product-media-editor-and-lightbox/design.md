# Design — Product Media Editor & Unified Lightbox

## Context

Two concerns, one change, because they share the same surfaces (`ProductForm`, `ProductGallery`, `image_service`) and the same goal: give the owner control over how product media looks:

- **Admin side:** frame photos before they're stored (the storefront's `object-cover 4/5` crop is unforgiving and the admin currently has zero control over it).
- **Storefront side:** let shoppers inspect detail (pan/pinch) and move through all media — photos and video — in one viewer.

The guiding decision from exploration: **use standard, maintained, MIT libraries instead of hand-writing crop math or a media carousel.**

## Decision 1 — Bake framing into pixels (not store framing metadata)

**Chosen:** the admin editor exports a transformed image; that becomes the stored file.

**Rejected:** storing focal-point / rotation / zoom metadata per image and applying it via CSS at every render site.

| | Bake in (chosen) | Framing metadata |
|---|---|---|
| Storefront changes | none — image is pre-framed | every `<Image>` must honor position/rotation/zoom |
| Schema | none | new columns + serialization + mock/types |
| Re-edit original later | re-upload | tweak anytime |
| Correct on OG images / future consumers | automatically | only where re-applied |
| Surfaces that can drift out of sync | 0 | card, gallery, thumb, zoom, … |

For a single-photographer candle shop that frames a shot once, the metadata system is over-engineering and a standing source of "looks right on the card, wrong in the gallery" bugs. Baking in is simpler and self-contained in the admin panel — matching the owner's ask ("in the admin panel"). The one cost — losing the un-cropped original — is accepted; a future change can add "keep original for re-edit" if that workflow ever emerges.

## Decision 2 — `react-easy-crop` for the editor

The standard React crop/rotate/zoom control. MIT, tiny, headless-ish (styled with our Tailwind), exposes exactly crop area + rotation + zoom. Aspect **locked to `4/5`** so the editor preview *is* the storefront card — no post-upload surprise from `object-cover`.

Output path:

```
select file → <Cropper aspect={4/5} rotation zoom> → onCropComplete(croppedAreaPixels)
           → getCroppedImg(file, croppedAreaPixels, rotation)  [canvas helper, ~40 lines from docs]
           → Blob (image/jpeg) → existing image_files upload flow → backend pipeline
```

`getCroppedImg` is copy-paste-from-docs canvas work, not designed logic. The exported blob re-enters the **existing** validated upload path (type/size checks, 6-image limit, soft-warning). Because it's a fresh JPEG from a canvas, it carries **no EXIF** — which is fine; the backend orientation fix (below) handles files that *do*, and the manual rotate handles intent.

**Interaction with the 25MB cap:** a canvas re-encode of a framed crop is smaller than the original, so the cap is never the binding constraint here.

## Decision 3 — Fix EXIF orientation at the source

`process_image` currently strips metadata but never rotates pixels. Add, as the **first** step after decode:

```python
from PIL import ImageOps
img = ImageOps.exif_transpose(img)   # upright the pixels, then continue as today
```

This is a genuine bug fix (portrait phone photos currently save sideways), independent of the editor. Metadata is still stripped on WebP save, so the `image-upload` "EXIF metadata stripped" guarantee holds — the pixels are just correct now. The admin's manual rotate composes on top (user intent overrides/augments auto-orientation).

## Decision 4 — Quality bump (the real quality lever)

Input file size was never the quality constraint — output dimensions + WebP quality are. Concrete new values:

| Derivative | Before | After | Rationale |
|---|---|---|---|
| thumbnail | 400×500 q80 | unchanged | grid thumb, already fine |
| main | 2000×2500 q88 | 2000×2500 **q92** | crisper hero, negligible size cost |
| zoom | 2400×3000 q90 | **3000×3750 q95** | more pixels to pan into (wax texture, label) |

`3000×3750 = 11.25 MP` < `MAX_IMAGE_PIXELS` (25 MP) — safety ceiling untouched. `MAX_FILE_SIZE` (25MB input) untouched.

## Decision 5 — `yet-another-react-lightbox` as the single media viewer

**Chosen:** YARL with the **Zoom**, **Video**, and **Thumbnails** plugins, fed by the gallery's existing ordered `galleryItems[]`.

**Rejected:**
- **Keep the two custom modals** — they can't pan/pinch and can't page image↔video in one flow (the owner's explicit ask).
- **PhotoSwipe** — excellent for images, but video is DIY; unifying media is the whole point here.
- **Rip out the whole gallery for a library** — the thumbnail strip / selection / reduced-motion / i18n already work; only the *lightbox* needs replacing.

Why it fits both asks at once: it's the one standard viewer that does **pan/pinch zoom on images AND native video slides in one ordered carousel**. Net effect is a **code reduction** — it retires the custom zoom modal *and* `VideoLightbox.tsx`.

### Data mapping (no new backend data needed)

`galleryItems[]` is already an ordered mix of images and the video by `sort_order`:

```
{ kind: "image", zoom_url, image_url }  →  { type: "image", src: zoom_url ?? image_url }
{ kind: "video", video_url, poster_url } →  { type: "video", poster, sources: [{src: video_url, type}] }
```

Slide order = gallery order, so the admin's arrangement (primary first, video position) flows straight through. Opening the lightbox from any item sets YARL's initial `index`.

### Porting the existing lightbox guarantees into YARL

The custom modals provided: dialog role, focus trap, Esc/backdrop close, lazy zoom asset, reduced-motion (poster instead of autoplay), i18n labels. YARL supplies focus/keyboard/close natively; we map the rest onto its API:

- **Lazy zoom:** YARL only requests a slide's `src` when navigated to, preserving the "not fetched on page load" guarantee.
- **Fallback:** image slide `src = zoom_url ?? image_url`.
- **Reduced motion:** inline gallery autoplay behavior is unchanged (still handled in `ProductGallery`); the lightbox video uses controls, not autoplay-with-sound-on-open, respecting the existing pattern.
- **i18n:** pass localized `labels` to YARL; add editor + lightbox strings to `en.json` / `bg.json`.
- **Theme:** override YARL CSS variables to the luxury palette (charcoal backdrop, warm-ivory controls) to match the retired modals.

## Risks & Mitigations

- **YARL theming drift from luxury palette** → pin CSS-variable overrides in a small wrapper; visually verify against the retired modal's look.
- **Video autoplay/controls quirks across browsers** → rely on YARL Video plugin `playsInline`/`controls`; keep inline (non-lightbox) autoplay logic exactly as the video change shipped it.
- **Canvas export color/orientation surprises** → editor works on the browser-decoded (already display-oriented) image, and the backend `exif_transpose` is the safety net for any non-editor path.
- **Two unarchived changes touch the same files** → this proposal explicitly modifies their requirements (see Related Changes); merge, don't overwrite, `ProductGallery.tsx`.

## Out of Scope

- Storing/keeping the original un-cropped upload for later re-editing.
- Framing metadata / non-destructive re-crop.
- Filters, annotations, watermarking (Filerobot-style) — not needed.
- Any change to video transcoding, upload caps, or the product API contract.
