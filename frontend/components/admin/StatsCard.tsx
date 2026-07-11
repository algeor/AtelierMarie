import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/Skeleton";

interface StatsCardProps {
  label: string;
  value: string;
  icon: React.ReactNode;
  className?: string;
}

export function StatsCard({ label, value, icon, className }: StatsCardProps) {
  return (
    <div
      className={cn(
        "rounded-brand border border-champagne-beige bg-cream p-6",
        className
      )}
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-soft-brown">{label}</p>
          <p className="mt-2 text-2xl font-semibold text-charcoal">{value}</p>
        </div>
        <div className="flex h-12 w-12 items-center justify-center rounded-brand bg-muted-gold/10 text-muted-gold">
          {icon}
        </div>
      </div>
    </div>
  );
}

export function StatsCardSkeleton() {
  return (
    <div className="rounded-brand border border-champagne-beige bg-cream p-6">
      <div className="flex items-center justify-between">
        <div>
          <Skeleton className="h-4 w-24" />
          <Skeleton className="mt-3 h-7 w-16" />
        </div>
        <Skeleton className="h-12 w-12 rounded-brand" />
      </div>
    </div>
  );
}
