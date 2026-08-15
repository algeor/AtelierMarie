"use client";

import { useEffect, useMemo, useState } from "react";
import Image from "next/image";
import { useTranslations } from "next-intl";
import Lightbox, { type Slide } from "yet-another-react-lightbox";
import Zoom from "yet-another-react-lightbox/plugins/zoom";
import Video from "yet-another-react-lightbox/plugins/video";
import Thumbnails from "yet-another-react-lightbox/plugins/thumbnails";
import "yet-another-react-lightbox/styles.css";
import "yet-another-react-lightbox/plugins/thumbnails.css";
import { resolveMediaUrl } from "@/lib/media";
import { cn } from "@/lib/utils";
import type {
  ProductImage as ProductImageModel,
  ProductVideo,
} from "@/lib/types";
import { ProductImage } from "./ProductImage";

interface ProductGalleryProps {
  name: string;
  images: ProductImageModel[];
  video?: ProductVideo | null;
  primaryImageUrl: string | null;
}

type GalleryItem =
  | { kind: "image"; id: string; image: ProductImageModel }
  | { kind: "video"; id: string; video: ProductVideo };

function GalleryThumbnail({
  label,
  imageUrl,
}: {
  label: string;
  imageUrl: string | null;
}) {
  const [hasError, setHasError] = useState(false);

  if (!imageUrl || hasError) {
    return (
      <span
        aria-hidden="true"
        className="flex h-full w-full items-center justify-center bg-brand-gradient px-2 text-center font-heading text-xs text-charcoal/80"
      >
        {label}
      </span>
    );
  }

  return (
    <Image
      src={imageUrl}
      alt=""
      fill
      sizes="96px"
      className="object-cover"
      onError={() => setHasError(true)}
    />
  );
}

export function ProductGallery({
  name,
  images,
  video,
  primaryImageUrl,
}: ProductGalleryProps) {
  const t = useTranslations("products");
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  // -1 = lightbox closed; otherwise the open slide index.
  const [lightboxIndex, setLightboxIndex] = useState(-1);

  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    setPrefersReducedMotion(query.matches);
    function handleChange(event: MediaQueryListEvent) {
      setPrefersReducedMotion(event.matches);
    }
    query.addEventListener("change", handleChange);
    return () => query.removeEventListener("change", handleChange);
  }, []);

  const orderedImages = useMemo(
    () => [...images].sort((a, b) => a.sort_order - b.sort_order),
    [images],
  );

  const galleryItems = useMemo<GalleryItem[]>(() => {
    const items: GalleryItem[] = orderedImages.map((image) => ({
      kind: "image",
      id: image.id,
      image,
    }));
    if (video?.status === "ready" && video.video_url) {
      const insertionIndex = Math.min(
        Math.max(video.sort_order, 0),
        items.length,
      );
      items.splice(insertionIndex, 0, {
        kind: "video",
        id: `video-${video.id}`,
        video,
      });
    }
    return items;
  }, [orderedImages, video]);

  const initialItemId =
    galleryItems.find(
      (item) =>
        item.kind === "image" && item.image.image_url === primaryImageUrl,
    )?.id ??
    galleryItems[0]?.id ??
    null;

  useEffect(() => {
    if (!selectedItemId && initialItemId) {
      setSelectedItemId(initialItemId);
      return;
    }
    if (
      selectedItemId &&
      !galleryItems.some((item) => item.id === selectedItemId)
    ) {
      setSelectedItemId(initialItemId);
    }
  }, [galleryItems, initialItemId, selectedItemId]);

  const selectedItem =
    galleryItems.find((item) => item.id === selectedItemId) ?? galleryItems[0];
  const selectedImage =
    selectedItem?.kind === "image" ? selectedItem.image : null;
  const selectedVideo =
    selectedItem?.kind === "video" ? selectedItem.video : null;

  // One ordered slide array covering every image and the video, mirroring the
  // gallery order. Image slides use the high-res zoom derivative (falling back
  // to the main image) so the Zoom plugin can pan into detail; these assets are
  // only requested by YARL when their slide is shown, not on page load.
  const slides = useMemo<Slide[]>(
    () =>
      galleryItems.map((item) => {
        if (item.kind === "video") {
          return {
            type: "video",
            poster: resolveMediaUrl(item.video.poster_url) ?? undefined,
            sources: [
              {
                src: resolveMediaUrl(item.video.video_url) ?? "",
                type: "video/mp4",
              },
            ],
          };
        }
        return {
          src:
            resolveMediaUrl(item.image.zoom_url ?? item.image.image_url) ?? "",
          alt: name,
        };
      }),
    [galleryItems, name],
  );

  const selectedIndex = Math.max(
    0,
    galleryItems.findIndex((item) => item.id === selectedItem?.id),
  );

  if (!selectedItem) {
    return (
      <ProductImage
        name={name}
        imageUrl={null}
        sizes="(max-width: 1024px) 100vw, 50vw"
        priority
      />
    );
  }

  return (
    <div className="space-y-4">
      {selectedVideo ? (
        <button
          type="button"
          aria-label={name}
          onClick={() => setLightboxIndex(selectedIndex)}
          className="editorial-image-settle group relative block w-full overflow-hidden rounded-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page"
        >
          {prefersReducedMotion ? (
            <ProductImage
              name={name}
              imageUrl={selectedVideo.poster_url}
              sizes="(max-width: 1024px) 100vw, 50vw"
              priority
            />
          ) : (
            <video
              src={resolveMediaUrl(selectedVideo.video_url) ?? undefined}
              poster={resolveMediaUrl(selectedVideo.poster_url) ?? undefined}
              muted
              autoPlay
              loop
              playsInline
              className="aspect-[4/5] w-full rounded-brand bg-black object-cover"
            />
          )}
          <span className="absolute inset-0 flex items-center justify-center bg-text/0 transition-colors group-hover:bg-text/10">
            <span className="h-12 w-12 rounded-full bg-page/90 shadow-soft after:ml-[18px] after:mt-[13px] after:block after:h-0 after:w-0 after:border-y-[11px] after:border-l-[16px] after:border-y-transparent after:border-l-text" />
          </span>
        </button>
      ) : selectedImage ? (
        <button
          type="button"
          aria-label={t("zoomImage")}
          onClick={() => setLightboxIndex(selectedIndex)}
          className="editorial-image-settle group relative block w-full rounded-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page"
        >
          <ProductImage
            name={name}
            imageUrl={selectedImage.image_url}
            sizes="(max-width: 1024px) 100vw, 50vw"
            priority
            className="shadow-sm shadow-border/10"
          />
          <span className="absolute bottom-3 right-3 rounded-brand bg-text/85 px-3 py-1.5 text-sm font-medium text-page opacity-95 transition group-hover:bg-muted">
            {t("zoom")}
          </span>
        </button>
      ) : null}

      {galleryItems.length > 1 && (
        <div className="grid grid-cols-6 gap-2">
          {galleryItems.map((item) => {
            const thumbnailUrl = resolveMediaUrl(
              item.kind === "video"
                ? item.video.poster_url
                : item.image.thumbnail_url,
            );
            const isSelected = item.id === selectedItem.id;
            return (
              <button
                key={item.id}
                type="button"
                aria-label={name}
                aria-pressed={isSelected}
                onClick={() => setSelectedItemId(item.id)}
                className={cn(
                  "relative aspect-[4/5] overflow-hidden rounded-brand border bg-surface/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page",
                  isSelected ? "border-text/70" : "border-border/30",
                )}
              >
                <GalleryThumbnail label={name} imageUrl={thumbnailUrl} />
                {item.kind === "video" && (
                  <span className="absolute inset-0 flex items-center justify-center bg-text/10">
                    <span className="h-7 w-7 rounded-full bg-page/90 after:ml-[11px] after:mt-[7px] after:block after:h-0 after:w-0 after:border-y-[7px] after:border-l-[10px] after:border-y-transparent after:border-l-text" />
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}

      <Lightbox
        open={lightboxIndex >= 0}
        index={lightboxIndex >= 0 ? lightboxIndex : 0}
        close={() => setLightboxIndex(-1)}
        slides={slides}
        plugins={[Zoom, Video, Thumbnails]}
        on={{
          // Keep the inline hero/thumbnail selection in sync as the user pages.
          view: ({ index }) => {
            const item = galleryItems[index];
            if (item) setSelectedItemId(item.id);
          },
        }}
        carousel={{ finite: true }}
        controller={{ closeOnBackdropClick: true }}
        video={{ autoPlay: false, controls: true, playsInline: true }}
        zoom={{ maxZoomPixelRatio: 3, doubleTapDelay: 300 }}
        thumbnails={{ vignette: false, borderRadius: 8 }}
        labels={{
          Next: t("galleryNext"),
          Previous: t("galleryPrevious"),
          Close: t("closeZoom"),
        }}
        styles={{
          container: { backgroundColor: "rgb(var(--color-text) / 0.94)" },
        }}
      />
    </div>
  );
}
