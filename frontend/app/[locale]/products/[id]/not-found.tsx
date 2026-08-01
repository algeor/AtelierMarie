import { getTranslations } from "next-intl/server";
import { Button } from "@/components/ui/Button";
import { Link } from "@/i18n/navigation";

export default async function ProductNotFound() {
  const t = await getTranslations("products");

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 text-center">
      <h1 className="font-heading text-3xl text-charcoal mb-4">
        {t("notFound")}
      </h1>
      <p className="text-soft-brown text-lg mb-8">
        {t("notFoundDescription")}
      </p>
      <Link href="/products">
        <Button variant="primary">{t("notFoundCta")}</Button>
      </Link>
    </div>
  );
}
