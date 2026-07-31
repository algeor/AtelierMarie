import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { INSTAGRAM_URL, TIKTOK_URL } from "@/lib/social";
import { policyPath } from "@/lib/legal";
import { CookieSettingsButton } from "@/components/layout/CookieSettingsButton";

function InstagramIcon({ className }: { className?: string }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" className={className}>
      <rect x="3" y="3" width="18" height="18" rx="5" stroke="currentColor" strokeWidth="1.8" />
      <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="1.8" />
      <circle cx="17.5" cy="6.5" r="1.2" fill="currentColor" />
    </svg>
  );
}

function TikTokIcon({ className }: { className?: string }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" className={className}>
      <path
        d="M14.5 4v10.4a4.1 4.1 0 1 1-3.8-4.1"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M14.5 4c.6 3.2 2.4 5 5.3 5.4"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function Footer() {
  const t = useTranslations();
  const currentYear = new Date().getFullYear();

  return (
    <footer className="border-t border-champagne-beige mt-16" role="contentinfo">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="flex flex-col gap-8 md:flex-row md:items-center md:justify-between">
          {/* Navigation links */}
          <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:gap-8">
            <nav aria-label={t("nav.footerNavigation")}>
              <ul className="flex flex-wrap gap-6 text-sm">
              <li>
                <Link
                  href="/"
                  className="text-soft-brown hover:text-charcoal transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory rounded-brand px-1 py-0.5"
                >
                  {t("nav.home")}
                </Link>
              </li>
              <li>
                <Link
                  href="/products"
                  className="text-soft-brown hover:text-charcoal transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory rounded-brand px-1 py-0.5"
                >
                  {t("nav.shop")}
                </Link>
              </li>
              <li>
                <Link
                  href="/atelier"
                  className="text-soft-brown hover:text-charcoal transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory rounded-brand px-1 py-0.5"
                >
                  {t("nav.atelier")}
                </Link>
              </li>
              <li>
                <Link
                  href="/contact"
                  className="text-soft-brown hover:text-charcoal transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory rounded-brand px-1 py-0.5"
                >
                  {t("nav.contact")}
                </Link>
              </li>
              <li>
                <Link
                  href="/faq"
                  className="text-soft-brown hover:text-charcoal transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory rounded-brand px-1 py-0.5"
                >
                  {t("faq.footerLink")}
                </Link>
              </li>
              <li>
                <Link
                  href={policyPath("terms")}
                  className="text-soft-brown hover:text-charcoal transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory rounded-brand px-1 py-0.5"
                >
                  {t("terms.footerLink")}
                </Link>
              </li>
              <li>
                <Link
                  href={policyPath("privacy")}
                  className="text-soft-brown hover:text-charcoal transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory rounded-brand px-1 py-0.5"
                >
                  {t("legal.privacyPolicy")}
                </Link>
              </li>
              <li>
                <Link
                  href={policyPath("cookies")}
                  className="text-soft-brown hover:text-charcoal transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory rounded-brand px-1 py-0.5"
                >
                  {t("legal.cookiePolicy")}
                </Link>
              </li>
              <li>
                <CookieSettingsButton />
              </li>
              </ul>
            </nav>

            <div className="flex items-center gap-2" aria-label={t("footer.socialLinks")}>
              <a
                href={INSTAGRAM_URL}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={t("footer.instagram")}
                className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-brand text-soft-brown transition-colors duration-fast hover:text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory"
              >
                <InstagramIcon className="h-5 w-5" />
              </a>
              <a
                href={TIKTOK_URL}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={t("footer.tiktok")}
                className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-brand text-soft-brown transition-colors duration-fast hover:text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory"
              >
                <TikTokIcon className="h-5 w-5" />
              </a>
            </div>
          </div>

          {/* Branding */}
          <div className="text-sm text-soft-brown/70 md:text-right">
            <p>{t("footer.handcrafted")}</p>
            <p className="mt-1">{t("footer.copyright", { year: currentYear })}</p>
          </div>
        </div>
      </div>
    </footer>
  );
}
