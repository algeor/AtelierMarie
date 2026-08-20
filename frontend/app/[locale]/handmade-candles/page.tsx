import { redirect } from "next/navigation";
import type { Metadata } from "next";
import type { Locale } from "@/i18n/routing";
import { HANDMADE_CANDLES_PATHS } from "@/lib/seo-pages";
import {
  HandmadeCandlesLandingPage,
  getHandmadeCandlesMetadata,
} from "@/components/seo/HandmadeCandlesLandingPage";

type Props = {
  params: Promise<{ locale: Locale }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  return getHandmadeCandlesMetadata(locale);
}

export default async function HandmadeCandlesPage({ params }: Props) {
  const { locale } = await params;
  if (locale !== "en") redirect(`/${locale}${HANDMADE_CANDLES_PATHS[locale]}`);

  return <HandmadeCandlesLandingPage locale={locale} />;
}
