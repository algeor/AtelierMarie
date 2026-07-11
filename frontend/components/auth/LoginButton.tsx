"use client";

import { useTranslations } from "next-intl";
import { useAuth } from "@/contexts/AuthContext";

export function LoginButton() {
  const t = useTranslations("auth");
  const { login } = useAuth();

  return (
    <button
      onClick={login}
      className="text-soft-brown hover:text-charcoal transition-colors duration-fast font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory rounded-brand px-1 py-0.5"
    >
      {t("signIn")}
    </button>
  );
}
