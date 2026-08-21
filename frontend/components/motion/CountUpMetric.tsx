"use client";

import { useEffect, useMemo, useState } from "react";
import { useInViewOnce } from "./useInViewOnce";
import { usePrefersReducedMotion } from "./usePrefersReducedMotion";

interface CountUpMetricProps {
  value: string;
  countTo?: number;
  from?: number;
  durationMs?: number;
  formatter?: (value: number) => string;
  className?: string;
}

const DEFAULT_DURATION_MS = 900;

export function CountUpMetric({
  value,
  countTo,
  from = 0,
  durationMs = DEFAULT_DURATION_MS,
  formatter,
  className,
}: CountUpMetricProps) {
  const isNumeric = typeof countTo === "number" && Number.isFinite(countTo);
  const [ref, isVisible] = useInViewOnce<HTMLSpanElement>({ disabled: !isNumeric });
  const prefersReducedMotion = usePrefersReducedMotion();
  const formatValue = useMemo(() => formatter ?? ((next: number) => Math.round(next).toLocaleString()), [formatter]);
  const [displayValue, setDisplayValue] = useState(() => (isNumeric ? formatValue(from) : value));

  useEffect(() => {
    if (!isNumeric) {
      setDisplayValue(value);
      return;
    }

    if (prefersReducedMotion) {
      setDisplayValue(value);
      return;
    }

    if (!isVisible) {
      setDisplayValue(formatValue(from));
      return;
    }

    let animationFrame = 0;
    const start = performance.now();
    const delta = countTo - from;

    const tick = (now: number) => {
      const progress = Math.min((now - start) / durationMs, 1);
      const easedProgress = 1 - Math.pow(1 - progress, 3);
      setDisplayValue(formatValue(from + delta * easedProgress));

      if (progress < 1) {
        animationFrame = requestAnimationFrame(tick);
      } else {
        setDisplayValue(value);
      }
    };

    animationFrame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animationFrame);
  }, [countTo, durationMs, formatValue, from, isNumeric, isVisible, prefersReducedMotion, value]);

  return (
    <span ref={ref} className={className}>
      {displayValue}
    </span>
  );
}
