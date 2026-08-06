import { NextIntlClientProvider } from "next-intl";
import { getMessages } from "next-intl/server";
import { redirect } from "next/navigation";
import { routing } from "@/i18n/routing";
import { AuthProvider } from "@/contexts/AuthContext";
import { CookieConsentProvider } from "@/contexts/CookieConsentContext";
import { SavedProductsProvider } from "@/contexts/SavedProductsContext";
import { LocaleChrome } from "@/components/layout/LocaleChrome";

type Props = {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
};

export default async function LocaleLayout({ children, params }: Props) {
  const { locale } = await params;

  // Validate that the incoming `locale` parameter is valid
  if (!routing.locales.includes(locale as "en" | "bg")) {
    redirect("/en");
  }

  // Providing all messages to the client side
  const messages = await getMessages();

  return (
    <NextIntlClientProvider messages={messages}>
      <AuthProvider>
        <SavedProductsProvider>
          <CookieConsentProvider>
            <LocaleChrome>{children}</LocaleChrome>
          </CookieConsentProvider>
        </SavedProductsProvider>
      </AuthProvider>
    </NextIntlClientProvider>
  );
}
