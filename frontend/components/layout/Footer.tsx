import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";

export function Footer() {
  const t = useTranslations();
  const currentYear = new Date().getFullYear();

  return (
    <footer className="border-t border-champagne-beige mt-16" role="contentinfo">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-8">
          {/* Navigation links */}
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
                <a
                  href="#"
                  className="text-soft-brown hover:text-charcoal transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory rounded-brand px-1 py-0.5"
                >
                  {t("nav.about")}
                </a>
              </li>
              <li>
                <a
                  href="#"
                  className="text-soft-brown hover:text-charcoal transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory rounded-brand px-1 py-0.5"
                >
                  {t("nav.contact")}
                </a>
              </li>
            </ul>
          </nav>

          {/* Branding */}
          <div className="text-sm text-soft-brown/70">
            <p>{t("footer.handcrafted")}</p>
            <p className="mt-1">{t("footer.copyright", { year: currentYear })}</p>
          </div>
        </div>
      </div>
    </footer>
  );
}
