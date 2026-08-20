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
    title: "Account | Atelier Marie",
    robots: {
      index: false,
      follow: false,
    },
    alternates: getLocalizedAlternates(locale, "/account"),
  };
}

export default function AccountLayout({ children }: { children: React.ReactNode }) {
  return children;
}
