import Link from "next/link";

export function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="border-t border-champagne-beige mt-16" role="contentinfo">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-8">
          {/* Navigation links */}
          <nav aria-label="Footer navigation">
            <ul className="flex flex-wrap gap-6 text-sm">
              <li>
                <Link
                  href="/"
                  className="text-soft-brown hover:text-charcoal transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory rounded-brand px-1 py-0.5"
                >
                  Home
                </Link>
              </li>
              <li>
                <Link
                  href="/products"
                  className="text-soft-brown hover:text-charcoal transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory rounded-brand px-1 py-0.5"
                >
                  Shop
                </Link>
              </li>
              <li>
                <a
                  href="#"
                  className="text-soft-brown hover:text-charcoal transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory rounded-brand px-1 py-0.5"
                >
                  About
                </a>
              </li>
              <li>
                <a
                  href="#"
                  className="text-soft-brown hover:text-charcoal transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory rounded-brand px-1 py-0.5"
                >
                  Contact
                </a>
              </li>
            </ul>
          </nav>

          {/* Branding */}
          <div className="text-sm text-soft-brown/70">
            <p>Handcrafted with love</p>
            <p className="mt-1">© {currentYear} Atelier Marie. All rights reserved.</p>
          </div>
        </div>
      </div>
    </footer>
  );
}
