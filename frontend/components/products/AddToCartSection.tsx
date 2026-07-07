"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { QuantitySelector } from "./QuantitySelector";

interface AddToCartSectionProps {
  productId: string;
  stock: number;
}

export function AddToCartSection({ productId, stock }: AddToCartSectionProps) {
  const [quantity, setQuantity] = useState(1);
  const [isConfirming, setIsConfirming] = useState(false);

  const isOutOfStock = stock === 0;

  function handleAddToCart() {
    if (isConfirming || isOutOfStock) return;

    // Day 3 stub — will wire to cart API in Day 4
    console.log(`[stub] Add to cart: ${productId} x${quantity}`);

    setIsConfirming(true);
    setTimeout(() => {
      setIsConfirming(false);
    }, 1500);
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
        disabled={isOutOfStock || isConfirming}
        size="lg"
        className="w-full sm:w-auto"
      >
        {isOutOfStock
          ? "Out of Stock"
          : isConfirming
            ? "Added ✓"
            : "Add to Cart"}
      </Button>

      {/* Screen reader announcement */}
      <div aria-live="polite" role="status" className="sr-only">
        {isConfirming ? `Added ${quantity} item${quantity > 1 ? "s" : ""} to cart` : ""}
      </div>
    </div>
  );
}
