import { getHome, getProducts, getPublicSiteMedia } from "@/lib/api";
import { getTranslations } from "next-intl/server";
import { FeaturedProductsShowcase } from "@/components/products/FeaturedProductsShowcase";
import { HeroSection } from "@/components/products/HeroSection";
import { CategoryLineArt, type CategoryLineArtKind } from "@/components/rebrand";
import { BodyRenderer } from "@/components/atelier/BodyRenderer";
import { Link } from "@/i18n/navigation";
import type { Locale } from "@/i18n/routing";
import { resolveMediaUrl } from "@/lib/media";
import { getLocalizedAlternates } from "@/lib/seo";
import type { HomeSection, ProductResponse, SiteMediaMap } from "@/lib/types";

type LandingCategoryKey = "christmasBalls" | "customBoxes" | "candles" | "notebooks";
type HomeTranslator = Awaited<ReturnType<typeof getTranslations>>;

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

function fallbackHomeSections(t: HomeTranslator): HomeSection[] {
  const trustItems = ["handmade", "wax", "fragrance", "gift"] as const;
  return [
    {
      slug: "hero",
      type: "hero",
      heading: t("heroTitle"),
      subheading: t("heroEyebrow"),
      body: t("heroSubtitle"),
      cta: { label: t("shopCollection"), href: "/products" },
      image: null,
      items: [],
    },
    {
      slug: "featured",
      type: "featured_products",
      heading: t("featured"),
      subheading: t("featuredEyebrow"),
      body: t("featuredIntro"),
      cta: null,
      image: null,
      items: [],
    },
    {
      slug: "trust",
      type: "cards",
      heading: t("trustTitle"),
      subheading: t("trustEyebrow"),
      body: t("trustText"),
      cta: null,
      image: null,
      items: trustItems.map((item, index) => ({
        id: index + 1,
        title: t(`trustItems.${item}.title`),
        text: t(`trustItems.${item}.text`),
        image: null,
        link: null,
      })),
    },
    {
      slug: "categories",
      type: "category_links",
      heading: t("categoriesTitle"),
      subheading: t("categoriesEyebrow"),
      body: t("categoriesIntro"),
      cta: null,
      image: null,
      items: [],
    },
  ];
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
  const [{ products }, siteMedia, home] = await Promise.all([
    getProducts(1, 100, locale).catch(() => ({
      products: [],
      total: 0,
      page: 1,
      limit: 100,
    })),
    getPublicSiteMedia().catch(() => null),
    getHome(locale).catch(() => ({ sections: [] })),
  ]);
  const featured = products.filter((p) => p.is_featured);
  const heroProduct = featured[0] ?? products.find((product) => product.primary_image_url) ?? products[0] ?? null;
  const landingCategories = getLandingCategories(products);
  const siteMediaAssets = siteMedia?.assets ?? null;
  const homeSections = home.sections.length > 0 ? home.sections : fallbackHomeSections(t);

  const renderHomeSection = (section: HomeSection) => {
    switch (section.type) {
      case "hero":
        return <HeroSection key={section.slug} product={heroProduct} siteMedia={siteMediaAssets} section={section} />;
      case "featured_products":
        return featured.length > 0 ? <FeaturedProductsShowcase key={section.slug} products={featured} section={section} /> : null;
      case "category_links":
        return landingCategories.length > 0 ? <HomeCategoryLinks key={section.slug} section={section} categories={landingCategories} t={t} /> : null;
      case "text_image":
        return <HomeTextImage key={section.slug} section={section} siteMedia={siteMediaAssets} />;
      case "text_band":
        return <HomeTextBand key={section.slug} section={section} />;
      case "cards":
        return <HomeCardsSection key={section.slug} section={section} />;
      case "timeline":
        return <HomeTimeline key={section.slug} section={section} />;
      case "collections":
        return <HomeCollections key={section.slug} section={section} siteMedia={siteMediaAssets} />;
      case "cta_band":
        return <HomeCtaBand key={section.slug} section={section} />;
      default:
        return null;
    }
  };

  return (
    <main className="bg-page text-text">
      {homeSections.map(renderHomeSection)}
    </main>
  );
}

function HomeSectionHeader({ section }: { section: HomeSection }) {
  return (
    <div className="landing-scroll-reveal max-w-2xl">
      {section.subheading ? <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">{section.subheading}</p> : null}
      <h2 className="mt-3 font-heading text-3xl text-text sm:text-4xl">{section.heading}</h2>
      {section.body ? <BodyRenderer body={section.body} className="mt-4 text-base leading-7 text-muted" /> : null}
    </div>
  );
}

function HomeCardsSection({ section }: { section: HomeSection }) {
  return (
    <section id={section.slug} className="relative isolate overflow-hidden px-4 py-14 sm:px-6 lg:px-8 lg:py-20">
      <div className="relative z-10 mx-auto grid max-w-7xl gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-end">
        <HomeSectionHeader section={section} />
        <div className="grid gap-3 sm:grid-cols-2">
          {section.items.map((item, index) => (
            <div
              key={item.id}
              className="landing-scroll-reveal rounded-brand bg-[rgb(248_241_241)] p-4 shadow-lg shadow-border/10 ring-1 ring-border/25 transition-all duration-300 motion-safe:hover:-translate-y-0.5 motion-safe:hover:shadow-xl motion-safe:hover:shadow-border/15"
              style={{ animationDelay: `${index * 90}ms` }}
            >
              <h3 className="font-heading text-lg text-text">{item.title}</h3>
              {item.text ? <p className="mt-2 text-sm leading-6 text-muted">{item.text}</p> : null}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function HomeCategoryLinks({ section, categories, t }: { section: HomeSection; categories: LandingCategory[]; t: HomeTranslator }) {
  return (
    <section id={section.slug} className="relative isolate overflow-hidden px-4 py-14 sm:px-6 lg:px-8 lg:py-20">
      <div className="relative z-10 mx-auto max-w-7xl">
        <div className="mb-7">
          <HomeSectionHeader section={section} />
        </div>
        <div className="-mx-4 flex gap-4 overflow-x-auto px-4 pb-3 sm:mx-0 sm:grid sm:grid-cols-2 sm:px-0 lg:grid-cols-4">
          {categories.map((category, index) => (
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
                <span className="block font-heading text-xl text-text">{t(`categories.${category.key}`)}</span>
                <span className="mt-2 block text-sm leading-6 text-muted">{t(`categoryDescriptions.${category.key}`)}</span>
                <span className="mt-4 inline-flex text-sm font-semibold text-accent">{t("categoryCta", { count: category.count })}</span>
              </span>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}

function imageFor(section: HomeSection, itemImage?: string | null, siteMedia?: SiteMediaMap | null) {
  if (section.type === "collections") {
    return resolveMediaUrl(itemImage || section.image || siteMedia?.home_collections_fallback || "/rebrand/error-candle.webp");
  }
  return resolveMediaUrl(itemImage || section.image || siteMedia?.home_text_image_fallback || "/rebrand/error-candle.webp");
}

function HomeTextImage({ section, siteMedia }: { section: HomeSection; siteMedia?: SiteMediaMap | null }) {
  return (
    <section id={section.slug} className="bg-page px-4 py-16 sm:px-6 sm:py-20 lg:px-8 lg:py-28">
      <div className="mx-auto grid max-w-7xl items-center gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:gap-16">
        <div className="editorial-image-settle overflow-hidden rounded-brand bg-surface shadow-sm shadow-border/10">
          <img src={imageFor(section, null, siteMedia) ?? undefined} alt="" className="aspect-[4/5] w-full object-cover" />
        </div>
        <HomeSectionHeader section={section} />
      </div>
    </section>
  );
}

function HomeTextBand({ section }: { section: HomeSection }) {
  return (
    <section id={section.slug} className="bg-surface px-4 py-16 text-center sm:px-6 sm:py-20 lg:px-8 lg:py-28">
      <div className="mx-auto max-w-4xl">
        <HomeSectionHeader section={section} />
        <HomeCta section={section} />
      </div>
    </section>
  );
}

function HomeTimeline({ section }: { section: HomeSection }) {
  return (
    <section id={section.slug} className="bg-surface px-4 py-16 sm:px-6 sm:py-20 lg:px-8 lg:py-28">
      <div className="mx-auto grid max-w-7xl gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:gap-16">
        <HomeSectionHeader section={section} />
        <div className="space-y-5 border-l editorial-divider pl-5 sm:pl-7">
          {section.items.map((item, index) => (
            <article key={item.id} className="grid grid-cols-[3rem_1fr] gap-4 bg-page/35 py-2">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-accent text-sm font-semibold text-accent-foreground shadow-sm shadow-accent/15">{String(index + 1).padStart(2, "0")}</div>
              <div>
                <h3 className="font-heading text-2xl text-text">{item.title}</h3>
                {item.text ? <p className="mt-2 text-sm leading-7 text-muted">{item.text}</p> : null}
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function HomeCollections({ section, siteMedia }: { section: HomeSection; siteMedia?: SiteMediaMap | null }) {
  return (
    <section id={section.slug} className="bg-page px-4 py-16 sm:px-6 sm:py-20 lg:px-8 lg:py-28">
      <div className="mx-auto max-w-7xl">
        <HomeSectionHeader section={section} />
        <div className="mt-10 grid gap-6 md:grid-cols-3">
          {section.items.map((item) => {
            const content = (
              <article className="group overflow-hidden rounded-brand bg-surface/45 shadow-sm shadow-border/10">
                <img src={imageFor(section, item.image, siteMedia) ?? undefined} alt="" className="aspect-[4/3] w-full object-cover transition-transform duration-300 group-hover:scale-105 motion-reduce:transition-none motion-reduce:group-hover:scale-100" />
                <div className="p-6">
                  <h3 className="font-heading text-2xl text-text">{item.title}</h3>
                  {item.text ? <p className="mt-3 text-sm leading-7 text-muted">{item.text}</p> : null}
                </div>
              </article>
            );
            return item.link ? <Link key={item.id} href={normalizeInternalHref(item.link)}>{content}</Link> : <div key={item.id}>{content}</div>;
          })}
        </div>
      </div>
    </section>
  );
}

function HomeCtaBand({ section }: { section: HomeSection }) {
  return (
    <section id={section.slug} className="bg-text px-4 py-16 text-center text-page sm:px-6 sm:py-20 lg:px-8 lg:py-28">
      <div className="mx-auto max-w-4xl">
        <h2 className="font-heading text-4xl text-page sm:text-5xl">{section.heading}</h2>
        {section.body ? <BodyRenderer body={section.body} className="mt-6 text-surface" /> : null}
        <HomeCta section={section} />
      </div>
    </section>
  );
}

function HomeCta({ section }: { section: HomeSection }) {
  if (!section.cta) return null;
  return (
    <div className="mt-9">
      <Link href={normalizeInternalHref(section.cta.href)} className="inline-flex min-h-11 items-center justify-center rounded-brand bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page">
        {section.cta.label}
      </Link>
    </div>
  );
}

function normalizeInternalHref(href: string) {
  const trimmed = href.trim();
  if (/^[a-z][a-z\d+.-]*:/i.test(trimmed) || /^[/#.]/.test(trimmed)) return trimmed;
  return `/${trimmed}`;
}
