"use client";

import { useTranslations } from "next-intl";
import { TermsManager } from "@/components/admin/TermsManager";

export default function AdminTermsPage() {
  const t = useTranslations("admin.terms");

  return (
    <div>
      <div className="mb-8 flex items-center gap-2">
        <h1 className="font-heading text-2xl font-semibold text-charcoal">{t("title")}</h1>
      </div>
      <TermsManager />
    </div>
  );
}
