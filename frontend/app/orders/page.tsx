"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { getOrders } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { OrderStatusBadge } from "@/components/orders/OrderStatusBadge";
import { Skeleton } from "@/components/ui/Skeleton";
import { formatPrice } from "@/lib/utils";
import type { OrderResponse } from "@/lib/types";

type PageState = "loading" | "success" | "error";

export default function OrdersPage() {
  const { isAuthenticated } = useAuth();
  const [orders, setOrders] = useState<OrderResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [state, setState] = useState<PageState>("loading");
  const limit = 20;

  const fetchOrders = useCallback(async (pageNum: number) => {
    setState("loading");
    try {
      const data = await getOrders(pageNum, limit);
      setOrders(data.orders);
      setTotal(data.total);
      setPage(pageNum);
      setState("success");
    } catch {
      setState("error");
    }
  }, []);

  useEffect(() => {
    fetchOrders(1);
  }, [fetchOrders]);

  const totalPages = Math.max(1, Math.ceil(total / limit));

  if (state === "loading") {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12">
        <h1 className="font-heading text-3xl text-charcoal mb-8">My Orders</h1>
        <div className="space-y-4">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="bg-white rounded-brand p-6 shadow-sm border border-champagne-beige"
            >
              <div className="flex items-center justify-between">
                <div className="space-y-2">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-4 w-24" />
                </div>
                <Skeleton className="h-6 w-20" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (state === "error") {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12">
        <h1 className="font-heading text-3xl text-charcoal mb-8">My Orders</h1>
        <div className="bg-white rounded-brand p-8 shadow-sm border border-champagne-beige text-center">
          <p className="text-soft-brown mb-4">
            Something went wrong loading your orders
          </p>
          <button
            onClick={() => fetchOrders(page)}
            className="inline-flex items-center justify-center px-6 py-3 bg-charcoal text-warm-ivory font-medium rounded-brand hover:bg-soft-brown transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  if (orders.length === 0) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12">
        <h1 className="font-heading text-3xl text-charcoal mb-8">My Orders</h1>
        <div className="bg-white rounded-brand p-8 shadow-sm border border-champagne-beige text-center">
          <p className="text-charcoal font-medium mb-2">No orders yet</p>
          <p className="text-soft-brown mb-6">
            Browse our collection and place your first order.
          </p>
          <Link
            href="/products"
            className="inline-flex items-center justify-center px-6 py-3 bg-charcoal text-warm-ivory font-medium rounded-brand hover:bg-soft-brown transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2"
          >
            Start Shopping
          </Link>
          {!isAuthenticated && (
            <p className="text-soft-brown text-sm mt-4">
              Sign in to see all your orders
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-12">
      <h1 className="font-heading text-3xl text-charcoal mb-8">My Orders</h1>

      <div className="space-y-4">
        {orders.map((order) => {
          const itemCount = order.items.reduce((sum, item) => sum + item.quantity, 0);
          const date = new Date(order.created_at).toLocaleDateString("en-US", {
            year: "numeric",
            month: "short",
            day: "numeric",
          });

          return (
            <Link
              key={order.id}
              href={`/orders/${order.id}`}
              className="block bg-white rounded-brand p-6 shadow-sm border border-champagne-beige hover:border-soft-brown transition-colors duration-fast"
            >
              <div className="flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <span className="text-sm font-mono text-soft-brown">
                      #{order.id.slice(0, 8)}
                    </span>
                    <OrderStatusBadge status={order.status} />
                  </div>
                  <p className="text-sm text-soft-brown">
                    {date} · {itemCount} {itemCount === 1 ? "item" : "items"}
                  </p>
                </div>
                <span className="text-charcoal font-medium whitespace-nowrap">
                  {formatPrice(order.total_cents)}
                </span>
              </div>
            </Link>
          );
        })}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 mt-8">
          <button
            onClick={() => fetchOrders(page - 1)}
            disabled={page <= 1}
            className="px-4 py-2 text-sm font-medium text-charcoal border border-champagne-beige rounded-brand hover:bg-cream disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-fast"
          >
            Previous
          </button>
          <span className="text-sm text-soft-brown">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => fetchOrders(page + 1)}
            disabled={page >= totalPages}
            className="px-4 py-2 text-sm font-medium text-charcoal border border-champagne-beige rounded-brand hover:bg-cream disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-fast"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
