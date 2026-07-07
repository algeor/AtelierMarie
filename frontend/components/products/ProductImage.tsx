"use client";

import { useState } from "react";
import Image from "next/image";
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
  sizes = "(max-width: 768px) 100vw, (max-width: 1024px) 50vw, 25vw",
  priority = false,
  className,
}: ProductImageProps) {
  const [hasError, setHasError] = useState(false);

  const showPlaceholder = !imageUrl || hasError;

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
      <Image
        src={imageUrl}
        alt={name}
        fill
        sizes={sizes}
        priority={priority}
        className="object-cover"
        onError={() => setHasError(true)}
      />
    </div>
  );
}
