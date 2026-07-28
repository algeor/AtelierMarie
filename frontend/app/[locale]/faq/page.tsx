import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";
import { getFaq } from "@/lib/api";
import { buildFaqJsonLd, getLocalizedAlternates, serializeJsonLd } from "@/lib/seo";
import { FaqAccordion } from "@/components/faq/FaqAccordion";

interface FaqPageProps {
  params: Promise<{ locale: Locale }>;
}

export async function generateMetadata({ params }: FaqPageProps): Promise<Metadata> {
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
    <main className="bg-warm-ivory">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: serializeJsonLd(jsonLd) }}
      />

      <section className="mx-auto max-w-[900px] px-4 pb-10 pt-12 sm:px-6 sm:pb-14 sm:pt-16 lg:px-8">
        <div className="text-center">
          <p className="text-sm font-medium uppercase tracking-wide text-muted-gold">
            {t("eyebrow")}
          </p>
          <h1 className="mt-3 font-heading text-4xl text-charcoal sm:text-5xl">
            {t("title")}
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-8 text-soft-brown sm:text-lg">
            {t("subtitle")}
          </p>
          <Link
            href="/contact"
            className="mt-6 inline-flex min-h-[48px] items-center rounded-brand border border-muted-gold px-5 py-3 text-sm font-medium text-charcoal transition-colors duration-fast hover:bg-muted-gold/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-muted-gold focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory"
          >
            {t("contactUs")}
          </Link>
        </div>
      </section>

      <section className="mx-auto max-w-[900px] space-y-12 px-4 pb-14 sm:px-6 lg:px-8">
        {faq.sections.map((section) => (
          <section key={section.slug} id={section.slug} className="scroll-mt-28">
            <div className="mb-5 flex items-center gap-4">
              {section.icon && (
                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-white text-xl shadow-sm">
                  {section.icon}
                </span>
              )}
              <div>
                <h2 className="font-heading text-2xl text-charcoal sm:text-3xl">
                  {section.title}
                </h2>
                <div className="mt-2 h-0.5 w-20 bg-muted-gold" />
              </div>
            </div>
            <FaqAccordion items={section.items} />
          </section>
        ))}
      </section>

      <section className="bg-cream py-12">
        <div className="mx-auto max-w-[900px] px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-5 border-y border-champagne-beige py-8 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="font-heading text-2xl text-charcoal">{t("bannerTitle")}</h2>
              <p className="mt-2 max-w-2xl text-sm leading-7 text-soft-brown">
                {t("bannerText")}
              </p>
            </div>
            <Link
              href="/contact"
              className="inline-flex min-h-[48px] shrink-0 items-center justify-center rounded-brand bg-charcoal px-5 py-3 text-sm font-medium text-white transition-colors duration-fast hover:bg-soft-brown focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-charcoal focus-visible:ring-offset-2 focus-visible:ring-offset-cream"
            >
              {t("contactUs")}
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-[900px] gap-4 px-4 py-12 sm:grid-cols-3 sm:px-6 lg:px-8">
        {[0, 1, 2].map((index) => (
          <div key={index} className="rounded-brand border border-champagne-beige bg-white p-5">
            <h3 className="font-heading text-lg text-charcoal">
              {t(`trustCards.${index}.title`)}
            </h3>
            <p className="mt-2 text-sm leading-6 text-soft-brown">
              {t(`trustCards.${index}.text`)}
            </p>
          </div>
        ))}
      </section>
    </main>
  );
}
