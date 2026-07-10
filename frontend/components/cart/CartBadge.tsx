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
        "absolute -top-1 -right-1 min-w-[18px] h-[18px] flex items-center justify-center rounded-full",
        "bg-muted-gold text-charcoal text-xs font-medium px-1",
        shouldAnimate && "motion-safe:animate-badge-bounce"
      )}
    >
      {count}
    </span>
  );
}
