"use client";

import { useEffect, useRef, useState, type CSSProperties } from "react";
import { Portal } from "@/components/ui/Portal";
import { cn } from "@/lib/utils";

interface AdminMobileTargetSelectOption {
  description?: string;
  group?: string;
  label: string;
  value: string;
}

interface AdminMobileTargetSelectProps {
  label: string;
  onChange: (value: string) => void;
  options: AdminMobileTargetSelectOption[];
  value: string;
  className?: string;
}

export function AdminMobileTargetSelect({
  label,
  onChange,
  options,
  value,
  className,
}: AdminMobileTargetSelectProps) {
  const [open, setOpen] = useState(false);
  const [menuStyle, setMenuStyle] = useState<CSSProperties>({});
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const selectedOption = options.find((option) => option.value === value) ?? options[0];
  const idBase = `${label.replaceAll(" ", "-").toLowerCase()}-mobile-target`;

  useEffect(() => {
    if (!open) return;

    function updateMenuPosition() {
      const trigger = triggerRef.current;
      if (!trigger) return;

      const rect = trigger.getBoundingClientRect();
      const viewportWidth = window.innerWidth || rect.width;
      const viewportHeight = window.innerHeight || 720;
      const menuHeight = Math.min(options.length * 44 + 8, 280);
      const left = Math.min(
        Math.max(8, rect.left),
        Math.max(8, viewportWidth - rect.width - 8),
      );
      const shouldOpenUp = rect.bottom + menuHeight > viewportHeight && rect.top > menuHeight;
      const top = shouldOpenUp ? rect.top - menuHeight + 1 : rect.bottom - 1;

      setMenuStyle({
        left,
        maxHeight: menuHeight,
        position: "fixed",
        top: Math.max(8, top),
        width: rect.width,
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
  }, [open, options.length]);

  return (
    <div className={cn("rounded-brand border border-admin-border/50 bg-admin-surface p-3 shadow-sm xl:hidden", className)}>
      <p className="block text-xs font-semibold uppercase tracking-wide text-admin-muted" id={`${idBase}-label`}>
        {label}
      </p>
      <button
        ref={triggerRef}
        type="button"
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-labelledby={`${idBase}-label ${idBase}-button`}
        id={`${idBase}-button`}
        onClick={() => setOpen((current) => !current)}
        className={cn(
          "mt-2 inline-flex min-h-11 w-full items-center justify-between gap-3 rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-left text-sm font-medium text-charcoal shadow-sm transition-colors duration-fast hover:border-soft-brown/35 hover:bg-cream focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-admin-surface",
          open && "rounded-b-none border-soft-brown/35 bg-warm-ivory shadow-none",
        )}
      >
        <span className="min-w-0">
          <span className="block truncate">{selectedOption?.label ?? label}</span>
          {selectedOption?.description ? (
            <span className="mt-0.5 block truncate text-xs font-normal text-soft-brown">
              {selectedOption.description}
            </span>
          ) : null}
        </span>
        <span
          aria-hidden="true"
          className={cn("shrink-0 text-[10px] text-soft-brown/70 transition-transform duration-fast", open && "rotate-180")}
        >
          v
        </span>
      </button>

      {open && (
        <Portal>
          <div
            ref={menuRef}
            role="listbox"
            aria-labelledby={`${idBase}-label`}
            style={menuStyle}
            className="z-50 overflow-auto rounded-b-brand border border-soft-brown/35 bg-warm-ivory py-1 shadow-xl ring-1 ring-charcoal/5"
          >
            {options.map((option, index) => {
              const selected = option.value === value;
              const previousGroup = index > 0 ? options[index - 1]?.group : undefined;
              const showGroup = option.group && option.group !== previousGroup;
              return (
                <div key={option.value}>
                  {showGroup ? (
                    <div className="border-t border-champagne-beige/70 px-3 pb-1 pt-2 first:border-t-0 first:pt-1">
                      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-gold">
                        {option.group}
                      </p>
                    </div>
                  ) : null}
                  <button
                    type="button"
                    role="option"
                    aria-selected={selected}
                    onClick={() => {
                      onChange(option.value);
                      setOpen(false);
                      triggerRef.current?.focus();
                    }}
                    className={cn(
                      "flex min-h-10 w-full min-w-0 items-center gap-2 px-3 py-2 text-left text-sm font-medium text-soft-brown transition-colors duration-fast hover:bg-cream/70 hover:text-charcoal focus-visible:bg-cream/70 focus-visible:text-charcoal focus-visible:outline-none",
                      selected && "bg-cream/70 text-charcoal",
                    )}
                  >
                    <span
                      aria-hidden="true"
                      className={cn("h-2 w-2 shrink-0 rounded-full", selected ? "bg-muted-gold" : "bg-transparent")}
                    />
                    <span className="min-w-0">
                      <span className="block truncate">{option.label}</span>
                      {option.description ? (
                        <span className="mt-0.5 block truncate text-xs font-normal text-soft-brown/80">
                          {option.description}
                        </span>
                      ) : null}
                    </span>
                  </button>
                </div>
              );
            })}
          </div>
        </Portal>
      )}
    </div>
  );
}
