import { getProducts } from "@/lib/api";
import { getTranslations } from "next-intl/server";
import { FeaturedProductsShowcase } from "@/components/products/FeaturedProductsShowcase";
import { HeroSection } from "@/components/products/HeroSection";
import { CategoryLineArt, type CategoryLineArtKind } from "@/components/rebrand";
import { Link } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";
import { getLocalizedAlternates } from "@/lib/seo";
import type { ProductResponse } from "@/lib/types";

type LandingCategoryKey = "christmasBalls" | "customBoxes" | "candles" | "notebooks";

interface LandingCategoryConfig {
  key: LandingCategoryKey;
  art: CategoryLineArtKind;
  match: string[];
  preferredTypes?: string[];
}

interface LandingCategory extends LandingCategoryConfig {
  href: string;
  count: number;
}

const LANDING_CATEGORIES: LandingCategoryConfig[] = [
  {
    key: "christmasBalls",
    art: "christmas-balls",
    match: ["christmas", "xmas", "ornament", "bauble", "ball", "balls", "коледа", "колед", "топка"],
  },
  {
    key: "customBoxes",
    art: "custom-boxes",
    match: ["custom", "bespoke", "personal", "box", "boxes", "gift-box", "кут", "персон"],
    preferredTypes: ["boxes", "custom-boxes"],
  },
  {
    key: "candles",
    art: "candles",
    match: ["candle", "candles", "свещ", "свещи"],
    preferredTypes: ["candles"],
  },
  {
    key: "notebooks",
    art: "notebooks",
    match: ["notebook", "notebooks", "journal", "diary", "тетрад", "дневник"],
    preferredTypes: ["notebooks"],
  },
];

function normalized(value: string | null | undefined) {
  return (value ?? "").toLocaleLowerCase().replace(/[\s_]+/g, "-");
}

function searchableProductText(product: ProductResponse) {
  return [
    product.id,
    product.name,
    product.description,
    product.product_type,
    product.product_type_name,
    product.category,
    product.category_name,
    ...product.labels.flatMap((label) => [label.slug, label.name]),
  ]
    .map(normalized)
    .join(" ");
}

function matchesLandingCategory(product: ProductResponse, config: LandingCategoryConfig) {
  const text = searchableProductText(product);
  return config.match.some((term) => text.includes(normalized(term)));
}

function landingCategoryHref(products: ProductResponse[], config: LandingCategoryConfig) {
  const preferredTypeProduct = products.find((product) =>
    config.preferredTypes?.includes(product.product_type)
  );
  const matchedCategoryProduct = products.find((product) => {
    const categoryText = `${normalized(product.category)} ${normalized(product.category_name)}`;
    return product.category && config.match.some((term) => categoryText.includes(normalized(term)));
  });
  const matchedTypeProduct = products.find((product) => {
    const typeText = `${normalized(product.product_type)} ${normalized(product.product_type_name)}`;
    return config.match.some((term) => typeText.includes(normalized(term)));
  });
  const params = new URLSearchParams();
  const typeProduct = preferredTypeProduct ?? matchedTypeProduct;

  if (typeProduct) params.set("type", typeProduct.product_type);
  if (matchedCategoryProduct?.category) params.set("category", matchedCategoryProduct.category);

  return `/products?${params.toString()}`;
}

function getLandingCategories(products: ProductResponse[]): LandingCategory[] {
  return LANDING_CATEGORIES.flatMap((config) => {
    const matches = products.filter((product) => matchesLandingCategory(product, config));
    if (!matches.length) return [];
    return [{ ...config, href: landingCategoryHref(matches, config), count: matches.length }];
  });
}

export async function generateMetadata({ params }: { params: Promise<{ locale: Locale }> }) {
  const { locale } = await params;
  return {
    title: "Atelier Marie | Luxury Handcrafted Candles",
    alternates: getLocalizedAlternates(locale, ""),
  };
}

export default async function HomePage({ params }: { params: Promise<{ locale: Locale }> }) {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "home" });
  const { products } = await getProducts(1, 100, locale).catch(() => ({
    products: [],
    total: 0,
    page: 1,
    limit: 100,
  }));
  const featured = products.filter((p) => p.is_featured);
  const heroProduct = featured[0] ?? products.find((product) => product.primary_image_url) ?? products[0] ?? null;
  const landingCategories = getLandingCategories(products);
  const trustItems = [
    "handmade",
    "wax",
    "fragrance",
    "gift",
  ] as const;

  return (
    <>
      <HeroSection product={heroProduct} />

      {featured.length > 0 ? <FeaturedProductsShowcase products={featured} /> : null}

      <section className="relative isolate overflow-hidden px-4 py-14 sm:px-6 lg:px-8 lg:py-20">
        <div className="relative z-10 mx-auto grid max-w-7xl gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-end">
          <div className="landing-scroll-reveal">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">
              {t("trustEyebrow")}
            </p>
            <h2 className="mt-3 max-w-2xl font-heading text-3xl text-text sm:text-4xl">
              {t("trustTitle")}
            </h2>
            <p className="mt-4 max-w-2xl text-base leading-7 text-muted">
              {t("trustText")}
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {trustItems.map((item, index) => (
              <div
                key={item}
                className="landing-scroll-reveal rounded-brand bg-[rgb(248_241_241)] p-4 shadow-lg shadow-border/10 ring-1 ring-border/25 transition-all duration-300 motion-safe:hover:-translate-y-0.5 motion-safe:hover:shadow-xl motion-safe:hover:shadow-border/15"
                style={{ animationDelay: `${index * 90}ms` }}
              >
                <h3 className="font-heading text-lg text-text">{t(`trustItems.${item}.title`)}</h3>
                <p className="mt-2 text-sm leading-6 text-muted">{t(`trustItems.${item}.text`)}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {landingCategories.length > 0 ? (
        <section className="relative isolate overflow-hidden px-4 py-14 sm:px-6 lg:px-8 lg:py-20">
          <div className="relative z-10 mx-auto max-w-7xl">
            <div className="landing-scroll-reveal mb-7 max-w-2xl">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">
                {t("categoriesEyebrow")}
              </p>
              <h2 className="mt-3 font-heading text-3xl text-text sm:text-4xl">
                {t("categoriesTitle")}
              </h2>
              <p className="mt-4 text-base leading-7 text-muted">{t("categoriesIntro")}</p>
            </div>
            <div className="-mx-4 flex gap-4 overflow-x-auto px-4 pb-3 sm:mx-0 sm:grid sm:grid-cols-2 sm:px-0 lg:grid-cols-4">
              {landingCategories.map((category, index) => (
                <Link
                  key={category.key}
                  href={category.href}
                  className="landing-scroll-reveal group flex min-h-[236px] w-[76vw] max-w-[20rem] shrink-0 flex-col justify-between rounded-brand bg-[rgb(248_241_241)] p-5 text-left shadow-lg shadow-border/10 ring-1 ring-border/30 transition-all duration-300 motion-safe:hover:-translate-y-1 motion-safe:hover:shadow-xl motion-safe:hover:shadow-border/15 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page sm:w-auto sm:max-w-none"
                  style={{ animationDelay: `${index * 100}ms` }}
                >
                  <CategoryLineArt
                    kind={category.art}
                    title={t(`categories.${category.key}`)}
                    className="h-24 w-full text-accent transition-colors group-hover:text-text"
                  />
                  <span>
                    <span className="block font-heading text-xl text-text">
                      {t(`categories.${category.key}`)}
                    </span>
                    <span className="mt-2 block text-sm leading-6 text-muted">
                      {t(`categoryDescriptions.${category.key}`)}
                    </span>
                    <span className="mt-4 inline-flex text-sm font-semibold text-accent">
                      {t("categoryCta", { count: category.count })}
                    </span>
                  </span>
                </Link>
              ))}
            </div>
          </div>
        </section>
      ) : null}
    </>
  );
}
