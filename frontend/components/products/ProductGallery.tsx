"use client";

import { useMemo, useState } from "react";
import Image from "next/image";
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
  const orderedImages = useMemo(
    () => [...images].sort((a, b) => a.sort_order - b.sort_order),
    [images]
  );
  const initialImageId =
    orderedImages.find((image) => image.image_url === primaryImageUrl)?.id ??
    orderedImages[0]?.id ??
    null;
  const [selectedImageId, setSelectedImageId] = useState<string | null>(initialImageId);
  const selectedImage =
    orderedImages.find((image) => image.id === selectedImageId) ?? orderedImages[0];

  if (!selectedImage) {
    return <ProductImage name={name} imageUrl={null} sizes="(max-width: 1024px) 100vw, 50vw" priority />;
  }

  return (
    <div className="space-y-3">
      <ProductImage
        name={name}
        imageUrl={selectedImage.image_url}
        sizes="(max-width: 1024px) 100vw, 50vw"
        priority
      />
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
    </div>
  );
}
