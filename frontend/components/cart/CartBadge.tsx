"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

interface CartBadgeProps {
  count: number;
}

export function CartBadge({ count }: CartBadgeProps) {
  const [shouldAnimate, setShouldAnimate] = useState(false);
  const [prevCount, setPrevCount] = useState(count);

  useEffect(() => {
    if (count !== prevCount && count > 0) {
      setShouldAnimate(true);
      setPrevCount(count);
      const timer = setTimeout(() => {
        setShouldAnimate(false);
      }, 300);
      return () => clearTimeout(timer);
    }
    setPrevCount(count);
  }, [count, prevCount]);

  if (count === 0) return null;

  return (
    <span
      aria-hidden="true"
      className={cn(
        "absolute -right-1 -top-1 flex h-[18px] min-w-[18px] items-center justify-center rounded-full",
        "bg-primary px-1 text-xs font-medium text-primary-foreground",
        shouldAnimate && "motion-safe:animate-badge-bounce"
      )}
    >
      {count}
    </span>
  );
}
