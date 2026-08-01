import type { Metadata } from "next";
import type { Locale } from "@/i18n/routing";
import { Link } from "@/i18n/navigation";
import { getPrivacy } from "@/lib/api";
import { loadLegalIdentity, policyPath } from "@/lib/legal";
import { getLocalizedAlternates } from "@/lib/seo";
import type { PrivacyResponse } from "@/lib/types";
import enMessages from "@/messages/en.json";
import bgMessages from "@/messages/bg.json";

interface PrivacyPageProps {
  params: Promise<{ locale: Locale }>;
}

interface PolicySection {
  id: string;
  title: string;
  nav: string;
  body: string[];
}

interface PrivacyMessages {
  metaTitle: string;
  metaDescription: string;
  eyebrow: string;
  title: string;
  subtitle: string;
  lastUpdated: string;
  controllerTitle: string;
  sections: PolicySection[];
}

function getPrivacyMessages(locale: Locale): PrivacyMessages {
  return (locale === "bg" ? bgMessages.privacy : enMessages.privacy) as PrivacyMessages;
}

function mapPrivacyResponse(privacy: PrivacyResponse): PrivacyMessages {
  return {
    metaTitle: privacy.meta_title,
    metaDescription: privacy.meta_description,
    eyebrow: privacy.eyebrow,
    title: privacy.title,
    subtitle: privacy.subtitle,
    lastUpdated: privacy.last_updated,
    controllerTitle: privacy.controller_title,
    sections: privacy.sections,
  };
}

async function getEditablePrivacyMessages(locale: Locale): Promise<PrivacyMessages> {
  try {
    return mapPrivacyResponse(await getPrivacy(locale));
  } catch {
    return getPrivacyMessages(locale);
  }
}

export async function generateMetadata({ params }: PrivacyPageProps): Promise<Metadata> {
  const { locale } = await params;
  const privacy = await getEditablePrivacyMessages(locale);

  return {
    title: privacy.metaTitle,
    description: privacy.metaDescription,
    alternates: getLocalizedAlternates(locale, policyPath("privacy")),
  };
}

export default async function PrivacyPage({ params }: PrivacyPageProps) {
  const { locale } = await params;
  const privacy = await getEditablePrivacyMessages(locale);
  const legal = locale === "bg" ? bgMessages.legal : enMessages.legal;
  const legalIdentity = await loadLegalIdentity();

  return (
    <main className="overflow-x-hidden bg-warm-ivory">
      <section id="privacy-top" className="mx-auto max-w-5xl scroll-mt-28 px-4 pb-8 pt-12 sm:px-6 sm:pt-16 lg:px-8">
        <p className="text-sm font-medium uppercase tracking-[0.08em] text-muted-gold">{privacy.eyebrow}</p>
        <div className="mt-3 max-w-3xl">
          <h1 className="break-words font-heading text-3xl text-charcoal sm:text-5xl">{privacy.title}</h1>
          <p className="mt-5 max-w-full break-words text-base leading-8 text-soft-brown sm:text-lg">{privacy.subtitle}</p>
          <p className="mt-4 text-sm text-soft-brown/75">{privacy.lastUpdated}</p>
        </div>
      </section>

      <div className="mx-auto grid max-w-5xl min-w-0 gap-10 px-4 pb-16 sm:px-6 lg:grid-cols-[220px_minmax(0,760px)] lg:px-8">
        <aside className="min-w-0 lg:sticky lg:top-24 lg:self-start" aria-label={privacy.title}>
          <nav className="border-y border-champagne-beige py-4 lg:border-y-0 lg:border-l lg:py-0 lg:pl-5">
            <ul className="grid min-w-0 grid-cols-2 gap-2 text-sm sm:grid-cols-3 lg:flex lg:flex-col">
              {privacy.sections.map((section) => (
                <li key={section.id} className="min-w-0">
                  <a href={`#${section.id}`} className="inline-flex min-h-[48px] w-full min-w-0 items-center justify-center rounded-brand border border-champagne-beige bg-cream/60 px-3 py-2 text-center text-soft-brown transition-colors hover:bg-cream hover:text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-muted-gold focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory lg:justify-start lg:border-0 lg:bg-transparent lg:text-left">
                    <span className="min-w-0 break-words">{section.nav}</span>
                  </a>
                </li>
              ))}
            </ul>
          </nav>
        </aside>

        <article className="min-w-0 space-y-10 sm:space-y-12">
          <section className="min-w-0 rounded-brand border border-champagne-beige bg-cream p-5">
            <h2 className="font-heading text-2xl text-charcoal">{privacy.controllerTitle}</h2>
            <dl className="mt-4 grid gap-3 text-sm text-soft-brown sm:grid-cols-2">
              <div><dt className="font-medium text-charcoal">{legal.tradingName}</dt><dd>{legalIdentity.tradingName}</dd></div>
              <div><dt className="font-medium text-charcoal">{legal.legalName}</dt><dd>{legalIdentity.legalName}</dd></div>
              <div><dt className="font-medium text-charcoal">{legal.geographicAddress}</dt><dd>{legalIdentity.geographicAddress}</dd></div>
              <div><dt className="font-medium text-charcoal">{legal.country}</dt><dd>{legalIdentity.country}</dd></div>
              <div><dt className="font-medium text-charcoal">{legal.contactEmail}</dt><dd>{legalIdentity.contactEmail}</dd></div>
              <div><dt className="font-medium text-charcoal">{legal.registrationNumber}</dt><dd>{legalIdentity.registrationNumber}</dd></div>
            </dl>
            <p className="mt-4 text-sm leading-6 text-soft-brown/80">{legal.ownerReviewNotice}</p>
          </section>

          {privacy.sections.map((section) => (
            <section key={section.id} id={section.id} className="min-w-0 scroll-mt-28 border-b border-champagne-beige pb-10 last:border-b-0">
              <h2 className="break-words font-heading text-2xl text-charcoal sm:text-3xl">{section.title}</h2>
              <div className="mt-3 h-0.5 w-16 bg-muted-gold" />
              <div className="mt-5 max-w-full space-y-4 break-words text-[15px] leading-7 text-soft-brown sm:text-base sm:leading-8">
                {section.body.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
              </div>
            </section>
          ))}

          <div className="flex flex-wrap gap-3 text-sm">
            <Link href={policyPath("cookies")} className="rounded-pill bg-cream px-4 py-2 text-soft-brown underline-offset-4 hover:text-charcoal hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-muted-gold">{legal.cookiePolicy}</Link>
            <Link href={policyPath("contact")} className="rounded-pill bg-cream px-4 py-2 text-soft-brown underline-offset-4 hover:text-charcoal hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-muted-gold">{legal.contactPage}</Link>
          </div>
        </article>
      </div>
    </main>
  );
}
