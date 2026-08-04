import { getTranslations } from "next-intl/server";
import { BrandedRecoveryPage } from "@/components/errors/BrandedRecoveryPage";

export default async function NotFound() {
  const t = await getTranslations("errorPages.notFound");
  const tErrorPages = await getTranslations("errorPages");
  const tCommon = await getTranslations("common");

  return (
    <BrandedRecoveryPage
      code="404"
      eyebrow={t("eyebrow")}
      title={t("title")}
      description={t("description")}
      backLabel={t("backHome")}
      brandName={tCommon("appName")}
      brandMarkTitle={tErrorPages("brandMarkTitle")}
    />
  );
}
