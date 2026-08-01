import type { Metadata } from "next";
import type { Locale } from "@/i18n/routing";
import { Link } from "@/i18n/navigation";
import { getTerms } from "@/lib/api";
import { loadLegalIdentity, policyPath } from "@/lib/legal";
import { getLocalizedAlternates } from "@/lib/seo";
import type { TermsResponse } from "@/lib/types";
import enMessages from "@/messages/en.json";
import bgMessages from "@/messages/bg.json";

interface TermsPageProps {
  params: Promise<{ locale: Locale }>;
}

interface TermSection {
  id: string;
  title: string;
  nav: string;
  body: string[];
  modelFormTitle?: string;
  modelFormIntro?: string;
  modelFormLines?: string[];
}

interface TermsMessages {
  metaTitle: string;
  metaDescription: string;
  eyebrow: string;
  title: string;
  subtitle: string;
  lastUpdated: string;
  identityIntro: string;
  policyLinksTitle: string;
  privacyLink: string;
  cookiesLink: string;
  navLabel: string;
  backToTop: string;
  sections: TermSection[];
}

function getStaticTermsMessages(locale: Locale): TermsMessages {
  return (locale === "bg" ? bgMessages.terms : enMessages.terms) as TermsMessages;
}

function mapTermsResponse(terms: TermsResponse): TermsMessages {
  return {
    metaTitle: terms.meta_title,
    metaDescription: terms.meta_description,
    eyebrow: terms.eyebrow,
    title: terms.title,
    subtitle: terms.subtitle,
    lastUpdated: terms.last_updated,
    identityIntro: terms.identity_intro,
    policyLinksTitle: terms.policy_links_title,
    privacyLink: terms.privacy_link,
    cookiesLink: terms.cookies_link,
    navLabel: terms.nav_label,
    backToTop: terms.back_to_top,
    sections: terms.sections.map((section) => ({
      id: section.id,
      title: section.title,
      nav: section.nav,
      body: section.body,
      modelFormTitle: section.model_form_title ?? undefined,
      modelFormIntro: section.model_form_intro ?? undefined,
      modelFormLines: section.model_form_lines ?? undefined,
    })),
  };
}

async function getTermsMessages(locale: Locale): Promise<TermsMessages> {
  try {
    return mapTermsResponse(await getTerms(locale));
  } catch {
    return getStaticTermsMessages(locale);
  }
}

export async function generateMetadata({ params }: TermsPageProps): Promise<Metadata> {
  const { locale } = await params;
  const terms = await getTermsMessages(locale);

  return {
    title: terms.metaTitle,
    description: terms.metaDescription,
    alternates: getLocalizedAlternates(locale, "/terms"),
  };
}

export default async function TermsPage({ params }: TermsPageProps) {
  const { locale } = await params;
  const terms = await getTermsMessages(locale);
  const legal = locale === "bg" ? bgMessages.legal : enMessages.legal;
  const legalIdentity = await loadLegalIdentity();

  return (
    <main className="overflow-x-hidden bg-warm-ivory">
      <section id="terms-top" className="mx-auto max-w-5xl scroll-mt-28 px-4 pb-8 pt-12 sm:px-6 sm:pt-16 lg:px-8">
        <p className="text-sm font-medium uppercase tracking-[0.08em] text-muted-gold">
          {terms.eyebrow}
        </p>
        <div className="mt-3 max-w-3xl">
          <h1 className="break-words font-heading text-3xl text-charcoal sm:text-5xl">
            {terms.title}
          </h1>
          <p className="mt-5 max-w-full break-words text-base leading-8 text-soft-brown sm:text-lg">
            {terms.subtitle}
          </p>
          <p className="mt-4 text-sm text-soft-brown/75">{terms.lastUpdated}</p>
          <p className="mt-4 max-w-full break-words text-sm leading-6 text-soft-brown/80">
            {terms.identityIntro}
          </p>
        </div>
      </section>

      <div className="mx-auto grid max-w-5xl min-w-0 gap-10 px-4 pb-16 sm:px-6 lg:grid-cols-[220px_minmax(0,760px)] lg:px-8">
        <aside className="min-w-0 lg:sticky lg:top-24 lg:self-start" aria-label={terms.navLabel}>
          <nav className="border-y border-champagne-beige py-4 lg:border-y-0 lg:border-l lg:py-0 lg:pl-5">
            <ul className="grid min-w-0 grid-cols-2 gap-2 text-sm sm:grid-cols-3 lg:flex lg:flex-col">
              {terms.sections.map((section) => (
                <li key={section.id} className="min-w-0">
                  <a
                    href={`#${section.id}`}
                    className="inline-flex min-h-[48px] w-full min-w-0 items-center justify-center rounded-brand border border-champagne-beige bg-cream/60 px-3 py-2 text-center text-soft-brown transition-colors hover:bg-cream hover:text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-muted-gold focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory lg:justify-start lg:border-0 lg:bg-transparent lg:text-left"
                  >
                    <span className="min-w-0 break-words">{section.nav}</span>
                  </a>
                </li>
              ))}
            </ul>
          </nav>
        </aside>

        <article className="min-w-0 space-y-10 sm:space-y-12">
          <section className="min-w-0 rounded-brand border border-champagne-beige bg-cream p-5">
            <h2 className="font-heading text-2xl text-charcoal">{legal.identityTitle}</h2>
            <dl className="mt-4 grid gap-3 text-sm text-soft-brown sm:grid-cols-2">
              <div><dt className="font-medium text-charcoal">{legal.tradingName}</dt><dd>{legalIdentity.tradingName}</dd></div>
              <div><dt className="font-medium text-charcoal">{legal.legalName}</dt><dd>{legalIdentity.legalName}</dd></div>
              <div><dt className="font-medium text-charcoal">{legal.geographicAddress}</dt><dd>{legalIdentity.geographicAddress}</dd></div>
              <div><dt className="font-medium text-charcoal">{legal.country}</dt><dd>{legalIdentity.country}</dd></div>
              <div><dt className="font-medium text-charcoal">{legal.contactEmail}</dt><dd>{legalIdentity.contactEmail}</dd></div>
              <div><dt className="font-medium text-charcoal">{legal.registrationNumber}</dt><dd>{legalIdentity.registrationNumber}</dd></div>
              <div><dt className="font-medium text-charcoal">{legal.vatNumber}</dt><dd>{legalIdentity.vatNumber}</dd></div>
            </dl>
          </section>

          <section className="min-w-0 rounded-brand border border-champagne-beige bg-cream p-5">
            <h2 className="font-heading text-2xl text-charcoal">{terms.policyLinksTitle}</h2>
            <div className="mt-4 flex flex-wrap gap-3 text-sm">
              <Link href={policyPath("privacy")} className="rounded-pill bg-white px-4 py-2 text-soft-brown underline-offset-4 hover:text-charcoal hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-muted-gold">
                {terms.privacyLink}
              </Link>
              <Link href={policyPath("cookies")} className="rounded-pill bg-white px-4 py-2 text-soft-brown underline-offset-4 hover:text-charcoal hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-muted-gold">
                {terms.cookiesLink}
              </Link>
            </div>
          </section>

          {terms.sections.map((section) => (
            <section
              key={section.id}
              id={section.id}
              className="min-w-0 scroll-mt-28 border-b border-champagne-beige pb-10 last:border-b-0"
            >
              <h2 className="break-words font-heading text-2xl text-charcoal sm:text-3xl">
                {section.title}
              </h2>
              <div className="mt-3 h-0.5 w-16 bg-muted-gold" />
              <div className="mt-5 max-w-full space-y-4 break-words text-[15px] leading-7 text-soft-brown sm:text-base sm:leading-8">
                {section.body.map((paragraph) => (
                  <p key={paragraph} className="max-w-full">
                    {paragraph}
                  </p>
                ))}
              </div>

              {section.modelFormLines && (
                <div className="mt-7 max-w-full overflow-hidden rounded-brand border border-champagne-beige bg-cream px-4 py-5 sm:px-5">
                  <h3 className="break-words font-heading text-xl text-charcoal">
                    {section.modelFormTitle}
                  </h3>
                  {section.modelFormIntro && (
                    <p className="mt-3 break-words text-sm leading-7 text-soft-brown">
                      {section.modelFormIntro}
                    </p>
                  )}
                  <div className="mt-4 max-w-full space-y-2 break-words text-sm leading-6 text-charcoal">
                    {section.modelFormLines.map((line) => (
                      <p key={line} className="max-w-full">
                        {line}
                      </p>
                    ))}
                  </div>
                </div>
              )}

              <div className="mt-6 flex justify-end">
                <a
                  href="#terms-top"
                  aria-label={terms.backToTop}
                  className="inline-flex h-11 w-11 items-center justify-center rounded-brand border border-champagne-beige bg-cream text-soft-brown transition-colors hover:bg-warm-ivory hover:text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-muted-gold focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory"
                >
                  <span aria-hidden="true" className="text-xl leading-none">
                    ↑
                  </span>
                </a>
              </div>
            </section>
          ))}
        </article>
      </div>
    </main>
  );
}
