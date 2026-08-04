"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { createStripeRetrySession } from "@/lib/api";
import { ApiError } from "@/lib/api-client";
import { Skeleton } from "@/components/ui/Skeleton";

type PageState = "redirecting" | "error";

export default function RetryPaymentPage() {
  const tOrders = useTranslations("orders");
  const tPayment = useTranslations("orders.payment");
  const params = useParams();
  const searchParams = useSearchParams();
  const orderId = params.id as string;
  const paymentReturnToken =
    searchParams.get("payment_return_token") ?? searchParams.get("token");
  const [state, setState] = useState<PageState>("redirecting");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    async function startSession() {
      try {
        const { stripe_checkout_url } = await createStripeRetrySession(
          orderId,
          paymentReturnToken
        );
        window.location.href = stripe_checkout_url;
      } catch (err) {
        if (err instanceof ApiError && err.code === "INVALID_PAYMENT_STATE") {
          setErrorMessage(tPayment("retryNotCard"));
        } else {
          setErrorMessage(tPayment("retryError"));
        }
        setState("error");
      }
    }

    startSession();
  }, [orderId, paymentReturnToken, tPayment]);

  if (state === "redirecting") {
    return (
      <main className="bg-page px-4 py-24 text-center text-text">
        <div className="mx-auto max-w-md">
        <Skeleton className="mx-auto mb-4 h-6 w-48" />
        <p className="text-sm text-muted">{tPayment("retryRedirecting")}</p>
        </div>
      </main>
    );
  }

  return (
    <main className="bg-page px-4 py-24 text-center text-text">
      <div className="mx-auto max-w-md rounded-brand border border-border/60 bg-surface-elevated/75 p-8">
      <p className="mb-6 text-sm text-error">{errorMessage}</p>
      <Link
        href={`/orders/${orderId}`}
        className="inline-flex items-center justify-center rounded-brand bg-primary px-6 py-3 font-medium text-primary-foreground transition-colors duration-fast hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page"
      >
        {tOrders("backToOrders")}
      </Link>
      </div>
    </main>
  );
}
