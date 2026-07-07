import { Skeleton } from "@/components/ui/Skeleton";

export default function HomeLoading() {
  return (
    <>
      {/* Hero skeleton */}
      <div className="w-full py-24 md:py-32 lg:py-40 px-4 flex flex-col items-center gap-6">
        <Skeleton className="h-12 w-96 max-w-full" />
        <Skeleton className="h-6 w-80 max-w-full" />
        <Skeleton className="h-12 w-48 mt-4" />
      </div>

      {/* Featured products skeleton */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <Skeleton className="h-9 w-48 mb-8" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="space-y-3">
              <Skeleton className="aspect-[4/5] w-full rounded-brand" />
              <Skeleton className="h-5 w-3/4" />
              <Skeleton className="h-4 w-1/3" />
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
