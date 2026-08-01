"use client";

import { useTranslations } from "next-intl";
import { AdminInfoPopover } from "@/components/admin/AdminInfoPopover";
import { FaqManager } from "@/components/admin/FaqManager";

export default function AdminFaqPage() {
  const t = useTranslations("admin.faq");

  return (
    <div>
      <div className="mb-8 flex items-center gap-2">
        <h1 className="font-heading text-2xl font-semibold text-charcoal">{t("title")}</h1>
        <AdminInfoPopover content={t("subtitle")} />
      </div>
      <FaqManager />
    </div>
  );
}
