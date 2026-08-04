"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { AddToCartButton } from "@/components/cart/AddToCartButton";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import type { ProductResponse } from "@/lib/types";
import { PriceDisplay } from "./PriceDisplay";
import { ProductImage } from "./ProductImage";

interface FeaturedProductsShowcaseProps {
  products: ProductResponse[];
}

function productDescriptor(product: ProductResponse) {
  return product.category_name || product.product_type_name || product.labels[0]?.name || "Atelier Marie";
}

export function FeaturedProductsShowcase({ products }: FeaturedProductsShowcaseProps) {
  const t = useTranslations("home");
  const featuredProducts = products.slice(0, 3);
  const [activeIndex, setActiveIndex] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const [hasUserInteracted, setHasUserInteracted] = useState(false);

  useEffect(() => {
    if (featuredProducts.length <= 1 || isPaused || hasUserInteracted) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const interval = window.setInterval(() => {
      setActiveIndex((current) => (current + 1) % featuredProducts.length);
    }, 6500);

    return () => window.clearInterval(interval);
  }, [featuredProducts.length, hasUserInteracted, isPaused]);

  function chooseProduct(index: number, userInitiated = true) {
    setActiveIndex((index + featuredProducts.length) % featuredProducts.length);
    if (userInitiated) setHasUserInteracted(true);
  }

  if (!featuredProducts.length) return null;

  return (
    <section
      className="landing-featured-showcase relative isolate overflow-hidden bg-transparent py-16 sm:py-20 lg:py-16 lg:pb-24"
      aria-labelledby="featured-products-title"
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
      onFocus={() => setIsPaused(true)}
      onBlur={() => setIsPaused(false)}
    >
      <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="landing-scroll-reveal mb-10 max-w-2xl lg:mb-0">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">
            {t("featuredEyebrow")}
          </p>
          <h2 id="featured-products-title" className="mt-3 font-heading text-3xl text-text sm:text-4xl lg:text-5xl">
            {t("featured")}
          </h2>
          <p className="mt-4 max-w-xl text-base leading-7 text-muted">
            {t("featuredIntro")}
          </p>
        </div>

        <div className="relative mt-8 lg:mt-12">
          <div className="overflow-hidden pb-6 lg:pb-36">
            <div
              className="featured-carousel-track flex"
              style={{ transform: `translateX(-${activeIndex * 100}%)` }}
            >
            {featuredProducts.map((product, index) => {
              const isActive = activeIndex === index;
              return (
                <div key={product.id} className="min-w-full px-0 sm:px-10 lg:px-16">
                  <FeaturedProductCard
                    product={product}
                    index={index}
                    active={isActive}
                    className="mx-auto w-full max-w-[24rem] lg:max-w-5xl"
                    onActivate={() => chooseProduct(index, false)}
                  />
                </div>
              );
            })}
            </div>
          </div>

          {featuredProducts.length > 1 ? (
            <>
              <button
                type="button"
                className="absolute left-0 top-1/2 hidden h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full border border-border/55 bg-page/90 text-3xl leading-none text-text shadow-lg shadow-text/10 transition-colors hover:text-accent active:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page lg:flex"
                aria-label={t("featuredCarouselPrevious")}
                onClick={() => chooseProduct(activeIndex - 1)}
              >
                <span aria-hidden="true">‹</span>
              </button>
              <button
                type="button"
                className="absolute right-0 top-1/2 hidden h-11 w-11 -translate-y-1/2 items-center justify-center rounded-full border border-border/55 bg-page/90 text-3xl leading-none text-text shadow-lg shadow-text/10 transition-colors hover:text-accent active:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page lg:flex"
                aria-label={t("featuredCarouselNext")}
                onClick={() => chooseProduct(activeIndex + 1)}
              >
                <span aria-hidden="true">›</span>
              </button>
              <div className="mt-2 flex items-center justify-center gap-3" aria-label={t("featuredCarouselLabel")}>
                <button
                  type="button"
                  className="inline-flex h-10 w-10 items-center justify-center text-2xl leading-none text-text transition-colors hover:text-accent active:text-accent focus-visible:outline-none focus-visible:text-accent lg:hidden"
                  aria-label={t("featuredCarouselPrevious")}
                  onClick={() => chooseProduct(activeIndex - 1)}
                >
                  <span aria-hidden="true">‹</span>
                </button>
                {featuredProducts.map((product, index) => (
                  <button
                    key={product.id}
                    type="button"
                    className={cn(
                      "h-2.5 rounded-full transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page",
                      activeIndex === index ? "w-8 bg-accent" : "w-2.5 bg-border/70"
                    )}
                    aria-label={t("featuredCarouselGoTo", { index: index + 1 })}
                    aria-current={activeIndex === index ? "true" : undefined}
                    onClick={() => chooseProduct(index)}
                  />
                ))}
                <button
                  type="button"
                  className="inline-flex h-10 w-10 items-center justify-center text-2xl leading-none text-text transition-colors hover:text-accent active:text-accent focus-visible:outline-none focus-visible:text-accent lg:hidden"
                  aria-label={t("featuredCarouselNext")}
                  onClick={() => chooseProduct(activeIndex + 1)}
                >
                  <span aria-hidden="true">›</span>
                </button>
              </div>
            </>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function FeaturedProductCard({
  product,
  index,
  active,
  className,
  onActivate,
}: {
  product: ProductResponse;
  index: number;
  active: boolean;
  className?: string;
  onActivate: () => void;
}) {
  const t = useTranslations("home");
  const descriptor = productDescriptor(product);
  const inactiveTabIndex = active ? undefined : -1;

  return (
    <article
      className={cn(
        "featured-preview-card landing-scroll-reveal group relative",
        active && "featured-preview-card--active",
        !active && "pointer-events-none",
        className
      )}
      aria-hidden={!active ? true : undefined}
      style={{ animationDelay: `${index * 110}ms` }}
      onMouseEnter={onActivate}
      onFocus={onActivate}
    >
      <Link
        href={`/products/${product.id}`}
        tabIndex={inactiveTabIndex}
        className="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page"
      >
        <ProductImage
          name={product.name}
          imageUrl={product.video?.poster_url ?? product.primary_image_url}
          sizes="(max-width: 1024px) 82vw, 64vw"
          className="featured-preview-card__image aspect-[4/4.35] shadow-2xl shadow-text/10 lg:aspect-[16/9]"
        />
      </Link>

      <div className="featured-preview-card__panel mt-4 bg-[rgb(248_241_241)] p-3.5 shadow-xl shadow-text/10 backdrop-blur-md sm:p-4 lg:absolute lg:-bottom-28 lg:left-6 lg:right-6 lg:mt-0">
        <p className="text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-accent">{descriptor}</p>
        <Link
          href={`/products/${product.id}`}
          tabIndex={inactiveTabIndex}
          className="mt-1.5 block font-heading text-xl leading-tight text-text transition-colors hover:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page"
        >
          {product.name}
        </Link>
        <div className="mt-1.5 text-sm font-semibold text-text">
          <PriceDisplay product={product} />
        </div>
        <div className="mt-3 flex flex-col gap-2 min-[420px]:flex-row min-[420px]:items-center">
          <AddToCartButton
            productId={product.id}
            stock={product.stock}
            disabled={!active}
            tabIndex={inactiveTabIndex}
            className="min-h-[42px] text-sm min-[420px]:w-auto min-[420px]:flex-1"
          />
          <Link
            href={`/products/${product.id}`}
            tabIndex={inactiveTabIndex}
            className="inline-flex min-h-[42px] items-center justify-center rounded-brand border border-border/70 bg-surface-elevated/80 px-4 py-2 text-sm font-semibold text-text transition-colors hover:bg-page focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page min-[420px]:shrink-0"
          >
            {t("viewProduct")}
          </Link>
        </div>
      </div>
    </article>
  );
}
