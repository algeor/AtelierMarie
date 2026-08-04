import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";
import { getFaq } from "@/lib/api";
import {
  buildFaqJsonLd,
  getLocalizedAlternates,
  serializeJsonLd,
} from "@/lib/seo";
import { FaqCategoryBrowser } from "@/components/faq/FaqCategoryBrowser";

interface FaqPageProps {
  params: Promise<{ locale: Locale }>;
}

export async function generateMetadata({
  params,
}: FaqPageProps): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "faq" });
  return {
    title: t("metaTitle"),
    description: t("metaDescription"),
    alternates: getLocalizedAlternates(locale, "/faq"),
  };
}

export default async function FaqPage({ params }: FaqPageProps) {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "faq" });
  const faq = await getFaq(locale);
  const jsonLd = buildFaqJsonLd(faq.sections);

  return (
    <main className="bg-page">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: serializeJsonLd(jsonLd) }}
      />

      <section className="editorial-band px-4 pb-12 pt-12 sm:px-6 sm:pb-16 sm:pt-16 lg:px-8">
        <div className="mx-auto max-w-[900px]">
          <div className="text-center">
            <p className="text-sm font-medium uppercase tracking-wide text-accent">
              {t("eyebrow")}
            </p>
            <h1 className="mt-3 font-heading text-4xl text-text sm:text-5xl">
              {t("title")}
            </h1>
            <p className="mx-auto mt-5 max-w-2xl text-base leading-8 text-muted sm:text-lg">
              {t("subtitle")}
            </p>
            <Link
              href="/contact"
              className="mt-6 inline-flex min-h-[48px] items-center rounded-brand border border-accent px-5 py-3 text-sm font-medium text-text transition-colors duration-fast hover:bg-accent/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page"
            >
              {t("contactUs")}
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-[900px] px-4 pb-14 sm:px-6 lg:px-8">
        <FaqCategoryBrowser
          sections={faq.sections}
          categoryLabel={t("categoryNavLabel")}
        />
      </section>

      <section className="bg-surface/45 py-12">
        <div className="mx-auto max-w-[900px] px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-5 border-y editorial-divider py-8 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="font-heading text-2xl text-text">
                {t("bannerTitle")}
              </h2>
              <p className="mt-2 max-w-2xl text-sm leading-7 text-muted">
                {t("bannerText")}
              </p>
            </div>
            <Link
              href="/contact"
              className="inline-flex min-h-[48px] shrink-0 items-center justify-center rounded-brand bg-text px-5 py-3 text-sm font-medium text-page transition-colors duration-fast hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
            >
              {t("contactUs")}
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-[900px] gap-6 px-4 py-12 sm:grid-cols-3 sm:px-6 lg:px-8">
        {[0, 1, 2].map((index) => (
          <div
            key={index}
            className="border-l border-accent/35 bg-surface-elevated/35 px-5 py-2"
          >
            <h3 className="font-heading text-lg text-text">
              {t(`trustCards.${index}.title`)}
            </h3>
            <p className="mt-2 text-sm leading-6 text-muted">
              {t(`trustCards.${index}.text`)}
            </p>
          </div>
        ))}
      </section>
    </main>
  );
}
