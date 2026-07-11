import { getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { Button } from "@/components/ui/Button";

export async function HeroSection() {
  const t = await getTranslations("home");

  return (
    <section
      className="w-full py-24 md:py-32 lg:py-40 px-4 sm:px-6 lg:px-8 flex flex-col items-center text-center bg-brand-gradient"
    >
      <h1 className="font-heading text-4xl md:text-5xl lg:text-6xl text-charcoal max-w-3xl">
        {t("heroTitle")}
      </h1>
      <p className="mt-6 text-lg md:text-xl text-soft-brown max-w-2xl">
        {t("heroSubtitle")}
      </p>
      <Link href="/products" className="mt-10">
        <Button size="lg">{t("shopCollection")}</Button>
      </Link>
    </section>
  );
}
