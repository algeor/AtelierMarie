"use client";

/**
 * CourierComparison — side-by-side courier quote cards for the checkout flow.
 *
 * Renders one card per quote (Speedy / Econt) showing the price and delivery
 * estimate with a radio selection. A fallback disclaimer is shown **only** when
 * a quote's `price_source` is not "live" (i.e. the price is a guess / flat
 * fallback). Live prices carry no disclaimer.
 */

import { useTranslations } from "next-intl";
import { cn, formatPrice } from "@/lib/utils";
import type { Courier, ShippingQuote } from "@/lib/types";

interface CourierComparisonProps {
  quotes: ShippingQuote[];
  selectedCourier: Courier | null;
  onSelect: (quote: ShippingQuote) => void;
  isLoading?: boolean;
}

export function CourierComparison({
  quotes,
  selectedCourier,
  onSelect,
  isLoading = false,
}: CourierComparisonProps) {
  const t = useTranslations("checkout.delivery");
  const tCourier = useTranslations("checkout.delivery.courier");

  if (isLoading) {
    return (
      <fieldset className="mb-6">
        <legend className="mb-2 block text-sm font-medium text-muted">
          {t("priceEstimate")}
        </legend>
        <p className="text-sm italic text-muted">{t("calculating")}</p>
      </fieldset>
    );
  }

  if (quotes.length === 0) return null;

  const anyFallback = quotes.some((q) => q.price_source !== "live");

  return (
    <fieldset className="mb-6">
      <legend className="mb-2 block text-sm font-medium text-muted">
        {quotes.length > 1 ? t("priceEstimate") : t("priceExact")}
      </legend>
      <div
        className="grid gap-3 sm:grid-cols-2"
        role="radiogroup"
        aria-label={t("priceEstimate")}
      >
        {quotes.map((quote) => {
          const selected = selectedCourier === quote.courier;
          const isFree = quote.cents === 0;
          return (
            <label
              key={quote.courier}
              className={cn(
                "flex cursor-pointer flex-col gap-1 rounded-brand border px-4 py-3 transition-colors",
                selected
                  ? "border-primary bg-primary/10"
                  : "border-border bg-surface hover:border-muted/40"
              )}
            >
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <input
                    type="radio"
                    name="courier-quote"
                    value={quote.courier}
                    checked={selected}
                    onChange={() => onSelect(quote)}
                    className="h-4 w-4 accent-primary"
                  />
                  <span className="font-medium text-text">
                    {tCourier(quote.courier)}
                  </span>
                </div>
                <span className="font-heading text-text">
                  {isFree ? t("freeShipping") : formatPrice(quote.cents)}
                </span>
              </div>
              {quote.estimated_delivery_days !== null && (
                <p className="ml-7 text-xs text-muted">
                  {t("deliveryEstimate", { days: quote.estimated_delivery_days })}
                </p>
              )}
            </label>
          );
        })}
      </div>

      {anyFallback && (
        <p className="mt-2 text-xs italic text-muted" role="note">
          {t("fallbackDisclaimer")}
        </p>
      )}
    </fieldset>
  );
}
