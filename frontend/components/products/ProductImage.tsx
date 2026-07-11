"use client";

import { useState } from "react";
import { BASE_URL } from "@/lib/api-client";
import { cn } from "@/lib/utils";

interface ProductImageProps {
  name: string;
  imageUrl: string | null;
  sizes?: string;
  priority?: boolean;
  className?: string;
}

export function ProductImage({
  name,
  imageUrl,
  priority = false,
  className,
}: ProductImageProps) {
  const [hasError, setHasError] = useState(false);
  const resolvedImageUrl = imageUrl?.startsWith("/static/")
    ? `${BASE_URL}${imageUrl}`
    : imageUrl;

  const showPlaceholder = !resolvedImageUrl || hasError;

  if (showPlaceholder) {
    return (
      <div
        role="img"
        aria-label={name}
        className={cn(
          "relative w-full aspect-[4/5] rounded-brand overflow-hidden flex items-center justify-center px-4 bg-brand-gradient",
          className
        )}
      >
        <span className="font-heading text-lg text-charcoal/80 text-center line-clamp-2">
          {name}
        </span>
      </div>
    );
  }

  return (
    <div className={cn("relative w-full aspect-[4/5] rounded-brand overflow-hidden", className)}>
      <img
        src={resolvedImageUrl}
        alt={name}
        loading={priority ? "eager" : "lazy"}
        className="h-full w-full object-cover"
        onError={() => setHasError(true)}
      />
    </div>
  );
}
