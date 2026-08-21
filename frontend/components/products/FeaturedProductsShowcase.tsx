"use client";

import { useEffect, useMemo, useRef, useState, type PointerEvent } from "react";
import { useTranslations } from "next-intl";
import { AddToCartButton } from "@/components/cart/AddToCartButton";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import type { HomeSection, ProductResponse } from "@/lib/types";
import { PriceDisplay } from "./PriceDisplay";
import { ProductImage } from "./ProductImage";
import {
  trackProductClick,
  useProductImpression,
  type ProductDiscoveryContext,
} from "./productAnalytics";

interface FeaturedProductsShowcaseProps {
  products: ProductResponse[];
  section?: HomeSection | null;
}

const AUTO_ROTATE_MS = 10000;
const SWIPE_THRESHOLD_PX = 48;

function productDescriptor(product: ProductResponse) {
  return product.category_name || product.product_type_name || product.labels[0]?.name || "Atelier Marie";
}

export function FeaturedProductsShowcase({ products, section }: FeaturedProductsShowcaseProps) {
  const t = useTranslations("home");
  const featuredProducts = products.slice(0, 3);
  const [activeIndex, setActiveIndex] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const [interactionNonce, setInteractionNonce] = useState(0);
  const pointerStartRef = useRef<{ x: number; y: number; pointerId: number } | null>(null);
  const suppressNextClickRef = useRef(false);

  useEffect(() => {
    if (featuredProducts.length <= 1 || isPaused) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const timeout = window.setTimeout(() => {
      setActiveIndex((current) => (current + 1) % featuredProducts.length);
    }, AUTO_ROTATE_MS);

    return () => window.clearTimeout(timeout);
  }, [activeIndex, featuredProducts.length, interactionNonce, isPaused]);

  function chooseProduct(index: number, userInitiated = true) {
    setActiveIndex((index + featuredProducts.length) % featuredProducts.length);
    if (userInitiated) setInteractionNonce((current) => current + 1);
  }

  function handlePointerDown(event: PointerEvent<HTMLDivElement>) {
    if (featuredProducts.length <= 1) return;
    if (event.pointerType === "mouse" && event.button !== 0) return;
    pointerStartRef.current = {
      x: event.clientX,
      y: event.clientY,
      pointerId: event.pointerId,
    };
    event.currentTarget.setPointerCapture?.(event.pointerId);
  }

  function handlePointerUp(event: PointerEvent<HTMLDivElement>) {
    const pointerStart = pointerStartRef.current;
    if (!pointerStart || pointerStart.pointerId !== event.pointerId) return;

    pointerStartRef.current = null;
    event.currentTarget.releasePointerCapture?.(event.pointerId);

    const deltaX = event.clientX - pointerStart.x;
    const deltaY = event.clientY - pointerStart.y;
    const isHorizontalSwipe = Math.abs(deltaX) >= SWIPE_THRESHOLD_PX && Math.abs(deltaX) > Math.abs(deltaY) * 1.25;

    if (!isHorizontalSwipe) return;

    event.preventDefault();
    suppressNextClickRef.current = true;
    chooseProduct(activeIndex + (deltaX < 0 ? 1 : -1));
  }

  function handlePointerCancel(event: PointerEvent<HTMLDivElement>) {
    if (pointerStartRef.current?.pointerId === event.pointerId) {
      pointerStartRef.current = null;
    }
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
            {section?.subheading ?? t("featuredEyebrow")}
          </p>
          <h2 id="featured-products-title" className="mt-3 font-heading text-3xl text-text sm:text-4xl lg:text-5xl">
            {section?.heading ?? t("featured")}
          </h2>
          <p className="mt-4 max-w-xl text-base leading-7 text-muted">
            {section?.body ?? t("featuredIntro")}
          </p>
        </div>

        <div className="relative mt-8 lg:mt-12">
          <div
            className="featured-carousel-viewport overflow-hidden pb-6 lg:pb-36"
            onClickCapture={(event) => {
              if (!suppressNextClickRef.current) return;
              event.preventDefault();
              event.stopPropagation();
              suppressNextClickRef.current = false;
            }}
            onPointerDown={handlePointerDown}
            onPointerUp={handlePointerUp}
            onPointerCancel={handlePointerCancel}
          >
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
                    totalCount={featuredProducts.length}
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
  totalCount,
  active,
  className,
  onActivate,
}: {
  product: ProductResponse;
  index: number;
  totalCount: number;
  active: boolean;
  className?: string;
  onActivate: () => void;
}) {
  const t = useTranslations("home");
  const productT = useTranslations("products");
  const descriptor = productDescriptor(product);
  const inactiveTabIndex = active ? undefined : -1;
  const isCraftedLater = product.can_order && !product.available_now;
  const cardRef = useRef<HTMLElement>(null);
  const discoveryContext = useMemo<ProductDiscoveryContext>(
    () => ({
      index,
      listingContext: "featured_products",
      resultCount: totalCount,
      totalCount,
    }),
    [index, totalCount],
  );

  useProductImpression(cardRef, product, discoveryContext);

  return (
    <article
      ref={cardRef}
      className={cn(
        "featured-preview-card landing-scroll-reveal group relative h-full",
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
        onClick={() => trackProductClick(product, discoveryContext, "featured_image")}
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
        <div className="grid h-full min-w-0 gap-4 min-[720px]:grid-cols-[minmax(0,1fr)_auto] min-[720px]:items-end">
          <div className="min-w-0 self-start">
            <p className="featured-preview-card__descriptor text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-accent">
              {descriptor}
            </p>
            <Link
              href={`/products/${product.id}`}
              tabIndex={inactiveTabIndex}
              onClick={() => trackProductClick(product, discoveryContext, "featured_title")}
              className="featured-preview-card__title mt-1.5 block max-w-2xl font-heading text-xl leading-tight text-text transition-colors hover:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page sm:text-2xl"
            >
              {product.name}
            </Link>
            <div className="mt-1.5 truncate text-sm font-semibold text-text sm:text-base">
              <PriceDisplay product={product} />
            </div>
          </div>

          <div className="flex min-w-0 flex-col justify-end gap-2 min-[720px]:w-[19rem] min-[720px]:items-stretch">
            {isCraftedLater ? (
              <p className="rounded-brand border border-border/45 bg-page/60 px-3 py-2 text-xs leading-5 text-muted">
                {productT("craftedLaterShort")}
              </p>
            ) : null}
            <div className="grid gap-2 min-[420px]:grid-cols-2">
              <AddToCartButton
                productId={product.id}
                canOrder={product.can_order}
                availableNow={product.available_now}
                disabled={!active}
                tabIndex={inactiveTabIndex}
                showCraftedLaterNote={false}
                className="min-h-[42px] w-full text-sm"
              />
              <Link
                href={`/products/${product.id}`}
                tabIndex={inactiveTabIndex}
                onClick={() => trackProductClick(product, discoveryContext, "featured_cta")}
                className="inline-flex min-h-[42px] min-w-0 items-center justify-center truncate rounded-brand border border-border/70 bg-surface-elevated/80 px-4 py-2 text-sm font-semibold text-text transition-colors hover:bg-page focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page"
              >
                {t("viewProduct")}
              </Link>
            </div>
          </div>
        </div>
      </div>
    </article>
  );
}
