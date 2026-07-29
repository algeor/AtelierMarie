import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import type { Locale } from "@/i18n/routing";
import { Link } from "@/i18n/navigation";
import { policyPath } from "@/lib/legal";
import { getLocalizedAlternates } from "@/lib/seo";
import enMessages from "@/messages/en.json";
import bgMessages from "@/messages/bg.json";

interface CookiesPageProps {
  params: Promise<{ locale: Locale }>;
}

interface CookieInventoryItem {
  name: string;
  purpose: string;
  type: string;
  duration: string;
}

interface CookieSection {
  id: string;
  title: string;
  body: string[];
}

interface CookiesMessages {
  metaTitle: string;
  metaDescription: string;
  eyebrow: string;
  title: string;
  subtitle: string;
  lastUpdated: string;
  inventoryTitle: string;
  headers: { name: string; purpose: string; type: string; duration: string };
  cookies: CookieInventoryItem[];
  sections: CookieSection[];
}

function getCookiesMessages(locale: Locale): CookiesMessages {
  return (locale === "bg" ? bgMessages.cookies : enMessages.cookies) as CookiesMessages;
}

export async function generateMetadata({ params }: CookiesPageProps): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "cookies" });

  return {
    title: t("metaTitle"),
    description: t("metaDescription"),
    alternates: getLocalizedAlternates(locale, policyPath("cookies")),
  };
}

export default async function CookiesPage({ params }: CookiesPageProps) {
  const { locale } = await params;
  const cookies = getCookiesMessages(locale);
  const legal = locale === "bg" ? bgMessages.legal : enMessages.legal;

  return (
    <main className="overflow-x-hidden bg-warm-ivory">
      <section id="cookies-top" className="mx-auto max-w-5xl scroll-mt-28 px-4 pb-8 pt-12 sm:px-6 sm:pt-16 lg:px-8">
        <p className="text-sm font-medium uppercase tracking-[0.08em] text-muted-gold">{cookies.eyebrow}</p>
        <div className="mt-3 max-w-3xl">
          <h1 className="break-words font-heading text-3xl text-charcoal sm:text-5xl">{cookies.title}</h1>
          <p className="mt-5 max-w-full break-words text-base leading-8 text-soft-brown sm:text-lg">{cookies.subtitle}</p>
          <p className="mt-4 text-sm text-soft-brown/75">{cookies.lastUpdated}</p>
        </div>
      </section>

      <article className="mx-auto max-w-5xl px-4 pb-16 sm:px-6 lg:px-8">
        <section className="min-w-0 rounded-brand border border-champagne-beige bg-cream p-5">
          <h2 className="font-heading text-2xl text-charcoal">{cookies.inventoryTitle}</h2>
          <div className="mt-5 overflow-x-auto">
            <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
              <thead className="text-charcoal">
                <tr>
                  <th className="border-b border-champagne-beige px-3 py-2 font-medium">{cookies.headers.name}</th>
                  <th className="border-b border-champagne-beige px-3 py-2 font-medium">{cookies.headers.purpose}</th>
                  <th className="border-b border-champagne-beige px-3 py-2 font-medium">{cookies.headers.type}</th>
                  <th className="border-b border-champagne-beige px-3 py-2 font-medium">{cookies.headers.duration}</th>
                </tr>
              </thead>
              <tbody className="text-soft-brown">
                {cookies.cookies.map((item) => (
                  <tr key={item.name}>
                    <td className="border-b border-champagne-beige px-3 py-3 font-medium text-charcoal">{item.name}</td>
                    <td className="border-b border-champagne-beige px-3 py-3">{item.purpose}</td>
                    <td className="border-b border-champagne-beige px-3 py-3">{item.type}</td>
                    <td className="border-b border-champagne-beige px-3 py-3">{item.duration}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <div className="mt-12 space-y-10 sm:space-y-12">
          {cookies.sections.map((section) => (
            <section key={section.id} id={section.id} className="min-w-0 scroll-mt-28 border-b border-champagne-beige pb-10 last:border-b-0">
              <h2 className="break-words font-heading text-2xl text-charcoal sm:text-3xl">{section.title}</h2>
              <div className="mt-3 h-0.5 w-16 bg-muted-gold" />
              <div className="mt-5 max-w-full space-y-4 break-words text-[15px] leading-7 text-soft-brown sm:text-base sm:leading-8">
                {section.body.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
              </div>
            </section>
          ))}
        </div>

        <div className="mt-8 flex flex-wrap gap-3 text-sm">
          <Link href={policyPath("privacy")} className="rounded-pill bg-cream px-4 py-2 text-soft-brown underline-offset-4 hover:text-charcoal hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-muted-gold">{legal.privacyPolicy}</Link>
          <Link href={policyPath("terms")} className="rounded-pill bg-cream px-4 py-2 text-soft-brown underline-offset-4 hover:text-charcoal hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-muted-gold">{legal.termsConditions}</Link>
        </div>
      </article>
    </main>
  );
}
