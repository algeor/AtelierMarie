import type { Metadata } from "next";
import type { Locale } from "@/i18n/routing";
import { getLocalizedAlternates } from "@/lib/seo";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: Locale }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return {
    title: "Checkout | Atelier Marie",
    robots: {
      index: false,
      follow: false,
    },
    alternates: getLocalizedAlternates(locale, "/checkout"),
  };
}

export default function CheckoutLayout({ children }: { children: React.ReactNode }) {
  return children;
}
