"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { UserAvatar } from "@/components/auth/UserAvatar";

export function UserMenu() {
  const t = useTranslations("auth");
  const { user, logout } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  // Close on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        menuRef.current &&
        !menuRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  // Close on Escape and return focus to trigger
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && isOpen) {
        setIsOpen(false);
        triggerRef.current?.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  async function handleSignOut() {
    setIsOpen(false);
    await logout();
  }

  return (
    <div ref={menuRef} className="relative">
      <button
        ref={triggerRef}
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-haspopup="menu"
        aria-label={t("myAccount")}
        className="flex items-center gap-2 rounded-brand p-1 transition-colors duration-fast hover:bg-cream focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory"
      >
        {user ? (
          <UserAvatar name={user.name} email={user.email} avatarUrl={user.avatar_url} />
        ) : null}
      </button>

      {isOpen && (
        <div
          role="menu"
          className="absolute right-0 mt-2 w-48 rounded-brand bg-white shadow-lg ring-1 ring-black/5 py-1 z-50"
        >
          <Link
            href="/account"
            role="menuitem"
            onClick={() => setIsOpen(false)}
            className="block px-4 py-2 text-sm text-charcoal hover:bg-cream transition-colors duration-fast"
          >
            {t("myAccount")}
          </Link>
          <Link
            href="/orders"
            role="menuitem"
            onClick={() => setIsOpen(false)}
            className="block px-4 py-2 text-sm text-charcoal hover:bg-cream transition-colors duration-fast"
          >
            {t("myOrders")}
          </Link>
          <button
            role="menuitem"
            onClick={handleSignOut}
            className="block w-full text-left px-4 py-2 text-sm text-charcoal hover:bg-cream transition-colors duration-fast"
          >
            {t("signOut")}
          </button>
        </div>
      )}
    </div>
  );
}
