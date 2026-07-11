"use client";

import Link from "next/link";
import { useCart } from "@/contexts/CartContext";
import { useAuth } from "@/contexts/AuthContext";
import { CartBadge } from "@/components/cart/CartBadge";
import { LoginButton } from "@/components/auth/LoginButton";
import { UserMenu } from "@/components/auth/UserMenu";
import { Skeleton } from "@/components/ui/Skeleton";

export function Header() {
  const { item_count, openDrawer } = useCart();
  const { isAuthenticated, isLoading } = useAuth();

  return (
    <header className="sticky top-0 z-50 bg-warm-ivory/95 backdrop-blur-sm border-b border-champagne-beige">
      <nav
        className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between"
        aria-label="Main navigation"
      >
        {/* Logo */}
        <Link
          href="/"
          className="font-heading text-xl md:text-2xl text-charcoal hover:text-soft-brown transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory rounded-brand"
        >
          Atelier Marie
        </Link>

        {/* Navigation links — hidden on mobile, visible on tablet+ */}
        <ul className="hidden md:flex items-center gap-8">
          <li>
            <Link
              href="/"
              className="text-soft-brown hover:text-charcoal transition-colors duration-fast font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory rounded-brand px-1 py-0.5"
            >
              Home
            </Link>
          </li>
          <li>
            <Link
              href="/products"
              className="text-soft-brown hover:text-charcoal transition-colors duration-fast font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory rounded-brand px-1 py-0.5"
            >
              Shop
            </Link>
          </li>
        </ul>

        {/* Right side: Auth + Cart */}
        <div className="flex items-center gap-4">
          {/* Auth state */}
          {isLoading ? (
            <Skeleton className="h-8 w-8 rounded-full" />
          ) : isAuthenticated ? (
            <UserMenu />
          ) : (
            <LoginButton />
          )}

          {/* Cart button */}
          <button
            onClick={openDrawer}
            aria-label={`Shopping cart${item_count > 0 ? `, ${item_count} item${item_count === 1 ? "" : "s"}` : ""}`}
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
  );
}
