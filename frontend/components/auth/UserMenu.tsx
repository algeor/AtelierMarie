"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { useAuth } from "@/contexts/AuthContext";

export function UserMenu() {
  const { user, logout } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  const close = useCallback(() => {
    setIsOpen(false);
    triggerRef.current?.focus();
  }, []);

  // Click outside to dismiss
  useEffect(() => {
    if (!isOpen) return;

    function handleClickOutside(event: MouseEvent) {
      if (
        menuRef.current &&
        !menuRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  // Escape key to close
  useEffect(() => {
    if (!isOpen) return;

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        close();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, close]);

  if (!user) return null;

  const initial = (user.name ?? user.email)[0]?.toUpperCase() ?? "?";

  return (
    <div ref={menuRef} className="relative">
      <button
        ref={triggerRef}
        onClick={() => setIsOpen((prev) => !prev)}
        aria-expanded={isOpen}
        aria-haspopup="true"
        aria-label="User menu"
        className="flex items-center gap-2 rounded-brand p-1 transition-colors duration-fast hover:bg-cream focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory"
      >
        {user.avatar_url ? (
          <Image
            src={user.avatar_url}
            alt=""
            width={32}
            height={32}
            className="h-8 w-8 rounded-full object-cover"
          />
        ) : (
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-muted-gold text-sm font-medium text-charcoal">
            {initial}
          </span>
        )}
      </button>

      {isOpen && (
        <div
          role="group"
          aria-label="User menu"
          className="absolute right-0 top-full mt-2 w-48 rounded-brand border border-champagne-beige bg-warm-ivory py-1 shadow-lg"
        >
          <Link
            href="/account"
            onClick={() => setIsOpen(false)}
            className="block px-4 py-2 text-sm text-charcoal hover:bg-cream transition-colors duration-fast"
          >
            My Account
          </Link>
          <Link
            href="/orders"
            onClick={() => setIsOpen(false)}
            className="block px-4 py-2 text-sm text-charcoal hover:bg-cream transition-colors duration-fast"
          >
            My Orders
          </Link>
          <button
            onClick={async () => {
              setIsOpen(false);
              await logout();
            }}
            className="block w-full px-4 py-2 text-left text-sm text-charcoal hover:bg-cream transition-colors duration-fast"
          >
            Sign Out
          </button>
        </div>
      )}
    </div>
  );
}
