"use client";

import { useTranslations } from "next-intl";
import { FaqManager } from "@/components/admin/FaqManager";

export default function AdminFaqPage() {
  const t = useTranslations("admin.faq");

  return (
    <div>
      <div className="mb-8">
        <h1 className="font-heading text-2xl font-semibold text-charcoal">{t("title")}</h1>
        <p className="mt-1 text-sm text-soft-brown">{t("subtitle")}</p>
      </div>
      <FaqManager />
    </div>
  );
}
