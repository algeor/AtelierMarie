import { Skeleton } from "@/components/ui/Skeleton";

export default function ProductDetailLoading() {
  return (
    <main className="editorial-band px-4 py-10 text-text sm:px-6 lg:px-8 lg:py-16">
      <div className="mx-auto grid max-w-7xl grid-cols-1 gap-10 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,0.85fr)] lg:gap-14">
        {/* Image skeleton */}
        <Skeleton className="aspect-[4/5] w-full rounded-brand" />

        {/* Details skeleton */}
        <div className="flex flex-col gap-6">
          <div className="space-y-3">
            <Skeleton className="h-10 w-3/4" />
            <Skeleton className="h-8 w-32" />
            <Skeleton className="h-6 w-20 rounded-pill" />
          </div>
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-2/3" />
          </div>
          <Skeleton className="h-12 w-48" />
        </div>
      </div>
    </main>
  );
}
