"use client";

import { useTranslations } from "next-intl";
import { formatPrice } from "@/lib/utils";
import { cn } from "@/lib/utils";
import type { ProductResponse } from "@/lib/types";

interface PriceDisplayProps {
  product: Pick<
    ProductResponse,
    "price_cents" | "effective_price_cents" | "discount_percent" | "discount_active"
  >;
  /** Tailwind classes for the primary (charged) price text. */
  className?: string;
  /** Tailwind classes for the struck-through original price. */
  originalClassName?: string;
}

/**
 * Shared price renderer used by the product card, detail page, and cart.
 * When a discount is active it shows the effective price as the primary price,
 * the original price struck through, and a `−X%` badge. Otherwise it shows the
 * regular price with no strikethrough or badge.
 */
export function PriceDisplay({ product, className, originalClassName }: PriceDisplayProps) {
  const t = useTranslations("products");

  if (!product.discount_active || product.discount_percent == null) {
    return <span className={className}>{formatPrice(product.price_cents)}</span>;
  }

  return (
    <span className="inline-flex flex-wrap items-baseline gap-x-2 gap-y-1">
      <span className={className} aria-label={t("salePrice")}>
        {formatPrice(product.effective_price_cents)}
      </span>
      <span
        className={cn("text-sm line-through text-soft-brown/60", originalClassName)}
        aria-label={t("originalPrice")}
      >
        {formatPrice(product.price_cents)}
      </span>
      <span className="rounded-pill bg-muted-gold px-2 py-0.5 text-xs font-semibold text-white">
        {t("discountBadge", { percent: product.discount_percent })}
      </span>
    </span>
  );
}
