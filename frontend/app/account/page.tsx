"use client";

import Link from "next/link";
import Image from "next/image";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";

export default function AccountPage() {
  const { user, isLoading, isAuthenticated, login, logout } = useAuth();

  // Loading skeleton
  if (isLoading) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-12 sm:px-6">
        <Skeleton className="mb-8 h-10 w-48" />
        <div className="rounded-brand border border-champagne-beige bg-warm-ivory p-8">
          <div className="flex flex-col items-center gap-4">
            <Skeleton className="h-24 w-24 rounded-full" />
            <Skeleton className="h-6 w-40" />
            <Skeleton className="h-5 w-56" />
          </div>
        </div>
      </div>
    );
  }

  // Anonymous view
  if (!isAuthenticated || !user) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-12 sm:px-6">
        <div className="rounded-brand border border-champagne-beige bg-warm-ivory p-8 text-center">
          <h1 className="mb-4 font-heading text-2xl text-charcoal">
            My Account
          </h1>
          <p className="mb-6 text-soft-brown">
            Sign in to view your account and order history
          </p>
          <Button onClick={login} variant="primary" size="lg">
            Sign In with Google
          </Button>
        </div>
      </div>
    );
  }

  // Authenticated view
  const initial = (user.name ?? user.email)[0]?.toUpperCase() ?? "?";

  return (
    <div className="mx-auto max-w-2xl px-4 py-12 sm:px-6">
      <h1 className="mb-8 font-heading text-3xl text-charcoal">My Account</h1>

      <div className="rounded-brand border border-champagne-beige bg-warm-ivory p-8">
        <div className="flex flex-col items-center gap-4">
          {/* Avatar */}
          {user.avatar_url ? (
            <Image
              src={user.avatar_url}
              alt={`${user.name ?? "User"} avatar`}
              width={96}
              height={96}
              className="h-24 w-24 rounded-full object-cover"
            />
          ) : (
            <span className="flex h-24 w-24 items-center justify-center rounded-full bg-muted-gold text-3xl font-medium text-charcoal">
              {initial}
            </span>
          )}

          {/* Name */}
          {user.name && (
            <h2 className="font-heading text-xl text-charcoal">{user.name}</h2>
          )}

          {/* Email */}
          <p className="text-soft-brown">{user.email}</p>
        </div>

        {/* Links */}
        <div className="mt-8 flex flex-col gap-3">
          <Link
            href="/orders"
            className="rounded-brand border border-champagne-beige px-4 py-3 text-center text-charcoal transition-colors duration-fast hover:bg-cream"
          >
            My Orders
          </Link>
          <Button
            onClick={logout}
            variant="secondary"
            size="md"
            className="w-full"
          >
            Sign Out
          </Button>
        </div>
      </div>
    </div>
  );
}
