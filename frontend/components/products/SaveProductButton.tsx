"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useOptionalSavedProducts } from "@/contexts/SavedProductsContext";
import { cn } from "@/lib/utils";

interface SaveProductButtonProps {
  productId: string;
  className?: string;
  variant?: "floating" | "inline";
}

export function SaveProductButton({
  productId,
  className,
  variant = "floating",
}: SaveProductButtonProps) {
  const t = useTranslations("products");
  const savedProducts = useOptionalSavedProducts();
  const [isPending, setIsPending] = useState(false);
  if (!savedProducts) return null;

  const { isSaved, toggleSaved } = savedProducts;
  const saved = isSaved(productId);

  async function handleClick() {
    if (isPending) return;
    setIsPending(true);
    try {
      await toggleSaved(productId);
    } finally {
      setIsPending(false);
    }
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={isPending}
      aria-pressed={saved}
      aria-label={saved ? t("removeSavedProduct") : t("saveProduct")}
      title={saved ? t("removeSavedProduct") : t("saveProduct")}
      className={cn(
        "inline-flex items-center justify-center rounded-full border transition-all duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 disabled:cursor-wait disabled:opacity-70",
        variant === "floating"
          ? "h-10 w-10 border-border/35 bg-page/90 text-text shadow-lg shadow-text/10 backdrop-blur-md hover:-translate-y-0.5 hover:bg-surface"
          : "h-11 gap-2 border-border/40 bg-surface/60 px-4 text-sm font-medium text-text hover:bg-surface",
        saved && "border-accent/40 bg-accent-soft/55 text-accent",
        className,
      )}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill={saved ? "currentColor" : "none"}
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="h-5 w-5"
        aria-hidden="true"
      >
        <path d="M6.75 4.75A2.25 2.25 0 0 1 9 2.5h6a2.25 2.25 0 0 1 2.25 2.25v16.5L12 17.75l-5.25 3.5V4.75Z" />
      </svg>
      {variant === "inline" && <span>{saved ? t("saved") : t("save")}</span>}
    </button>
  );
}
