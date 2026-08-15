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
  canOrder?: boolean;
  availableNow?: boolean;
  shipsWhenComplete?: boolean;
}

export function AddToCartSection({
  productId,
  canOrder = true,
  availableNow = true,
  shipsWhenComplete = true,
}: AddToCartSectionProps) {
  const t = useTranslations("products");
  const { addToCart, openDrawer } = useCart();
  const [quantity, setQuantity] = useState(1);
  const [status, setStatus] = useState<"idle" | "loading" | "success">("idle");
  const isCraftedLater = canOrder && !availableNow;

  async function handleAddToCart() {
    if (status !== "idle" || !canOrder) return;

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
      <QuantitySelector
        quantity={quantity}
        onQuantityChange={setQuantity}
        maxQuantity={10}
      />

      {isCraftedLater && (
        <div className="rounded-brand border border-border/40 bg-surface/70 px-4 py-3 text-sm leading-6 text-muted">
          <p>{t("craftedLater")}</p>
          {shipsWhenComplete && <p>{t("shipsWhenComplete")}</p>}
        </div>
      )}

      <Button
        onClick={handleAddToCart}
        disabled={!canOrder || status !== "idle"}
        isLoading={status === "loading"}
        size="lg"
        className="w-full sm:w-auto"
      >
        {status === "success" ? `${t("added")} ✓` : t("addToCart")}
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
