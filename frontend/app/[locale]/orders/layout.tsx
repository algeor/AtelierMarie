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
    title: "Orders | Atelier Marie",
    robots: {
      index: false,
      follow: false,
    },
    alternates: getLocalizedAlternates(locale, "/orders"),
  };
}

export default function OrdersLayout({ children }: { children: React.ReactNode }) {
  return children;
}
