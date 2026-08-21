"use client";

import { type CSSProperties, type ReactNode } from "react";
import { cn } from "@/lib/utils";
import { useInViewOnce } from "./useInViewOnce";

const MAX_STAGGER_INDEX = 8;

interface ScrollRevealProps {
  children: ReactNode;
  className?: string;
  index?: number;
  disabled?: boolean;
}

export function ScrollReveal({
  children,
  className,
  index = 0,
  disabled = false,
}: ScrollRevealProps) {
  const [ref, isVisible] = useInViewOnce<HTMLDivElement>({ disabled });
  const staggerIndex = Math.max(0, Math.min(index, MAX_STAGGER_INDEX));

  return (
    <div
      ref={ref}
      className={cn("scroll-reveal", isVisible && "scroll-reveal--visible", className)}
      data-visible={isVisible ? "true" : "false"}
      style={{ "--scroll-reveal-delay": `${staggerIndex * 80}ms` } as CSSProperties}
    >
      {children}
    </div>
  );
}
