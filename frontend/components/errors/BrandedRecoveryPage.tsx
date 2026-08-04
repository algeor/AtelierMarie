"use client";

import Image from "next/image";
import { Button } from "@/components/ui/Button";
import { BrandMark } from "@/components/rebrand";
import { Link } from "@/i18n/navigation";

interface BrandedRecoveryPageProps {
  eyebrow: string;
  title: string;
  description: string;
  backLabel: string;
  backHref?: string;
  brandName: string;
  brandMarkTitle: string;
  code?: string;
  tryAgainLabel?: string;
  onReset?: () => void;
}

export function BrandedRecoveryPage({
  eyebrow,
  title,
  description,
  backLabel,
  backHref = "/",
  brandName,
  brandMarkTitle,
  code,
  tryAgainLabel,
  onReset,
}: BrandedRecoveryPageProps) {
  return (
    <main className="bg-page px-4 py-8 text-text sm:px-6 lg:px-8">
      <section className="mx-auto grid min-h-[calc(100svh-12rem)] max-w-6xl items-center gap-8 py-8 md:grid-cols-[minmax(0,0.95fr)_minmax(18rem,0.8fr)] md:py-12">
        <div className="rebrand-slow-reveal max-w-xl">
          <BrandMark
            animated
            title={brandMarkTitle}
            className="mb-4 h-16 w-24 text-accent md:h-20 md:w-28"
          />
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted md:text-sm">
            {eyebrow}
          </p>
          {code ? (
            <p
              className="mt-4 font-heading text-[clamp(5rem,32vw,13rem)] leading-[0.78] text-text"
              aria-hidden="true"
            >
              {code}
            </p>
          ) : null}
          <h1 className="mt-4 font-heading text-4xl leading-none text-text sm:text-5xl md:text-6xl">
            {title}
          </h1>
          <p className="mt-5 max-w-lg text-base leading-7 text-muted sm:text-lg">
            {description}
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
            <Link
              href={backHref}
              className="inline-flex min-h-[48px] items-center justify-center rounded-brand bg-primary px-6 py-3 text-base font-semibold text-primary-foreground shadow-lg shadow-primary/20 transition-colors duration-fast hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page motion-reduce:transition-none"
            >
              {backLabel}
            </Link>
            {onReset && tryAgainLabel ? (
              <Button
                type="button"
                variant="secondary"
                size="lg"
                onClick={onReset}
              >
                {tryAgainLabel}
              </Button>
            ) : null}
          </div>
        </div>

        <div className="editorial-image-settle relative mx-auto aspect-[4/5] w-full max-w-sm overflow-hidden rounded-brand bg-surface/60 shadow-xl shadow-border/15 ring-1 ring-border/25 md:max-w-md">
          <Image
            src="/rebrand/error-candle.webp"
            alt=""
            fill
            sizes="(min-width: 768px) 360px, 80vw"
            className="object-cover opacity-80"
            priority={Boolean(code)}
          />
          <div className="absolute inset-0 bg-[linear-gradient(180deg,rgb(var(--color-page)/0.18)_0%,rgb(var(--color-surface)/0.72)_100%)]" />
          <div className="absolute inset-x-6 bottom-6 text-text drop-shadow-sm">
            <BrandMark className="h-12 w-16 text-accent" />
            <p className="mt-3 font-heading text-2xl italic">{brandName}</p>
          </div>
        </div>
      </section>
    </main>
  );
}
