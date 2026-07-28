"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

interface PortalProps {
  children: React.ReactNode;
}

/**
 * Renders children into document.body so overlays escape ancestor stacking
 * contexts, transforms, and overflow clipping. Guarded by a mounted flag so
 * the first (server + hydration) render produces nothing and createPortal only
 * runs client-side where document exists.
 */
export function Portal({ children }: PortalProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;
  return createPortal(children, document.body);
}
