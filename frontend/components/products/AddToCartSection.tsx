"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { useCart } from "@/contexts/CartContext";
import { Button } from "@/components/ui/Button";
import { PurchaseAssurance } from "@/components/commerce/PurchaseAssurance";
import { QuantitySelector } from "./QuantitySelector";

interface AddToCartSectionProps {
  productId: string;
  stock: number;
}

export function AddToCartSection({ productId, stock }: AddToCartSectionProps) {
  const t = useTranslations("products");
  const { addToCart, openDrawer } = useCart();
  const [quantity, setQuantity] = useState(1);
  const [status, setStatus] = useState<"idle" | "loading" | "success">("idle");

  const isOutOfStock = stock === 0;

  async function handleAddToCart() {
    if (status !== "idle" || isOutOfStock) return;

    setStatus("loading");
    try {
      await addToCart(productId, quantity);
      setStatus("success");
      openDrawer();
      setTimeout(() => {
        setStatus("idle");
        setQuantity(1);
      }, 1500);
    } catch {
      setStatus("idle");
    }
  }

  return (
    <div className="flex flex-col gap-4 border-t editorial-divider pt-5">
      {!isOutOfStock && (
        <QuantitySelector
          quantity={quantity}
          onQuantityChange={setQuantity}
          maxQuantity={stock}
        />
      )}

      <Button
        onClick={handleAddToCart}
        disabled={isOutOfStock || status !== "idle"}
        isLoading={status === "loading"}
        size="lg"
        className="w-full sm:w-auto"
      >
        {isOutOfStock
          ? t("outOfStock")
          : status === "success"
            ? `${t("added")} ✓`
            : t("addToCart")}
      </Button>

      <PurchaseAssurance />

      <Link
        href="/faq#care"
        className="w-fit rounded-brand text-sm font-medium text-muted underline-offset-4 transition-colors duration-fast hover:text-text hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page"
      >
        {t("questions")}
      </Link>

      {/* Screen reader announcement */}
      <div aria-live="polite" role="status" className="sr-only">
        {status === "success" ? t("addedToCart", { count: quantity }) : ""}
      </div>
    </div>
  );
}
