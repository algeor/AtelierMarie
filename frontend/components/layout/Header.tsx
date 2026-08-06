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

const headerLinkClass =
  "text-sm font-semibold text-muted transition-colors duration-fast hover:text-accent active:text-accent focus-visible:outline-none focus-visible:text-accent focus-visible:underline focus-visible:underline-offset-4";

const headerIconButtonClass =
  "inline-flex min-h-[44px] min-w-[44px] items-center justify-center text-muted transition-colors duration-fast hover:text-accent active:text-accent focus-visible:outline-none focus-visible:text-accent";

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
  const isAtelierPage = pathname === "/atelier" || pathname.startsWith("/atelier/");

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
    return <LoginButton className={headerLinkClass} />;
  }

  return (
    <>
      <header
        className={cn(
          "sticky top-0 z-50 px-3 py-3 sm:px-4",
          isAtelierPage ? "bg-text" : "bg-accent"
        )}
      >
        <nav
          className="mx-auto flex h-14 max-w-7xl items-center justify-between rounded-brand border border-border/30 bg-[rgb(248_241_241)] px-4 shadow-lg shadow-border/15 backdrop-blur-xl sm:px-6 lg:px-8"
          aria-label={t("nav.mainNavigation")}
        >
          {/* Logo */}
          <Link
            href="/"
            className="font-heading text-xl text-text transition-colors duration-fast hover:text-accent active:text-accent focus-visible:outline-none focus-visible:text-accent focus-visible:underline focus-visible:underline-offset-4 md:text-2xl"
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
                  className={cn(
                    headerLinkClass,
                    isLinkActive(link.href) && "text-text underline underline-offset-4"
                  )}
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
              className={cn(headerIconButtonClass, "md:hidden")}
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
                  d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
                />
              </svg>
            </button>

            <button
              onClick={openDrawer}
              aria-label={cartAriaLabel}
              className={cn(headerIconButtonClass, "relative")}
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
              "fixed inset-0 bg-text/35 backdrop-blur-[2px] transition-opacity duration-normal",
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
              "fixed inset-y-0 left-0 flex w-[min(22rem,calc(100vw-2rem))] flex-col border-r border-border/30 bg-[rgb(248_241_241)] shadow-2xl shadow-border/20 transition-transform duration-normal",
              mobileMenuOpen ? "translate-x-0" : "-translate-x-full"
            )}
          >
            {mobileMenuOpen && (
              <>
                <div className="flex items-center justify-between border-b border-border/30 px-5 py-4">
                  <h2 className="font-heading text-xl text-text">
                    {t("header.mobileMenuTitle")}
                  </h2>
                  <button
                    type="button"
                    onClick={closeMobileMenu}
                    aria-label={t("header.closeMenu")}
                    className={headerIconButtonClass}
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
                              "block px-1 py-3 text-base font-semibold transition-colors duration-fast focus-visible:outline-none focus-visible:text-accent focus-visible:underline focus-visible:underline-offset-4",
                              isActive
                                ? "text-text underline underline-offset-4"
                                : "text-muted hover:text-accent active:text-accent"
                            )}
                          >
                            {t(link.labelKey)}
                          </Link>
                        </li>
                      );
                    })}
                  </ul>

                  <div className="mt-6 border-t border-border/30 pt-5">
                    <div className="flex items-center justify-between gap-4">
                      <span className="text-sm font-semibold text-muted">
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
