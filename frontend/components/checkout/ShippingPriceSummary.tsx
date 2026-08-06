"use client";

/**
 * ShippingPriceSummary — the order-total breakdown shown above the submit button.
 *
 * Displays subtotal, shipping (or a free-shipping badge), and the grand total.
 * When the cart is below the free-shipping threshold it shows how much more the
 * customer needs to add to qualify ("Add X more for free shipping").
 */

import { useTranslations } from "next-intl";
import { cn, formatPrice } from "@/lib/utils";
import { FREE_SHIPPING_THRESHOLD_CENTS } from "@/lib/constants";

interface ShippingPriceSummaryProps {
  itemsTotalCents: number;
  shippingCents: number | null;
  className?: string;
}

export function ShippingPriceSummary({
  itemsTotalCents,
  shippingCents,
  className,
}: ShippingPriceSummaryProps) {
  const t = useTranslations("checkout.delivery");
  const tCart = useTranslations("cart");

  const qualifiesForFree = itemsTotalCents >= FREE_SHIPPING_THRESHOLD_CENTS;
  const amountToFree = Math.max(
    0,
    FREE_SHIPPING_THRESHOLD_CENTS - itemsTotalCents,
  );
  // Shipping is still pending until we have a concrete quote (or free-shipping
  // qualification). Only then does it contribute to the grand total — showing
  // "pending" while silently adding 0 would understate the total (review S5).
  const isPending = shippingCents === null && !qualifiesForFree;
  // A 0¢ result is "free" whether it came from the threshold or a live 0 quote.
  const isFreeShipping = qualifiesForFree || shippingCents === 0;
  const totalCents =
    itemsTotalCents + (isFreeShipping ? 0 : (shippingCents ?? 0));

  return (
    <div className={cn("space-y-2 text-sm", className)}>
      {!qualifiesForFree && amountToFree > 0 && (
        <p className="editorial-note-panel rounded-brand px-3 py-2 text-xs text-muted">
          {t("amountToFreeShipping", { amount: formatPrice(amountToFree) })}
        </p>
      )}

      <div className="flex items-center justify-between">
        <span className="text-muted">{tCart("subtotal")}</span>
        <span className="text-text">{formatPrice(itemsTotalCents)}</span>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-muted">{t("shippingLabel")}</span>
        {isPending ? (
          <span className="text-muted">{t("shippingPending")}</span>
        ) : isFreeShipping ? (
          <span className="font-medium text-accent">{t("freeShipping")}</span>
        ) : (
          <span className="text-text">{formatPrice(shippingCents ?? 0)}</span>
        )}
      </div>

      <div className="flex items-center justify-between border-t editorial-divider pt-2">
        <span className="font-heading text-lg text-text">{t("total")}</span>
        <span className="font-heading text-lg text-text">
          {isPending ? "—" : formatPrice(totalCents)}
        </span>
      </div>
    </div>
  );
}
