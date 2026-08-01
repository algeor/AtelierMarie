import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type DeleteIconButtonSize = "sm" | "md";

interface DeleteIconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  size?: DeleteIconButtonSize;
  isLoading?: boolean;
}

const sizeStyles: Record<DeleteIconButtonSize, string> = {
  sm: "h-9 w-9",
  md: "h-10 w-10",
};

export const DeleteIconButton = forwardRef<HTMLButtonElement, DeleteIconButtonProps>(
  ({ label, size = "sm", isLoading = false, disabled, className, ...props }, ref) => {
    const isDisabled = disabled || isLoading;

    return (
      <button
        ref={ref}
        type="button"
        aria-label={label}
        aria-busy={isLoading || undefined}
        disabled={isDisabled}
        title={label}
        className={cn(
          "delete-icon-button inline-flex shrink-0 items-center justify-center rounded-brand border border-champagne-beige bg-transparent text-soft-brown/75",
          "transition-colors duration-fast ease-brand",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-600 focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory",
          "disabled:cursor-not-allowed disabled:opacity-50",
          sizeStyles[size],
          className,
        )}
        {...props}
      >
        <svg
          aria-hidden="true"
          className="h-5 w-5"
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <g
            className="delete-bin-lid"
            stroke="currentColor"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="1.8"
          >
            <path d="M7 7h10" />
            <path d="M10 7V5.5A1.5 1.5 0 0 1 11.5 4h1A1.5 1.5 0 0 1 14 5.5V7" />
          </g>
          <g
            className="delete-bin-body"
            stroke="currentColor"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="1.8"
          >
            <path d="M9 10v7" />
            <path d="M15 10v7" />
            <path d="M6.8 9.5 7.6 19A2.2 2.2 0 0 0 9.8 21h4.4a2.2 2.2 0 0 0 2.2-2l.8-9.5" />
          </g>
        </svg>
        <span className="sr-only">{label}</span>
      </button>
    );
  },
);

DeleteIconButton.displayName = "DeleteIconButton";
