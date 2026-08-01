"use client";

import { useMemo } from "react";
import { useTranslations } from "next-intl";
import { usePathname } from "@/i18n/navigation";

type GuideEntry = {
  term: string;
  meaning: string;
};

type GuidePage = {
  key: string;
  match: (pathname: string) => boolean;
};

const GUIDE_PAGES: GuidePage[] = [
  { key: "productNew", match: (path) => path === "/admin/products/new" },
  { key: "productEdit", match: (path) => /^\/admin\/products\/[^/]+\/edit$/.test(path) },
  { key: "products", match: (path) => path === "/admin/products" },
  { key: "orderDetail", match: (path) => /^\/admin\/orders\/[^/]+$/.test(path) },
  { key: "orders", match: (path) => path === "/admin/orders" },
  { key: "inventoryMaterials", match: (path) => path === "/admin/inventory/materials" },
  { key: "inventoryRecipes", match: (path) => path === "/admin/inventory/recipes" },
  { key: "inventoryBatches", match: (path) => path === "/admin/inventory/batches" },
  { key: "inventoryMovements", match: (path) => path === "/admin/inventory/movements" },
  { key: "inventoryValuation", match: (path) => path.startsWith("/admin/inventory/valuation") },
  { key: "inventory", match: (path) => path === "/admin/inventory" },
  { key: "deliveryEcont", match: (path) => path === "/admin/econt" || path === "/admin/delivery/econt" },
  { key: "deliverySpeedy", match: (path) => path === "/admin/speedy" || path === "/admin/delivery/speedy" },
  { key: "delivery", match: (path) => path === "/admin/delivery" },
  { key: "paymentSettings", match: (path) => path === "/admin/settings/payments" },
  { key: "accounting", match: (path) => path === "/admin/accounting" },
  { key: "analytics", match: (path) => path === "/admin/analytics" },
  { key: "taxonomy", match: (path) => path === "/admin/taxonomy" },
  { key: "atelier", match: (path) => path === "/admin/atelier" },
  { key: "terms", match: (path) => path === "/admin/terms" },
  { key: "cookies", match: (path) => path === "/admin/cookies" },
  { key: "legal", match: (path) => path === "/admin/legal" },
  { key: "faq", match: (path) => path === "/admin/faq" },
  { key: "promotions", match: (path) => path === "/admin/promotions" },
  { key: "dashboard", match: (path) => path === "/admin" },
];

function currentGuideKey(pathname: string): string {
  return GUIDE_PAGES.find((page) => page.match(pathname))?.key ?? "dashboard";
}

export function AdminPageGuide() {
  const pathname = usePathname();
  const t = useTranslations("admin.pageGuide");
  const guideKey = useMemo(() => currentGuideKey(pathname), [pathname]);
  const steps = t.raw(`pages.${guideKey}.steps`) as string[];
  const watch = t.raw(`pages.${guideKey}.watch`) as string[];
  const glossary = t.raw(`pages.${guideKey}.glossary`) as GuideEntry[];

  return (
    <section className="mb-6 rounded-brand border border-champagne-beige bg-cream p-4 text-sm text-soft-brown">
      <div className="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase text-muted-gold">{t("eyebrow")}</p>
        </div>
        <p className="max-w-3xl leading-6 text-charcoal">{t(`pages.${guideKey}.purpose`)}</p>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        <div>
          <h3 className="font-semibold text-charcoal">{t("howTitle")}</h3>
          <ol className="mt-2 list-decimal space-y-1 pl-5 leading-6">
            {steps.map((step) => <li key={step}>{step}</li>)}
          </ol>
        </div>
        <div>
          <h3 className="font-semibold text-charcoal">{t("watchTitle")}</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 leading-6">
            {watch.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </div>
        <div>
          <h3 className="font-semibold text-charcoal">{t("glossaryTitle")}</h3>
          <dl className="mt-2 space-y-2 leading-6">
            {glossary.map((entry) => (
              <div key={entry.term}>
                <dt className="font-semibold text-charcoal">{entry.term}</dt>
                <dd>{entry.meaning}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </section>
  );
}
