"use client";

import { Suspense } from "react";
import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { getCurrentUser } from "@/lib/api";
import { validateRedirectPath } from "@/lib/validateRedirectPath";
import { Button } from "@/components/ui/Button";

function LoadingSpinner() {
  return (
    <div role="status" aria-live="polite" className="flex min-h-[50vh] flex-col items-center justify-center">
      <svg
        aria-hidden="true"
        className="h-8 w-8 animate-spin text-muted-gold motion-reduce:animate-none"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>
      <p className="mt-4 text-soft-brown">Signing you in...</p>
    </div>
  );
}

function CallbackContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { login, loginComplete } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(true);

  useEffect(() => {
    const errorParam = searchParams.get("error");

    // If there's an error param, show error immediately
    if (errorParam) {
      setError("Sign in failed. Please try again.");
      setIsProcessing(false);
      return;
    }

    let cancelled = false;

    async function handleCallback() {
      try {
        const user = await getCurrentUser();
        if (cancelled) return;

        if (!user) {
          setError("Sign in failed. Please try again.");
          setIsProcessing(false);
          return;
        }

        loginComplete(user);

        // Determine redirect destination (prefer sessionStorage — set by user's
        // own login action — over query param which is attacker-controllable)
        const storedPath = sessionStorage.getItem("auth_redirect_to");
        const redirectParam = searchParams.get("redirect_to");
        const rawPath = storedPath || redirectParam || "/";
        const destination = validateRedirectPath(rawPath);

        // Clear stored redirect
        sessionStorage.removeItem("auth_redirect_to");

        router.replace(destination);
      } catch {
        if (!cancelled) {
          setError("Sign in failed. Please try again.");
          setIsProcessing(false);
        }
      }
    }

    handleCallback();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (error) {
    return (
      <div className="flex min-h-[50vh] flex-col items-center justify-center px-4">
        <div className="rounded-brand border border-champagne-beige bg-warm-ivory p-8 text-center max-w-md">
          <h1 className="mb-4 font-heading text-2xl text-charcoal">
            Sign In Failed
          </h1>
          <p className="mb-6 text-soft-brown">{error}</p>
          <Button onClick={login} variant="primary" size="md">
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  if (isProcessing) {
    return <LoadingSpinner />;
  }

  return null;
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <CallbackContent />
    </Suspense>
  );
}
