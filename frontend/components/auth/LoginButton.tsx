"use client";

import { useAuth } from "@/contexts/AuthContext";

export function LoginButton() {
  const { login } = useAuth();

  return (
    <button
      onClick={login}
      className="min-w-[44px] min-h-[44px] inline-flex items-center justify-center text-soft-brown hover:text-charcoal transition-colors duration-fast font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory rounded-brand px-3 py-2"
    >
      Sign In
    </button>
  );
}
