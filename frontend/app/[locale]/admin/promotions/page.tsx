"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { AdminInfoPopover } from "@/components/admin/AdminInfoPopover";
import { CampaignsPanel } from "@/components/admin/promotions/CampaignsPanel";
import { BannerPanel } from "@/components/admin/promotions/BannerPanel";

type Tab = "campaigns" | "banner";

export default function AdminPromotionsPage() {
  const t = useTranslations("admin");
  const [tab, setTab] = useState<Tab>("campaigns");

  return (
    <div>
      <div className="mb-8 flex items-center gap-2">
        <h1 className="font-heading text-2xl font-semibold text-charcoal">
          {t("promotions.title")}
        </h1>
        <AdminInfoPopover content={t("promotions.subtitle")} />
      </div>

      <div className="mb-6 flex gap-1 border-b border-champagne-beige" role="tablist">
        {(["campaigns", "banner"] as const).map((key) => (
          <button
            key={key}
            role="tab"
            aria-selected={tab === key}
            onClick={() => setTab(key)}
            className={cn(
              "-mb-px border-b-2 px-4 py-2 text-sm font-medium transition-colors",
              tab === key
                ? "border-muted-gold text-charcoal"
                : "border-transparent text-soft-brown hover:text-charcoal"
            )}
          >
            {key === "campaigns" ? t("promotions.campaigns") : t("promotions.topBanner")}
          </button>
        ))}
      </div>

      {tab === "campaigns" ? <CampaignsPanel /> : <BannerPanel />}
    </div>
  );
}
