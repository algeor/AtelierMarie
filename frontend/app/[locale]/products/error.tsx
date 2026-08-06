"use client";

import { useTranslations } from "next-intl";
import { BrandedRecoveryPage } from "@/components/errors/BrandedRecoveryPage";

export default function ProductsError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const t = useTranslations("products");
  const tErrorPages = useTranslations("errorPages");
  const tGenericError = useTranslations("errorPages.generic");
  const tCommon = useTranslations("common");

  return (
    <BrandedRecoveryPage
      eyebrow={tGenericError("eyebrow")}
      title={t("loadErrorTitle")}
      description={t("loadErrorDescription")}
      backLabel={tGenericError("backHome")}
      tryAgainLabel={t("tryAgain")}
      onReset={reset}
      brandName={tCommon("appName")}
      brandMarkTitle={tErrorPages("brandMarkTitle")}
    />
  );
}
