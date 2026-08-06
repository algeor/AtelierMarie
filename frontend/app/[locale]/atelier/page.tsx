import { getAbout, getPublicSiteMedia } from "@/lib/api";
import { getAboutJsonLd, getLocalizedAlternates } from "@/lib/seo";
import type { Locale } from "@/i18n/routing";
import { renderAtelierSection } from "@/components/atelier/AtelierSections";
import { getTranslations } from "next-intl/server";

export async function generateMetadata({ params }: { params: Promise<{ locale: Locale }> }) {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "atelierPage" });
  return {
    title: t("metaTitle"),
    description: t("metaDescription"),
    alternates: getLocalizedAlternates(locale, "/atelier"),
  };
}

export default async function AtelierPage({ params }: { params: Promise<{ locale: Locale }> }) {
  const { locale } = await params;
  const [{ sections }, siteMedia] = await Promise.all([
    getAbout(locale),
    getPublicSiteMedia().catch(() => null),
  ]);

  return (
    <main className="bg-page text-text">
      <script
        type="application/ld+json"
        suppressHydrationWarning
        dangerouslySetInnerHTML={{ __html: JSON.stringify(getAboutJsonLd(locale)) }}
      />
      {sections.map((section) => renderAtelierSection(section, siteMedia?.assets ?? null))}
    </main>
  );
}
