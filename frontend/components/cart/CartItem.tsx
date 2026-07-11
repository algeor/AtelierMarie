"use client";

import { useTranslations } from "next-intl";
import { cn, formatPrice } from "@/lib/utils";
import type { CartItemResponse } from "@/lib/types";

interface CartItemProps {
  item: CartItemResponse;
  onUpdateQuantity: (productId: string, quantity: number) => void;
  onRemove: (productId: string) => void;
}

export function CartItem({ item, onUpdateQuantity, onRemove }: CartItemProps) {
  const t = useTranslations("cart");
  const { product, quantity, product_id } = item;
  const lineTotal = product.price_cents * quantity;
  const canDecrement = quantity > 1;
  const canIncrement = quantity < 10;

  return (
    <div className="flex gap-4 py-4 border-b border-champagne-beige last:border-b-0">
      <div className="flex-1 min-w-0">
        <h3 className="text-sm font-medium text-charcoal truncate">
          {product.name}
        </h3>
        <p className="mt-1 text-sm text-soft-brown">
          {formatPrice(product.price_cents)}
        </p>

        <div className="mt-2 flex items-center gap-2">
          <button
            onClick={() => canDecrement && onUpdateQuantity(product_id, quantity - 1)}
            disabled={!canDecrement}
            aria-label={t("decreaseQuantity")}
            className={cn(
              "w-7 h-7 inline-flex items-center justify-center rounded-brand border border-champagne-beige text-sm font-medium",
              "transition-colors duration-fast",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory",
              canDecrement
                ? "text-charcoal hover:bg-cream"
                : "text-soft-brown/40 cursor-not-allowed"
            )}
          >
            −
          </button>
          <span
            className="min-w-[1.5rem] text-center text-sm font-medium text-charcoal"
            aria-live="polite"
            aria-atomic="true"
          >
            {quantity}
          </span>
          <button
            onClick={() => canIncrement && onUpdateQuantity(product_id, quantity + 1)}
            disabled={!canIncrement}
            aria-label={t("increaseQuantity")}
            className={cn(
              "w-7 h-7 inline-flex items-center justify-center rounded-brand border border-champagne-beige text-sm font-medium",
              "transition-colors duration-fast",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory",
              canIncrement
                ? "text-charcoal hover:bg-cream"
                : "text-soft-brown/40 cursor-not-allowed"
            )}
          >
            +
          </button>
        </div>
      </div>

      <div className="flex flex-col items-end justify-between">
        <p className="text-sm font-medium text-charcoal">
          {formatPrice(lineTotal)}
        </p>
        <button
          onClick={() => onRemove(product_id)}
          aria-label={t("removeFromCart", { name: product.name })}
          className={cn(
            "text-soft-brown/70 hover:text-charcoal transition-colors duration-fast",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory rounded-brand",
            "inline-flex items-center justify-center min-w-[28px] min-h-[28px]"
          )}
        >
          <span className="hidden sm:inline text-xs underline">{t("remove")}</span>
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
            className="w-4 h-4 sm:hidden"
            aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}
