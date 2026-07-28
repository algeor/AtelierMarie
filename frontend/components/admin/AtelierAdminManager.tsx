"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import {
  clearAboutItemImage,
  clearAboutSectionImage,
  createAboutItem,
  deleteAboutItem,
  getAdminAbout,
  reorderAboutItems,
  reorderAboutSections,
  setAboutItemPublished,
  setAboutSectionPublished,
  updateAboutItem,
  updateAboutSection,
  uploadAboutItemImage,
  uploadAboutSectionImage,
} from "@/lib/api";
import type { AboutItemAdmin, AboutSectionAdmin, CreateAboutItemRequest } from "@/lib/types";

const EMPTY_ITEM: CreateAboutItemRequest = {
  title_en: "",
  title_bg: "",
  text_en: "",
  text_bg: "",
  link_href: "",
};

export function AtelierAdminManager() {
  const [sections, setSections] = useState<AboutSectionAdmin[]>([]);
  const [drafts, setDrafts] = useState<AboutSectionAdmin[]>([]);
  const [newItems, setNewItems] = useState<Record<string, CreateAboutItemRequest>>({});
  const [error, setError] = useState<string | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);

  async function refresh() {
    const data = await getAdminAbout();
    setSections(data.sections);
    setDrafts(data.sections.map((section) => ({ ...section, items: section.items.map((item) => ({ ...item })) })));
  }

  useEffect(() => {
    refresh().catch(() => setError("Could not load atelier content."));
  }, []);

  function draftFor(slug: string) {
    return drafts.find((section) => section.slug === slug);
  }

  function updateSectionDraft(slug: string, field: keyof AboutSectionAdmin, value: string | boolean | null) {
    setDrafts((current) => current.map((section) => section.slug === slug ? { ...section, [field]: value } : section));
  }

  function updateItemDraft(slug: string, itemId: number, field: keyof AboutItemAdmin, value: string | boolean | null) {
    setDrafts((current) => current.map((section) => section.slug !== slug ? section : {
      ...section,
      items: section.items.map((item) => item.id === itemId ? { ...item, [field]: value } : item),
    }));
  }

  async function run(key: string, action: () => Promise<unknown>) {
    setBusyKey(key);
    setError(null);
    try {
      await action();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save atelier content.");
    } finally {
      setBusyKey(null);
    }
  }

  async function moveSection(slug: string, direction: -1 | 1) {
    const slugs = sections.map((section) => section.slug);
    const index = slugs.indexOf(slug);
    const next = index + direction;
    if (next < 0 || next >= slugs.length) return;
    [slugs[index], slugs[next]] = [slugs[next]!, slugs[index]!];
    await run(`section-order-${slug}`, () => reorderAboutSections(slugs));
  }

  async function moveItem(section: AboutSectionAdmin, itemId: number, direction: -1 | 1) {
    const ids = section.items.map((item) => item.id);
    const index = ids.indexOf(itemId);
    const next = index + direction;
    if (next < 0 || next >= ids.length) return;
    [ids[index], ids[next]] = [ids[next]!, ids[index]!];
    await run(`item-order-${itemId}`, () => reorderAboutItems(section.slug, ids));
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-heading text-2xl font-semibold text-charcoal">Atelier story</h1>
        <p className="mt-1 text-sm text-soft-brown">Edit bilingual copy, photos, order, and visibility.</p>
      </div>

      {error && <div className="rounded-brand border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      {sections.map((section, sectionIndex) => {
        const draft = draftFor(section.slug) ?? section;
        const newItem = newItems[section.slug] ?? EMPTY_ITEM;
        return (
          <article key={section.slug} className="rounded-brand border border-champagne-beige bg-cream p-5 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-champagne-beige pb-4">
              <div>
                <h2 className="font-heading text-xl text-charcoal">{section.heading_en}</h2>
                <p className="mt-1 font-mono text-xs text-soft-brown">{section.slug} · {section.type}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button type="button" variant="ghost" disabled={sectionIndex === 0} onClick={() => moveSection(section.slug, -1)}>↑</Button>
                <Button type="button" variant="ghost" disabled={sectionIndex === sections.length - 1} onClick={() => moveSection(section.slug, 1)}>↓</Button>
                <Button type="button" variant="secondary" onClick={() => run(`section-publish-${section.slug}`, () => setAboutSectionPublished(section.slug, !section.is_published))}>
                  {section.is_published ? "Hide" : "Publish"}
                </Button>
              </div>
            </div>

            <div className="mt-5 grid gap-4 lg:grid-cols-2">
              <Field label="Heading EN" value={draft.heading_en} onChange={(value) => updateSectionDraft(section.slug, "heading_en", value)} />
              <Field label="Heading BG" value={draft.heading_bg ?? ""} onChange={(value) => updateSectionDraft(section.slug, "heading_bg", value || null)} />
              <Field label="Subheading EN" value={draft.subheading_en ?? ""} onChange={(value) => updateSectionDraft(section.slug, "subheading_en", value || null)} />
              <Field label="Subheading BG" value={draft.subheading_bg ?? ""} onChange={(value) => updateSectionDraft(section.slug, "subheading_bg", value || null)} />
              <Area label="Body EN" value={draft.body_en ?? ""} onChange={(value) => updateSectionDraft(section.slug, "body_en", value || null)} />
              <Area label="Body BG" value={draft.body_bg ?? ""} onChange={(value) => updateSectionDraft(section.slug, "body_bg", value || null)} />
              <Field label="CTA label EN" value={draft.cta_label_en ?? ""} onChange={(value) => updateSectionDraft(section.slug, "cta_label_en", value || null)} />
              <Field label="CTA label BG" value={draft.cta_label_bg ?? ""} onChange={(value) => updateSectionDraft(section.slug, "cta_label_bg", value || null)} />
              <Field label="CTA href" value={draft.cta_href ?? ""} onChange={(value) => updateSectionDraft(section.slug, "cta_href", value || null)} />
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <Button type="button" isLoading={busyKey === `section-save-${section.slug}`} onClick={() => run(`section-save-${section.slug}`, () => updateAboutSection(section.slug, {
                heading_en: draft.heading_en,
                heading_bg: draft.heading_bg,
                subheading_en: draft.subheading_en,
                subheading_bg: draft.subheading_bg,
                body_en: draft.body_en,
                body_bg: draft.body_bg,
                cta_label_en: draft.cta_label_en,
                cta_label_bg: draft.cta_label_bg,
                cta_href: draft.cta_href,
              }))}>Save section</Button>
              <ImageControl
                image={section.image}
                onUpload={(file) => run(`section-image-${section.slug}`, () => uploadAboutSectionImage(section.slug, file))}
                onClear={() => run(`section-image-clear-${section.slug}`, () => clearAboutSectionImage(section.slug))}
              />
            </div>

            {section.items.length > 0 || ["cards", "timeline", "collections"].includes(section.type) ? (
              <div className="mt-6 border-t border-champagne-beige pt-5">
                <h3 className="text-sm font-semibold uppercase tracking-wide text-soft-brown">Items</h3>
                <div className="mt-4 space-y-4">
                  {draft.items.map((item, itemIndex) => (
                    <div key={item.id} className="rounded-brand border border-champagne-beige bg-warm-ivory p-4">
                      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                        <span className="font-mono text-xs text-soft-brown">#{item.id}</span>
                        <div className="flex flex-wrap gap-2">
                          <Button type="button" variant="ghost" disabled={itemIndex === 0} onClick={() => moveItem(section, item.id, -1)}>↑</Button>
                          <Button type="button" variant="ghost" disabled={itemIndex === section.items.length - 1} onClick={() => moveItem(section, item.id, 1)}>↓</Button>
                          <Button type="button" variant="secondary" onClick={() => run(`item-publish-${item.id}`, () => setAboutItemPublished(section.slug, item.id, !item.is_published))}>{item.is_published ? "Hide" : "Publish"}</Button>
                          <Button type="button" variant="ghost" onClick={() => run(`item-delete-${item.id}`, () => deleteAboutItem(section.slug, item.id))}>Delete</Button>
                        </div>
                      </div>
                      <div className="grid gap-3 lg:grid-cols-2">
                        <Field label="Title EN" value={item.title_en} onChange={(value) => updateItemDraft(section.slug, item.id, "title_en", value)} />
                        <Field label="Title BG" value={item.title_bg ?? ""} onChange={(value) => updateItemDraft(section.slug, item.id, "title_bg", value || null)} />
                        <Area label="Text EN" value={item.text_en ?? ""} onChange={(value) => updateItemDraft(section.slug, item.id, "text_en", value || null)} />
                        <Area label="Text BG" value={item.text_bg ?? ""} onChange={(value) => updateItemDraft(section.slug, item.id, "text_bg", value || null)} />
                        <Field label="Link href" value={item.link_href ?? ""} onChange={(value) => updateItemDraft(section.slug, item.id, "link_href", value || null)} />
                      </div>
                      <div className="mt-3 flex flex-wrap items-center gap-3">
                        <Button type="button" onClick={() => run(`item-save-${item.id}`, () => updateAboutItem(section.slug, item.id, item))}>Save item</Button>
                        <ImageControl image={item.image} onUpload={(file) => run(`item-image-${item.id}`, () => uploadAboutItemImage(section.slug, item.id, file))} onClear={() => run(`item-image-clear-${item.id}`, () => clearAboutItemImage(section.slug, item.id))} />
                      </div>
                    </div>
                  ))}
                </div>

                <div className="mt-4 rounded-brand border border-dashed border-muted-gold p-4">
                  <div className="grid gap-3 lg:grid-cols-2">
                    <Field label="New title EN" value={newItem.title_en} onChange={(value) => setNewItems((current) => ({ ...current, [section.slug]: { ...newItem, title_en: value } }))} />
                    <Field label="New title BG" value={newItem.title_bg ?? ""} onChange={(value) => setNewItems((current) => ({ ...current, [section.slug]: { ...newItem, title_bg: value } }))} />
                    <Area label="New text EN" value={newItem.text_en ?? ""} onChange={(value) => setNewItems((current) => ({ ...current, [section.slug]: { ...newItem, text_en: value } }))} />
                    <Area label="New text BG" value={newItem.text_bg ?? ""} onChange={(value) => setNewItems((current) => ({ ...current, [section.slug]: { ...newItem, text_bg: value } }))} />
                    <Field label="New link href" value={newItem.link_href ?? ""} onChange={(value) => setNewItems((current) => ({ ...current, [section.slug]: { ...newItem, link_href: value } }))} />
                  </div>
                  <Button type="button" className="mt-3" disabled={!newItem.title_en.trim()} onClick={() => run(`item-create-${section.slug}`, async () => {
                    await createAboutItem(section.slug, { ...newItem, title_bg: newItem.title_bg || null, text_en: newItem.text_en || null, text_bg: newItem.text_bg || null, link_href: newItem.link_href || null });
                    setNewItems((current) => ({ ...current, [section.slug]: EMPTY_ITEM }));
                  })}>Add item</Button>
                </div>
              </div>
            ) : null}
          </article>
        );
      })}
    </div>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block text-sm font-medium text-charcoal">
      {label}
      <input className="mt-1 w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm text-charcoal focus:border-muted-gold focus:outline-none" value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function Area({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block text-sm font-medium text-charcoal">
      {label}
      <textarea className="mt-1 min-h-32 w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm leading-6 text-charcoal focus:border-muted-gold focus:outline-none" value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function ImageControl({ image, onUpload, onClear }: { image: string | null; onUpload: (file: File) => void; onClear: () => void }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {image ? <img src={image} alt="" className="h-12 w-12 rounded-brand object-cover" /> : null}
      <label className="inline-flex min-h-10 cursor-pointer items-center rounded-brand border border-champagne-beige px-3 text-sm text-soft-brown hover:bg-champagne-beige/40">
        Upload
        <input type="file" accept="image/jpeg,image/png" className="sr-only" onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onUpload(file);
          event.target.value = "";
        }} />
      </label>
      {image ? <Button type="button" variant="ghost" onClick={onClear}>Clear image</Button> : null}
    </div>
  );
}
