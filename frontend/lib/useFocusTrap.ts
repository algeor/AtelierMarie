import { useEffect, useRef } from "react";

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

interface UseFocusTrapOptions {
  /** Whether the trap is engaged. Toggling this drives focus save/restore. */
  active: boolean;
  /** Called when Escape is pressed while the trap is active. */
  onClose?: () => void;
  /** Lock body scroll while active. Defaults to true. */
  lockScroll?: boolean;
}

/**
 * Shared modal behaviour for dialogs and drawers: while `active`, it moves
 * focus into the container, traps Tab within it, closes on Escape, restores
 * focus to the previously-focused element on deactivate, and (optionally)
 * locks body scroll.
 *
 * Attach the returned ref to the element whose focusable children should be
 * trapped. Works for components that mount on open (VideoLightbox) and for
 * always-mounted components that toggle visibility (CartDrawer) — the effects
 * key off `active`, not mount/unmount.
 */
export function useFocusTrap<T extends HTMLElement = HTMLElement>({
  active,
  onClose,
  lockScroll = true,
}: UseFocusTrapOptions) {
  const containerRef = useRef<T>(null);
  const returnFocusRef = useRef<Element | null>(null);

  // Save the outgoing focus target, move focus into the container, and restore
  // it on deactivate. requestAnimationFrame lets the container render/animate
  // in before we reach for its first focusable child.
  useEffect(() => {
    if (!active) return;
    returnFocusRef.current = document.activeElement;
    const raf = requestAnimationFrame(() => {
      const container = containerRef.current;
      const target = container?.querySelector<HTMLElement>(FOCUSABLE_SELECTOR);
      (target ?? container)?.focus();
    });
    return () => {
      cancelAnimationFrame(raf);
      if (returnFocusRef.current instanceof HTMLElement) {
        returnFocusRef.current.focus();
      }
      returnFocusRef.current = null;
    };
  }, [active]);

  // Escape to close + Tab focus trap.
  useEffect(() => {
    if (!active) return;
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose?.();
        return;
      }
      if (event.key !== "Tab") return;
      const container = containerRef.current;
      if (!container) return;
      const focusable = [
        ...container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
      ];
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (!first || !last) return;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [active, onClose]);

  // Body scroll lock.
  useEffect(() => {
    if (!active || !lockScroll) return;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "";
    };
  }, [active, lockScroll]);

  return containerRef;
}
