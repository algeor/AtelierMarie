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
  return (
    locale === "bg" ? bgMessages.privacy : enMessages.privacy
  ) as PrivacyMessages;
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

async function getEditablePrivacyMessages(
  locale: Locale,
): Promise<PrivacyMessages> {
  try {
    return mapPrivacyResponse(await getPrivacy(locale));
  } catch {
    return getPrivacyMessages(locale);
  }
}

export async function generateMetadata({
  params,
}: PrivacyPageProps): Promise<Metadata> {
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
    <main className="overflow-x-hidden bg-page text-text">
      <section
        id="privacy-top"
        className="mx-auto max-w-5xl scroll-mt-28 px-4 pb-8 pt-12 sm:px-6 sm:pt-16 lg:px-8"
      >
        <p className="text-sm font-medium uppercase tracking-[0.08em] text-accent">
          {privacy.eyebrow}
        </p>
        <div className="mt-3 max-w-3xl">
          <h1 className="break-words font-heading text-3xl text-text sm:text-5xl">
            {privacy.title}
          </h1>
          <p className="mt-5 max-w-full break-words text-base leading-8 text-muted sm:text-lg">
            {privacy.subtitle}
          </p>
          <p className="mt-4 text-sm text-muted/75">{privacy.lastUpdated}</p>
        </div>
      </section>

      <div className="mx-auto grid max-w-5xl min-w-0 gap-10 px-4 pb-16 sm:px-6 lg:grid-cols-[220px_minmax(0,760px)] lg:px-8">
        <aside
          className="min-w-0 lg:sticky lg:top-24 lg:self-start"
          aria-label={privacy.title}
        >
          <nav className="border-y editorial-divider py-4 lg:border-y-0 lg:border-l lg:py-0 lg:pl-5">
            <ul className="grid min-w-0 grid-cols-2 gap-2 text-sm sm:grid-cols-3 lg:flex lg:flex-col">
              {privacy.sections.map((section) => (
                <li key={section.id} className="min-w-0">
                  <a
                    href={`#${section.id}`}
                    className="inline-flex min-h-[48px] w-full min-w-0 items-center justify-center rounded-brand border border-border/25 bg-surface/35 px-3 py-2 text-center text-muted transition-colors hover:bg-surface/70 hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page lg:justify-start lg:border-0 lg:bg-transparent lg:text-left"
                  >
                    <span className="min-w-0 break-words">{section.nav}</span>
                  </a>
                </li>
              ))}
            </ul>
          </nav>
        </aside>

        <article className="min-w-0 space-y-10 sm:space-y-12">
          <section className="editorial-paper-panel min-w-0 rounded-brand p-5">
            <h2 className="font-heading text-2xl text-text">
              {privacy.controllerTitle}
            </h2>
            <dl className="mt-4 grid gap-3 text-sm text-muted sm:grid-cols-2">
              <div>
                <dt className="font-medium text-text">{legal.tradingName}</dt>
                <dd>{legalIdentity.tradingName}</dd>
              </div>
              <div>
                <dt className="font-medium text-text">{legal.legalName}</dt>
                <dd>{legalIdentity.legalName}</dd>
              </div>
              <div>
                <dt className="font-medium text-text">
                  {legal.geographicAddress}
                </dt>
                <dd>{legalIdentity.geographicAddress}</dd>
              </div>
              <div>
                <dt className="font-medium text-text">{legal.country}</dt>
                <dd>{legalIdentity.country}</dd>
              </div>
              <div>
                <dt className="font-medium text-text">{legal.contactEmail}</dt>
                <dd>{legalIdentity.contactEmail}</dd>
              </div>
              <div>
                <dt className="font-medium text-text">
                  {legal.registrationNumber}
                </dt>
                <dd>{legalIdentity.registrationNumber}</dd>
              </div>
            </dl>
            <p className="mt-4 text-sm leading-6 text-muted/80">
              {legal.ownerReviewNotice}
            </p>
          </section>

          {privacy.sections.map((section) => (
            <section
              key={section.id}
              id={section.id}
              className="min-w-0 scroll-mt-28 border-b editorial-divider pb-10 last:border-b-0"
            >
              <h2 className="break-words font-heading text-2xl text-text sm:text-3xl">
                {section.title}
              </h2>
              <div className="mt-3 h-0.5 w-16 bg-accent" />
              <div className="mt-5 max-w-full space-y-4 break-words text-[15px] leading-7 text-muted sm:text-base sm:leading-8">
                {section.body.map((paragraph) => (
                  <p key={paragraph}>{paragraph}</p>
                ))}
              </div>
            </section>
          ))}

          <div className="flex flex-wrap gap-3 text-sm">
            <Link
              href={policyPath("cookies")}
              className="rounded-pill bg-surface px-4 py-2 text-muted underline-offset-4 hover:text-text hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
            >
              {legal.cookiePolicy}
            </Link>
            <Link
              href={policyPath("contact")}
              className="rounded-pill bg-surface px-4 py-2 text-muted underline-offset-4 hover:text-text hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
            >
              {legal.contactPage}
            </Link>
          </div>
        </article>
      </div>
    </main>
  );
}
