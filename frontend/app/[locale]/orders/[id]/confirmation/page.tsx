"use client";

import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { getOrder } from "@/lib/api";
import { useCart } from "@/contexts/CartContext";
import { ApiError } from "@/lib/api-client";
import { useLocalizedError } from "@/lib/useLocalizedError";
import { policyPath } from "@/lib/legal";
import { formatPrice } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { CourierTrackingSummary } from "@/components/orders/CourierTrackingSummary";
import { DeliveryDetails } from "@/components/checkout/DeliveryDetails";
import type { OrderResponse } from "@/lib/types";

function getBankDetails() {
  return {
    iban: process.env.NEXT_PUBLIC_BANK_IBAN ?? "",
    bic: process.env.NEXT_PUBLIC_BANK_BIC ?? "",
    name: process.env.NEXT_PUBLIC_BANK_NAME ?? "",
  };
}

export default function OrderConfirmationPage() {
  const t = useTranslations("orders");
  const tPayment = useTranslations("orders.payment");
  const tCart = useTranslations("cart");
  const tDelivery = useTranslations("checkout.delivery");
  const tLegal = useTranslations("legal");
  const getLocalizedError = useLocalizedError();
  const params = useParams();
  const searchParams = useSearchParams();
  const orderId = params.id as string;
  const paymentReturnToken =
    searchParams.get("payment_return_token") ?? searchParams.get("token");
  const { refreshCart } = useCart();

  const [order, setOrder] = useState<OrderResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchOrder() {
      setIsLoading(true);
      setError(null);

      try {
        const data = await getOrder(orderId, paymentReturnToken);
        if (!cancelled) {
          setOrder(data);
        }
      } catch (err) {
        if (!cancelled) {
          if (err instanceof ApiError) {
            setError(getLocalizedError(err.code));
          } else {
            console.error("Order fetch failed:", err);
            setError(t("loadingError"));
          }
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchOrder();
    // Refresh cart to sync with backend (backend cleared it after order)
    refreshCart();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orderId, paymentReturnToken, getLocalizedError, t]);

  // Loading state
  if (isLoading) {
    return (
      <main className="bg-page px-4 py-12 text-text sm:px-6">
        <div className="editorial-soft-panel mx-auto max-w-2xl rounded-brand p-8">
          <Skeleton className="mb-4 h-10 w-64" />
          <Skeleton className="mb-8 h-6 w-40" />
          <div className="space-y-4">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
          <Skeleton className="mt-6 h-8 w-32" />
        </div>
      </main>
    );
  }

  // Error state
  if (error || !order) {
    return (
      <main className="bg-page px-4 py-12 text-text sm:px-6">
        <div className="editorial-soft-panel mx-auto max-w-2xl rounded-brand p-8 text-center">
          <h1 className="mb-4 font-heading text-2xl text-text">
            {t("notFound")}
          </h1>
          <p className="mb-6 text-muted">{error ?? t("notFoundDescription")}</p>
          <Link href="/products">
            <Button variant="primary" size="lg">
              {tCart("continueShopping")}
            </Button>
          </Link>
        </div>
      </main>
    );
  }

  const paymentMessage =
    order.payment_method === "card"
      ? order.payment_status === "paid"
        ? tPayment("returnPaid")
        : order.payment_status === "failed"
          ? tPayment("returnFailed")
          : tPayment("returnPending")
      : order.payment_method === "cod"
        ? tPayment("codConfirmation")
        : order.payment_method === "bank_transfer" &&
            order.payment_status === "pending"
          ? tPayment("bankInstructions")
          : null;
  const paymentMessageClass =
    order.payment_status === "paid"
      ? "border-success/25 bg-success/10 text-success"
      : order.payment_status === "failed"
        ? "border-error/20 bg-error/10 text-error"
        : "border-warning/25 bg-warning/10 text-warning";
  const bankDetails = getBankDetails();
  const showBankInstructions =
    order.payment_method === "bank_transfer" &&
    order.payment_status === "pending" &&
    Boolean(bankDetails.iban);

  // Success state
  return (
    <main className="bg-page px-4 py-12 text-text sm:px-6">
      <div className="editorial-soft-panel mx-auto max-w-2xl rounded-brand p-8">
        <h1 className="mb-2 font-heading text-3xl text-text">
          {t("orderConfirmationMessage")}
        </h1>
        <p className="mb-8 text-muted">{t("orderNumber", { id: order.id })}</p>

        {paymentMessage && (
          <div
            className={`mb-6 rounded-brand border px-4 py-3 text-sm font-medium ${paymentMessageClass}`}
            role="status"
          >
            {paymentMessage}
          </div>
        )}

        {order.fulfillment_status === "awaiting_production" && (
          <div className="mb-6 rounded-brand border border-warning/25 bg-warning/10 px-4 py-3 text-sm leading-6 text-warning">
            <p>{t("craftedLaterNotice")}</p>
            <p>{t("shipsWhenCompleteNotice")}</p>
          </div>
        )}

        {/* Order items */}
        <div className="mb-6">
          <h2 className="mb-3 font-heading text-lg text-text">
            {t("itemsOrdered")}
          </h2>
          <ul className="divide-y divide-border/30 rounded-brand border border-border/30 bg-page/35">
            {order.items.map((item) => (
              <li
                key={item.product_id}
                className="flex items-center justify-between px-4 py-3"
              >
                <div>
                  <p className="font-medium text-text">{item.product_name}</p>
                  <p className="text-sm text-muted">
                    {t("quantityShort", { quantity: item.quantity })} &times;{" "}
                    {formatPrice(item.price_cents)}
                  </p>
                </div>
                <p className="font-medium text-text">
                  {formatPrice(item.price_cents * item.quantity)}
                </p>
              </li>
            ))}
          </ul>
        </div>

        {/* Order total */}
        <div className="mb-6 space-y-2 border-t editorial-divider pt-4">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted">{tCart("subtotal")}</span>
            <span className="text-text">
              {formatPrice(order.items_total_cents)}
            </span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted">{tDelivery("shippingLabel")}</span>
            <span className="text-text">
              {order.shipping_cents === 0
                ? tDelivery("freeShipping")
                : formatPrice(order.shipping_cents)}
            </span>
          </div>
          <div className="flex items-center justify-between border-t editorial-divider pt-2">
            <span className="font-heading text-xl text-text">{t("total")}</span>
            <span className="font-heading text-xl text-text">
              {formatPrice(order.total_cents)}
            </span>
          </div>
        </div>

        {showBankInstructions && (
          <section
            className="editorial-note-panel mb-6 rounded-brand p-4 text-sm"
            aria-labelledby="bank-transfer-heading"
          >
            <h2 id="bank-transfer-heading" className="font-medium text-text">
              {tPayment("bankInstructions")}
            </h2>
            <dl className="mt-3 space-y-1.5">
              {bankDetails.name && (
                <div className="flex flex-wrap gap-2">
                  <dt className="font-medium text-text">
                    {tPayment("bankName")}:
                  </dt>
                  <dd className="text-muted">{bankDetails.name}</dd>
                </div>
              )}
              <div className="flex flex-wrap gap-2">
                <dt className="font-medium text-text">
                  {tPayment("bankIban")}:
                </dt>
                <dd className="font-mono text-muted">{bankDetails.iban}</dd>
              </div>
              {bankDetails.bic && (
                <div className="flex flex-wrap gap-2">
                  <dt className="font-medium text-text">
                    {tPayment("bankBic")}:
                  </dt>
                  <dd className="text-muted">{bankDetails.bic}</dd>
                </div>
              )}
              <div className="flex flex-wrap gap-2">
                <dt className="font-medium text-text">
                  {tPayment("bankAmount")}:
                </dt>
                <dd className="text-muted">{formatPrice(order.total_cents)}</dd>
              </div>
              <div className="flex flex-wrap gap-2">
                <dt className="font-medium text-text">
                  {tPayment("bankReference")}:
                </dt>
                <dd className="font-mono text-muted">{order.id.slice(0, 8)}</dd>
              </div>
            </dl>
            <p className="mt-3 text-xs text-muted/70">{tPayment("bankNote")}</p>
          </section>
        )}

        <p className="mb-6 text-sm leading-6 text-muted">
          {t("policyNote")}{" "}
          <Link
            href={policyPath("terms")}
            className="rounded-brand font-medium underline underline-offset-4 hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          >
            {tLegal("termsConditions")}
          </Link>{" "}
          <span aria-hidden="true">/</span>{" "}
          <Link
            href={policyPath("privacy")}
            className="rounded-brand font-medium underline underline-offset-4 hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          >
            {tLegal("privacyPolicy")}
          </Link>
        </p>

        {/* Contact note */}
        <p className="mb-8 text-sm text-muted">
          {t("confirmationFor", { email: order.customer_email })}
        </p>

        {/* Delivery details */}
        <CourierTrackingSummary order={order} />
        <DeliveryDetails order={order} />

        {/* Continue shopping */}
        <Link href="/products">
          <Button variant="primary" size="lg">
            {tCart("continueShopping")}
          </Button>
        </Link>
      </div>
    </main>
  );
}
