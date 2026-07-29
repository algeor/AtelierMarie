"use client";

import { useCallback, useState } from "react";
import { useTranslations } from "next-intl";
import { Link, usePathname } from "@/i18n/navigation";
import { useCart } from "@/contexts/CartContext";
import { useAuth } from "@/contexts/AuthContext";
import { CartBadge } from "@/components/cart/CartBadge";
import { LoginButton } from "@/components/auth/LoginButton";
import { UserMenu } from "@/components/auth/UserMenu";
import { LanguageToggle } from "@/components/layout/LanguageToggle";
import { Skeleton } from "@/components/ui/Skeleton";
import { Portal } from "@/components/ui/Portal";
import { useFocusTrap } from "@/lib/useFocusTrap";
import { cn } from "@/lib/utils";

const NAV_LINKS = [
  { href: "/", labelKey: "nav.home" },
  { href: "/products", labelKey: "nav.shop" },
  { href: "/atelier", labelKey: "nav.atelier" },
  { href: "/faq", labelKey: "nav.faq" },
  { href: "/contact", labelKey: "nav.contact" },
] as const;

export function Header() {
  const t = useTranslations();
  const pathname = usePathname();
  const { item_count, openDrawer } = useCart();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const closeMobileMenu = useCallback(() => setMobileMenuOpen(false), []);
  const mobileMenuRef = useFocusTrap<HTMLDivElement>({
    active: mobileMenuOpen,
    onClose: closeMobileMenu,
  });

  const cartAriaLabel =
    item_count > 0
      ? t("header.cartLabelWithItems", { count: item_count })
      : t("header.cartLabel");

  const isLinkActive = useCallback(
    (href: string) =>
      href === "/"
        ? pathname === href
        : pathname === href || pathname.startsWith(href + "/"),
    [pathname]
  );

  function renderAuthControl() {
    if (authLoading) return <Skeleton className="w-8 h-8 rounded-full" />;
    if (isAuthenticated) return <UserMenu />;
    return <LoginButton />;
  }

  return (
    <>
      <header className="sticky top-0 z-50 bg-warm-ivory/95 backdrop-blur-sm border-b border-champagne-beige">
        <nav
          className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between"
          aria-label={t("nav.mainNavigation")}
        >
          {/* Logo */}
          <Link
            href="/"
            className="font-heading text-xl md:text-2xl text-charcoal hover:text-soft-brown transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory rounded-brand"
          >
            Atelier Marie
          </Link>

          {/* Navigation links - visible on tablet+ */}
          <ul className="hidden md:flex items-center gap-8">
            {NAV_LINKS.slice(0, 3).map((link) => (
              <li key={link.href}>
                <Link
                  href={link.href}
                  aria-current={isLinkActive(link.href) ? "page" : undefined}
                  className="text-soft-brown hover:text-charcoal transition-colors duration-fast font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory rounded-brand px-1 py-0.5"
                >
                  {t(link.labelKey)}
                </Link>
              </li>
            ))}
          </ul>

          {/* Right side: desktop language/auth + mobile menu + cart */}
          <div className="flex items-center gap-2 sm:gap-3 md:gap-4">
            <div className="hidden md:block">
              <LanguageToggle />
            </div>

            <div className="hidden md:block">{renderAuthControl()}</div>

            <button
              type="button"
              onClick={() => setMobileMenuOpen(true)}
              aria-label={t("header.openMenu")}
              aria-expanded={mobileMenuOpen}
              aria-controls="mobile-navigation-menu"
              className="md:hidden min-w-[44px] min-h-[44px] inline-flex items-center justify-center rounded-brand transition-colors duration-fast hover:bg-cream focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
                className="h-6 w-6 text-soft-brown"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
                />
              </svg>
            </button>

            <button
              onClick={openDrawer}
              aria-label={cartAriaLabel}
              className="relative min-w-[44px] min-h-[44px] inline-flex items-center justify-center rounded-brand transition-colors duration-fast hover:bg-cream focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
                className="w-6 h-6 text-soft-brown"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M15.75 10.5V6a3.75 3.75 0 10-7.5 0v4.5m11.356-1.993l1.263 12c.07.665-.45 1.243-1.119 1.243H4.25a1.125 1.125 0 01-1.12-1.243l1.264-12A1.125 1.125 0 015.513 7.5h12.974c.576 0 1.059.435 1.119 1.007zM8.625 10.5a.375.375 0 11-.75 0 .375.375 0 01.75 0zm7.5 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"
                />
              </svg>
              <CartBadge count={item_count} />
            </button>
          </div>
        </nav>
      </header>

      <Portal>
        <div
          className={cn(
            "fixed inset-0 z-[100] md:hidden",
            mobileMenuOpen ? "pointer-events-auto" : "pointer-events-none"
          )}
          aria-hidden={!mobileMenuOpen}
        >
          <div
            className={cn(
              "fixed inset-0 bg-charcoal/45 backdrop-blur-[2px] transition-opacity duration-normal",
              mobileMenuOpen ? "opacity-100" : "opacity-0"
            )}
            aria-hidden="true"
            onClick={closeMobileMenu}
          />
          <div
            ref={mobileMenuRef}
            id="mobile-navigation-menu"
            role="dialog"
            aria-modal="true"
            aria-label={t("header.mobileMenuTitle")}
            tabIndex={-1}
            className={cn(
              "fixed inset-y-0 left-0 flex w-[min(22rem,calc(100vw-2rem))] flex-col bg-warm-ivory shadow-xl transition-transform duration-normal",
              mobileMenuOpen ? "translate-x-0" : "-translate-x-full"
            )}
          >
            {mobileMenuOpen && (
              <>
                <div className="flex items-center justify-between border-b border-champagne-beige px-5 py-4">
                  <h2 className="font-heading text-xl text-charcoal">
                    {t("header.mobileMenuTitle")}
                  </h2>
                  <button
                    type="button"
                    onClick={closeMobileMenu}
                    aria-label={t("header.closeMenu")}
                    className="min-h-[44px] min-w-[44px] inline-flex items-center justify-center rounded-brand text-soft-brown transition-colors duration-fast hover:bg-cream hover:text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth={1.5}
                      stroke="currentColor"
                      className="h-6 w-6"
                      aria-hidden="true"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                </div>

                <div className="flex-1 overflow-y-auto px-5 py-5">
                  <ul className="space-y-1" aria-label={t("nav.mainNavigation")}>
                    {NAV_LINKS.map((link) => {
                      const isActive = isLinkActive(link.href);
                      return (
                        <li key={link.href}>
                          <Link
                            href={link.href}
                            onClick={closeMobileMenu}
                            aria-current={isActive ? "page" : undefined}
                            className={cn(
                              "block rounded-brand px-3 py-3 text-base font-medium transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory",
                              isActive
                                ? "bg-muted-gold/15 text-charcoal"
                                : "text-soft-brown hover:bg-cream hover:text-charcoal"
                            )}
                          >
                            {t(link.labelKey)}
                          </Link>
                        </li>
                      );
                    })}
                  </ul>

                  <div className="mt-6 border-t border-champagne-beige pt-5">
                    <div className="flex items-center justify-between gap-4">
                      <span className="text-sm font-medium text-soft-brown">
                        {t("header.language")}
                      </span>
                      <LanguageToggle />
                    </div>
                    <div className="mt-5">{renderAuthControl()}</div>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </Portal>
    </>
  );
}
