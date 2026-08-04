"use client";

import { useEffect, useRef } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { cn, formatPrice } from "@/lib/utils";
import { FREE_SHIPPING_THRESHOLD_CENTS } from "@/lib/constants";
import { useCart } from "@/contexts/CartContext";
import { useFocusTrap } from "@/lib/useFocusTrap";
import { Portal } from "@/components/ui/Portal";
import { trackAnalytics } from "@/lib/analytics";
import { CartItem } from "./CartItem";

export function CartDrawer() {
  const t = useTranslations("cart");
  const {
    items,
    unavailable_items,
    total_cents,
    item_count,
    isDrawerOpen,
    closeDrawer,
    updateQuantity,
    removeItem,
    error,
    dismissError,
  } = useCart();
  const trackedOpenRef = useRef(false);
  const amountToFreeShipping = Math.max(0, FREE_SHIPPING_THRESHOLD_CENTS - total_cents);
  const hasAvailableItems = item_count > 0;
  const hasUnavailableItems = unavailable_items.length > 0;

  // Escape-to-close, Tab focus trap, focus save/restore, and body scroll lock —
  // all keyed off isDrawerOpen. The ref goes on the drawer panel below.
  const drawerRef = useFocusTrap<HTMLDivElement>({
    active: isDrawerOpen,
    onClose: closeDrawer,
  });
  useEffect(() => {
    const drawer = drawerRef.current;
    if (!drawer) return;
    if (isDrawerOpen) {
      drawer.removeAttribute("inert");
    } else {
      drawer.setAttribute("inert", "");
    }
  }, [drawerRef, isDrawerOpen]);

  useEffect(() => {
    if (isDrawerOpen && !trackedOpenRef.current) {
      trackAnalytics("cart_open", {
        item_count,
        value_cents: total_cents,
        currency: "BGN",
      });
      trackedOpenRef.current = true;
    }
    if (!isDrawerOpen) trackedOpenRef.current = false;
  }, [isDrawerOpen, item_count, total_cents]);

  return (
    <Portal>
      <div
        data-testid="cart-drawer-root"
        className={cn(
          "fixed inset-0 z-[100]",
          isDrawerOpen ? "pointer-events-auto" : "pointer-events-none"
        )}
        aria-hidden={!isDrawerOpen}
      >
        {/* Backdrop */}
        <div
          className={cn(
            "fixed inset-0 bg-text/45",
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
          className={cn(
            "fixed right-0 top-0 flex h-full w-full max-w-md flex-col bg-page text-text shadow-xl",
            "motion-safe:transition-transform motion-safe:duration-normal",
            isDrawerOpen ? "translate-x-0" : "translate-x-full"
          )}
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-border/60 px-6 py-4">
            <h2 className="font-heading text-xl text-text">{t("title")}</h2>
            <button
              onClick={closeDrawer}
              aria-label={t("closeCart")}
              className={cn(
                "inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-brand",
                "text-muted transition-colors duration-fast hover:text-text",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page"
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
            <div className="mx-6 mt-4 flex items-start gap-2 rounded-brand border border-error/20 bg-error/10 p-3 text-error">
              <p className="flex-1 text-sm">{error}</p>
              <button
                onClick={dismissError}
                aria-label={t("dismissError")}
                className={cn(
                  "inline-flex min-h-[44px] min-w-[44px] shrink-0 items-center justify-center rounded-brand",
                  "text-error/70 transition-colors duration-fast hover:text-error",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-error focus-visible:ring-offset-2 focus-visible:ring-offset-page"
                )}
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
            {!hasAvailableItems && !hasUnavailableItems ? (
              <div className="flex h-full flex-col items-center justify-center text-center">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={1.5}
                  stroke="currentColor"
                  className="mb-4 h-12 w-12 text-border"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M15.75 10.5V6a3.75 3.75 0 10-7.5 0v4.5m11.356-1.993l1.263 12c.07.665-.45 1.243-1.119 1.243H4.25a1.125 1.125 0 01-1.12-1.243l1.264-12A1.125 1.125 0 015.513 7.5h12.974c.576 0 1.059.435 1.119 1.007zM8.625 10.5a.375.375 0 11-.75 0 .375.375 0 01.75 0zm7.5 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"
                  />
                </svg>
                <p className="mb-4 text-base text-muted">{t("empty")}</p>
                <Link
                  href="/products"
                  onClick={closeDrawer}
                  className={cn(
                    "inline-flex items-center justify-center rounded-brand px-4 py-2 text-sm font-medium",
                    "bg-primary text-primary-foreground transition-colors duration-fast hover:bg-primary-hover",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page"
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
                {hasUnavailableItems && (
                  <div className="mt-4 rounded-brand border border-warning/25 bg-warning/10 p-3">
                    <h3 className="text-sm font-medium text-warning">
                      {t("unavailableTitle")}
                    </h3>
                    <ul className="mt-2 divide-y divide-warning/20">
                      {unavailable_items.map((item) => (
                        <li key={item.product_id} className="flex items-center justify-between gap-3 py-3">
                          <div className="min-w-0">
                            <p className="truncate text-sm font-medium text-text">
                              {item.product_name}
                            </p>
                            <p className="mt-0.5 text-xs text-warning">
                              {t("unavailableReason", { reason: item.reason })}
                            </p>
                          </div>
                          <button
                            type="button"
                            onClick={() => removeItem(item.product_id)}
                            className={cn(
                              "min-h-[44px] shrink-0 rounded-brand px-3 text-sm font-medium text-warning underline underline-offset-4",
                              "hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-warning focus-visible:ring-offset-2 focus-visible:ring-offset-page"
                            )}
                          >
                            {t("remove")}
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Footer */}
          {hasAvailableItems && (
            <div className="space-y-4 border-t border-border/60 px-6 py-4">
              <div className="rounded-brand bg-accent-soft/35 px-3 py-2 text-xs text-muted">
                {amountToFreeShipping > 0
                  ? t("amountToFreeShipping", { amount: formatPrice(amountToFreeShipping) })
                  : t("freeShippingUnlocked")}
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-muted">{t("subtotal")}</span>
                <span className="font-heading text-lg text-text">
                  {formatPrice(total_cents)}
                </span>
              </div>
              <Link
                href="/checkout"
                onClick={closeDrawer}
                className={cn(
                  "block w-full rounded-brand px-6 py-3 text-center font-medium",
                  "bg-primary text-primary-foreground transition-colors duration-fast hover:bg-primary-hover",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page"
                )}
              >
                {t("proceedToCheckout")}
              </Link>
            </div>
          )}
        </div>
      </div>
    </Portal>
  );
}
