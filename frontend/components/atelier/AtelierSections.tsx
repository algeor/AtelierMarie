import { Link } from "@/i18n/navigation";
import type { AboutSection } from "@/lib/types";
import { BodyRenderer } from "./BodyRenderer";

const FALLBACK_IMAGES: Record<string, string> = {
  hero: "/rebrand/error-candle.webp",
  story: "/rebrand/error-candle.webp",
  atelier: "/rebrand/error-candle.webp",
  collections: "/rebrand/error-candle.webp",
  process: "/rebrand/error-candle.webp",
};

function imageFor(section: AboutSection, itemImage?: string | null) {
  return (
    itemImage ||
    section.image ||
    FALLBACK_IMAGES[section.slug] ||
    FALLBACK_IMAGES.hero
  );
}

function SectionShell({
  section,
  children,
  className = "",
}: {
  section: AboutSection;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      id={section.slug}
      className={`scroll-mt-24 py-16 sm:py-20 lg:py-28 ${className}`}
    >
      {children}
    </section>
  );
}

function Eyebrow({ children }: { children: React.ReactNode }) {
  return <div className="mb-4 h-0.5 w-14 bg-accent" aria-hidden="true" />;
}

function Cta({ section }: { section: AboutSection }) {
  if (!section.cta) return null;
  return (
    <Link
      href={normalizeInternalHref(section.cta.href)}
      className="inline-flex min-h-11 items-center justify-center rounded-brand bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-page"
    >
      {section.cta.label}
    </Link>
  );
}

function normalizeInternalHref(href: string) {
  const trimmed = href.trim();
  if (/^[a-z][a-z\d+.-]*:/i.test(trimmed) || /^[/#.]/.test(trimmed)) {
    return trimmed;
  }
  return `/${trimmed}`;
}

export function Hero({ section }: { section: AboutSection }) {
  return (
    <SectionShell
      section={section}
      className="relative overflow-hidden bg-text py-0 text-page"
    >
      <div className="relative min-h-[82vh]">
        <img
          src={imageFor(section)}
          alt=""
          className="absolute inset-0 h-full w-full object-cover opacity-55"
        />
        <div className="absolute inset-0 bg-text/35" aria-hidden="true" />
        <div className="relative z-10 flex min-h-[82vh] items-end px-4 pb-16 sm:px-6 lg:px-8">
          <div className="mx-auto w-full max-w-7xl">
            <div className="max-w-3xl">
              <h1 className="font-heading text-5xl text-page sm:text-6xl lg:text-7xl">
                {section.heading}
              </h1>
              {section.subheading && (
                <p className="mt-5 max-w-2xl text-lg leading-8 text-surface sm:text-xl">
                  {section.subheading}
                </p>
              )}
              <div className="mt-8">
                <Cta section={section} />
              </div>
            </div>
          </div>
        </div>
      </div>
      <div className="bg-page px-4 py-14 text-text sm:px-6 lg:px-8">
        <div className="mx-auto max-w-3xl text-center">
          <BodyRenderer body={section.body} />
        </div>
      </div>
    </SectionShell>
  );
}

export function TextImage({ section }: { section: AboutSection }) {
  return (
    <SectionShell section={section} className="bg-page">
      <div className="mx-auto grid max-w-7xl items-center gap-10 px-4 sm:px-6 lg:grid-cols-[0.9fr_1.1fr] lg:gap-16 lg:px-8">
        <div className="editorial-image-settle overflow-hidden rounded-brand bg-surface shadow-sm shadow-border/10">
          <img
            src={imageFor(section)}
            alt=""
            className="aspect-[4/5] w-full object-cover"
          />
        </div>
        <div>
          <Eyebrow>{null}</Eyebrow>
          <h2 className="font-heading text-4xl text-text sm:text-5xl">
            {section.heading}
          </h2>
          {section.subheading && (
            <p className="mt-4 text-lg text-accent">{section.subheading}</p>
          )}
          <BodyRenderer body={section.body} className="mt-8" />
        </div>
      </div>
    </SectionShell>
  );
}

export function TextBand({ section }: { section: AboutSection }) {
  return (
    <SectionShell section={section} className="bg-surface">
      <div className="mx-auto max-w-4xl px-4 text-center sm:px-6 lg:px-8">
        <div className="mx-auto mb-5 h-0.5 w-14 bg-accent" aria-hidden="true" />
        <h2 className="font-heading text-4xl text-text sm:text-5xl">
          {section.heading}
        </h2>
        {section.subheading && (
          <p className="mt-4 text-lg text-accent">{section.subheading}</p>
        )}
        <BodyRenderer body={section.body} className="mt-8" />
        <div className="mt-9">
          <Cta section={section} />
        </div>
      </div>
    </SectionShell>
  );
}

export function CardGrid({ section }: { section: AboutSection }) {
  return (
    <SectionShell section={section} className="bg-page">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl">
          <Eyebrow>{null}</Eyebrow>
          <h2 className="font-heading text-4xl text-text sm:text-5xl">
            {section.heading}
          </h2>
          {section.subheading && (
            <p className="mt-4 text-lg text-accent">{section.subheading}</p>
          )}
        </div>
        <div className="mt-10 grid gap-7 sm:grid-cols-2 lg:grid-cols-4">
          {section.items.map((item) => (
            <article
              key={item.id}
              className="border-l border-accent/35 bg-surface-elevated/30 px-5 py-2"
            >
              <h3 className="font-heading text-2xl text-text">{item.title}</h3>
              {item.text && (
                <p className="mt-4 text-sm leading-7 text-muted">{item.text}</p>
              )}
            </article>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

export function ProcessTimeline({ section }: { section: AboutSection }) {
  return (
    <SectionShell section={section} className="bg-surface">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:gap-16">
          <div>
            <Eyebrow>{null}</Eyebrow>
            <h2 className="font-heading text-4xl text-text sm:text-5xl">
              {section.heading}
            </h2>
            {section.subheading && (
              <p className="mt-4 text-lg text-accent">{section.subheading}</p>
            )}
            <BodyRenderer body={section.body} className="mt-8" />
          </div>
          <div className="space-y-5 border-l editorial-divider pl-5 sm:pl-7">
            {section.items.map((item, index) => (
              <article
                key={item.id}
                className="grid grid-cols-[3rem_1fr] gap-4 bg-page/35 py-2"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-accent text-sm font-semibold text-accent-foreground shadow-sm shadow-accent/15">
                  {String(index + 1).padStart(2, "0")}
                </div>
                <div>
                  <h3 className="font-heading text-2xl text-text">
                    {item.title}
                  </h3>
                  {item.text && (
                    <p className="mt-2 text-sm leading-7 text-muted">
                      {item.text}
                    </p>
                  )}
                </div>
              </article>
            ))}
          </div>
        </div>
      </div>
    </SectionShell>
  );
}

export function CollectionsGrid({ section }: { section: AboutSection }) {
  return (
    <SectionShell section={section} className="bg-page">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl">
          <Eyebrow>{null}</Eyebrow>
          <h2 className="font-heading text-4xl text-text sm:text-5xl">
            {section.heading}
          </h2>
          {section.subheading && (
            <p className="mt-4 text-lg text-accent">{section.subheading}</p>
          )}
        </div>
        <div className="mt-10 grid gap-6 md:grid-cols-3">
          {section.items.map((item) => {
            const content = (
              <article className="group overflow-hidden rounded-brand bg-surface/45 shadow-sm shadow-border/10">
                <img
                  src={imageFor(section, item.image)}
                  alt=""
                  className="aspect-[4/3] w-full object-cover transition-transform duration-300 group-hover:scale-105 motion-reduce:transition-none motion-reduce:group-hover:scale-100"
                />
                <div className="p-6">
                  <h3 className="font-heading text-2xl text-text">
                    {item.title}
                  </h3>
                  {item.text && (
                    <p className="mt-3 text-sm leading-7 text-muted">
                      {item.text}
                    </p>
                  )}
                </div>
              </article>
            );
            return item.link ? (
              <Link key={item.id} href={item.link}>
                {content}
              </Link>
            ) : (
              <div key={item.id}>{content}</div>
            );
          })}
        </div>
      </div>
    </SectionShell>
  );
}

export function CtaBand({ section }: { section: AboutSection }) {
  return (
    <SectionShell section={section} className="bg-text text-page">
      <div className="mx-auto max-w-4xl px-4 text-center sm:px-6 lg:px-8">
        <h2 className="font-heading text-4xl text-page sm:text-5xl">
          {section.heading}
        </h2>
        <BodyRenderer body={section.body} className="mt-6 text-surface" />
        <div className="mt-9">
          <Cta section={section} />
        </div>
      </div>
    </SectionShell>
  );
}

export function renderAtelierSection(section: AboutSection) {
  switch (section.type) {
    case "hero":
      return <Hero key={section.slug} section={section} />;
    case "text_image":
      return <TextImage key={section.slug} section={section} />;
    case "text_band":
      return <TextBand key={section.slug} section={section} />;
    case "cards":
      return <CardGrid key={section.slug} section={section} />;
    case "timeline":
      return <ProcessTimeline key={section.slug} section={section} />;
    case "collections":
      return <CollectionsGrid key={section.slug} section={section} />;
    case "cta_band":
      return <CtaBand key={section.slug} section={section} />;
    default:
      return null;
  }
}
