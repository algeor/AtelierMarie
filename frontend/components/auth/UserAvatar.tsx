"use client";

import { useEffect, useState } from "react";
import Image from "next/image";

type AvatarSize = "sm" | "lg";

interface UserAvatarProps {
  name: string | null;
  email: string;
  avatarUrl: string | null;
  alt?: string;
  size?: AvatarSize;
}

const sizeClasses: Record<AvatarSize, { image: string; fallback: string; text: string; pixels: number }> = {
  sm: {
    image: "w-8 h-8",
    fallback: "w-8 h-8",
    text: "text-sm",
    pixels: 32,
  },
  lg: {
    image: "w-24 h-24",
    fallback: "w-24 h-24",
    text: "text-3xl",
    pixels: 96,
  },
};

export function UserAvatar({ name, email, avatarUrl, alt = "", size = "sm" }: UserAvatarProps) {
  const [hasImageError, setHasImageError] = useState(false);
  const classes = sizeClasses[size];
  const initial = name?.charAt(0).toUpperCase() ?? email.charAt(0).toUpperCase();

  useEffect(() => {
    setHasImageError(false);
  }, [avatarUrl]);

  if (avatarUrl && !hasImageError) {
    return (
      <Image
        src={avatarUrl}
        alt={alt}
        width={classes.pixels}
        height={classes.pixels}
        className={`${classes.image} rounded-full object-cover bg-cream`}
        onError={() => setHasImageError(true)}
      />
    );
  }

  return (
    <span
      className={`${classes.fallback} rounded-full bg-muted-gold text-charcoal flex items-center justify-center ${classes.text} font-medium`}
    >
      {initial}
    </span>
  );
}
