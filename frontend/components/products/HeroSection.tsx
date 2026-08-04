import { getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { BrandMark } from "@/components/rebrand";
import type { ProductResponse } from "@/lib/types";
import { ProductImage } from "./ProductImage";

interface HeroSectionProps {
  product?: ProductResponse | null;
}

export async function HeroSection({ product }: HeroSectionProps) {
  const t = await getTranslations("home");
  const heroImage = product?.video?.poster_url ?? product?.primary_image_url ?? "/rebrand/error-candle.webp";
  const heroImageName = product?.name ?? t("heroMediaFallback");

  return (
    <section
      className="relative isolate min-h-[78svh] overflow-hidden bg-page text-text"
      aria-label={t("heroAriaLabel")}
    >
      <ProductImage
        name={heroImageName}
        imageUrl={heroImage}
        priority
        sizes="100vw"
        className="landing-hero-media absolute inset-0 h-full aspect-auto rounded-none"
      />
      <div className="absolute inset-0 bg-[linear-gradient(180deg,rgb(var(--color-surface-elevated)/0.7)_0%,rgb(var(--color-page)/0.28)_42%,rgb(var(--color-surface-elevated)/0.52)_100%)] md:bg-[linear-gradient(90deg,rgb(var(--color-surface-elevated)/0.76)_0%,rgb(var(--color-page)/0.26)_42%,rgb(var(--color-page)/0.08)_100%)]" />
      <div className="relative z-10 mx-auto flex min-h-[78svh] max-w-7xl flex-col justify-end px-4 py-10 sm:px-6 lg:px-8 md:justify-center md:py-16">
        <div className="max-w-2xl rebrand-slow-reveal">
          <BrandMark
            animated
            title={t("brandMarkTitle")}
            className="mb-4 h-16 w-24 text-accent md:h-20 md:w-28"
          />
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted md:text-sm">
            {t("heroEyebrow")}
          </p>
          <h1 className="mt-4 max-w-3xl font-heading text-5xl leading-none text-text sm:text-6xl lg:text-7xl">
            {t("heroTitle")}
          </h1>
          <p className="mt-5 max-w-xl text-base leading-7 text-muted sm:text-lg">
            {t("heroSubtitle")}
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
            <Link
              href="/products"
              className="inline-flex min-h-[48px] items-center justify-center rounded-brand bg-accent px-6 py-3 text-base font-semibold text-accent-foreground shadow-lg shadow-accent/25 transition-colors duration-fast hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page"
            >
              {t("shopCollection")}
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
