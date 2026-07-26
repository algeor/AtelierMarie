import { cn } from "@/lib/utils";

type BadgeVariant = "default" | "accent" | "success" | "warning";

interface BadgeProps {
  variant?: BadgeVariant;
  className?: string;
  children: React.ReactNode;
  "data-testid"?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  default: "bg-champagne-beige text-charcoal",
  accent: "bg-muted-gold text-charcoal",
  success: "bg-green-100 text-green-800",
  warning: "bg-amber-100 text-amber-800",
};

export function Badge({ variant = "default", className, children, "data-testid": dataTestId }: BadgeProps) {
  return (
    <span
      data-testid={dataTestId}
      className={cn(
        "inline-flex items-center rounded-pill px-2.5 py-0.5 text-xs font-medium",
        variantStyles[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
