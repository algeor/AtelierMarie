"use client";

import { useEffect, useRef, useState, type CSSProperties } from "react";
import { Portal } from "@/components/ui/Portal";
import { cn } from "@/lib/utils";

export interface AdminTranslationGap {
  detail?: string;
  fieldId?: string;
  id: string;
  label: string;
  onFix?: () => void;
}

interface AdminTranslationGapButtonProps {
  gaps: AdminTranslationGap[];
  className?: string;
  emptyLabel?: string;
  label?: string;
}

export function AdminTranslationGapButton({
  gaps,
  className,
  emptyLabel = "EN/BG ready",
  label = "Translation gaps",
}: AdminTranslationGapButtonProps) {
  const [open, setOpen] = useState(false);
  const [menuStyle, setMenuStyle] = useState<CSSProperties>({});
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const count = gaps.length;

  useEffect(() => {
    if (!open) return;

    function updateMenuPosition() {
      const trigger = triggerRef.current;
      if (!trigger) return;

      const rect = trigger.getBoundingClientRect();
      const viewportWidth = window.innerWidth || rect.width;
      const viewportHeight = window.innerHeight || 720;
      const width = Math.min(Math.max(rect.width, 280), Math.max(280, viewportWidth - 16));
      const menuHeight = Math.min(count * 58 + 54, 340);
      const left = Math.min(Math.max(8, rect.left), Math.max(8, viewportWidth - width - 8));
      const shouldOpenUp = rect.bottom + menuHeight > viewportHeight && rect.top > menuHeight;
      const top = shouldOpenUp ? rect.top - menuHeight + 1 : rect.bottom + 6;

      setMenuStyle({
        left,
        maxHeight: menuHeight,
        position: "fixed",
        top: Math.max(8, top),
        width,
      });
    }

    function handlePointerDown(event: MouseEvent) {
      const target = event.target as Node;
      if (triggerRef.current?.contains(target) || menuRef.current?.contains(target)) return;
      setOpen(false);
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      setOpen(false);
      triggerRef.current?.focus();
    }

    updateMenuPosition();
    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    window.addEventListener("resize", updateMenuPosition);
    window.addEventListener("scroll", updateMenuPosition, true);

    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("resize", updateMenuPosition);
      window.removeEventListener("scroll", updateMenuPosition, true);
    };
  }, [count, open]);

  if (count === 0) {
    return (
      <span className={cn("rounded-pill border border-green-200 bg-green-50 px-2 py-1 text-xs font-semibold text-green-700", className)}>
        {emptyLabel}
      </span>
    );
  }

  function fixGap(gap: AdminTranslationGap) {
    setOpen(false);
    gap.onFix?.();
    const fieldId = gap.fieldId;
    if (!fieldId) return;
    window.setTimeout(() => focusTranslationGapField(fieldId), 90);
  }

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        aria-expanded={open}
        aria-haspopup="dialog"
        onClick={() => setOpen((current) => !current)}
        className={cn(
          "inline-flex items-center gap-1.5 rounded-pill border border-amber-200 bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-800 transition-colors duration-fast hover:border-amber-300 hover:bg-amber-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2",
          className,
        )}
      >
        {count} BG gap{count === 1 ? "" : "s"}
        <span aria-hidden="true" className={cn("text-[10px] transition-transform", open && "rotate-180")}>v</span>
      </button>

      {open ? (
        <Portal>
          <div
            ref={menuRef}
            role="dialog"
            aria-label={label}
            style={menuStyle}
            className="z-50 overflow-auto rounded-brand border border-soft-brown/25 bg-warm-ivory p-2 shadow-xl ring-1 ring-charcoal/5"
          >
            <div className="border-b border-champagne-beige/80 px-2 pb-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-gold">{label}</p>
              <p className="mt-0.5 text-xs text-soft-brown">Missing Bulgarian fields</p>
            </div>
            <div className="pt-1">
              {gaps.map((gap) => (
                <div key={gap.id} className="flex items-start justify-between gap-3 rounded-brand px-2 py-2 hover:bg-cream/70">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-charcoal">{gap.label}</p>
                    {gap.detail ? <p className="mt-0.5 line-clamp-2 text-xs leading-5 text-soft-brown">{gap.detail}</p> : null}
                  </div>
                  <button
                    type="button"
                    onClick={() => fixGap(gap)}
                    className="shrink-0 rounded-brand border border-champagne-beige bg-admin-surface px-2 py-1 text-xs font-semibold text-soft-brown hover:border-admin-accent hover:text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory"
                  >
                    Fix
                  </button>
                </div>
              ))}
            </div>
          </div>
        </Portal>
      ) : null}
    </>
  );
}

export function MissingBgLabel({ show }: { show: boolean }) {
  if (!show) return null;
  return (
    <span className="ml-2 inline-flex rounded-pill border border-amber-200 bg-amber-50 px-1.5 py-0.5 align-middle text-[11px] font-semibold text-amber-800">
      Missing BG
    </span>
  );
}

export function focusTranslationGapField(fieldId: string) {
  const field = document.getElementById(fieldId);
  field?.scrollIntoView({ block: "center", behavior: "smooth" });
  field?.focus({ preventScroll: true });
}

export function isMissingTranslation(source: string | null | undefined, target: string | null | undefined) {
  return Boolean(source?.trim()) && !target?.trim();
}
