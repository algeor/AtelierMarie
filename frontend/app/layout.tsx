import type { Metadata } from "next";
import { getLocale } from "next-intl/server";
import type { CSSProperties } from "react";
import { getPublicSiteMedia } from "@/lib/api";
import { resolveMediaUrl } from "@/lib/media";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    template: "%s | Atelier Marie",
    default: "Atelier Marie | Luxury Handcrafted Candles",
  },
  description:
    "Luxury handcrafted candles for your home. Artisan scents made with love.",
  icons: {
    icon: "/favicon-atelier.svg",
  },
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const locale = await getLocale();
  const siteMedia = await getPublicSiteMedia().catch(() => null);
  const pageBackground = resolveMediaUrl(siteMedia?.assets.page_background);
  const bodyStyle = pageBackground
    ? ({ "--site-page-background-image": `url("${pageBackground}")` } as CSSProperties)
    : undefined;

  return (
    <html lang={locale}>
      <body className="font-sans" style={bodyStyle}>{children}</body>
    </html>
  );
}
