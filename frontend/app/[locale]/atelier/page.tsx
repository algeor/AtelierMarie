import { getAbout } from "@/lib/api";
import { getAboutJsonLd, getLocalizedAlternates } from "@/lib/seo";
import type { Locale } from "@/i18n/routing";
import { renderAtelierSection } from "@/components/atelier/AtelierSections";

export async function generateMetadata({ params }: { params: Promise<{ locale: Locale }> }) {
  const { locale } = await params;
  return {
    title: "The Atelier Marie | Inside Our Atelier",
    description: "The story, craft, and handmade process behind The Atelier Marie candles.",
    alternates: getLocalizedAlternates(locale, "/atelier"),
  };
}

export default async function AtelierPage({ params }: { params: Promise<{ locale: Locale }> }) {
  const { locale } = await params;
  const { sections } = await getAbout(locale);

  return (
    <main className="bg-warm-ivory">
      <script
        type="application/ld+json"
        suppressHydrationWarning
        dangerouslySetInnerHTML={{ __html: JSON.stringify(getAboutJsonLd(locale)) }}
      />
      {sections.map((section) => renderAtelierSection(section))}
    </main>
  );
}
