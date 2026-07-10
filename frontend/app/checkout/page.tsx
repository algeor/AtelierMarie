"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useCart } from "@/contexts/CartContext";
import { createOrder } from "@/lib/api";
import { ApiError } from "@/lib/api-client";
import { formatPrice } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function CheckoutPage() {
  const router = useRouter();
  const { items, total_cents, isLoading, refreshCart } = useCart();

  // Form state
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [notes, setNotes] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Refs for focus management
  const emailRef = useRef<HTMLInputElement>(null);
  const hasRedirected = useRef(false);

  // Refresh cart on mount for freshest prices
  useEffect(() => {
    refreshCart();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Redirect to products if cart is empty after loading
  useEffect(() => {
    if (!isLoading && items.length === 0 && !hasRedirected.current) {
      hasRedirected.current = true;
      router.push("/products");
    }
  }, [isLoading, items.length, router]);

  const validateEmail = useCallback((value: string): string | null => {
    if (!value.trim()) return "Email is required";
    if (!EMAIL_REGEX.test(value)) return "Please enter a valid email address";
    return null;
  }, []);

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

      // Validate
      const emailError = validateEmail(email);
      if (emailError) {
        setErrors({ email: emailError });
        emailRef.current?.focus();
        return;
      }

      setErrors({});
      setIsSubmitting(true);

      try {
        const order = await createOrder({
          customer_email: email.trim(),
          customer_name: name.trim() || null,
          shipping_address: address.trim() || null,
          notes: notes.trim() || null,
        });
        router.push(`/orders/${order.id}/confirmation`);
      } catch (error) {
        if (error instanceof ApiError && error.code === "CONFLICT") {
          setSubmitError(
            "Some items are no longer available. Please review your cart."
          );
        } else {
          setSubmitError("Something went wrong. Please try again.");
        }
      } finally {
        setIsSubmitting(false);
      }
    },
    [email, name, address, notes, validateEmail, router]
  );

  // Loading skeleton
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

  // Don't render form if cart is empty (redirect will fire)
  if (items.length === 0) {
    return null;
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
      <h1 className="mb-8 font-heading text-3xl text-charcoal">Checkout</h1>

      <div className="grid gap-12 lg:grid-cols-[1fr_400px]">
        {/* Contact & Shipping Form */}
        <form onSubmit={handleSubmit} noValidate>
          {/* Submission error */}
          <div aria-live="polite" className="mb-6">
            {submitError && (
              <div className="rounded-brand border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {submitError}
              </div>
            )}
          </div>

          {/* Email */}
          <div className="mb-6">
            <label
              htmlFor="checkout-email"
              className="mb-1.5 block text-sm font-medium text-soft-brown"
            >
              Email <span className="text-red-700">*</span>
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
              placeholder="your@email.com"
            />
            {errors.email && (
              <p
                id="checkout-email-error"
                className="mt-1.5 text-sm text-red-700"
              >
                {errors.email}
              </p>
            )}
          </div>

          {/* Name */}
          <div className="mb-6">
            <label
              htmlFor="checkout-name"
              className="mb-1.5 block text-sm font-medium text-soft-brown"
            >
              Name
            </label>
            <input
              id="checkout-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-brand border border-champagne-beige px-4 py-3 text-charcoal bg-warm-ivory placeholder:text-soft-brown/50 focus:outline-none focus:ring-2 focus:ring-soft-brown focus:ring-offset-2 focus:ring-offset-warm-ivory"
              placeholder="Full name"
            />
          </div>

          {/* Shipping Address */}
          <div className="mb-6">
            <label
              htmlFor="checkout-address"
              className="mb-1.5 block text-sm font-medium text-soft-brown"
            >
              Shipping Address (optional)
            </label>
            <textarea
              id="checkout-address"
              rows={3}
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              className="w-full rounded-brand border border-champagne-beige px-4 py-3 text-charcoal bg-warm-ivory placeholder:text-soft-brown/50 focus:outline-none focus:ring-2 focus:ring-soft-brown focus:ring-offset-2 focus:ring-offset-warm-ivory"
              placeholder="Street, city, postal code"
            />
          </div>

          {/* Order Notes */}
          <div className="mb-6">
            <label
              htmlFor="checkout-notes"
              className="mb-1.5 block text-sm font-medium text-soft-brown"
            >
              Order Notes (optional)
            </label>
            <textarea
              id="checkout-notes"
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full rounded-brand border border-champagne-beige px-4 py-3 text-charcoal bg-warm-ivory placeholder:text-soft-brown/50 focus:outline-none focus:ring-2 focus:ring-soft-brown focus:ring-offset-2 focus:ring-offset-warm-ivory"
              placeholder="Any special requests..."
            />
          </div>

          {/* Submit button (visible on mobile, hidden on desktop where sidebar has it) */}
          <div className="lg:hidden">
            <Button
              type="submit"
              variant="primary"
              size="lg"
              isLoading={isSubmitting}
              className="w-full"
            >
              {isSubmitting ? "Placing order..." : "Place Order"}
            </Button>
          </div>
        </form>

        {/* Order Summary Sidebar */}
        <aside className="lg:sticky lg:top-24 lg:self-start">
          <div className="rounded-brand border border-champagne-beige bg-warm-ivory p-6">
            <h2 className="mb-4 font-heading text-xl text-charcoal">
              Order Summary
            </h2>

            <ul className="divide-y divide-champagne-beige">
              {items.map((item) => (
                <li
                  key={item.product_id}
                  className="flex items-center justify-between py-3 text-sm"
                >
                  <div className="flex-1 pr-4">
                    <p className="font-medium text-charcoal">
                      {item.product.name}
                    </p>
                    <p className="text-soft-brown">
                      {item.quantity} &times;{" "}
                      {formatPrice(item.product.price_cents)}
                    </p>
                  </div>
                  <p className="font-medium text-charcoal">
                    {formatPrice(item.product.price_cents * item.quantity)}
                  </p>
                </li>
              ))}
            </ul>

            <div className="mt-4 flex items-center justify-between border-t border-champagne-beige pt-4">
              <span className="font-heading text-lg text-charcoal">
                Subtotal
              </span>
              <span className="font-heading text-lg text-charcoal">
                {formatPrice(total_cents)}
              </span>
            </div>

            {/* Desktop submit button */}
            <div className="mt-6 hidden lg:block">
              <Button
                type="submit"
                variant="primary"
                size="lg"
                isLoading={isSubmitting}
                className="w-full"
                onClick={handleSubmit}
              >
                {isSubmitting ? "Placing order..." : "Place Order"}
              </Button>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
