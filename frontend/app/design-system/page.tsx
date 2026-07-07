// TODO: Remove after visual verification
"use client";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";

export default function DesignSystemPage() {
  return (
    <div className="mx-auto max-w-4xl space-y-12 p-8">
      <h1>Design System</h1>
      <p className="text-soft-brown">
        Temporary page to verify all components render correctly.
      </p>

      {/* Buttons */}
      <section className="space-y-4">
        <h2>Buttons</h2>

        <div className="space-y-3">
          <h3>Variants</h3>
          <div className="flex flex-wrap items-center gap-4">
            <Button variant="primary">Primary</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="ghost">Ghost</Button>
          </div>
        </div>

        <div className="space-y-3">
          <h3>Sizes</h3>
          <div className="flex flex-wrap items-center gap-4">
            <Button size="sm">Small</Button>
            <Button size="md">Medium</Button>
            <Button size="lg">Large</Button>
          </div>
        </div>

        <div className="space-y-3">
          <h3>States</h3>
          <div className="flex flex-wrap items-center gap-4">
            <Button isLoading>Loading</Button>
            <Button disabled>Disabled</Button>
            <Button variant="secondary" isLoading>
              Secondary Loading
            </Button>
          </div>
        </div>
      </section>

      {/* Inputs */}
      <section className="space-y-4">
        <h2>Inputs</h2>
        <div className="max-w-sm space-y-4">
          <Input label="Email" type="email" placeholder="you@example.com" />
          <Input
            label="Password"
            type="password"
            error="Password must be at least 8 characters"
          />
          <Input placeholder="No label, just placeholder" />
        </div>
      </section>

      {/* Badges */}
      <section className="space-y-4">
        <h2>Badges</h2>
        <div className="flex flex-wrap items-center gap-3">
          <Badge>Default</Badge>
          <Badge variant="accent">Featured</Badge>
          <Badge variant="success">In Stock</Badge>
          <Badge variant="warning">Low Stock</Badge>
        </div>
      </section>

      {/* Skeletons */}
      <section className="space-y-4">
        <h2>Skeletons</h2>
        <div className="max-w-sm space-y-3">
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-4 w-5/6" />
        </div>
      </section>

      {/* Typography */}
      <section className="space-y-4">
        <h2>Typography</h2>
        <h1>Heading 1 — Playfair Display</h1>
        <h2>Heading 2 — Playfair Display</h2>
        <h3>Heading 3 — Playfair Display</h3>
        <p>Body text — Inter. Prices always in cents as integers.</p>
        <p className="text-charcoal font-semibold">
          High-emphasis text in charcoal
        </p>
      </section>

      {/* Colors */}
      <section className="space-y-4">
        <h2>Color Palette</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="space-y-1">
            <div className="h-16 rounded-brand border border-champagne-beige bg-warm-ivory" />
            <p className="text-xs">warm-ivory</p>
          </div>
          <div className="space-y-1">
            <div className="h-16 rounded-brand border border-champagne-beige bg-cream" />
            <p className="text-xs">cream</p>
          </div>
          <div className="space-y-1">
            <div className="h-16 rounded-brand bg-champagne-beige" />
            <p className="text-xs">champagne-beige</p>
          </div>
          <div className="space-y-1">
            <div className="h-16 rounded-brand bg-dusty-pink" />
            <p className="text-xs">dusty-pink</p>
          </div>
          <div className="space-y-1">
            <div className="h-16 rounded-brand bg-soft-brown" />
            <p className="text-xs">soft-brown</p>
          </div>
          <div className="space-y-1">
            <div className="h-16 rounded-brand bg-charcoal" />
            <p className="text-xs">charcoal</p>
          </div>
          <div className="space-y-1">
            <div className="h-16 rounded-brand bg-muted-gold" />
            <p className="text-xs">muted-gold</p>
          </div>
        </div>
      </section>
    </div>
  );
}
