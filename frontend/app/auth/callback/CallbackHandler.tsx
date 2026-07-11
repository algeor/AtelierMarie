"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { getCurrentUser } from "@/lib/api";
import { validateRedirectPath } from "@/lib/validateRedirectPath";

type CallbackState = "loading" | "error";

export function CallbackHandler() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { login, loginComplete } = useAuth();
  const [state, setState] = useState<CallbackState>("loading");

  useEffect(() => {
    const error = searchParams.get("error");

    // If error param is present, show error immediately without API call
    if (error) {
      setState("error");
      return;
    }

    let cancelled = false;

    async function handleCallback() {
      try {
        const user = await getCurrentUser();
        if (cancelled) return;

        if (!user) {
          setState("error");
          return;
        }

        loginComplete(user);

        // Determine redirect path: query param first, sessionStorage fallback, then /
        const redirectParam = searchParams.get("redirect_to");
        const storedPath = sessionStorage.getItem("auth_redirect_to");
        const rawPath = redirectParam || storedPath || "/";
        const targetPath = validateRedirectPath(rawPath);

        // Clear sessionStorage immediately
        sessionStorage.removeItem("auth_redirect_to");

        router.replace(targetPath);
      } catch {
        if (!cancelled) {
          setState("error");
        }
      }
    }

    handleCallback();
    return () => {
      cancelled = true;
    };
  }, [searchParams, router, loginComplete]);

  if (state === "error") {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-center max-w-md mx-auto px-4">
          <h1 className="font-heading text-2xl text-charcoal mb-4">
            Sign in failed
          </h1>
          <p className="text-soft-brown mb-6">
            Something went wrong during sign in. Please try again.
          </p>
          <button
            onClick={login}
            className="inline-flex items-center justify-center px-6 py-3 bg-charcoal text-warm-ivory font-medium rounded-brand hover:bg-soft-brown transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  // Loading state
  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="text-center">
        <div className="w-8 h-8 border-2 border-soft-brown border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-soft-brown font-medium">Signing you in...</p>
      </div>
    </div>
  );
}
