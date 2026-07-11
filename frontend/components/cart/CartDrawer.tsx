"use client";

import { useCallback, useEffect, useRef } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { cn, formatPrice } from "@/lib/utils";
import { useCart } from "@/contexts/CartContext";
import { CartItem } from "./CartItem";

export function CartDrawer() {
  const t = useTranslations("cart");
  const {
    items,
    total_cents,
    item_count,
    isDrawerOpen,
    closeDrawer,
    updateQuantity,
    removeItem,
    error,
    dismissError,
  } = useCart();

  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const drawerRef = useRef<HTMLDivElement>(null);
  const returnFocusRef = useRef<Element | null>(null);

  // Save focus target when opening, restore when closing
  useEffect(() => {
    if (isDrawerOpen) {
      returnFocusRef.current = document.activeElement;
      // Small delay to let the DOM render before focusing
      requestAnimationFrame(() => {
        closeButtonRef.current?.focus();
      });
    } else {
      if (returnFocusRef.current instanceof HTMLElement) {
        returnFocusRef.current.focus();
      }
      returnFocusRef.current = null;
    }
  }, [isDrawerOpen]);

  // Body scroll lock
  useEffect(() => {
    if (isDrawerOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isDrawerOpen]);

  // Close on Escape
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && isDrawerOpen) {
        closeDrawer();
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isDrawerOpen, closeDrawer]);

  // Focus trap
  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      if (event.key !== "Tab" || !drawerRef.current) return;

      const focusableElements = drawerRef.current.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])'
      );

      if (focusableElements.length === 0) return;

      const firstElement = focusableElements[0] as HTMLElement | undefined;
      const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement | undefined;

      if (!firstElement || !lastElement) return;

      if (event.shiftKey) {
        if (document.activeElement === firstElement) {
          event.preventDefault();
          lastElement.focus();
        }
      } else {
        if (document.activeElement === lastElement) {
          event.preventDefault();
          firstElement.focus();
        }
      }
    },
    []
  );

  return (
    <div
      className={cn(
        "fixed inset-0 z-[100]",
        isDrawerOpen ? "pointer-events-auto" : "pointer-events-none"
      )}
      aria-hidden={!isDrawerOpen}
    >
      {/* Backdrop */}
      <div
        className={cn(
          "fixed inset-0 bg-black/50",
          "motion-safe:transition-opacity motion-safe:duration-normal",
          isDrawerOpen ? "opacity-100" : "opacity-0"
        )}
        onClick={closeDrawer}
        aria-hidden="true"
      />

      {/* Drawer panel */}
      <div
        ref={drawerRef}
        role="dialog"
        aria-modal="true"
        aria-label={t("title")}
        inert={!isDrawerOpen ? ("" as unknown as boolean) : undefined}
        onKeyDown={handleKeyDown}
        className={cn(
          "fixed top-0 right-0 h-full w-full max-w-md bg-warm-ivory shadow-xl flex flex-col",
          "motion-safe:transition-transform motion-safe:duration-normal",
          isDrawerOpen ? "translate-x-0" : "translate-x-full"
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-champagne-beige">
          <h2 className="font-heading text-xl text-charcoal">{t("title")}</h2>
          <button
            ref={closeButtonRef}
            onClick={closeDrawer}
            aria-label={t("closeCart")}
            className={cn(
              "min-w-[44px] min-h-[44px] inline-flex items-center justify-center rounded-brand",
              "text-soft-brown hover:text-charcoal transition-colors duration-fast",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory"
            )}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="w-6 h-6"
              aria-hidden="true"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Error banner */}
        {error && (
          <div className="mx-6 mt-4 bg-red-50 text-red-800 rounded-brand p-3 flex items-start gap-2">
            <p className="flex-1 text-sm">{error}</p>
            <button
              onClick={dismissError}
              aria-label={t("dismissError")}
              className="shrink-0 text-red-800/70 hover:text-red-800 transition-colors duration-fast"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
                className="w-4 h-4"
                aria-hidden="true"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {item_count === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
                className="w-12 h-12 text-champagne-beige mb-4"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M15.75 10.5V6a3.75 3.75 0 10-7.5 0v4.5m11.356-1.993l1.263 12c.07.665-.45 1.243-1.119 1.243H4.25a1.125 1.125 0 01-1.12-1.243l1.264-12A1.125 1.125 0 015.513 7.5h12.974c.576 0 1.059.435 1.119 1.007zM8.625 10.5a.375.375 0 11-.75 0 .375.375 0 01.75 0zm7.5 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"
                />
              </svg>
              <p className="text-soft-brown text-base mb-4">{t("empty")}</p>
              <Link
                href="/products"
                onClick={closeDrawer}
                className={cn(
                  "inline-flex items-center justify-center rounded-brand px-4 py-2 text-sm font-medium",
                  "bg-muted-gold text-charcoal hover:bg-muted-gold/90 transition-colors duration-fast",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory"
                )}
              >
                {t("continueShopping")}
              </Link>
            </div>
          ) : (
            <div>
              {items.map((item) => (
                <CartItem
                  key={item.product_id}
                  item={item}
                  onUpdateQuantity={updateQuantity}
                  onRemove={removeItem}
                />
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        {item_count > 0 && (
          <div className="border-t border-champagne-beige px-6 py-4 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-soft-brown">{t("subtotal")}</span>
              <span className="text-lg font-heading text-charcoal">
                {formatPrice(total_cents)}
              </span>
            </div>
            <Link
              href="/checkout"
              onClick={closeDrawer}
              className={cn(
                "block w-full text-center rounded-brand px-6 py-3 font-medium",
                "bg-muted-gold text-charcoal hover:bg-muted-gold/90 transition-colors duration-fast",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory"
              )}
            >
              {t("proceedToCheckout")}
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
