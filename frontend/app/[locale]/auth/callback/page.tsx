import { Suspense } from "react";
import { getTranslations } from "next-intl/server";
import { CallbackHandler } from "./CallbackHandler";

function LoadingSpinner({ label }: { label: string }) {
  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="text-center">
        <div className="w-8 h-8 border-2 border-soft-brown border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-soft-brown font-medium">{label}</p>
      </div>
    </div>
  );
}

export default async function AuthCallbackPage() {
  const t = await getTranslations("auth");

  return (
    <Suspense fallback={<LoadingSpinner label={t("signingIn")} />}>
      <CallbackHandler />
    </Suspense>
  );
}
