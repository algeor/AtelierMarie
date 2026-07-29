"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Link, useRouter } from "@/i18n/navigation";
import { useCart } from "@/contexts/CartContext";
import { createOrder } from "@/lib/api";
import { ApiError } from "@/lib/api-client";
import { useLocalizedError } from "@/lib/useLocalizedError";
import { formatPrice } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  DeliverySection,
  validateDelivery,
  type DeliveryValidationErrors,
} from "@/components/checkout/DeliverySection";
import type { DeliveryInfo, PaymentMethod } from "@/lib/types";

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const STRIPE_ENABLED = process.env.NEXT_PUBLIC_STRIPE_ENABLED === "true";
const BANK_TRANSFER_ENABLED = Boolean(process.env.NEXT_PUBLIC_BANK_IBAN);

export default function CheckoutPage() {
  const t = useTranslations("checkout");
  const tRoot = useTranslations();
  const tCart = useTranslations("cart");
  const getLocalizedError = useLocalizedError();
  const router = useRouter();
  const { items, total_cents, isLoading, refreshCart } = useCart();

  // Form state
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [notes, setNotes] = useState("");
  const [delivery, setDelivery] = useState<Partial<DeliveryInfo>>({});
  const [deliveryErrors, setDeliveryErrors] = useState<DeliveryValidationErrors>({});
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("cod");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const emailRef = useRef<HTMLInputElement>(null);
  const hasRedirected = useRef(false);

  useEffect(() => {
    refreshCart();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!isLoading && items.length === 0 && !hasRedirected.current) {
      hasRedirected.current = true;
      router.push("/products");
    }
  }, [isLoading, items.length, router]);

  const validateEmail = useCallback(
    (value: string): string | null => {
      if (!value.trim()) return t("emailRequired");
      if (value.length > 254) return t("emailTooLong");
      if (!EMAIL_REGEX.test(value)) return t("emailInvalid");
      return null;
    },
    [t],
  );

  const handleEmailBlur = useCallback(() => {
    const error = validateEmail(email);
    setErrors((prev) => {
      if (error) return { ...prev, email: error };
      const { email: _, ...rest } = prev;
      return rest;
    });
  }, [email, validateEmail]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setSubmitError(null);

      const emailError = validateEmail(email);
      if (emailError) {
        setErrors({ email: emailError });
        emailRef.current?.focus();
        return;
      }

      const { valid, errors: dErrors, normalized } = validateDelivery(delivery, (k) => tRoot(k));
      if (!valid || !normalized) {
        setDeliveryErrors(dErrors);
        return;
      }

      setErrors({});
      setDeliveryErrors({});
      setIsSubmitting(true);

      try {
        const order = await createOrder({
          customer_email: email.trim(),
          customer_name: name.trim() || null,
          delivery: normalized,
          notes: notes.trim() || null,
          payment_method: paymentMethod,
        });
        if (order.stripe_checkout_url) {
          window.location.href = order.stripe_checkout_url;
        } else {
          router.push(`/orders/${order.id}/confirmation`);
        }
      } catch (error) {
        if (error instanceof ApiError) {
          setSubmitError(getLocalizedError(error.code));
        } else {
          setSubmitError(t("genericError"));
        }
      } finally {
        setIsSubmitting(false);
      }
    },
    [email, name, notes, delivery, paymentMethod, validateEmail, router, t, tRoot, getLocalizedError],
  );

  const renderLegalDisclosure = () => (
    <p className="mt-3 text-xs leading-5 text-soft-brown/75">
      {tRoot("terms.checkoutPrefix")} {" "}
      <Link
        href="/terms"
        className="font-medium text-soft-brown underline underline-offset-4 transition-colors hover:text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory rounded-brand"
      >
        {tRoot("terms.checkoutLink")}
      </Link>{" "}
      {tRoot("terms.checkoutSuffix")}
    </p>
  );

  if (isLoading) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <Skeleton className="mb-8 h-10 w-48" />
        <div className="grid gap-12 lg:grid-cols-[1fr_400px]">
          <div className="space-y-6">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
          <div className="space-y-4">
            <Skeleton className="h-8 w-32" />
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        </div>
      </div>
    );
  }

  if (items.length === 0) return null;

  return (
    <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
      <h1 className="mb-8 font-heading text-3xl text-charcoal">{t("title")}</h1>

      <div className="grid gap-12 lg:grid-cols-[1fr_400px]">
        <form id="checkout-form" onSubmit={handleSubmit} noValidate>
          <div aria-live="polite" className="mb-6">
            {submitError && (
              <div className="rounded-brand border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {submitError}
              </div>
            )}
          </div>

          {/* Email */}
          <div className="mb-6">
            <label htmlFor="checkout-email" className="mb-1.5 block text-sm font-medium text-soft-brown">
              {t("email")} <span className="text-red-700">*</span>
            </label>
            <input
              ref={emailRef}
              id="checkout-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onBlur={handleEmailBlur}
              aria-required="true"
              aria-invalid={errors.email ? "true" : undefined}
              aria-describedby={errors.email ? "checkout-email-error" : undefined}
              className={`w-full rounded-brand border px-4 py-3 text-charcoal bg-warm-ivory placeholder:text-soft-brown/50 focus:outline-none focus:ring-2 focus:ring-soft-brown focus:ring-offset-2 focus:ring-offset-warm-ivory ${
                errors.email ? "border-red-700" : "border-champagne-beige"
              }`}
              placeholder={t("emailPlaceholder")}
            />
            {errors.email && (
              <p id="checkout-email-error" className="mt-1.5 text-sm text-red-700">
                {errors.email}
              </p>
            )}
          </div>

          {/* Name */}
          <div className="mb-6">
            <label htmlFor="checkout-name" className="mb-1.5 block text-sm font-medium text-soft-brown">
              {t("name")}
            </label>
            <input
              id="checkout-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={200}
              className="w-full rounded-brand border border-champagne-beige px-4 py-3 text-charcoal bg-warm-ivory placeholder:text-soft-brown/50 focus:outline-none focus:ring-2 focus:ring-soft-brown focus:ring-offset-2 focus:ring-offset-warm-ivory"
              placeholder={t("namePlaceholder")}
            />
          </div>

          {/* Delivery */}
          <DeliverySection value={delivery} onChange={setDelivery} errors={deliveryErrors} />

          {/* Order Notes */}
          <div className="mb-6">
            <label htmlFor="checkout-notes" className="mb-1.5 block text-sm font-medium text-soft-brown">
              {t("orderNotes")}
            </label>
            <textarea
              id="checkout-notes"
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              maxLength={500}
              className="w-full rounded-brand border border-champagne-beige px-4 py-3 text-charcoal bg-warm-ivory placeholder:text-soft-brown/50 focus:outline-none focus:ring-2 focus:ring-soft-brown focus:ring-offset-2 focus:ring-offset-warm-ivory"
              placeholder={t("notesPlaceholder")}
            />
          </div>

          {/* Payment method — only shown when more than one option is available */}
          {(STRIPE_ENABLED || BANK_TRANSFER_ENABLED) && (
          <div className="mb-6">
            <p className="mb-2 text-sm font-medium text-soft-brown">{t("paymentMethod.label")}</p>
            <div className="flex flex-col gap-2">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="radio"
                  name="payment_method"
                  value="cod"
                  checked={paymentMethod === "cod"}
                  onChange={() => setPaymentMethod("cod")}
                  className="accent-soft-brown"
                />
                <span className="text-sm text-charcoal">{t("paymentMethod.cod")}</span>
              </label>
              {STRIPE_ENABLED && (
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="radio"
                    name="payment_method"
                    value="card"
                    checked={paymentMethod === "card"}
                    onChange={() => setPaymentMethod("card")}
                    className="accent-soft-brown"
                  />
                  <span className="text-sm text-charcoal">{t("paymentMethod.card")}</span>
                </label>
              )}
              {BANK_TRANSFER_ENABLED && (
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="radio"
                    name="payment_method"
                    value="bank_transfer"
                    checked={paymentMethod === "bank_transfer"}
                    onChange={() => setPaymentMethod("bank_transfer")}
                    className="accent-soft-brown"
                  />
                  <span className="text-sm text-charcoal">{t("paymentMethod.bank_transfer")}</span>
                </label>
              )}
            </div>
          </div>
          )}

          <div className="lg:hidden">
            <Button type="submit" variant="primary" size="lg" isLoading={isSubmitting} className="w-full">
              {isSubmitting ? t("placingOrder") : t("placeOrder")}
            </Button>
            {renderLegalDisclosure()}
          </div>
        </form>

        <aside className="lg:sticky lg:top-24 lg:self-start">
          <div className="rounded-brand border border-champagne-beige bg-warm-ivory p-6">
            <h2 className="mb-4 font-heading text-xl text-charcoal">{t("orderSummary")}</h2>

            <ul className="divide-y divide-champagne-beige">
              {items.map((item) => (
                <li key={item.product_id} className="flex items-center justify-between py-3 text-sm">
                  <div className="flex-1 pr-4">
                    <p className="font-medium text-charcoal">{item.product.name}</p>
                    <p className="text-soft-brown">
                      {item.quantity} &times; {formatPrice(item.product.price_cents)}
                    </p>
                  </div>
                  <p className="font-medium text-charcoal">
                    {formatPrice(item.product.price_cents * item.quantity)}
                  </p>
                </li>
              ))}
            </ul>

            <div className="mt-4 flex items-center justify-between border-t border-champagne-beige pt-4">
              <span className="font-heading text-lg text-charcoal">{tCart("subtotal")}</span>
              <span className="font-heading text-lg text-charcoal">{formatPrice(total_cents)}</span>
            </div>

            <div className="mt-6 hidden lg:block">
              <Button
                type="submit"
                form="checkout-form"
                variant="primary"
                size="lg"
                isLoading={isSubmitting}
                className="w-full"
              >
                {isSubmitting ? t("placingOrder") : t("placeOrder")}
              </Button>
              {renderLegalDisclosure()}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
