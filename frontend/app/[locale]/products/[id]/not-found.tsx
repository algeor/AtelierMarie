import { getTranslations } from "next-intl/server";
import { BrandedRecoveryPage } from "@/components/errors/BrandedRecoveryPage";

export default async function ProductNotFound() {
  const t = await getTranslations("products");
  const tErrorPages = await getTranslations("errorPages");
  const tCommon = await getTranslations("common");

  return (
    <BrandedRecoveryPage
      eyebrow={tErrorPages("notFound.eyebrow")}
      title={t("notFound")}
      description={t("notFoundDescription")}
      backLabel={t("notFoundCta")}
      backHref="/products"
      brandName={tCommon("appName")}
      brandMarkTitle={tErrorPages("brandMarkTitle")}
    />
  );
}
