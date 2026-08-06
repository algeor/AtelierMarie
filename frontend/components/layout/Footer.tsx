import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { INSTAGRAM_URL, TIKTOK_URL } from "@/lib/social";
import { policyPath } from "@/lib/legal";
import { CookieSettingsButton } from "@/components/layout/CookieSettingsButton";
import { LoginButton } from "@/components/auth/LoginButton";
import { BrandMark } from "@/components/rebrand";
import { cn } from "@/lib/utils";

const footerLinkClass =
  "inline-flex min-h-[36px] items-center py-1 text-left text-sm font-semibold leading-snug text-muted transition-colors duration-fast hover:text-accent active:text-accent focus-visible:outline-none focus-visible:text-accent focus-visible:underline focus-visible:underline-offset-4";

const socialLinkClass =
  "inline-flex min-h-[44px] min-w-[44px] items-center justify-center text-muted transition-colors duration-fast hover:text-accent active:text-accent focus-visible:outline-none focus-visible:text-accent";

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

export function Footer({ isAtelierPage = false }: { isAtelierPage?: boolean }) {
  const t = useTranslations();
  const currentYear = new Date().getFullYear();

  const linkGroups = [
    {
      title: t("footer.groups.explore"),
      links: [
        { href: "/" as const, label: t("nav.home") },
        { href: "/products" as const, label: t("nav.shop") },
        { href: "/atelier" as const, label: t("nav.atelier") },
      ],
    },
    {
      title: t("footer.groups.help"),
      links: [
        { href: "/contact" as const, label: t("nav.contact") },
        { href: "/faq" as const, label: t("faq.footerLink") },
      ],
    },
    {
      title: t("footer.groups.account"),
      links: [
        { href: "/account" as const, label: t("auth.myAccount") },
        { href: "/orders" as const, label: t("auth.myOrders") },
      ],
    },
    {
      title: t("footer.groups.legal"),
      links: [
        { href: policyPath("terms"), label: t("terms.footerLink") },
        { href: policyPath("privacy"), label: t("legal.privacyPolicy") },
        { href: policyPath("cookies"), label: t("legal.cookiePolicy") },
      ],
    },
  ];

  return (
    <footer
      className={cn(
        "relative overflow-hidden py-12 text-text lg:py-16",
        isAtelierPage ? "bg-text" : "bg-accent"
      )}
      role="contentinfo"
    >
      <div className="pointer-events-none absolute -bottom-5 left-1/2 z-0 -translate-x-1/2 whitespace-nowrap font-heading text-[17vw] leading-none text-accent-foreground/10 rebrand-footer-wordmark-reveal">
        ATELIER MARIE
      </div>

      <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="landing-footer-panel rounded-brand border border-border/30 bg-[rgb(248_241_241)] p-5 shadow-2xl shadow-text/15 md:p-8 lg:p-10">
          <div className="grid items-start gap-10 lg:grid-cols-[minmax(17rem,0.95fr)_minmax(0,1.85fr)] lg:gap-14">
            <div className="max-w-md">
              <BrandMark className="h-14 w-24 text-accent" title={t("footer.brandMarkTitle")} />
              <p className="mt-4 font-heading text-4xl font-semibold text-text">Atelier Marie</p>
              <p className="mt-4 max-w-sm text-base font-medium leading-7 text-muted">{t("footer.editorialText")}</p>
              <div className="mt-6">
                <p className="text-xs font-bold uppercase tracking-[0.18em] text-accent">
                  {t("footer.groups.social")}
                </p>
                <div className="mt-3 flex items-center gap-4" aria-label={t("footer.socialLinks")}>
                  <a
                    href={INSTAGRAM_URL}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={t("footer.instagram")}
                    className={socialLinkClass}
                  >
                    <InstagramIcon className="h-7 w-7" />
                  </a>
                  <a
                    href={TIKTOK_URL}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={t("footer.tiktok")}
                    className={socialLinkClass}
                  >
                    <TikTokIcon className="h-7 w-7" />
                  </a>
                </div>
              </div>
            </div>

            <nav aria-label={t("nav.footerNavigation")} className="lg:pt-3">
              <div className="grid grid-cols-2 items-start gap-x-6 gap-y-8 md:grid-cols-4 lg:gap-x-8">
                {linkGroups.map((group) => (
                  <div key={group.title}>
                    <h2 className="text-xs font-bold uppercase tracking-[0.18em] text-accent">{group.title}</h2>
                    <ul className="mt-3 space-y-1.5">
                      {group.links.map((link) => (
                        <li key={`${group.title}-${link.href}`}>
                          <Link href={link.href} className={footerLinkClass}>
                            {link.label}
                          </Link>
                        </li>
                      ))}
                      {group.title === t("footer.groups.account") ? (
                        <li>
                          <LoginButton className={footerLinkClass} />
                        </li>
                      ) : null}
                      {group.title === t("footer.groups.legal") ? (
                        <li>
                          <CookieSettingsButton className={footerLinkClass} />
                        </li>
                      ) : null}
                    </ul>
                  </div>
                ))}
              </div>
            </nav>
          </div>

          <div className="mt-10 flex flex-col gap-2 border-t border-border/30 pt-5 text-sm font-semibold text-muted md:flex-row md:items-center md:justify-between">
            <p>{t("footer.handcrafted")}</p>
            <p>{t("footer.copyright", { year: currentYear })}</p>
          </div>
        </div>
      </div>
    </footer>
  );
}
