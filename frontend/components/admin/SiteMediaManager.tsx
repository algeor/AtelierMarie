"use client";

import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import Image from "next/image";
import { ImageCropEditor } from "@/components/admin/ImageCropEditor";
import { SaveConfirmation } from "@/components/admin/SaveConfirmation";
import { Button } from "@/components/ui/Button";
import { DeleteIconButton } from "@/components/ui/DeleteIconButton";
import {
  clearAboutItemImage,
  clearAboutSectionImage,
  clearSiteMediaImage,
  getAdminAbout,
  getAdminSiteMedia,
  updateAboutItem,
  uploadAboutItemImage,
  uploadAboutSectionImage,
  uploadSiteMediaImage,
} from "@/lib/api";
import { resolveMediaUrl } from "@/lib/media";
import type { AboutItemAdmin, AboutSectionAdmin, SiteMediaAssetAdmin } from "@/lib/types";

const ABOUT_FALLBACK_KEYS: Partial<Record<string, SiteMediaAssetAdmin["key"]>> = {
  hero: "atelier_hero_fallback",
  story: "atelier_story_fallback",
  atelier: "atelier_atelier_fallback",
  collections: "atelier_collections_fallback",
  process: "atelier_process_fallback",
};

const IMAGE_SECTION_TYPES = new Set(["hero", "text_image", "collections"]);

type CollectionItemTextDraft = {
  title_en: string;
  title_bg: string | null;
  text_en: string | null;
  text_bg: string | null;
  link_href: string | null;
};

export function SiteMediaManager() {
  const [assets, setAssets] = useState<SiteMediaAssetAdmin[]>([]);
  const [aboutSections, setAboutSections] = useState<AboutSectionAdmin[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [saveNotice, setSaveNotice] = useState<{ id: number; message: string } | null>(null);
  const saveNoticeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  async function refresh() {
    const [siteMedia, about] = await Promise.all([getAdminSiteMedia(), getAdminAbout()]);
    setAssets(siteMedia.assets);
    setAboutSections(about.sections);
  }

  useEffect(() => {
    refresh().catch(() => setError("Could not load site media."));
  }, []);

  useEffect(() => {
    return () => {
      if (saveNoticeTimerRef.current) clearTimeout(saveNoticeTimerRef.current);
    };
  }, []);

  function showSaved(message = "Saved.") {
    if (saveNoticeTimerRef.current) clearTimeout(saveNoticeTimerRef.current);
    setSaveNotice((current) => ({ id: (current?.id ?? 0) + 1, message }));
    saveNoticeTimerRef.current = setTimeout(() => setSaveNotice(null), 3200);
  }

  async function run(key: string, action: () => Promise<unknown>) {
    setBusyKey(key);
    setError(null);
    try {
      await action();
      await refresh();
      showSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save site media.");
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-heading text-2xl font-semibold text-charcoal">Site media</h1>
        <p className="mt-1 text-sm text-soft-brown">
          Manage storefront images, main page photos, and fallback photos with page previews.
        </p>
      </div>

      {error ? (
        <div className="rounded-brand border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}
      {saveNotice ? <SaveConfirmation key={saveNotice.id} message={saveNotice.message} /> : null}

      <MediaGroup title="Main page images">
        {assets.filter((asset) => !asset.key.endsWith("_fallback")).map((asset) => (
          <MediaAssetCard
            key={asset.key}
            asset={asset}
            busy={busyKey === asset.key}
            onUpload={(file) => run(asset.key, () => uploadSiteMediaImage(asset.key, file))}
            onClear={() => run(asset.key, () => clearSiteMediaImage(asset.key))}
          />
        ))}

        {aboutSections.filter((section) => IMAGE_SECTION_TYPES.has(section.type)).map((section) => {
          const fallbackUrl = fallbackUrlForAboutSection(section, assets);
          return (
            <AboutSectionMediaCard
              key={`about-section-${section.slug}`}
              section={section}
              fallbackUrl={fallbackUrl}
              busy={busyKey === `about-section-${section.slug}`}
              onUpload={(file) => run(`about-section-${section.slug}`, () => uploadAboutSectionImage(section.slug, file))}
              onClear={() => run(`about-section-${section.slug}`, () => clearAboutSectionImage(section.slug))}
            />
          );
        })}

        {aboutSections.filter((section) => section.type === "collections").flatMap((section) => {
          const fallbackUrl = section.image || fallbackUrlForAboutSection(section, assets);
          return section.items.map((item) => (
            <AboutItemMediaCard
              key={`about-item-${item.id}`}
              section={section}
              item={item}
              fallbackUrl={fallbackUrl}
              busy={busyKey === `about-item-${item.id}`}
              onSaveText={(draft) => run(`about-item-${item.id}`, () => updateAboutItem(section.slug, item.id, draft))}
              onUpload={(file) => run(`about-item-${item.id}`, () => uploadAboutItemImage(section.slug, item.id, file))}
              onClear={() => run(`about-item-${item.id}`, () => clearAboutItemImage(section.slug, item.id))}
            />
          ));
        })}
      </MediaGroup>

      <MediaGroup title="Fallback images">
        {assets.filter((asset) => asset.key.endsWith("_fallback")).map((asset) => (
          <MediaAssetCard
            key={asset.key}
            asset={asset}
            busy={busyKey === asset.key}
            onUpload={(file) => run(asset.key, () => uploadSiteMediaImage(asset.key, file))}
            onClear={() => run(asset.key, () => clearSiteMediaImage(asset.key))}
          />
        ))}
      </MediaGroup>
    </div>
  );
}

function MediaGroup({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-3">
      <h2 className="font-heading text-xl font-semibold text-charcoal">{title}</h2>
      <div className="grid gap-4 lg:grid-cols-2">{children}</div>
    </section>
  );
}

function MediaAssetCard({
  asset,
  busy,
  onUpload,
  onClear,
}: {
  asset: SiteMediaAssetAdmin;
  busy: boolean;
  onUpload: (file: File) => void;
  onClear: () => void;
}) {
  const previewUrl = resolveMediaUrl(asset.thumbnail_url || asset.effective_url);
  const pageImageUrl = resolveMediaUrl(asset.effective_url);
  const isCustom = Boolean(asset.image_url);
  const [showPagePreview, setShowPagePreview] = useState(false);
  const [cropFile, setCropFile] = useState<File | null>(null);
  const cropAspect = cropAspectForSiteMedia(asset.key);
  const cropHint = `Drag to reposition, zoom, or rotate. The frame matches the ${asset.label.toLowerCase()} preview.`;

  return (
    <article className="rounded-brand border border-champagne-beige bg-cream p-4 shadow-sm">
      <div className="grid gap-4 sm:grid-cols-[9rem_1fr]">
        <div className="relative aspect-[4/5] overflow-hidden rounded-brand border border-champagne-beige bg-warm-ivory">
          {previewUrl ? (
            <Image
              src={previewUrl}
              alt=""
              fill
              sizes="144px"
              className="object-cover"
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center px-3 text-center text-xs text-soft-brown">
              No image set
            </div>
          )}
        </div>
        <div className="min-w-0">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h2 className="font-heading text-xl text-charcoal">{asset.label}</h2>
              <p className="mt-1 font-mono text-xs text-soft-brown">{asset.key}</p>
            </div>
            <span className="rounded-brand bg-warm-ivory px-2 py-1 text-xs font-medium text-soft-brown">
              {isCustom ? "Custom" : asset.default_url ? "Default" : "Empty"}
            </span>
          </div>
          <p className="mt-3 text-sm leading-6 text-soft-brown">{asset.description}</p>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <label className="inline-flex min-h-10 cursor-pointer items-center rounded-brand border border-champagne-beige px-3 text-sm text-soft-brown hover:bg-champagne-beige/40">
              Upload
              <input
                type="file"
                accept="image/jpeg,image/png"
                className="sr-only"
                disabled={busy}
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) setCropFile(file);
                  event.target.value = "";
                }}
              />
            </label>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setShowPagePreview((current) => !current)}
            >
              {showPagePreview ? "Hide preview" : "Preview"}
            </Button>
            {busy ? <span className="text-sm text-soft-brown">Saving...</span> : null}
            {isCustom ? <DeleteIconButton label={`Clear ${asset.label}`} onClick={onClear} /> : null}
          </div>
        </div>
      </div>
      {showPagePreview ? <PageContextPreview asset={asset} imageUrl={pageImageUrl} /> : null}
      {cropFile ? (
        <ImageCropEditor
          file={cropFile}
          aspect={cropAspect}
          title={`Adjust ${asset.label}`}
          hint={cropHint}
          onConfirm={(framedFile) => {
            setCropFile(null);
            onUpload(framedFile);
          }}
          onCancel={() => setCropFile(null)}
        />
      ) : null}
    </article>
  );
}

function AboutSectionMediaCard({
  section,
  fallbackUrl,
  busy,
  onUpload,
  onClear,
}: {
  section: AboutSectionAdmin;
  fallbackUrl: string | null;
  busy: boolean;
  onUpload: (file: File) => void;
  onClear: () => void;
}) {
  const imageUrl = resolveMediaUrl(section.image || fallbackUrl);
  const isCustom = Boolean(section.image);
  const [showPagePreview, setShowPagePreview] = useState(false);
  const [cropFile, setCropFile] = useState<File | null>(null);
  const label = `${section.heading_en} image`;
  const description = descriptionForAboutSection(section);
  const cropAspect = cropAspectForAboutSection(section);

  return (
    <article className="rounded-brand border border-champagne-beige bg-cream p-4 shadow-sm">
      <div className="grid gap-4 sm:grid-cols-[9rem_1fr]">
        <div className="relative aspect-[4/5] overflow-hidden rounded-brand border border-champagne-beige bg-warm-ivory">
          {imageUrl ? (
            <Image src={imageUrl} alt="" fill sizes="144px" className="object-cover" />
          ) : (
            <div className="flex h-full w-full items-center justify-center px-3 text-center text-xs text-soft-brown">
              No image set
            </div>
          )}
        </div>
        <div className="min-w-0">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h2 className="font-heading text-xl text-charcoal">{label}</h2>
              <p className="mt-1 font-mono text-xs text-soft-brown">atelier/{section.slug} · {section.type}</p>
            </div>
            <span className="rounded-brand bg-warm-ivory px-2 py-1 text-xs font-medium text-soft-brown">
              {isCustom ? "Custom" : fallbackUrl ? "Uses fallback" : "Empty"}
            </span>
          </div>
          <p className="mt-3 text-sm leading-6 text-soft-brown">{description}</p>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <label className="inline-flex min-h-10 cursor-pointer items-center rounded-brand border border-champagne-beige px-3 text-sm text-soft-brown hover:bg-champagne-beige/40">
              Upload
              <input
                type="file"
                accept="image/jpeg,image/png"
                className="sr-only"
                disabled={busy}
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) setCropFile(file);
                  event.target.value = "";
                }}
              />
            </label>
            <Button type="button" variant="secondary" size="sm" onClick={() => setShowPagePreview((current) => !current)}>
              {showPagePreview ? "Hide preview" : "Preview"}
            </Button>
            {busy ? <span className="text-sm text-soft-brown">Saving...</span> : null}
            {isCustom ? <DeleteIconButton label={`Clear ${label}`} onClick={onClear} /> : null}
          </div>
        </div>
      </div>
      {showPagePreview ? <AboutSectionContextPreview section={section} imageUrl={imageUrl} /> : null}
      {cropFile ? (
        <ImageCropEditor
          file={cropFile}
          aspect={cropAspect}
          title={`Adjust ${label}`}
          hint={`Drag to reposition, zoom, or rotate. The frame matches the ${section.heading_en} page preview.`}
          onConfirm={(framedFile) => {
            setCropFile(null);
            onUpload(framedFile);
          }}
          onCancel={() => setCropFile(null)}
        />
      ) : null}
    </article>
  );
}

function AboutItemMediaCard({
  section,
  item,
  fallbackUrl,
  busy,
  onSaveText,
  onUpload,
  onClear,
}: {
  section: AboutSectionAdmin;
  item: AboutItemAdmin;
  fallbackUrl: string | null;
  busy: boolean;
  onSaveText: (draft: CollectionItemTextDraft) => void;
  onUpload: (file: File) => void;
  onClear: () => void;
}) {
  const imageUrl = resolveMediaUrl(item.image || fallbackUrl);
  const isCustom = Boolean(item.image);
  const [showPagePreview, setShowPagePreview] = useState(false);
  const [cropFile, setCropFile] = useState<File | null>(null);
  const [draft, setDraft] = useState<CollectionItemTextDraft>(() => textDraftFromItem(item));
  const label = `Collection card: ${item.title_en}`;
  const titleIsEmpty = draft.title_en.trim().length === 0;

  useEffect(() => {
    setDraft(textDraftFromItem(item));
  }, [item.id, item.title_en, item.title_bg, item.text_en, item.text_bg, item.link_href]);

  return (
    <article className="rounded-brand border border-champagne-beige bg-cream p-4 shadow-sm">
      <div className="grid gap-4 sm:grid-cols-[9rem_1fr]">
        <div className="relative aspect-[4/5] overflow-hidden rounded-brand border border-champagne-beige bg-warm-ivory">
          {imageUrl ? (
            <Image src={imageUrl} alt="" fill sizes="144px" className="object-cover" />
          ) : (
            <div className="flex h-full w-full items-center justify-center px-3 text-center text-xs text-soft-brown">
              No image set
            </div>
          )}
        </div>
        <div className="min-w-0">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h2 className="font-heading text-xl text-charcoal">{label}</h2>
              <p className="mt-1 font-mono text-xs text-soft-brown">atelier/{section.slug}/items/{item.id}</p>
            </div>
            <span className="rounded-brand bg-warm-ivory px-2 py-1 text-xs font-medium text-soft-brown">
              {isCustom ? "Custom" : fallbackUrl ? "Uses fallback" : "Empty"}
            </span>
          </div>
          <p className="mt-3 text-sm leading-6 text-soft-brown">
            Displayed on this collection card. When empty, it uses the shared collection image or fallback.
          </p>
          <div className="mt-4 grid gap-3 lg:grid-cols-2">
            <TextField
              label="Name EN"
              value={draft.title_en}
              onChange={(value) => setDraft((current) => ({ ...current, title_en: value }))}
            />
            <TextField
              label="Name BG"
              value={draft.title_bg ?? ""}
              onChange={(value) => setDraft((current) => ({ ...current, title_bg: value || null }))}
            />
            <TextArea
              label="Description EN"
              value={draft.text_en ?? ""}
              onChange={(value) => setDraft((current) => ({ ...current, text_en: value || null }))}
            />
            <TextArea
              label="Description BG"
              value={draft.text_bg ?? ""}
              onChange={(value) => setDraft((current) => ({ ...current, text_bg: value || null }))}
            />
            <TextField
              label="Link"
              value={draft.link_href ?? ""}
              onChange={(value) => setDraft((current) => ({ ...current, link_href: value || null }))}
            />
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <Button
              type="button"
              size="sm"
              isLoading={busy}
              disabled={titleIsEmpty}
              onClick={() => onSaveText(normalizeTextDraft(draft))}
            >
              Save text
            </Button>
            <label className="inline-flex min-h-10 cursor-pointer items-center rounded-brand border border-champagne-beige px-3 text-sm text-soft-brown hover:bg-champagne-beige/40">
              Upload
              <input
                type="file"
                accept="image/jpeg,image/png"
                className="sr-only"
                disabled={busy}
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) setCropFile(file);
                  event.target.value = "";
                }}
              />
            </label>
            <Button type="button" variant="secondary" size="sm" onClick={() => setShowPagePreview((current) => !current)}>
              {showPagePreview ? "Hide preview" : "Preview"}
            </Button>
            {busy ? <span className="text-sm text-soft-brown">Saving...</span> : null}
            {isCustom ? <DeleteIconButton label={`Clear ${label}`} onClick={onClear} /> : null}
          </div>
        </div>
      </div>
      {showPagePreview ? <CollectionItemPreview item={item} imageUrl={imageUrl} /> : null}
      {cropFile ? (
        <ImageCropEditor
          file={cropFile}
          aspect={4 / 3}
          title={`Adjust ${label}`}
          hint="Drag to reposition, zoom, or rotate. The frame matches the collection card preview."
          onConfirm={(framedFile) => {
            setCropFile(null);
            onUpload(framedFile);
          }}
          onCancel={() => setCropFile(null)}
        />
      ) : null}
    </article>
  );
}

function textDraftFromItem(item: AboutItemAdmin): CollectionItemTextDraft {
  return {
    title_en: item.title_en,
    title_bg: item.title_bg,
    text_en: item.text_en,
    text_bg: item.text_bg,
    link_href: item.link_href,
  };
}

function normalizeTextDraft(draft: CollectionItemTextDraft): CollectionItemTextDraft {
  return {
    title_en: draft.title_en.trim(),
    title_bg: draft.title_bg?.trim() || null,
    text_en: draft.text_en?.trim() || null,
    text_bg: draft.text_bg?.trim() || null,
    link_href: draft.link_href?.trim() || null,
  };
}

function TextField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block text-sm font-medium text-charcoal">
      {label}
      <input
        className="mt-1 w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm text-charcoal focus:border-muted-gold focus:outline-none"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function TextArea({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block text-sm font-medium text-charcoal lg:col-span-2">
      {label}
      <textarea
        className="mt-1 min-h-24 w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm leading-6 text-charcoal focus:border-muted-gold focus:outline-none"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function fallbackUrlForAboutSection(section: AboutSectionAdmin, assets: SiteMediaAssetAdmin[]) {
  const fallbackKey = ABOUT_FALLBACK_KEYS[section.slug];
  if (!fallbackKey) return null;
  return assets.find((asset) => asset.key === fallbackKey)?.effective_url ?? null;
}

function cropAspectForAboutSection(section: AboutSectionAdmin) {
  if (section.type === "hero") return 16 / 9;
  if (section.type === "collections") return 4 / 3;
  return 4 / 5;
}

function descriptionForAboutSection(section: AboutSectionAdmin) {
  if (section.type === "hero") {
    return "Displayed as the main Atelier hero image. When empty, it uses the Atelier hero fallback.";
  }
  if (section.type === "collections") {
    return "Used as the shared collection-card image when an individual collection card has no image.";
  }
  return "Displayed in this Atelier image-and-text section. When empty, it uses that section fallback.";
}

function cropAspectForSiteMedia(key: SiteMediaAssetAdmin["key"]) {
  switch (key) {
    case "home_hero":
    case "home_hero_fallback":
    case "atelier_hero_fallback":
    case "page_background":
      return 16 / 9;
    case "atelier_collections_fallback":
      return 4 / 3;
    default:
      return 4 / 5;
  }
}

function PageContextPreview({ asset, imageUrl }: { asset: SiteMediaAssetAdmin; imageUrl: string | null }) {
  if (asset.key === "page_background") return <BackgroundPreview imageUrl={imageUrl} />;
  if (asset.key === "error_page_image") return <ErrorPagePreview imageUrl={imageUrl} />;
  if (asset.key === "home_hero" || asset.key === "home_hero_fallback") {
    return <HomeHeroPreview imageUrl={imageUrl} />;
  }
  if (asset.key === "atelier_hero_fallback") return <AtelierHeroPreview imageUrl={imageUrl} />;
  if (asset.key === "atelier_collections_fallback") return <AtelierCollectionsPreview imageUrl={imageUrl} />;
  return <AtelierTextImagePreview imageUrl={imageUrl} />;
}

function AboutSectionContextPreview({ section, imageUrl }: { section: AboutSectionAdmin; imageUrl: string | null }) {
  if (section.type === "hero") return <AtelierHeroPreview imageUrl={imageUrl} />;
  if (section.type === "collections") return <AtelierCollectionsPreview imageUrl={imageUrl} />;
  return <AtelierTextImagePreview imageUrl={imageUrl} />;
}

function CollectionItemPreview({ item, imageUrl }: { item: AboutItemAdmin; imageUrl: string | null }) {
  if (!imageUrl) return <PreviewShell><EmptyPreview /></PreviewShell>;
  return (
    <PreviewShell>
      <div className="max-w-sm rounded-brand bg-page p-5">
        <article className="overflow-hidden rounded-brand bg-warm-ivory shadow-sm">
          <div className="aspect-[4/3] bg-cover bg-center" style={imageStyle(imageUrl)} />
          <div className="p-4">
            <h3 className="font-heading text-2xl text-charcoal">{item.title_en}</h3>
            {item.text_en ? <p className="mt-2 text-sm leading-6 text-soft-brown">{item.text_en}</p> : null}
          </div>
        </article>
      </div>
    </PreviewShell>
  );
}

function imageStyle(imageUrl: string | null): CSSProperties | undefined {
  return imageUrl ? { backgroundImage: `url("${imageUrl}")` } : undefined;
}

function EmptyPreview() {
  return (
    <div className="flex min-h-48 items-center justify-center rounded-brand border border-dashed border-champagne-beige bg-warm-ivory px-4 text-center text-sm text-soft-brown">
      No image set for this slot.
    </div>
  );
}

function HomeHeroPreview({ imageUrl }: { imageUrl: string | null }) {
  if (!imageUrl) return <PreviewShell><EmptyPreview /></PreviewShell>;
  return (
    <PreviewShell>
      <div className="relative min-h-72 overflow-hidden rounded-brand bg-page">
        <div className="absolute inset-0 bg-cover bg-center" style={imageStyle(imageUrl)} />
        <div className="absolute inset-0 bg-[linear-gradient(90deg,rgb(255_255_255/0.78)_0%,rgb(255_255_255/0.24)_48%,rgb(255_255_255/0.05)_100%)]" />
        <div className="relative z-10 flex min-h-72 max-w-lg flex-col justify-center p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-soft-brown">Hand-poured in small batches</p>
          <h3 className="mt-3 font-heading text-5xl leading-none text-charcoal">Atelier Marie</h3>
          <p className="mt-4 max-w-sm text-sm leading-6 text-soft-brown">Handmade candles, soft scents, and gift-ready details.</p>
        </div>
      </div>
    </PreviewShell>
  );
}

function AtelierHeroPreview({ imageUrl }: { imageUrl: string | null }) {
  if (!imageUrl) return <PreviewShell><EmptyPreview /></PreviewShell>;
  return (
    <PreviewShell>
      <div className="relative min-h-72 overflow-hidden rounded-brand bg-charcoal text-warm-ivory">
        <div className="absolute inset-0 bg-cover bg-center opacity-55" style={imageStyle(imageUrl)} />
        <div className="absolute inset-0 bg-charcoal/35" />
        <div className="relative z-10 flex min-h-72 items-end p-8">
          <div className="max-w-xl">
            <h3 className="font-heading text-5xl leading-none text-warm-ivory">The Atelier Marie</h3>
            <p className="mt-4 text-base leading-7 text-cream">A warm first impression for the story page.</p>
          </div>
        </div>
      </div>
    </PreviewShell>
  );
}

function AtelierTextImagePreview({ imageUrl }: { imageUrl: string | null }) {
  if (!imageUrl) return <PreviewShell><EmptyPreview /></PreviewShell>;
  return (
    <PreviewShell>
      <div className="grid gap-5 rounded-brand bg-page p-5 md:grid-cols-[0.8fr_1fr] md:items-center">
        <div className="aspect-[4/5] rounded-brand bg-cover bg-center shadow-sm" style={imageStyle(imageUrl)} />
        <div>
          <div className="mb-4 h-0.5 w-14 bg-muted-gold" />
          <h3 className="font-heading text-4xl text-charcoal">Our Story</h3>
          <p className="mt-4 text-sm leading-7 text-soft-brown">This is the common image-and-text treatment used across the Atelier page.</p>
        </div>
      </div>
    </PreviewShell>
  );
}

function AtelierCollectionsPreview({ imageUrl }: { imageUrl: string | null }) {
  if (!imageUrl) return <PreviewShell><EmptyPreview /></PreviewShell>;
  return (
    <PreviewShell>
      <div className="grid gap-4 rounded-brand bg-page p-5 md:grid-cols-3">
        {["Floral", "Sculptural", "Custom"].map((title) => (
          <article key={title} className="overflow-hidden rounded-brand bg-warm-ivory shadow-sm">
            <div className="aspect-[4/3] bg-cover bg-center" style={imageStyle(imageUrl)} />
            <div className="p-4">
              <h3 className="font-heading text-2xl text-charcoal">{title}</h3>
              <p className="mt-2 text-sm leading-6 text-soft-brown">Collection card preview.</p>
            </div>
          </article>
        ))}
      </div>
    </PreviewShell>
  );
}

function ErrorPagePreview({ imageUrl }: { imageUrl: string | null }) {
  if (!imageUrl) return <PreviewShell><EmptyPreview /></PreviewShell>;
  return (
    <PreviewShell>
      <div className="grid gap-5 rounded-brand bg-page p-5 md:grid-cols-[1fr_0.7fr] md:items-center">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-soft-brown">Atelier Marie</p>
          <h3 className="mt-3 font-heading text-5xl text-charcoal">Page not found</h3>
          <p className="mt-4 text-sm leading-7 text-soft-brown">The image appears beside the recovery message.</p>
        </div>
        <div className="aspect-[4/5] rounded-brand bg-cover bg-center shadow-xl" style={imageStyle(imageUrl)} />
      </div>
    </PreviewShell>
  );
}

function BackgroundPreview({ imageUrl }: { imageUrl: string | null }) {
  if (!imageUrl) return <PreviewShell><EmptyPreview /></PreviewShell>;
  return (
    <PreviewShell>
      <div
        className="rounded-brand p-6"
        style={{
          backgroundImage: `linear-gradient(115deg,rgb(249_248_245/0.72),rgb(255_255_255/0.74),rgb(240_204_208/0.26)),url("${imageUrl}")`,
          backgroundPosition: "center top",
          backgroundSize: "cover",
        }}
      >
        <div className="max-w-md rounded-brand bg-white/78 p-5 shadow-sm ring-1 ring-champagne-beige/60">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-soft-brown">Store page</p>
          <h3 className="mt-3 font-heading text-4xl text-charcoal">Soft page surface</h3>
          <p className="mt-3 text-sm leading-6 text-soft-brown">The texture sits behind normal page content and color layers.</p>
        </div>
      </div>
    </PreviewShell>
  );
}

function PreviewShell({ children }: { children: ReactNode }) {
  return (
    <div className="mt-4 rounded-brand border border-champagne-beige bg-warm-ivory/70 p-3">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-soft-brown">Page preview</p>
      {children}
    </div>
  );
}
