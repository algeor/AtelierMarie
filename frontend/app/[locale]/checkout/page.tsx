"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Image from "next/image";
import { useTranslations } from "next-intl";
import { Link, useRouter } from "@/i18n/navigation";
import { useCart } from "@/contexts/CartContext";
import { useAuth } from "@/contexts/AuthContext";
import {
  createOrder,
  calculateShipping,
  getDeliverySettings,
  getPublicPaymentSettings,
} from "@/lib/api";
import { ApiError } from "@/lib/api-client";
import { trackAnalytics } from "@/lib/analytics";
import { useLocalizedError } from "@/lib/useLocalizedError";
import { useCookieConsent } from "@/contexts/CookieConsentContext";
import { policyPath } from "@/lib/legal";
import { formatPrice } from "@/lib/utils";
import { resolveMediaUrl } from "@/lib/media";
import { FREE_SHIPPING_THRESHOLD_CENTS } from "@/lib/constants";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  DeliverySection,
  validateDelivery,
  type DeliveryValidationErrors,
} from "@/components/checkout/DeliverySection";
import { CourierComparison } from "@/components/checkout/CourierComparison";
import { ShippingPriceSummary } from "@/components/checkout/ShippingPriceSummary";
import type {
  CalculateShippingRequest,
  Courier,
  DeliveryInfo,
  DeliverySettingsResponse,
  PaymentMethod,
  PublicPaymentSettingsResponse,
  ShippingQuote,
} from "@/lib/types";

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type DeliveryPhase = "method" | "approximate" | "exact" | "ready";

const ALL_COURIERS: Courier[] = ["speedy", "econt"];

function courierMethodEnabled(
  settings: DeliverySettingsResponse | null,
  courier: Courier,
  method: "office" | "door",
): boolean {
  if (!settings) return true;
  const key = `${courier}_${method}_enabled` as keyof Pick<
    DeliverySettingsResponse,
    | "speedy_office_enabled"
    | "speedy_door_enabled"
    | "econt_office_enabled"
    | "econt_door_enabled"
  >;
  return settings[key];
}

function enabledCouriersForMethod(
  settings: DeliverySettingsResponse | null,
  method: "office" | "door",
): Courier[] {
  return ALL_COURIERS.filter((courier) => courierMethodEnabled(settings, courier, method));
}

export default function CheckoutPage() {
  const t = useTranslations("checkout");
  const tRoot = useTranslations();
  const tCart = useTranslations("cart");
  const getLocalizedError = useLocalizedError();
  const router = useRouter();
  const { items, unavailable_items, total_cents, isLoading, refreshCart, removeItem } = useCart();
  const { analytics: analyticsConsent } = useCookieConsent();
  const { user } = useAuth();

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

  // Shipping-pricing state (Phase A)
  const [deliveryPhase, setDeliveryPhase] = useState<DeliveryPhase>("method");
  const [quotes, setQuotes] = useState<ShippingQuote[]>([]);
  const [selectedQuote, setSelectedQuote] = useState<ShippingQuote | null>(null);
  const [quotesLoading, setQuotesLoading] = useState(false);
  const [shippingError, setShippingError] = useState(false);
  const [deliverySettings, setDeliverySettings] = useState<DeliverySettingsResponse | null>(null);

  const qualifiesForFreeShipping = total_cents >= FREE_SHIPPING_THRESHOLD_CENTS;

  const emailRef = useRef<HTMLInputElement>(null);
  const nameRef = useRef<HTMLInputElement>(null);
  const hasRedirected = useRef(false);
  const trackedCheckoutStart = useRef(false);
  const paymentMethodTouched = useRef(false);
  const lastDeliverySignatureRef = useRef("");

  const [paymentSettings, setPaymentSettings] =
    useState<PublicPaymentSettingsResponse | null>(null);
  const [paymentSettingsLoading, setPaymentSettingsLoading] = useState(true);
  const [paymentSettingsError, setPaymentSettingsError] = useState(false);

  useEffect(() => {
    refreshCart();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    let cancelled = false;
    getDeliverySettings()
      .then((settings) => {
        if (!cancelled) setDeliverySettings(settings);
      })
      .catch(() => {
        if (!cancelled) setDeliverySettings(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setPaymentSettingsLoading(true);
    setPaymentSettingsError(false);
    getPublicPaymentSettings()
      .then((settings) => {
        if (cancelled) return;
        setPaymentSettings(settings);
        setPaymentMethod((current) => {
          const methods = settings.available_payment_methods;
          if (paymentMethodTouched.current && methods.includes(current)) return current;
          return methods[0] ?? "cod";
        });
      })
      .catch(() => {
        if (!cancelled) {
          setPaymentSettings(null);
          setPaymentSettingsError(true);
        }
      })
      .finally(() => {
        if (!cancelled) setPaymentSettingsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Pre-fill the email for logged-in users. Only seed when the field is still
  // empty so we never clobber a value the customer has started typing (e.g. a
  // different address than their account email).
  const hasPrefilledEmail = useRef(false);
  useEffect(() => {
    if (user?.email && !hasPrefilledEmail.current) {
      hasPrefilledEmail.current = true;
      setEmail((current) => (current.trim() ? current : user.email));
    }
  }, [user]);

  useEffect(() => {
    if (!isLoading && items.length === 0 && !hasRedirected.current) {
      hasRedirected.current = true;
      router.push("/products");
    }
  }, [isLoading, items.length, router]);

  useEffect(() => {
    if (!isLoading && items.length > 0 && !trackedCheckoutStart.current) {
      trackAnalytics("checkout_start", {
        item_count: items.reduce((sum, item) => sum + item.quantity, 0),
        value_cents: total_cents,
        currency: "BGN",
      });
      trackedCheckoutStart.current = true;
    }
  }, [isLoading, items, total_cents]);

  const handleDeliveryChange = useCallback((next: Partial<DeliveryInfo>) => {
    setDelivery(next);
    const courier = next.office?.courier || next.door?.courier || null;
    if (!next.method || !courier) return;
    const signature = `${next.method}:${courier}`;
    if (signature === lastDeliverySignatureRef.current) return;
    lastDeliverySignatureRef.current = signature;
    trackAnalytics("delivery_selected", {
      delivery_method: next.method,
      delivery_courier: courier,
    });
  }, []);

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

  const validateName = useCallback(
    (value: string): string | null => {
      const trimmed = value.trim();
      if (!trimmed) return t("nameRequired");
      if (trimmed.length > 200) return t("nameTooLong");
      return null;
    },
    [t],
  );

  const handleNameBlur = useCallback(() => {
    const error = validateName(name);
    setErrors((prev) => {
      if (error) return { ...prev, name: error };
      const { name: _, ...rest } = prev;
      return rest;
    });
  }, [name, validateName]);

  // --- Shipping calculation (two-phase) ---
  // Derive the calculate request from the exposed delivery state and cart total.
  // On city/address entry → approximate (both couriers); on office/address
  // confirmation → exact (chosen courier only). Free shipping short-circuits.
  const method = delivery.method;
  const office = delivery.office ?? null;
  const door = delivery.door ?? null;
  const currentCourier: Courier | undefined = office?.courier ?? door?.courier;
  const officeConfirmed = Boolean(office?.office_id);
  const officeCity = office?.city ?? "";
  const officeId = office?.office_id ?? null;
  const doorCity = door?.city ?? "";
  const doorPostal = door?.postal_code ?? "";
  const doorStreet = door?.street ?? "";
  const doorComplete = Boolean(doorCity && doorPostal && doorStreet);

  useEffect(() => {
    if (!method || !currentCourier) {
      setDeliveryPhase("method");
      setQuotes([]);
      setSelectedQuote(null);
      setShippingError(false);
      return;
    }

    if (!courierMethodEnabled(deliverySettings, currentCourier, method)) {
      setDeliveryPhase("method");
      setQuotes([]);
      setSelectedQuote(null);
      setShippingError(false);
      return;
    }

    // Free shipping — no courier call needed.
    if (qualifiesForFreeShipping) {
      const freeQuote: ShippingQuote = {
        courier: currentCourier,
        cents: 0,
        estimated_delivery_days: null,
        is_fallback: false,
        price_source: "live",
        quoted_at: new Date().toISOString(),
      };
      setQuotes([freeQuote]);
      setSelectedQuote(freeQuote);
      setDeliveryPhase("ready");
      setShippingError(false);
      return;
    }

    const isExact = method === "office" ? officeConfirmed : doorComplete;
    // Office mode quotes against the selected office's city; door mode against
    // the typed city. Office approximate (no city yet) is skipped — it jumps
    // straight to exact once an office is picked.
    const city = method === "office" ? officeCity : doorCity;

    // Approximate needs at least a city for door; office approximate is skipped
    // (we quote only once an office — and thus its city — is selected).
    if (!isExact && method === "door" && !doorCity) {
      setDeliveryPhase("method");
      setQuotes([]);
      setSelectedQuote(null);
      setShippingError(false);
      return;
    }
    if (!isExact && method === "office") {
      // Waiting for office selection — nothing to quote yet.
      setDeliveryPhase("method");
      setQuotes([]);
      setSelectedQuote(null);
      setShippingError(false);
      return;
    }

    let cancelled = false;
    const couriers: Courier[] = isExact
      ? [currentCourier]
      : enabledCouriersForMethod(deliverySettings, method);
    if (couriers.length === 0) {
      setDeliveryPhase("method");
      setQuotes([]);
      setSelectedQuote(null);
      setShippingError(false);
      return;
    }
    const payload: CalculateShippingRequest = {
      method,
      city,
      office_id: method === "office" ? officeId : null,
      address: method === "door" && door ? door : null,
      items_total_cents: total_cents,
      couriers,
    };

    // Debounce so door-address keystrokes don't fire a request each time.
    const timer = setTimeout(() => {
      setQuotesLoading(true);
      setShippingError(false);
      setDeliveryPhase(isExact ? "exact" : "approximate");
      calculateShipping(payload)
        .then((res) => {
          if (cancelled) return;
          setQuotes(res.quotes);
          setSelectedQuote((prev) => {
            if (isExact) return res.quotes[0] ?? null;
            const match = prev
              ? res.quotes.find((q) => q.courier === prev.courier)
              : undefined;
            return match ?? res.quotes[0] ?? null;
          });
          if (isExact) setDeliveryPhase("ready");
        })
        .catch(() => {
          if (!cancelled) {
            // Surface the failure so a sub-€50 customer isn't silently stranded
            // with only the generic "choose a shipping option" message.
            setQuotes([]);
            setSelectedQuote(null);
            setShippingError(true);
          }
        })
        .finally(() => {
          if (!cancelled) setQuotesLoading(false);
        });
    }, 400);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [
    method,
    currentCourier,
    officeConfirmed,
    officeCity,
    officeId,
    doorComplete,
    doorCity,
    doorPostal,
    doorStreet,
    door,
    total_cents,
    qualifiesForFreeShipping,
    deliverySettings,
  ]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setSubmitError(null);

      const emailError = validateEmail(email);
      const nameError = validateName(name);
      if (unavailable_items.length > 0) {
        setSubmitError(t("unavailableItems"));
        return;
      }
      if (emailError || nameError) {
        setErrors({
          ...(emailError ? { email: emailError } : {}),
          ...(nameError ? { name: nameError } : {}),
        });
        if (emailError) {
          emailRef.current?.focus();
        } else {
          nameRef.current?.focus();
        }
        return;
      }

      const { valid, errors: dErrors, normalized } = validateDelivery(delivery, (k) => tRoot(k));
      if (!valid || !normalized) {
        setDeliveryErrors(dErrors);
        return;
      }

      setErrors({});
      setDeliveryErrors({});

      // Require a shipping quote unless the order qualifies for free shipping.
      if (!qualifiesForFreeShipping && !selectedQuote) {
        setSubmitError(t("delivery.shippingRequired"));
        return;
      }

      const availablePaymentMethods = paymentSettings?.available_payment_methods ?? [];
      if (!availablePaymentMethods.includes(paymentMethod)) {
        setSubmitError(t("paymentMethod.unavailable"));
        return;
      }

      setIsSubmitting(true);

      try {
        trackAnalytics("order_submit", {
          payment_method: paymentMethod,
          delivery_method: normalized.method,
          value_cents: total_cents,
          currency: "BGN",
        });
        const order = await createOrder({
          customer_email: email.trim(),
          customer_name: name.trim(),
          delivery: normalized,
          notes: notes.trim() || null,
          payment_method: paymentMethod,
          analytics_consent: analyticsConsent,
          shipping_cents: qualifiesForFreeShipping ? 0 : selectedQuote?.cents ?? 0,
          shipping_price_source: qualifiesForFreeShipping
            ? "live"
            : selectedQuote?.price_source ?? "live",
          shipping_is_fallback: qualifiesForFreeShipping
            ? false
            : selectedQuote?.is_fallback ?? false,
          shipping_quoted_at: qualifiesForFreeShipping
            ? null
            : selectedQuote?.quoted_at ?? null,
        });
        if (order.stripe_checkout_url) {
          trackAnalytics("payment_redirect", {
            order_id: order.id,
            payment_method: paymentMethod,
            payment_provider: "stripe",
            value_cents: order.total_cents,
            currency: "BGN",
          });
          window.location.href = order.stripe_checkout_url;
        } else {
          const tokenQuery =
            order.payment_method === "card" && order.payment_return_token
              ? `?token=${encodeURIComponent(order.payment_return_token)}`
              : "";
          router.push(`/orders/${order.id}/confirmation${tokenQuery}`);
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
    [
      analyticsConsent,
      email,
      name,
      notes,
      delivery,
      paymentMethod,
      paymentSettings,
      validateEmail,
      validateName,
      router,
      t,
      tRoot,
      getLocalizedError,
      total_cents,
      qualifiesForFreeShipping,
      selectedQuote,
      unavailable_items,
    ],
  );

  const renderLegalDisclosure = () => (
    <p className="mt-3 text-xs leading-5 text-soft-brown/75">
      {t("legalPrefix")} {" "}
      <Link
        href={policyPath("terms")}
        className="font-medium text-soft-brown underline underline-offset-4 transition-colors hover:text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory rounded-brand"
      >
        {t("legalTerms")}
      </Link>{" "}
      {t("legalMiddle")} {" "}
      <Link
        href={policyPath("privacy")}
        className="font-medium text-soft-brown underline underline-offset-4 transition-colors hover:text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory rounded-brand"
      >
        {t("legalPrivacy")}
      </Link>
      {t("legalSuffix")}
    </p>
  );

  const availablePaymentMethods = paymentSettings?.available_payment_methods ?? [];
  const showPaymentUnavailable =
    !paymentSettingsLoading && (paymentSettingsError || availablePaymentMethods.length === 0);

  const handlePaymentMethodChange = (method: PaymentMethod) => {
    paymentMethodTouched.current = true;
    setPaymentMethod(method);
  };

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
        <form id="checkout-form" onSubmit={handleSubmit} noValidate data-delivery-phase={deliveryPhase}>
          <div aria-live="polite" className="mb-6">
            {submitError && (
              <div className="rounded-brand border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {submitError}
              </div>
            )}
          </div>

          {unavailable_items.length > 0 && (
            <div className="mb-6 rounded-brand border border-amber-200 bg-amber-50 px-4 py-3" role="alert">
              <h2 className="text-sm font-medium text-amber-900">
                {t("unavailableItems")}
              </h2>
              <ul className="mt-2 divide-y divide-amber-200/70">
                {unavailable_items.map((item) => (
                  <li key={item.product_id} className="flex items-center justify-between gap-3 py-2">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-charcoal">
                        {item.product_name}
                      </p>
                      <p className="text-xs text-amber-800">{item.reason}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => removeItem(item.product_id)}
                      className="min-h-[44px] shrink-0 rounded-brand px-3 text-sm font-medium text-amber-900 underline underline-offset-4 hover:text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-700 focus-visible:ring-offset-2 focus-visible:ring-offset-amber-50"
                    >
                      {tCart("remove")}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

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
              {t("name")} <span className="text-red-700">*</span>
            </label>
            <input
              ref={nameRef}
              id="checkout-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onBlur={handleNameBlur}
              aria-required="true"
              aria-invalid={errors.name ? "true" : undefined}
              aria-describedby={errors.name ? "checkout-name-error" : undefined}
              maxLength={200}
              className={`w-full rounded-brand border px-4 py-3 text-charcoal bg-warm-ivory placeholder:text-soft-brown/50 focus:outline-none focus:ring-2 focus:ring-soft-brown focus:ring-offset-2 focus:ring-offset-warm-ivory ${
                errors.name ? "border-red-700" : "border-champagne-beige"
              }`}
              placeholder={t("namePlaceholder")}
            />
            {errors.name && (
              <p id="checkout-name-error" className="mt-1.5 text-sm text-red-700">
                {errors.name}
              </p>
            )}
          </div>

          {/* Delivery */}
          <DeliverySection
            value={delivery}
            onChange={handleDeliveryChange}
            errors={deliveryErrors}
            deliverySettings={deliverySettings}
          />

          {/* Courier price comparison — shown once a quote can be calculated */}
          {!qualifiesForFreeShipping &&
            (quotesLoading || quotes.length > 0) && (
              <CourierComparison
                quotes={quotes}
                selectedCourier={selectedQuote?.courier ?? null}
                onSelect={setSelectedQuote}
                isLoading={quotesLoading}
              />
            )}

          {/* Free-shipping celebration once the cart clears the threshold. */}
          {qualifiesForFreeShipping && method && currentCourier && (
            <p className="mb-6 rounded-brand bg-muted-gold/10 px-4 py-3 text-sm font-medium text-muted-gold" role="status">
              {t("delivery.freeShippingAchieved")}
            </p>
          )}

          {/* Calculate failure — offer the customer a way forward. */}
          {shippingError && !quotesLoading && (
            <div className="mb-6 rounded-brand border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">
              {t("delivery.shippingError")}
            </div>
          )}

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

          <div className="mb-6">
            <p className="mb-2 text-sm font-medium text-soft-brown">{t("paymentMethod.label")}</p>
            {paymentSettingsLoading ? (
              <Skeleton className="h-12 w-full" />
            ) : showPaymentUnavailable ? (
              <div className="rounded-brand border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">
                {t("paymentMethod.unavailable")}
              </div>
            ) : (
              <div className="flex flex-col gap-2" role="radiogroup" aria-label={t("paymentMethod.label")}>
                {availablePaymentMethods.map((method) => {
                  const label = t(`paymentMethod.${method}`);
                  return (
                    <label key={method} className="flex cursor-pointer items-start gap-3 rounded-brand border border-champagne-beige px-4 py-3">
                      <input
                        type="radio"
                        name="payment_method"
                        value={method}
                        checked={paymentMethod === method}
                        onChange={() => handlePaymentMethodChange(method)}
                        aria-label={label}
                        className="mt-1 accent-soft-brown"
                      />
                      <span>
                        <span className="block text-sm font-medium text-charcoal">{label}</span>
                        {method === "card" && (
                          <span className="mt-1 block text-xs leading-5 text-soft-brown/75">
                            {t("paymentMethod.cardCopy")}
                          </span>
                        )}
                        {method === "cod" && (
                          <span className="mt-1 block text-xs leading-5 text-soft-brown/75">
                            {t("paymentMethod.codCopy", {
                              amount: formatPrice(paymentSettings?.pay_on_delivery_max_cents ?? 5000),
                            })}
                          </span>
                        )}
                      </span>
                    </label>
                  );
                })}
              </div>
            )}
          </div>

        </form>

        <aside className="lg:sticky lg:top-24 lg:self-start">
          <div className="rounded-brand border border-champagne-beige bg-warm-ivory p-6">
            <h2 className="mb-4 font-heading text-xl text-charcoal">{t("orderSummary")}</h2>

            <ul className="divide-y divide-champagne-beige">
              {items.map((item) => {
                const thumbnailUrl = resolveMediaUrl(
                  item.product.primary_thumbnail_url ?? item.product.primary_image_url
                );
                return (
                  <li key={item.product_id} className="flex items-center justify-between gap-3 py-3 text-sm">
                    <div className="h-14 w-14 shrink-0 overflow-hidden rounded-brand border border-champagne-beige bg-cream">
                      {thumbnailUrl ? (
                        <Image src={thumbnailUrl} alt="" width={56} height={56} className="h-full w-full object-cover" />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center px-1 text-center font-heading text-[9px] leading-tight text-soft-brown/70">
                          {item.product.name}
                        </div>
                      )}
                    </div>
                    <div className="min-w-0 flex-1 pr-2">
                      <p className="truncate font-medium text-charcoal">{item.product.name}</p>
                      <p className="text-soft-brown">
                        {item.quantity} &times; {formatPrice(item.product.effective_price_cents)}
                      </p>
                    </div>
                    <p className="shrink-0 font-medium text-charcoal">
                      {formatPrice(item.product.effective_price_cents * item.quantity)}
                    </p>
                  </li>
                );
              })}
            </ul>

            <div className="mt-4 border-t border-champagne-beige pt-4">
              <ShippingPriceSummary
                itemsTotalCents={total_cents}
                shippingCents={
                  qualifiesForFreeShipping ? 0 : selectedQuote?.cents ?? null
                }
              />
            </div>

            <div className="mt-6">
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
