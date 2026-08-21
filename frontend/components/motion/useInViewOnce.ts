"use client";

import { useEffect, useRef, useState, type RefObject } from "react";
import { usePrefersReducedMotion } from "./usePrefersReducedMotion";

interface UseInViewOnceOptions extends IntersectionObserverInit {
  disabled?: boolean;
}

export function useInViewOnce<T extends Element>(
  options: UseInViewOnceOptions = {},
): [RefObject<T>, boolean] {
  const { disabled = false, root = null, rootMargin = "0px 0px -10%", threshold = 0.12 } = options;
  const ref = useRef<T>(null);
  const prefersReducedMotion = usePrefersReducedMotion();
  const [isVisible, setIsVisible] = useState(disabled || prefersReducedMotion);

  useEffect(() => {
    if (disabled || prefersReducedMotion) {
      setIsVisible(true);
      return;
    }

    const element = ref.current;
    if (!element) return;

    if (typeof IntersectionObserver === "undefined") {
      setIsVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry?.isIntersecting) return;
        setIsVisible(true);
        observer.disconnect();
      },
      { root, rootMargin, threshold },
    );

    observer.observe(element);
    return () => observer.disconnect();
  }, [disabled, prefersReducedMotion, root, rootMargin, threshold]);

  return [ref, isVisible];
}
