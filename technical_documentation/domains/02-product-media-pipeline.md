# Product Media Pipeline

Product media includes image galleries and optional video.

## What It Does

- Admin uploads product images.
- Backend validates and converts images.
- Product has gallery ordering and one primary image.
- Public storefront uses image derivatives.
- Admin can crop/rotate/zoom before upload.
- Admin can upload one product video.
- Backend transcodes video in background.

## Main Backend Files

- `app/services/image_service.py`: image validation and WebP derivatives.
- `app/services/product_image_service.py`: image DB rows, primary image, ordering, delete.
- `app/services/video_service.py`: ffprobe, ffmpeg, poster extraction.
- `app/services/product_video_service.py`: video queue and state machine.
- `app/routes/admin.py`: image/video admin endpoints.
- `app/models/products.py`: `ProductImage` and `ProductVideo` response models.

## Main Frontend Files

- `frontend/components/products/ProductGallery.tsx`
- `frontend/components/products/ProductImage.tsx`
- `frontend/components/products/ProductCard.tsx`
- `frontend/components/admin/ProductForm.tsx`
- `frontend/components/admin/ImageCropEditor.tsx`
- `frontend/lib/cropImage.ts`
- `frontend/lib/media.ts`

## Image Upload Flow

```text
Admin selects/crops image
  -> ProductForm posts multipart FormData
  -> admin image endpoint reads file with limit
  -> image_service validates type/size/product id
  -> image is orientation-fixed, resized, WebP-converted
  -> thumbnail and zoom derivatives are written
  -> product_images row inserted
  -> primary image is set if first image
```

## Image Rules

- Store URLs, not binary blobs, in Postgres.
- Exactly one primary image per product.
- Thumbnail is for cards/lists.
- Zoom URL is for crisp lightbox/detail inspection.
- Upload processing strips/normalizes unsafe image details.
- Delete should remove DB row and attempt file cleanup.
- Reorder changes `sort_order` only.

## Video Upload Flow

```text
Admin uploads video
  -> admin video endpoint streams to temp path with limit
  -> product_video_service queues row status=queued
  -> video_transcode_loop claims queued row
  -> video_service validates with ffprobe
  -> ffmpeg transcodes output
  -> poster is extracted
  -> row becomes ready or failed
```

## Video States

- `queued`: uploaded and waiting.
- `transcoding`: worker owns current attempt.
- `ready`: public video URL/poster ready.
- `failed`: validation/transcode failed.

## Important Safety Rule

Raw video temp path must not be inside public static path. Startup checks this.

## Failure Behavior

- Bad image upload returns validation error.
- Video failure becomes `failed` with reason.
- Public product page should still render if media is missing or failed.
- Admin can delete/retry by replacing media.

## Safe Change Checklist

- Gallery still has one primary image.
- Product card uses primary thumbnail/image.
- Detail page handles empty gallery.
- Video transcode failure does not break product response.
- Upload size/type limits still apply.
- Static URLs resolve correctly in mock and real modes.

