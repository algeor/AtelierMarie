const path = require("path");
const createNextIntlPlugin = require("next-intl/plugin");

const withNextIntl = createNextIntlPlugin("./i18n/request.ts");
const distDir = process.env.NEXT_DIST_DIR;

/** @type {import('next').NextConfig} */
const nextConfig = {
  // The build/start npm scripts set NEXT_DIST_DIR (=.next-build for build/start,
  // .next-dev for dev); the Docker build relies on the same. Next.js only honors
  // the output dir via `distDir` here, so read the env var. When unset, omit the
  // key so Next.js uses its default `.next`.
  ...(distDir ? { distDir } : {}),
  // Two lockfiles exist (repo-root workspace wrapper + this app). Pin the trace
  // root to this directory so Next.js stops guessing and warning about it.
  outputFileTracingRoot: path.join(__dirname),
  images: {
    // Disable optimization in dev — product images are placeholders.
    // Switch to optimized + remotePatterns when real backend serves images.
    unoptimized: true,
  },
  async redirects() {
    // 301 redirects from old non-prefixed URLs to /en/ equivalents.
    // Preserves SEO equity from any existing search engine indexing.
    return [
      {
        source: "/products",
        destination: "/en/products",
        permanent: true,
      },
      {
        source: "/products/:id",
        destination: "/en/products/:id",
        permanent: true,
      },
      {
        source: "/checkout",
        destination: "/en/checkout",
        permanent: true,
      },
      {
        source: "/orders",
        destination: "/en/orders",
        permanent: true,
      },
      {
        source: "/orders/:path*",
        destination: "/en/orders/:path*",
        permanent: true,
      },
      {
        source: "/account",
        destination: "/en/account",
        permanent: true,
      },
      {
        source: "/admin",
        destination: "/en/admin",
        permanent: true,
      },
      {
        source: "/admin/:path*",
        destination: "/en/admin/:path*",
        permanent: true,
      },
    ];
  },
};

module.exports = withNextIntl(nextConfig);
