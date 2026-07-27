## Context

Product images are uploaded by the admin, processed by `app/services/image_service.py` into two WebP derivatives (main `1200×1500` q85, thumbnail `400×500` q80), stored under `static/products/`, and recorded as a `product_images` row (`image_url`, `thumbnail_url`). The frontend gallery (`ProductGallery.tsx`) shows the main image as a hero and thumbnails as a strip, with Next.js `images.unoptimized: true`.

Two facts drive this change:

1. **Perceived softness is a resolution/serving problem, not an upload problem.** Every image is capped at 1200px wide and served as a single file to all viewports. On a 2× (retina) display a ~960px-wide CSS hero needs ~1920 device pixels; a 1200px source gets upscaled by the browser → soft. Raising the 5MB upload cap alone changes nothing about output quality.
2. **There is no zoom asset.** Customers cannot inspect fine detail. Nothing larger than 1200px is stored.

The owner's goal: photos that look **as crisp as uploaded** on the page, plus **click-to-zoom**. The project is **not live**, so no data migration or backfill is required.

## Goals / Non-Goals

**Goals:**
- Accept large source uploads (cap 5MB → 25MB).
- Store a high-resolution zoom derivative (~2400×3000 q90) per image.
- Sharpen the on-page hero (main → ~2000×2500 q88) so it's crisp on 2× displays.
- Add click-to-zoom on the product page, loading the zoom asset lazily.
- Warn the admin before uploading unusually large (15–25MB) files.

**Non-Goals:**
- Storing the byte-for-byte original file (zoom is a downscaled derivative — see Decision 2).
- Raising the 25-megapixel decompression-bomb cap (kept as a safety ceiling).
- Data migration/backfill of existing images (project not live — Decision 5).
- Switching to the Next.js image optimizer (backend pre-generates sizes — Decision 4).
- Any change to cart, checkout, orders, pricing, or auth.

## Decisions

### 1. Three derivatives: thumb / main / zoom
`process_image` currently emits main + thumb. Add a third "zoom" size. Final sizes and quality:

| Derivative | Max box | Quality | Purpose | Approx size |
|---|---|---|---|---|
| thumbnail | 400×500 | 80 | gallery strip | ~20 KB |
| main | **2000×2500** | **88** | on-page hero (retina-crisp) | ~200 KB |
| zoom | **2400×3000** | **90** | click-to-zoom lightbox | ~400–600 KB |

`thumbnail()` mode is preserved (fit within box, never upscale, aspect ratio kept), so small uploads are not upscaled to fill these boxes.

**Why bump main and also add zoom?** Main at ~2000px makes the *default* hero crisp on 2× displays without downloading the heavier zoom asset. Zoom exists only for the deliberate zoom interaction and is fetched lazily.

### 2. Zoom is a derivative, not the original (owner decision)
The zoom view loads a ~2400px q90 WebP derivative, not the uploaded file. This is visually indistinguishable at screen zoom levels, keeps bandwidth bounded and predictable, and preserves the existing EXIF-stripping / re-encode safety guarantees uniformly across all stored assets. Keeping the true original (potentially a 25MB JPEG) was considered and rejected for bandwidth and for the privacy/consistency benefit of always re-encoding.

**Trade-off:** true print-resolution download is not supported. If ever needed, add an `original_url` asset later — additive and non-breaking.

### 3. Upload cap 25MB; pixel cap unchanged (owner decision)
`MAX_FILE_SIZE` → `25 * 1024 * 1024`. Enforced in **two** backend locations that must stay in sync: `image_service.validate_image_file` and the streaming chunk guard in `app/routes/admin.py` (~line 740, which rejects mid-stream so a huge upload can't exhaust memory). Nginx `client_max_body_size` must also be raised to `25m` at deploy time (defense-in-depth; the spec documents this).

`MAX_IMAGE_PIXELS = 25_000_000` (25MP) is **left as-is**. A 2400×3000 zoom is only 7.2MP, so processing never approaches it; the cap remains a decompression-bomb guard. Consequence: a >25MP source is still rejected on pixels even under the 25MB byte cap — acceptable and intentional.

### 4. Keep `images.unoptimized: true`; serve pre-generated sizes directly
The backend already produces the discrete sizes we need, so we do not enable the Next.js optimizer. The hero `<Image>` points at the sharper main asset; the lightbox points at the zoom asset. Retina crispness comes from main now being ~2000px (larger than any realistic hero CSS size × 2), not from a runtime srcset transform.

**Alternative considered:** enable the Next optimizer + `remotePatterns`. Rejected for now — adds a runtime image server dependency for no gain over pre-sized assets on a single-VPS deploy.

### 5. No migration — add `zoom_url` to the fresh schema directly
The project is not live and `product_images` holds no production data. Add `zoom_url TEXT` to the `CREATE TABLE product_images` definition in `app/database.py` directly. **No** `products_new`-style rebuild, no `select_exprs` backfill, no legacy `_legacy_thumbnail_url` path for zoom. (Contrast with the `products` table's four-edit rebuild dance — not applicable here because there's no data to preserve.)

`zoom_url` is `TEXT` (nullable at the DB level for forward-safety), but every newly processed image writes all three URLs, so in practice it's always populated for images created after this change.

### 6. Frontend zoom UX: lazy lightbox
Clicking the hero opens an accessible lightbox (dialog role, focus trap, Esc to close, backdrop click to dismiss) that loads the `zoom_url` image. The zoom asset is **not** requested until the lightbox opens, so the product page's initial payload is unaffected. Falls back to the main image if `zoom_url` is null.

### 7. Admin soft-warning at 15MB, hard block at 25MB (owner decision)
Client-side, on file select in the admin upload UI:

```
size < 15MB        → proceed silently
15MB ≤ size ≤ 25MB → confirm dialog: "This image is large (N MB). Large files
                     slow your store. Add it anyway?"  [Cancel] [Add anyway]
size > 25MB        → block with inline error "Maximum image size is 25 MB"
```

The 15MB threshold is advisory only (proceed on confirm); 25MB is the hard client stop. The backend independently hard-rejects >25MB regardless of the UI, so the client checks are UX, not security.

## Risks / Open Questions

- **Storage growth:** three derivatives per image instead of two, and larger main/zoom. For a small candle catalog this is negligible (low hundreds of KB per image).
- **Zoom dimension tuning:** 2400×3000 is a starting point; if zoom still feels soft on very large monitors it can be raised toward the 25MP pixel ceiling (e.g. 3000×3750 = 11.25MP) without other changes.
- **Nginx config lives outside the repo** — the deploy step to raise `client_max_body_size` must not be forgotten, or 25MB uploads 413 at the proxy before reaching FastAPI.
