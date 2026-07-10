"use client";

import { useState } from "react";
import { useCart } from "@/contexts/CartContext";
import { Button } from "@/components/ui/Button";
import { QuantitySelector } from "./QuantitySelector";

interface AddToCartSectionProps {
  productId: string;
  stock: number;
}

export function AddToCartSection({ productId, stock }: AddToCartSectionProps) {
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
    <div className="flex flex-col gap-4 pt-4 border-t border-champagne-beige">
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
          ? "Out of Stock"
          : status === "success"
            ? "Added ✓"
            : "Add to Cart"}
      </Button>

      {/* Screen reader announcement */}
      <div aria-live="polite" role="status" className="sr-only">
        {status === "success"
          ? `Added ${quantity} item${quantity > 1 ? "s" : ""} to cart`
          : ""}
      </div>
    </div>
  );
}
