"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { getOrders } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { formatPrice } from "@/lib/utils";
import { OrderStatusBadge } from "@/components/orders/OrderStatusBadge";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import type { OrderListResponse } from "@/lib/types";

export default function OrdersPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [data, setData] = useState<OrderListResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const limit = 20;

  const fetchOrders = useCallback(async (pageNum: number) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await getOrders(pageNum, limit);
      setData(result);
    } catch {
      setError("Something went wrong loading your orders");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authLoading) return;
    if (!isAuthenticated) {
      setIsLoading(false);
      return;
    }
    fetchOrders(page);
  }, [page, fetchOrders, authLoading, isAuthenticated]);

  // Loading skeleton
  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
        <Skeleton className="mb-8 h-10 w-40" />
        <div className="space-y-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full rounded-brand" />
          ))}
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
        <h1 className="mb-8 font-heading text-3xl text-charcoal">My Orders</h1>
        <div className="rounded-brand border border-champagne-beige bg-warm-ivory p-8 text-center">
          <p className="mb-4 text-soft-brown">{error}</p>
          <Button onClick={() => fetchOrders(page)} variant="primary" size="md">
            Try again
          </Button>
        </div>
      </div>
    );
  }

  const orders = data?.orders ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / limit);

  // Empty state
  if (orders.length === 0 && page === 1) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
        <h1 className="mb-8 font-heading text-3xl text-charcoal">My Orders</h1>
        <div className="rounded-brand border border-champagne-beige bg-warm-ivory p-8 text-center">
          <p className="mb-2 text-lg text-charcoal">No orders yet</p>
          {!isAuthenticated && (
            <p className="mb-4 text-sm text-soft-brown">
              Sign in to see all your orders
            </p>
          )}
          <Link href="/products">
            <Button variant="primary" size="md">
              Start Shopping
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="mb-8 font-heading text-3xl text-charcoal">My Orders</h1>

      {/* Order list */}
      <div className="space-y-4">
        {orders.map((order) => {
          const date = new Date(order.created_at).toLocaleDateString("en-US", {
            year: "numeric",
            month: "short",
            day: "numeric",
          });
          const itemCount = order.items.reduce(
            (sum, item) => sum + item.quantity,
            0
          );

          return (
            <Link
              key={order.id}
              href={`/orders/${order.id}`}
              className="block rounded-brand border border-champagne-beige bg-warm-ivory p-4 transition-colors duration-fast hover:bg-cream"
            >
              <div className="flex items-center justify-between">
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-soft-brown">{date}</span>
                    <span className="text-xs text-soft-brown/70">
                      #{order.id.slice(0, 8)}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <OrderStatusBadge status={order.status} />
                    <span className="text-sm text-soft-brown">
                      {itemCount} {itemCount === 1 ? "item" : "items"}
                    </span>
                  </div>
                </div>
                <span className="font-medium text-charcoal">
                  {formatPrice(order.total_cents)}
                </span>
              </div>
            </Link>
          );
        })}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-8 flex items-center justify-center gap-4">
          <Button
            onClick={() => setPage((p) => p - 1)}
            disabled={page <= 1}
            variant="secondary"
            size="sm"
          >
            Previous
          </Button>
          <span className="text-sm text-soft-brown">
            Page {page} of {totalPages}
          </span>
          <Button
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= totalPages}
            variant="secondary"
            size="sm"
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
