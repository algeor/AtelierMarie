import type { Metadata } from "next";
import { headers } from "next/headers";
import { Link } from "@/i18n/navigation";
import { ProductCard } from "@/components/products/ProductCard";
import { ProductGrid } from "@/components/products/ProductGrid";
import { FaqAccordion } from "@/components/faq/FaqAccordion";
import { getProducts, getSeoLandingPage } from "@/lib/api";
import type { Locale } from "@/i18n/routing";
import type { FaqItemResponse, ProductResponse, SeoLandingPagePublicResponse } from "@/lib/types";
import { HANDMADE_CANDLES_PATHS } from "@/lib/seo-pages";
import {
  BASE_URL,
  getLocalizedPathAlternates,
  SEO,
  serializeJsonLd,
} from "@/lib/seo";

const FALLBACK_COPY = {
  en: {
    metaTitle: "Handmade Candles | Atelier Marie",
    metaDescription:
      "Shop handmade candles from Atelier Marie: small-batch scents, gift-ready presentation, and custom candle options.",
    eyebrow: "Handmade candles",
    title: "Handmade candles for warm, thoughtful spaces",
    intro:
      "Discover Atelier Marie candles poured in small batches for quiet rituals, personal gifts, and seasonal moments. Each piece is finished with care, from scent and wax to packaging.",
    note:
      "Looking for something personal? Custom candles and gift sets can be prepared for birthdays, holidays, weddings, and intimate celebrations.",
    shopAll: "Shop all products",
    sectionTitle: "Current candle collection",
    empty: "The candle collection is being refreshed. Browse the full shop for available handmade pieces.",
    benefitsTitle: "Why choose Atelier Marie candles?",
    benefits: [
      "Small-batch handmade production",
      "Gift-ready details and careful packaging",
      "Custom options for personal occasions",
    ],
    faqTitle: "Handmade candle questions",
    faq: [
      {
        id: 101,
        question: "Are Atelier Marie candles handmade?",
        answer:
          "Yes. Atelier Marie candles are prepared in small batches with attention to scent, finish, and presentation.",
      },
      {
        id: 102,
        question: "Can I order a custom candle?",
        answer:
          "Yes. Use the contact page to share the occasion, timing, preferred style, and any names or details you want included.",
      },
      {
        id: 103,
        question: "Are the candles suitable as gifts?",
        answer:
          "Yes. The candles are designed to feel gift-ready, with careful finishing and packaging for personal occasions.",
      },
    ],
  },
  bg: {
    metaTitle: "Ръчно изработени свещи | Ателие Мари",
    metaDescription:
      "Разгледайте ръчно изработени свещи от Ателие Мари: малки серии, подаръчна визия и възможности за персонална поръчка.",
    eyebrow: "Ръчно изработени свещи",
    title: "Ръчно изработени свещи за уют и специални моменти",
    intro:
      "Открийте свещи от Ателие Мари, изработени в малки серии за уютен дом, личен подарък и сезонни поводи. Всяко изделие е подготвено с внимание към аромат, финиш и представяне.",
    note:
      "Търсите нещо лично? Можем да подготвим персонални свещи и подаръчни комплекти за рожден ден, празник, сватба или друг специален повод.",
    shopAll: "Разгледай всички продукти",
    sectionTitle: "Актуална колекция свещи",
    empty: "Колекцията със свещи се обновява. Разгледайте магазина за налични ръчно изработени изделия.",
    benefitsTitle: "Защо свещи от Ателие Мари?",
    benefits: [
      "Ръчна изработка в малки серии",
      "Грижа към детайла и подаръчна визия",
      "Персонални варианти за специални поводи",
    ],
    faqTitle: "Въпроси за ръчно изработени свещи",
    faq: [
      {
        id: 201,
        question: "Свещите на Ателие Мари ръчно изработени ли са?",
        answer:
          "Да. Свещите се подготвят в малки серии с внимание към аромат, финиш и представяне.",
      },
      {
        id: 202,
        question: "Мога ли да поръчам персонална свещ?",
        answer:
          "Да. Изпратете ни повод, срок, предпочитан стил и детайли като име, цвят или тема чрез страницата за контакт.",
      },
      {
        id: 203,
        question: "Подходящи ли са свещите за подарък?",
        answer:
          "Да. Свещите са създадени с подаръчна визия, внимателен финиш и опаковка за лични поводи.",
      },
    ],
  },
} satisfies Record<Locale, {
  metaTitle: string;
  metaDescription: string;
  eyebrow: string;
  title: string;
  intro: string;
  note: string;
  shopAll: string;
  sectionTitle: string;
  empty: string;
  benefitsTitle: string;
  benefits: string[];
  faqTitle: string;
  faq: FaqItemResponse[];
}>;

function fallbackContent(locale: Locale): SeoLandingPagePublicResponse {
  const copy = FALLBACK_COPY[locale];
  return {
    slug: "handmade-candles",
    product_type: "candles",
    path: HANDMADE_CANDLES_PATHS[locale],
    meta_title: copy.metaTitle,
    meta_description: copy.metaDescription,
    eyebrow: copy.eyebrow,
    title: copy.title,
    intro: copy.intro,
    note: copy.note,
    shop_all_label: copy.shopAll,
    section_title: copy.sectionTitle,
    empty_text: copy.empty,
    benefits_title: copy.benefitsTitle,
    benefits: copy.benefits,
    faq_title: copy.faqTitle,
    faq: copy.faq,
  };
}

async function loadContent(locale: Locale): Promise<SeoLandingPagePublicResponse> {
  return getSeoLandingPage("handmade-candles", locale).catch(() => fallbackContent(locale));
}

export async function getHandmadeCandlesMetadata(locale: Locale): Promise<Metadata> {
  const copy = await loadContent(locale);
  return {
    title: copy.meta_title,
    description: copy.meta_description,
    alternates: getLocalizedPathAlternates(locale, HANDMADE_CANDLES_PATHS),
    openGraph: {
      type: "website",
      title: copy.meta_title,
      description: copy.meta_description,
      url: `${BASE_URL}/${locale}${HANDMADE_CANDLES_PATHS[locale]}`,
      siteName: SEO.brandName,
    },
  };
}

function buildJsonLd(
  locale: Locale,
  products: ProductResponse[],
  copy: SeoLandingPagePublicResponse,
) {
  const path = HANDMADE_CANDLES_PATHS[locale];
  const url = `${BASE_URL}/${locale}${path}`;

  return {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "CollectionPage",
        "@id": `${url}#collection`,
        url,
        name: copy.title,
        description: copy.meta_description,
        inLanguage: locale,
        isPartOf: { "@id": `${BASE_URL}/#website` },
      },
      {
        "@type": "BreadcrumbList",
        "@id": `${url}#breadcrumbs`,
        itemListElement: [
          {
            "@type": "ListItem",
            position: 1,
            name: SEO.brandName,
            item: `${BASE_URL}/${locale}`,
          },
          {
            "@type": "ListItem",
            position: 2,
            name: copy.eyebrow,
            item: url,
          },
        ],
      },
      {
        "@type": "ItemList",
        "@id": `${url}#products`,
        itemListElement: products.map((product, index) => ({
          "@type": "ListItem",
          position: index + 1,
          url: `${BASE_URL}/${locale}/products/${product.id}`,
          name: product.name,
        })),
      },
      {
        "@type": "FAQPage",
        "@id": `${url}#faq`,
        mainEntity: copy.faq.map((item) => ({
          "@type": "Question",
          name: item.question,
          acceptedAnswer: {
            "@type": "Answer",
            text: item.answer,
          },
        })),
      },
    ],
  };
}

export async function HandmadeCandlesLandingPage({ locale }: { locale: Locale }) {
  const nonce = (await headers()).get("x-nonce") ?? undefined;
  const copy = await loadContent(locale);
  const { products, total } = await getProducts(1, 24, locale, {
    product_type: copy.product_type,
    sort: "newest",
  }).catch(() => ({ products: [], total: 0, page: 1, limit: 24 }));
  const jsonLd = buildJsonLd(locale, products, copy);

  return (
    <main className="bg-page text-text">
      <script
        nonce={nonce}
        type="application/ld+json"
        suppressHydrationWarning
        dangerouslySetInnerHTML={{ __html: serializeJsonLd(jsonLd) }}
      />

      <section className="editorial-band px-4 py-12 sm:px-6 lg:px-8 lg:py-16">
        <div className="mx-auto grid max-w-7xl gap-8 border-b editorial-divider pb-10 lg:grid-cols-[minmax(0,0.85fr)_minmax(18rem,0.45fr)] lg:items-end">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-accent">
              {copy.eyebrow}
            </p>
            <h1 className="mt-3 max-w-3xl font-heading text-4xl leading-tight text-text sm:text-5xl">
              {copy.title}
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-8 text-muted sm:text-lg">
              {copy.intro}
            </p>
          </div>
          <div className="editorial-paper-panel rounded-brand p-5">
            <h2 className="font-heading text-xl text-text">{copy.benefits_title}</h2>
            <ul className="mt-4 space-y-3 text-sm leading-6 text-muted">
              {copy.benefits.map((benefit) => (
                <li key={benefit} className="border-l border-accent/45 pl-3">
                  {benefit}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <section className="px-4 pb-14 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <div className="mb-7 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="font-heading text-3xl text-text">{copy.section_title}</h2>
              <p className="mt-2 text-sm text-muted">
                {total > 0 ? `${total} ${locale === "bg" ? "изделия" : "pieces"}` : copy.empty_text}
              </p>
            </div>
            <Link
              href="/products?type=candles"
              className="inline-flex min-h-[44px] items-center rounded-brand border border-accent px-4 py-2 text-sm font-medium text-text transition-colors hover:bg-accent/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page"
            >
              {copy.shop_all_label}
            </Link>
          </div>

          {products.length > 0 ? (
            <ProductGrid>
              {products.map((product, index) => (
                <ProductCard
                  key={product.id}
                  product={product}
                  index={index}
                  listingContext="handmade-candles"
                  activeFilters="type:candles"
                  sort="newest"
                  resultCount={products.length}
                  totalCount={total}
                />
              ))}
            </ProductGrid>
          ) : (
            <div className="editorial-paper-panel rounded-brand p-6 text-muted">
              {copy.empty_text}
            </div>
          )}
        </div>
      </section>

      <section className="bg-surface/45 px-4 py-12 sm:px-6 lg:px-8">
        <div className="mx-auto grid max-w-7xl gap-8 lg:grid-cols-[0.8fr_1.2fr] lg:items-start">
          <div>
            <h2 className="font-heading text-3xl text-text">{copy.faq_title}</h2>
            <p className="mt-4 max-w-md text-sm leading-7 text-muted">{copy.note}</p>
          </div>
          <FaqAccordion items={copy.faq} />
        </div>
      </section>
    </main>
  );
}
