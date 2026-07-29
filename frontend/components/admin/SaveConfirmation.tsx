"use client";

import { cn } from "@/lib/utils";

type SaveConfirmationProps = {
  message: string;
  className?: string;
  onDismiss?: () => void;
  dismissLabel?: string;
};

export function SaveConfirmation({
  message,
  className,
  onDismiss,
  dismissLabel = "Dismiss",
}: SaveConfirmationProps) {
  return (
    <div className="fixed bottom-5 left-4 right-4 z-[80] sm:left-auto sm:right-6 sm:w-[360px]">
      <div
        role="status"
        aria-live="polite"
        className={cn(
          "admin-save-flash flex items-center justify-between gap-3 rounded-brand border border-green-300 bg-green-50 px-4 py-3 text-sm font-semibold text-green-800 shadow-lg",
          className
        )}
      >
        <span className="flex min-w-0 items-center gap-3">
          <span className="admin-save-flash__icon flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-green-600 text-white shadow-sm">
          <svg
            aria-hidden="true"
            className="h-4 w-4"
            viewBox="0 0 20 20"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M4.5 10.4 8.1 14 15.5 6"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </span>
        <span className="truncate">{message}</span>
      </span>
      {onDismiss ? (
        <button
          type="button"
          onClick={onDismiss}
          className="rounded-brand px-2 py-1 text-xs font-semibold text-green-700 hover:bg-green-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-700"
          aria-label={dismissLabel}
        >
          <svg
            aria-hidden="true"
            className="h-4 w-4"
            viewBox="0 0 20 20"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="m5.5 5.5 9 9m0-9-9 9"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            />
          </svg>
        </button>
        ) : null}
      </div>
    </div>
  );
}
