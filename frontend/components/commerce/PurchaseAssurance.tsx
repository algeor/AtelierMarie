"use client";

import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

type PurchaseAssuranceVariant = "pdp" | "cart";

interface PurchaseAssuranceProps {
  variant?: PurchaseAssuranceVariant;
  className?: string;
}

const ITEM_KEYS = {
  pdp: ["craft", "delivery", "returns", "payment"],
  cart: ["delivery", "returns", "payment"],
} as const;

export function PurchaseAssurance({
  variant = "pdp",
  className,
}: PurchaseAssuranceProps) {
  const t = useTranslations("purchaseAssurance");
  const itemKeys = ITEM_KEYS[variant];

  return (
    <section
      aria-label={t("label")}
      className={cn(
        "rounded-brand border border-border/35 bg-surface/55 px-4 py-3",
        variant === "cart" ? "text-xs" : "text-sm",
        className,
      )}
    >
      <ul className="space-y-2">
        {itemKeys.map((key) => (
          <li key={key} className="flex gap-2.5 leading-5 text-muted">
            <span
              aria-hidden="true"
              className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-accent"
            />
            <span>
              <span className="font-semibold text-text">
                {t(`items.${key}.title`)}
              </span>{" "}
              {t(`items.${key}.text`)}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
