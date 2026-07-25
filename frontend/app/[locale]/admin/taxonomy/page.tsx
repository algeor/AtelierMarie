"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { TaxonomyManager } from "@/components/admin/TaxonomyManager";
import type { TaxonomyKind } from "@/lib/types";

const TABS: { kind: TaxonomyKind; labelKey: string }[] = [
  { kind: "product-types", labelKey: "taxonomy.productTypes" },
  { kind: "categories", labelKey: "taxonomy.categories" },
  { kind: "labels", labelKey: "taxonomy.labels" },
];

export default function TaxonomyPage() {
  const t = useTranslations("admin");
  const [activeKind, setActiveKind] = useState<TaxonomyKind>("product-types");

  return (
    <div>
      <div className="mb-8">
        <h1 className="font-heading text-2xl font-semibold text-charcoal">{t("taxonomy.title")}</h1>
        <p className="mt-1 text-sm text-soft-brown">{t("taxonomy.subtitle")}</p>
      </div>

      <div
        role="tablist"
        aria-label={t("taxonomy.title")}
        className="mb-6 flex gap-2 border-b border-champagne-beige"
      >
        {TABS.map((tab) => (
          <button
            key={tab.kind}
            role="tab"
            aria-selected={activeKind === tab.kind}
            onClick={() => setActiveKind(tab.kind)}
            className={cn(
              "-mb-px border-b-2 px-4 py-2 text-sm font-medium transition-colors",
              activeKind === tab.kind
                ? "border-muted-gold text-charcoal"
                : "border-transparent text-soft-brown hover:text-charcoal"
            )}
          >
            {t(tab.labelKey)}
          </button>
        ))}
      </div>

      <div className="rounded-brand border border-champagne-beige bg-cream p-6">
        <TaxonomyManager kind={activeKind} />
      </div>
    </div>
  );
}
