"use client";

import { useEffect, useMemo, useState } from "react";
import Image from "next/image";
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
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);
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
  const [selectedItemId, setSelectedItemId] = useState<string | null>(initialItemId);
  const [lightboxVideo, setLightboxVideo] = useState<ProductVideo | null>(null);
  const selectedItem = galleryItems.find((item) => item.id === selectedItemId) ?? galleryItems[0];

  if (!selectedItem) {
    return <ProductImage name={name} imageUrl={null} sizes="(max-width: 1024px) 100vw, 50vw" priority />;
  }

  const selectedVideo = selectedItem.kind === "video" ? selectedItem.video : null;

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
      ) : selectedItem.kind === "image" ? (
        <ProductImage
          name={name}
          imageUrl={selectedItem.image.image_url}
          sizes="(max-width: 1024px) 100vw, 50vw"
          priority
        />
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
    </div>
  );
}
