"use client";

import Image from "next/image";
import { useTranslations } from "next-intl";
import { cn, formatPrice } from "@/lib/utils";
import { resolveMediaUrl } from "@/lib/media";
import { PriceDisplay } from "@/components/products/PriceDisplay";
import { DeleteIconButton } from "@/components/ui/DeleteIconButton";
import type { CartItemResponse } from "@/lib/types";

interface CartItemProps {
  item: CartItemResponse;
  onUpdateQuantity: (productId: string, quantity: number) => void;
  onRemove: (productId: string) => void;
}

export function CartItem({ item, onUpdateQuantity, onRemove }: CartItemProps) {
  const t = useTranslations("cart");
  const { product, quantity, product_id } = item;
  const lineTotal = product.effective_price_cents * quantity;
  const thumbnailUrl = resolveMediaUrl(
    product.primary_thumbnail_url ?? product.primary_image_url,
  );
  const maxQuantity = 10;
  const canDecrement = quantity > 1;
  const canIncrement = quantity < maxQuantity;
  const isCraftedLater = product.can_order && !product.available_now;

  return (
    <div className="flex gap-4 border-b editorial-divider py-4 last:border-b-0">
      <div className="h-16 w-16 shrink-0 overflow-hidden rounded-brand border border-border/30 bg-surface/70">
        {thumbnailUrl ? (
          <Image
            src={thumbnailUrl}
            alt=""
            width={64}
            height={64}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center px-2 text-center font-heading text-[10px] leading-tight text-muted/70">
            {product.name}
          </div>
        )}
      </div>
      <div className="min-w-0 flex-1">
        <h3 className="truncate text-sm font-medium text-text">
          {product.name}
        </h3>
        <p className="mt-1 text-sm text-muted">
          <PriceDisplay product={product} className="text-sm text-muted" />
        </p>

        <div className="mt-2 flex items-center gap-2">
          <button
            onClick={() =>
              canDecrement && onUpdateQuantity(product_id, quantity - 1)
            }
            disabled={!canDecrement}
            aria-label={t("decreaseQuantity")}
            className={cn(
              "inline-flex h-7 w-7 items-center justify-center rounded-brand border border-border/40 text-sm font-medium",
              "transition-colors duration-fast",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page",
              canDecrement
                ? "text-text hover:bg-surface"
                : "cursor-not-allowed text-muted/40",
            )}
          >
            −
          </button>
          <span
            className="min-w-[1.5rem] text-center text-sm font-medium text-text"
            aria-live="polite"
            aria-atomic="true"
          >
            {quantity}
          </span>
          <button
            onClick={() =>
              canIncrement && onUpdateQuantity(product_id, quantity + 1)
            }
            disabled={!canIncrement}
            aria-label={t("increaseQuantity")}
            title={
              !canIncrement && maxQuantity > 0
                ? t("itemLimit", { count: maxQuantity })
                : undefined
            }
            className={cn(
              "inline-flex h-7 w-7 items-center justify-center rounded-brand border border-border/40 text-sm font-medium",
              "transition-colors duration-fast",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page",
              canIncrement
                ? "text-text hover:bg-surface"
                : "cursor-not-allowed text-muted/40",
            )}
          >
            +
          </button>
        </div>
        {!canIncrement && maxQuantity > 0 && (
          <p className="mt-1 text-xs text-muted">
            {t("itemLimit", { count: maxQuantity })}
          </p>
        )}
        {isCraftedLater && (
          <p className="mt-1 text-xs text-muted">{t("craftedLaterItem")}</p>
        )}
      </div>

      <div className="flex flex-col items-end justify-between">
        <p className="text-sm font-medium text-text">
          {formatPrice(lineTotal)}
        </p>
        <DeleteIconButton
          onClick={() => onRemove(product_id)}
          label={t("removeFromCart", { name: product.name })}
        />
      </div>
    </div>
  );
}
