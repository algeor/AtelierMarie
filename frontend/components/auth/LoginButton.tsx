"use client";

import { useTranslations } from "next-intl";
import { useAuth } from "@/contexts/AuthContext";
import { cn } from "@/lib/utils";

interface LoginButtonProps {
  className?: string;
}

export function LoginButton({ className }: LoginButtonProps) {
  const t = useTranslations("auth");
  const { login } = useAuth();
  const hasCustomClassName = Boolean(className);

  return (
    <button
      onClick={login}
      className={cn(
        !hasCustomClassName && "text-soft-brown hover:text-charcoal transition-colors duration-fast font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory rounded-brand px-1 py-0.5",
        className
      )}
    >
      {t("signIn")}
    </button>
  );
}
