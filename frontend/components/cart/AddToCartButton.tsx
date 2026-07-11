"use client";

import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { useCart } from "@/contexts/CartContext";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

interface AddToCartButtonProps {
  productId: string;
  stock: number;
  quantity?: number;
  className?: string;
}

export function AddToCartButton({
  productId,
  stock,
  quantity = 1,
  className,
}: AddToCartButtonProps) {
  const t = useTranslations("products");
  const { addToCart, openDrawer } = useCart();
  const [status, setStatus] = useState<"idle" | "loading" | "success">("idle");

  const isOutOfStock = stock === 0;

  const handleClick = useCallback(
    async (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();

      if (status !== "idle" || isOutOfStock) return;

      setStatus("loading");
      try {
        await addToCart(productId, quantity);
        setStatus("success");
        openDrawer();
        setTimeout(() => setStatus("idle"), 1500);
      } catch {
        setStatus("idle");
      }
    },
    [addToCart, openDrawer, productId, quantity, status, isOutOfStock]
  );

  if (isOutOfStock) {
    return (
      <Button
        disabled
        variant="secondary"
        className={cn("w-full sm:w-auto", className)}
      >
        {t("outOfStock")}
      </Button>
    );
  }

  return (
    <Button
      onClick={handleClick}
      disabled={status !== "idle"}
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
  );
}
