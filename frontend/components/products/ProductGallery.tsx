"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Image from "next/image";
import { useTranslations } from "next-intl";
import { BASE_URL } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type { ProductImage as ProductImageModel } from "@/lib/types";
import { ProductImage } from "./ProductImage";

interface ProductGalleryProps {
  name: string;
  images: ProductImageModel[];
  primaryImageUrl: string | null;
}

function resolveImageUrl(url: string | null): string | null {
  return url?.startsWith("/static/") ? `${BASE_URL}${url}` : url;
}

export function ProductGallery({ name, images, primaryImageUrl }: ProductGalleryProps) {
  const t = useTranslations("products");
  const orderedImages = useMemo(
    () => [...images].sort((a, b) => a.sort_order - b.sort_order),
    [images]
  );
  const initialImageId =
    orderedImages.find((image) => image.image_url === primaryImageUrl)?.id ??
    orderedImages[0]?.id ??
    null;
  const [selectedImageId, setSelectedImageId] = useState<string | null>(initialImageId);
  const [isZoomOpen, setIsZoomOpen] = useState(false);
  const lightboxRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const selectedImage =
    orderedImages.find((image) => image.id === selectedImageId) ?? orderedImages[0];

  useEffect(() => {
    if (!isZoomOpen) return;

    const previousActiveElement = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;
    closeButtonRef.current?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsZoomOpen(false);
        return;
      }
      if (event.key !== "Tab") return;

      const focusable = Array.from(lightboxRef.current?.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      ) ?? []);
      if (focusable.length === 0) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (!first || !last) return;
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
      previousActiveElement?.focus();
    };
  }, [isZoomOpen]);

  if (!selectedImage) {
    return <ProductImage name={name} imageUrl={null} sizes="(max-width: 1024px) 100vw, 50vw" priority />;
  }

  const zoomImageUrl = selectedImage.zoom_url ?? selectedImage.image_url;
  const resolvedZoomImageUrl = resolveImageUrl(zoomImageUrl);

  return (
    <div className="space-y-3">
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
      {orderedImages.length > 1 && (
        <div className="grid grid-cols-6 gap-2">
          {orderedImages.map((image) => {
            const thumbnailUrl = resolveImageUrl(image.thumbnail_url);
            const isSelected = image.id === selectedImage.id;
            return (
              <button
                key={image.id}
                type="button"
                aria-label={name}
                aria-pressed={isSelected}
                onClick={() => setSelectedImageId(image.id)}
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
              </button>
            );
          })}
        </div>
      )}
      {isZoomOpen && resolvedZoomImageUrl && (
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
              src={resolvedZoomImageUrl}
              alt={name}
              fill
              sizes="100vw"
              className="object-contain"
            />
          </div>
        </div>
      )}
    </div>
  );
}
