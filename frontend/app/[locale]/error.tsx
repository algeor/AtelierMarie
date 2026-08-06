"use client";

import { useTranslations } from "next-intl";
import { BrandedRecoveryPage } from "@/components/errors/BrandedRecoveryPage";

export default function ErrorPage({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const t = useTranslations("errorPages.generic");
  const tErrorPages = useTranslations("errorPages");
  const tCommon = useTranslations("common");

  return (
    <BrandedRecoveryPage
      eyebrow={t("eyebrow")}
      title={t("title")}
      description={t("description")}
      backLabel={t("backHome")}
      tryAgainLabel={t("tryAgain")}
      onReset={reset}
      brandName={tCommon("appName")}
      brandMarkTitle={tErrorPages("brandMarkTitle")}
    />
  );
}
