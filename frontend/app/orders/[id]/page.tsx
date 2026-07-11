"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getOrder } from "@/lib/api";
import { ApiError } from "@/lib/api-client";
import { formatPrice } from "@/lib/utils";
import { OrderStatusBadge } from "@/components/orders/OrderStatusBadge";
import { StatusTimeline } from "@/components/orders/StatusTimeline";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import type { OrderResponse } from "@/lib/types";

export default function OrderDetailPage() {
  const params = useParams();
  const orderId = params.id as string;

  const [order, setOrder] = useState<OrderResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchOrder() {
      setIsLoading(true);
      setNotFound(false);
      setError(null);
      try {
        const data = await getOrder(orderId);
        if (!cancelled) {
          setOrder(data);
        }
      } catch (err) {
        if (!cancelled) {
          if (err instanceof ApiError && err.code === "NOT_FOUND") {
            setNotFound(true);
          } else {
            setError("Something went wrong loading this order.");
          }
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchOrder();
    return () => {
      cancelled = true;
    };
  }, [orderId]);

  // Loading skeleton
  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
        <Skeleton className="mb-4 h-10 w-48" />
        <Skeleton className="mb-8 h-6 w-32" />
        <div className="grid gap-8 md:grid-cols-[1fr_200px]">
          <div className="space-y-4">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
          </div>
          <div className="space-y-3">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-32 w-full" />
          </div>
        </div>
      </div>
    );
  }

  // Error state (network/server errors)
  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
        <div className="rounded-brand border border-champagne-beige bg-warm-ivory p-8 text-center">
          <h1 className="mb-4 font-heading text-2xl text-charcoal">
            Something went wrong
          </h1>
          <p className="mb-6 text-soft-brown">{error}</p>
          <Button
            onClick={() => window.location.reload()}
            variant="primary"
            size="md"
          >
            Try again
          </Button>
        </div>
      </div>
    );
  }

  // Not found state
  if (notFound || !order) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
        <div className="rounded-brand border border-champagne-beige bg-warm-ivory p-8 text-center">
          <h1 className="mb-4 font-heading text-2xl text-charcoal">
            Order not found
          </h1>
          <p className="mb-6 text-soft-brown">
            We couldn&apos;t find this order.
          </p>
          <Link href="/orders">
            <Button variant="primary" size="md">
              Back to Orders
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  const date = new Date(order.created_at).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      {/* Header */}
      <div className="mb-8">
        <Link
          href="/orders"
          className="mb-4 inline-block text-sm text-soft-brown hover:text-charcoal transition-colors duration-fast"
        >
          ← Back to Orders
        </Link>
        <div className="flex items-center gap-4">
          <h1 className="font-heading text-2xl text-charcoal">
            Order #{order.id.slice(0, 8)}
          </h1>
          <OrderStatusBadge status={order.status} />
        </div>
        <p className="mt-1 text-sm text-soft-brown">{date}</p>
      </div>

      <div className="grid gap-8 md:grid-cols-[1fr_200px]">
        {/* Items table */}
        <div>
          <h2 className="mb-3 font-heading text-lg text-charcoal">Items</h2>
          <div className="divide-y divide-champagne-beige rounded-brand border border-champagne-beige">
            {order.items.map((item) => (
              <div
                key={item.product_id}
                className="flex items-center justify-between px-4 py-3"
              >
                <div>
                  <p className="font-medium text-charcoal">
                    {item.product_name}
                  </p>
                  <p className="text-sm text-soft-brown">
                    Qty: {item.quantity} × {formatPrice(item.price_cents)}
                  </p>
                </div>
                <p className="font-medium text-charcoal">
                  {formatPrice(item.price_cents * item.quantity)}
                </p>
              </div>
            ))}
          </div>

          {/* Total */}
          <div className="mt-4 flex items-center justify-between border-t border-champagne-beige pt-4">
            <span className="font-heading text-xl text-charcoal">Total</span>
            <span className="font-heading text-xl text-charcoal">
              {formatPrice(order.total_cents)}
            </span>
          </div>

          {/* Customer email */}
          <p className="mt-4 text-sm text-soft-brown">
            Contact: {order.customer_email}
          </p>
        </div>

        {/* Status Timeline */}
        <div>
          <h2 className="mb-3 font-heading text-lg text-charcoal">Status</h2>
          <StatusTimeline currentStatus={order.status} />
        </div>
      </div>
    </div>
  );
}
