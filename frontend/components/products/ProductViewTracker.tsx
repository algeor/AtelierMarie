"use client";

import { useEffect } from "react";
import { trackAnalytics } from "@/lib/analytics";

interface ProductViewTrackerProps {
  productId: string;
  category: string | null;
  valueCents: number;
}

export function ProductViewTracker({ productId, category, valueCents }: ProductViewTrackerProps) {
  useEffect(() => {
    trackAnalytics("product_view", {
      product_id: productId,
      category,
      value_cents: valueCents,
      currency: "BGN",
    });
  }, [category, productId, valueCents]);

  return null;
}
