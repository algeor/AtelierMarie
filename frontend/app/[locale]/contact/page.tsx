import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { ContactForm } from "@/components/contact/ContactForm";
import { BrandMark } from "@/components/rebrand";
import { INSTAGRAM_URL, TIKTOK_URL } from "@/lib/social";
import type { Locale } from "@/i18n/routing";

interface ContactPageProps {
  params: Promise<{ locale: Locale }>;
}

export async function generateMetadata({
  params,
}: ContactPageProps): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "contact" });
  return {
    title: `${t("title")} | Atelier Marie`,
    description: t("intro"),
  };
}

export default async function ContactPage({ params }: ContactPageProps) {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "contact" });

  return (
    <main className="editorial-band px-4 py-10 text-text sm:px-6 lg:px-8 lg:py-16">
      <div className="mx-auto grid max-w-5xl gap-12 lg:grid-cols-[0.85fr_1.15fr] lg:items-start">
        <section className="space-y-7">
          <div>
            <BrandMark className="mb-4 h-14 w-20 text-accent" />
            <p className="mb-3 text-sm font-medium uppercase tracking-[0.08em] text-muted/70">
              {t("eyebrow")}
            </p>
            <h1 className="font-heading text-4xl leading-tight text-text sm:text-5xl">
              {t("title")}
            </h1>
            <p className="mt-4 max-w-prose text-base leading-7 text-muted">
              {t("intro")}
            </p>
          </div>

          <div className="space-y-4 border-t editorial-divider pt-6">
            <div>
              <p className="text-sm font-medium text-text">{t("emailLabel")}</p>
              <a
                href="mailto:contacts@theateliermarie.com"
                className="mt-1 inline-flex min-h-[44px] items-center rounded-brand text-muted underline-offset-4 transition-colors hover:text-text hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page"
              >
                contacts@theateliermarie.com
              </a>
            </div>

            <div>
              <p className="text-sm font-medium text-text">
                {t("socialLabel")}
              </p>
              <div className="mt-1 flex flex-wrap gap-4 text-sm">
                <a
                  href={INSTAGRAM_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex min-h-[44px] items-center rounded-brand text-muted underline-offset-4 transition-colors hover:text-text hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page"
                >
                  Instagram
                </a>
                <a
                  href={TIKTOK_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex min-h-[44px] items-center rounded-brand text-muted underline-offset-4 transition-colors hover:text-text hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page"
                >
                  TikTok
                </a>
              </div>
            </div>
          </div>
        </section>

        <ContactForm />
      </div>
    </main>
  );
}
