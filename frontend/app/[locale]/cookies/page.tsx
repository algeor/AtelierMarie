import type { Metadata } from "next";
import type { Locale } from "@/i18n/routing";
import { Link } from "@/i18n/navigation";
import { getCookies } from "@/lib/api";
import { policyPath } from "@/lib/legal";
import { getLocalizedAlternates } from "@/lib/seo";
import type { CookiesResponse } from "@/lib/types";
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

function getStaticCookiesMessages(locale: Locale): CookiesMessages {
  return (
    locale === "bg" ? bgMessages.cookies : enMessages.cookies
  ) as CookiesMessages;
}

function mapCookiesResponse(cookies: CookiesResponse): CookiesMessages {
  return {
    metaTitle: cookies.meta_title,
    metaDescription: cookies.meta_description,
    eyebrow: cookies.eyebrow,
    title: cookies.title,
    subtitle: cookies.subtitle,
    lastUpdated: cookies.last_updated,
    inventoryTitle: cookies.inventory_title,
    headers: cookies.headers,
    cookies: cookies.cookies,
    sections: cookies.sections,
  };
}

async function getCookiesMessages(locale: Locale): Promise<CookiesMessages> {
  try {
    return mapCookiesResponse(await getCookies(locale));
  } catch {
    return getStaticCookiesMessages(locale);
  }
}

export async function generateMetadata({
  params,
}: CookiesPageProps): Promise<Metadata> {
  const { locale } = await params;
  const cookies = await getCookiesMessages(locale);

  return {
    title: cookies.metaTitle,
    description: cookies.metaDescription,
    alternates: getLocalizedAlternates(locale, policyPath("cookies")),
  };
}

export default async function CookiesPage({ params }: CookiesPageProps) {
  const { locale } = await params;
  const cookies = await getCookiesMessages(locale);
  const legal = locale === "bg" ? bgMessages.legal : enMessages.legal;

  return (
    <main className="overflow-x-hidden bg-page text-text">
      <section
        id="cookies-top"
        className="mx-auto max-w-5xl scroll-mt-28 px-4 pb-8 pt-12 sm:px-6 sm:pt-16 lg:px-8"
      >
        <p className="text-sm font-medium uppercase tracking-[0.08em] text-accent">
          {cookies.eyebrow}
        </p>
        <div className="mt-3 max-w-3xl">
          <h1 className="break-words font-heading text-3xl text-text sm:text-5xl">
            {cookies.title}
          </h1>
          <p className="mt-5 max-w-full break-words text-base leading-8 text-muted sm:text-lg">
            {cookies.subtitle}
          </p>
          <p className="mt-4 text-sm text-muted/75">{cookies.lastUpdated}</p>
        </div>
      </section>

      <article className="mx-auto max-w-5xl px-4 pb-16 sm:px-6 lg:px-8">
        <section className="editorial-paper-panel min-w-0 rounded-brand p-5">
          <h2 className="font-heading text-2xl text-text">
            {cookies.inventoryTitle}
          </h2>
          <div className="mt-5 overflow-x-auto rounded-brand bg-page/35">
            <table className="min-w-full border-separate border-spacing-0 text-left text-sm">
              <thead className="text-text">
                <tr>
                  <th className="border-b editorial-divider px-3 py-2 font-medium">
                    {cookies.headers.name}
                  </th>
                  <th className="border-b editorial-divider px-3 py-2 font-medium">
                    {cookies.headers.purpose}
                  </th>
                  <th className="border-b editorial-divider px-3 py-2 font-medium">
                    {cookies.headers.type}
                  </th>
                  <th className="border-b editorial-divider px-3 py-2 font-medium">
                    {cookies.headers.duration}
                  </th>
                </tr>
              </thead>
              <tbody className="text-muted">
                {cookies.cookies.map((item) => (
                  <tr key={item.name}>
                    <td className="border-b editorial-divider px-3 py-3 font-medium text-text">
                      {item.name}
                    </td>
                    <td className="border-b editorial-divider px-3 py-3">
                      {item.purpose}
                    </td>
                    <td className="border-b editorial-divider px-3 py-3">
                      {item.type}
                    </td>
                    <td className="border-b editorial-divider px-3 py-3">
                      {item.duration}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <div className="mt-12 space-y-10 sm:space-y-12">
          {cookies.sections.map((section) => (
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
        </div>

        <div className="mt-8 flex flex-wrap gap-3 text-sm">
          <Link
            href={policyPath("privacy")}
            className="rounded-pill bg-surface px-4 py-2 text-muted underline-offset-4 hover:text-text hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          >
            {legal.privacyPolicy}
          </Link>
          <Link
            href={policyPath("terms")}
            className="rounded-pill bg-surface px-4 py-2 text-muted underline-offset-4 hover:text-text hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          >
            {legal.termsConditions}
          </Link>
        </div>
      </article>
    </main>
  );
}
