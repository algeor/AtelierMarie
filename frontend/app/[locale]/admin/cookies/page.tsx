"use client";

import { useTranslations } from "next-intl";
import { CookiesManager } from "@/components/admin/CookiesManager";

export default function AdminCookiesPage() {
  const t = useTranslations("admin.cookies");

  return (
    <div>
      <div className="mb-8 flex items-center gap-2">
        <h1 className="font-heading text-2xl font-semibold text-charcoal">{t("title")}</h1>
      </div>
      <CookiesManager />
    </div>
  );
}
