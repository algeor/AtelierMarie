"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getOrder } from "@/lib/api";
import { useCart } from "@/contexts/CartContext";
import { ApiError } from "@/lib/api-client";
import { formatPrice } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import type { OrderResponse } from "@/lib/types";

export default function OrderConfirmationPage() {
  const params = useParams();
  const orderId = params.id as string;
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
        const data = await getOrder(orderId);
        if (!cancelled) {
          setOrder(data);
        }
      } catch (err) {
        if (!cancelled) {
          if (err instanceof ApiError && err.code === "NOT_FOUND") {
            setError("Order not found");
          } else {
            console.error("Order fetch failed:", err);
            setError("Something went wrong loading your order. Please try again.");
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
  }, [orderId]);

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
            Order not found
          </h1>
          <p className="mb-6 text-soft-brown">
            We couldn&apos;t find this order. It may have been removed or the
            link is incorrect.
          </p>
          <Link href="/products">
            <Button variant="primary" size="lg">
              Continue Shopping
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  // Success state
  return (
    <div className="mx-auto max-w-2xl px-4 py-12 sm:px-6">
      <div className="rounded-brand border border-champagne-beige bg-warm-ivory p-8">
        <h1 className="mb-2 font-heading text-3xl text-charcoal">
          Thank you for your order!
        </h1>
        <p className="mb-8 text-soft-brown">Order #{order.id}</p>

        {/* Order items */}
        <div className="mb-6">
          <h2 className="mb-3 font-heading text-lg text-charcoal">
            Items ordered
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
                    Qty: {item.quantity} &times;{" "}
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
        <div className="mb-6 flex items-center justify-between border-t border-champagne-beige pt-4">
          <span className="font-heading text-xl text-charcoal">Total</span>
          <span className="font-heading text-xl text-charcoal">
            {formatPrice(order.total_cents)}
          </span>
        </div>

        {/* Contact note */}
        <p className="mb-8 text-sm text-soft-brown">
          Order confirmation noted for {order.customer_email}
        </p>

        {/* Continue shopping */}
        <Link href="/products">
          <Button variant="primary" size="lg">
            Continue Shopping
          </Button>
        </Link>
      </div>
    </div>
  );
}
