"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Image from "next/image";
import { useTranslations } from "next-intl";
import { BASE_URL } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type { ProductImage as ProductImageModel, ProductVideo } from "@/lib/types";
import { ProductImage } from "./ProductImage";
import { VideoLightbox } from "./VideoLightbox";

interface ProductGalleryProps {
  name: string;
  images: ProductImageModel[];
  video?: ProductVideo | null;
  primaryImageUrl: string | null;
}

type GalleryItem =
  | { kind: "image"; id: string; image: ProductImageModel }
  | { kind: "video"; id: string; video: ProductVideo };

function resolveImageUrl(url: string | null): string | null {
  return url?.startsWith("/static/") ? `${BASE_URL}${url}` : url;
}

export function ProductGallery({ name, images, video, primaryImageUrl }: ProductGalleryProps) {
  const t = useTranslations("products");
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [lightboxVideo, setLightboxVideo] = useState<ProductVideo | null>(null);
  const [isZoomOpen, setIsZoomOpen] = useState(false);
  const [zoomFailed, setZoomFailed] = useState(false);
  const lightboxRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

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
    [images]
  );

  const galleryItems = useMemo<GalleryItem[]>(() => {
    const items: GalleryItem[] = orderedImages.map((image) => ({
      kind: "image",
      id: image.id,
      image,
    }));
    if (video?.status === "ready" && video.video_url) {
      const insertionIndex = Math.min(Math.max(video.sort_order, 0), items.length);
      items.splice(insertionIndex, 0, { kind: "video", id: `video-${video.id}`, video });
    }
    return items;
  }, [orderedImages, video]);

  const initialItemId =
    galleryItems.find((item) => item.kind === "image" && item.image.image_url === primaryImageUrl)
      ?.id ??
    galleryItems[0]?.id ??
    null;

  useEffect(() => {
    if (!selectedItemId && initialItemId) {
      setSelectedItemId(initialItemId);
      return;
    }
    if (selectedItemId && !galleryItems.some((item) => item.id === selectedItemId)) {
      setSelectedItemId(initialItemId);
    }
  }, [galleryItems, initialItemId, selectedItemId]);

  const selectedItem =
    galleryItems.find((item) => item.id === selectedItemId) ?? galleryItems[0];
  const selectedImage = selectedItem?.kind === "image" ? selectedItem.image : null;
  const selectedVideo = selectedItem?.kind === "video" ? selectedItem.video : null;

  useEffect(() => {
    if (!isZoomOpen) return;

    const previousActiveElement =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    closeButtonRef.current?.focus();
    document.body.style.overflow = "hidden";
    setZoomFailed(false);

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsZoomOpen(false);
        return;
      }
      if (event.key !== "Tab") return;

      const dialog = lightboxRef.current;
      if (!dialog) return;
      const focusable = Array.from(
        dialog.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
        )
      );
      if (focusable.length === 0) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (!first || !last) return;
      if (!dialog.contains(document.activeElement)) {
        event.preventDefault();
        first.focus();
        return;
      }
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
      previousActiveElement?.focus();
    };
  }, [isZoomOpen]);

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

  const zoomImageUrl = selectedImage ? selectedImage.zoom_url ?? selectedImage.image_url : null;
  const resolvedZoomImageUrl = resolveImageUrl(zoomImageUrl);
  const resolvedMainImageUrl = resolveImageUrl(selectedImage?.image_url ?? null);
  const zoomDisplayUrl = zoomFailed ? resolvedMainImageUrl : resolvedZoomImageUrl;

  return (
    <div className="space-y-3">
      {selectedVideo ? (
        <button
          type="button"
          aria-label={name}
          onClick={() => setLightboxVideo(selectedVideo)}
          className="group relative block w-full overflow-hidden rounded-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2"
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
              src={resolveImageUrl(selectedVideo.video_url) ?? undefined}
              poster={resolveImageUrl(selectedVideo.poster_url) ?? undefined}
              muted
              autoPlay
              loop
              playsInline
              className="aspect-[4/5] w-full rounded-brand bg-black object-cover"
            />
          )}
          <span className="absolute inset-0 flex items-center justify-center bg-charcoal/0 transition-colors group-hover:bg-charcoal/10">
            <span className="h-12 w-12 rounded-full bg-warm-ivory/90 shadow-soft after:ml-[18px] after:mt-[13px] after:block after:h-0 after:w-0 after:border-y-[11px] after:border-l-[16px] after:border-y-transparent after:border-l-charcoal" />
          </span>
        </button>
      ) : selectedImage ? (
        <button
          type="button"
          aria-label={t("zoomImage")}
          onClick={() => setIsZoomOpen(true)}
          className="group relative block w-full rounded-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2"
        >
          <ProductImage
            name={name}
            imageUrl={selectedImage.image_url}
            sizes="(max-width: 1024px) 100vw, 50vw"
            priority
          />
          <span className="absolute right-3 bottom-3 rounded-brand bg-charcoal/85 px-3 py-1.5 text-sm font-medium text-warm-ivory opacity-95 transition group-hover:bg-soft-brown">
            {t("zoom")}
          </span>
        </button>
      ) : null}

      {galleryItems.length > 1 && (
        <div className="grid grid-cols-6 gap-2">
          {galleryItems.map((item) => {
            const thumbnailUrl = resolveImageUrl(
              item.kind === "video" ? item.video.poster_url : item.image.thumbnail_url
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
                  "relative aspect-[4/5] overflow-hidden rounded-brand border bg-cream focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2",
                  isSelected ? "border-charcoal" : "border-champagne-beige"
                )}
              >
                {thumbnailUrl ? (
                  <Image src={thumbnailUrl} alt="" fill sizes="96px" className="object-cover" />
                ) : (
                  <span className="sr-only">{name}</span>
                )}
                {item.kind === "video" && (
                  <span className="absolute inset-0 flex items-center justify-center bg-charcoal/10">
                    <span className="h-7 w-7 rounded-full bg-warm-ivory/90 after:ml-[11px] after:mt-[7px] after:block after:h-0 after:w-0 after:border-y-[7px] after:border-l-[10px] after:border-y-transparent after:border-l-charcoal" />
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}

      {lightboxVideo?.video_url && (
        <VideoLightbox
          name={name}
          videoUrl={lightboxVideo.video_url}
          posterUrl={lightboxVideo.poster_url}
          onClose={() => setLightboxVideo(null)}
        />
      )}

      {isZoomOpen && zoomDisplayUrl && (
        <div
          ref={lightboxRef}
          role="dialog"
          aria-modal="true"
          aria-label={t("zoomImage")}
          className="fixed inset-0 z-50 flex items-center justify-center bg-charcoal/90 p-4"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setIsZoomOpen(false);
          }}
        >
          <button
            ref={closeButtonRef}
            type="button"
            aria-label={t("closeZoom")}
            onClick={() => setIsZoomOpen(false)}
            className="absolute right-4 top-4 rounded-brand bg-warm-ivory px-3 py-2 text-sm font-medium text-charcoal shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-warm-ivory focus-visible:ring-offset-2 focus-visible:ring-offset-charcoal"
          >
            {t("closeZoom")}
          </button>
          <div className="relative h-[88vh] w-full max-w-6xl">
            <Image
              src={zoomDisplayUrl}
              alt={name}
              fill
              sizes="100vw"
              className="object-contain"
              onError={() => {
                if (!zoomFailed) setZoomFailed(true);
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
