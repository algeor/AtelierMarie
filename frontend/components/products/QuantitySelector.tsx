"use client";

import { cn } from "@/lib/utils";

interface QuantitySelectorProps {
  quantity: number;
  onQuantityChange: (quantity: number) => void;
  maxQuantity: number;
}

export function QuantitySelector({
  quantity,
  onQuantityChange,
  maxQuantity,
}: QuantitySelectorProps) {
  const max = Math.min(10, maxQuantity);
  const canDecrement = quantity > 1;
  const canIncrement = quantity < max;

  return (
    <div className="flex items-center gap-3" aria-label={`Quantity: ${quantity}`}>
      <button
        onClick={() => canDecrement && onQuantityChange(quantity - 1)}
        disabled={!canDecrement}
        aria-label="Decrease quantity"
        className={cn(
          "min-w-[44px] min-h-[44px] inline-flex items-center justify-center rounded-brand border border-champagne-beige text-lg font-medium",
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
        className="min-w-[2rem] text-center text-lg font-medium text-charcoal"
        aria-live="polite"
        aria-atomic="true"
      >
        {quantity}
      </span>
      <button
        onClick={() => canIncrement && onQuantityChange(quantity + 1)}
        disabled={!canIncrement}
        aria-label="Increase quantity"
        className={cn(
          "min-w-[44px] min-h-[44px] inline-flex items-center justify-center rounded-brand border border-champagne-beige text-lg font-medium",
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
  );
}
