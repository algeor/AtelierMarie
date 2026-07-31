import type { Metadata } from "next";
import { getLocale } from "next-intl/server";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    template: "%s | Atelier Marie",
    default: "Atelier Marie | Luxury Handcrafted Candles",
  },
  description:
    "Luxury handcrafted candles for your home. Artisan scents made with love.",
  icons: {
    icon: "/favicon.svg",
  },
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const locale = await getLocale();

  return (
    <html lang={locale}>
      <body className="font-sans">{children}</body>
    </html>
  );
}
