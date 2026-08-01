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
      <div className="mx-auto max-w-2xl px-4 py-12 sm:px-6">
        <div className="rounded-brand border border-champagne-beige bg-warm-ivory p-8">
          <Skeleton className="mb-4 h-10 w-64" />
          <Skeleton className="mb-8 h-6 w-40" />
          <div className="space-y-4">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
          <Skeleton className="mt-6 h-8 w-32" />
        </div>
      </div>
    );
  }

  // Error state
  if (error || !order) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-12 sm:px-6">
        <div className="rounded-brand border border-champagne-beige bg-warm-ivory p-8 text-center">
          <h1 className="mb-4 font-heading text-2xl text-charcoal">
            {t("notFound")}
          </h1>
          <p className="mb-6 text-soft-brown">
            {error ?? t("notFoundDescription")}
          </p>
          <Link href="/products">
            <Button variant="primary" size="lg">
              {tCart("continueShopping")}
            </Button>
          </Link>
        </div>
      </div>
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
        : order.payment_method === "bank_transfer" && order.payment_status === "pending"
          ? tPayment("bankInstructions")
          : null;
  const paymentMessageClass =
    order.payment_status === "paid"
      ? "border-green-200 bg-green-50 text-green-800"
      : order.payment_status === "failed"
        ? "border-red-200 bg-red-50 text-red-700"
        : "border-amber-200 bg-amber-50 text-amber-800";
  const bankDetails = getBankDetails();
  const showBankInstructions =
    order.payment_method === "bank_transfer" &&
    order.payment_status === "pending" &&
    Boolean(bankDetails.iban);

  // Success state
  return (
    <div className="mx-auto max-w-2xl px-4 py-12 sm:px-6">
      <div className="rounded-brand border border-champagne-beige bg-warm-ivory p-8">
        <h1 className="mb-2 font-heading text-3xl text-charcoal">
          {t("orderConfirmationMessage")}
        </h1>
        <p className="mb-8 text-soft-brown">{t("orderNumber", { id: order.id })}</p>

        {paymentMessage && (
          <div
            className={`mb-6 rounded-brand border px-4 py-3 text-sm font-medium ${paymentMessageClass}`}
            role="status"
          >
            {paymentMessage}
          </div>
        )}

        {/* Order items */}
        <div className="mb-6">
          <h2 className="mb-3 font-heading text-lg text-charcoal">
            {t("itemsOrdered")}
          </h2>
          <ul className="divide-y divide-champagne-beige rounded-brand border border-champagne-beige">
            {order.items.map((item) => (
              <li
                key={item.product_id}
                className="flex items-center justify-between px-4 py-3"
              >
                <div>
                  <p className="font-medium text-charcoal">
                    {item.product_name}
                  </p>
                  <p className="text-sm text-soft-brown">
                    {t("quantityShort", { quantity: item.quantity })} &times;{" "}
                    {formatPrice(item.price_cents)}
                  </p>
                </div>
                <p className="font-medium text-charcoal">
                  {formatPrice(item.price_cents * item.quantity)}
                </p>
              </li>
            ))}
          </ul>
        </div>

        {/* Order total */}
        <div className="mb-6 space-y-2 border-t border-champagne-beige pt-4">
          <div className="flex items-center justify-between text-sm">
            <span className="text-soft-brown">{tCart("subtotal")}</span>
            <span className="text-charcoal">
              {formatPrice(order.items_total_cents)}
            </span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-soft-brown">{tDelivery("shippingLabel")}</span>
            <span className="text-charcoal">
              {order.shipping_cents === 0
                ? tDelivery("freeShipping")
                : formatPrice(order.shipping_cents)}
            </span>
          </div>
          <div className="flex items-center justify-between border-t border-champagne-beige pt-2">
            <span className="font-heading text-xl text-charcoal">{t("total")}</span>
            <span className="font-heading text-xl text-charcoal">
              {formatPrice(order.total_cents)}
            </span>
          </div>
        </div>

        {showBankInstructions && (
          <section className="mb-6 rounded-brand border border-champagne-beige bg-cream p-4 text-sm" aria-labelledby="bank-transfer-heading">
            <h2 id="bank-transfer-heading" className="font-medium text-charcoal">
              {tPayment("bankInstructions")}
            </h2>
            <dl className="mt-3 space-y-1.5">
              {bankDetails.name && (
                <div className="flex flex-wrap gap-2">
                  <dt className="font-medium text-charcoal">{tPayment("bankName")}:</dt>
                  <dd className="text-soft-brown">{bankDetails.name}</dd>
                </div>
              )}
              <div className="flex flex-wrap gap-2">
                <dt className="font-medium text-charcoal">{tPayment("bankIban")}:</dt>
                <dd className="font-mono text-soft-brown">{bankDetails.iban}</dd>
              </div>
              {bankDetails.bic && (
                <div className="flex flex-wrap gap-2">
                  <dt className="font-medium text-charcoal">{tPayment("bankBic")}:</dt>
                  <dd className="text-soft-brown">{bankDetails.bic}</dd>
                </div>
              )}
              <div className="flex flex-wrap gap-2">
                <dt className="font-medium text-charcoal">{tPayment("bankAmount")}:</dt>
                <dd className="text-soft-brown">{formatPrice(order.total_cents)}</dd>
              </div>
              <div className="flex flex-wrap gap-2">
                <dt className="font-medium text-charcoal">{tPayment("bankReference")}:</dt>
                <dd className="font-mono text-soft-brown">{order.id.slice(0, 8)}</dd>
              </div>
            </dl>
            <p className="mt-3 text-xs text-soft-brown/70">{tPayment("bankNote")}</p>
          </section>
        )}

        <p className="mb-6 text-sm leading-6 text-soft-brown">
          {t("policyNote")} {" "}
          <Link href={policyPath("terms")} className="font-medium underline underline-offset-4 hover:text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-muted-gold">
            {tLegal("termsConditions")}
          </Link>{" "}
          <span aria-hidden="true">/</span>{" "}
          <Link href={policyPath("privacy")} className="font-medium underline underline-offset-4 hover:text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-muted-gold">
            {tLegal("privacyPolicy")}
          </Link>
        </p>

        {/* Contact note */}
        <p className="mb-8 text-sm text-soft-brown">
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
    </div>
  );
}
