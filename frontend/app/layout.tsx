import type { Metadata } from "next";
import { headers } from "next/headers";
import { getLocale } from "next-intl/server";
import type { CSSProperties } from "react";
import { getPublicSiteMedia } from "@/lib/api";
import type { Locale } from "@/i18n/routing";
import { resolveMediaUrl } from "@/lib/media";
import { BASE_URL, getSiteJsonLd, SEO, serializeJsonLd } from "@/lib/seo";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(BASE_URL),
  title: {
    template: `%s | ${SEO.brandName}`,
    default: `${SEO.brandName} | Handmade Candles and Custom Gifts`,
  },
  description: SEO.siteDescription,
  applicationName: SEO.brandName,
  openGraph: {
    type: "website",
    siteName: SEO.brandName,
    title: `${SEO.brandName} | Handmade Candles and Custom Gifts`,
    description: SEO.siteDescription,
    url: BASE_URL,
    locale: "en",
    alternateLocale: ["bg"],
  },
  twitter: {
    card: "summary_large_image",
    title: `${SEO.brandName} | Handmade Candles and Custom Gifts`,
    description: SEO.siteDescription,
  },
  icons: {
    icon: "/favicon-atelier.svg",
  },
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const nonce = (await headers()).get("x-nonce") ?? undefined;
  const locale = (await getLocale()) as Locale;
  const siteMedia = await getPublicSiteMedia().catch(() => null);
  const pageBackground = resolveMediaUrl(siteMedia?.assets.page_background);
  const bodyStyle = pageBackground
    ? ({ "--site-page-background-image": `url("${pageBackground}")` } as CSSProperties)
    : undefined;

  return (
    <html lang={locale}>
      <body className="font-sans" style={bodyStyle}>
        <script
          nonce={nonce}
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: serializeJsonLd(getSiteJsonLd(locale)),
          }}
        />
        {children}
      </body>
    </html>
  );
}
