"use client";

import { useEffect, useId, useRef, useState } from "react";
import { cn } from "@/lib/utils";

type AdminInfoPopoverProps = {
  content: string;
  ariaLabel?: string;
  className?: string;
};

export function AdminInfoPopover({ content, ariaLabel = "More information", className }: AdminInfoPopoverProps) {
  const [open, setOpen] = useState(false);
  const popoverId = useId();
  const rootRef = useRef<HTMLSpanElement | null>(null);
  const closeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!open) return;

    function handlePointerDown(event: PointerEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  function cancelClose() {
    if (closeTimerRef.current) clearTimeout(closeTimerRef.current);
    closeTimerRef.current = null;
  }

  function closeSoon() {
    cancelClose();
    closeTimerRef.current = setTimeout(() => setOpen(false), 120);
  }

  return (
    <span
      ref={rootRef}
      className={cn("relative inline-flex align-middle", className)}
      onMouseEnter={() => {
        cancelClose();
        setOpen(true);
      }}
      onMouseLeave={closeSoon}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setOpen(false);
      }}
    >
      <button
        type="button"
        aria-label={ariaLabel}
        aria-expanded={open}
        aria-controls={open ? popoverId : undefined}
        onClick={() => setOpen((value) => !value)}
        onFocus={() => setOpen(true)}
        className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-soft-brown/35 bg-cream text-xs font-bold leading-none text-soft-brown transition-colors hover:border-charcoal hover:text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory"
      >
        i
      </button>
      {open && (
        <span
          id={popoverId}
          role="dialog"
          aria-label={ariaLabel}
          className="absolute right-0 top-8 z-[120] block w-[min(20rem,calc(100vw-2rem))] rounded-brand border border-champagne-beige bg-cream p-3 text-left text-sm font-normal leading-6 text-charcoal shadow-lg"
        >
          <button
            type="button"
            aria-label="Close"
            onClick={() => setOpen(false)}
            className="absolute right-2 top-2 inline-flex h-6 w-6 items-center justify-center rounded-full text-sm font-semibold text-soft-brown hover:bg-champagne-beige/60 hover:text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown"
          >
            X
          </button>
          <span className="block max-h-64 overflow-y-auto pr-7 whitespace-pre-wrap">{content}</span>
        </span>
      )}
    </span>
  );
}
