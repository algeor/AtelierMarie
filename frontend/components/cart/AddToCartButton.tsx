"use client";

import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { useCart } from "@/contexts/CartContext";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import { trackAnalytics } from "@/lib/analytics";

interface AddToCartButtonProps {
  productId: string;
  canOrder?: boolean;
  availableNow?: boolean;
  quantity?: number;
  className?: string;
  disabled?: boolean;
  tabIndex?: number;
  showCraftedLaterNote?: boolean;
}

export function AddToCartButton({
  productId,
  canOrder = true,
  availableNow = true,
  quantity = 1,
  className,
  disabled = false,
  tabIndex,
  showCraftedLaterNote = true,
}: AddToCartButtonProps) {
  const t = useTranslations("products");
  const { addToCart, openDrawer } = useCart();
  const [status, setStatus] = useState<"idle" | "loading" | "success">("idle");
  const isCraftedLater = canOrder && !availableNow;

  const handleClick = useCallback(
    async (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();

      if (disabled || status !== "idle" || !canOrder) return;

      setStatus("loading");
      try {
        await addToCart(productId, quantity);
        trackAnalytics("add_to_cart", { product_id: productId, quantity });
        setStatus("success");
        openDrawer();
        setTimeout(() => setStatus("idle"), 1500);
      } catch {
        setStatus("idle");
      }
    },
    [addToCart, canOrder, disabled, openDrawer, productId, quantity, status]
  );

  return (
    <div className="space-y-1.5">
      <Button
        onClick={handleClick}
        disabled={disabled || status !== "idle" || !canOrder}
        tabIndex={tabIndex}
        isLoading={status === "loading"}
        className={cn("w-full sm:w-auto", className)}
      >
        {status === "success" ? (
          <span className="inline-flex items-center gap-1.5">
            <svg
              className="w-5 h-5 motion-safe:animate-checkmark"
              viewBox="0 0 20 20"
              fill="currentColor"
              aria-hidden="true"
            >
              <path
                fillRule="evenodd"
                d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                clipRule="evenodd"
              />
            </svg>
            {t("added")}
          </span>
        ) : (
          t("addToCart")
        )}
      </Button>
      {showCraftedLaterNote && isCraftedLater && (
        <p className="text-xs leading-5 text-muted">{t("craftedLaterShort")}</p>
      )}
    </div>
  );
}
