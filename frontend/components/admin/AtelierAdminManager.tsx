"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { SaveConfirmation } from "@/components/admin/SaveConfirmation";
import { Button } from "@/components/ui/Button";
import { DeleteIconButton } from "@/components/ui/DeleteIconButton";
import { Link } from "@/i18n/navigation";
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
import { cn } from "@/lib/utils";
import type { AboutItemAdmin, AboutSectionAdmin, CreateAboutItemRequest } from "@/lib/types";

type EditorTab = "content" | "items" | "settings";

const EMPTY_ITEM: CreateAboutItemRequest = {
  title_en: "",
  title_bg: "",
  text_en: "",
  text_bg: "",
  link_href: "",
};

const ITEM_SECTION_TYPES = new Set<AboutSectionAdmin["type"]>(["cards", "timeline", "collections"]);

const SECTION_TYPE_LABELS: Record<AboutSectionAdmin["type"], string> = {
  hero: "Hero",
  text_image: "Story with image",
  text_band: "Text band",
  cards: "Cards",
  timeline: "Timeline",
  collections: "Collections",
  cta_band: "CTA band",
};

export function AtelierAdminManager() {
  const [sections, setSections] = useState<AboutSectionAdmin[]>([]);
  const [drafts, setDrafts] = useState<AboutSectionAdmin[]>([]);
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<EditorTab>("content");
  const [editingItemId, setEditingItemId] = useState<number | null>(null);
  const [addingItemForSlug, setAddingItemForSlug] = useState<string | null>(null);
  const [newItems, setNewItems] = useState<Record<string, CreateAboutItemRequest>>({});
  const [error, setError] = useState<string | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [saveNotice, setSaveNotice] = useState<{ id: number; message: string } | null>(null);
  const saveNoticeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  async function refresh() {
    const data = await getAdminAbout();
    setSections(data.sections);
    setDrafts(data.sections.map((section) => ({ ...section, items: section.items.map((item) => ({ ...item })) })));
  }

  useEffect(() => {
    refresh().catch(() => setError("Could not load atelier content."));
  }, []);

  useEffect(() => {
    if (sections.length === 0) return;
    if (!selectedSlug || !sections.some((section) => section.slug === selectedSlug)) {
      setSelectedSlug(sections[0]!.slug);
    }
  }, [sections, selectedSlug]);

  useEffect(() => {
    return () => {
      if (saveNoticeTimerRef.current) clearTimeout(saveNoticeTimerRef.current);
    };
  }, []);

  const selectedSection = sections.find((section) => section.slug === selectedSlug) ?? sections[0] ?? null;
  const selectedDraft = selectedSection ? draftFor(selectedSection.slug) ?? selectedSection : null;
  const selectedIndex = selectedSection ? sections.findIndex((section) => section.slug === selectedSection.slug) : -1;
  const overview = useMemo(() => summarizeSections(drafts.length > 0 ? drafts : sections), [drafts, sections]);

  function showSaved(message = "Saved.") {
    if (saveNoticeTimerRef.current) clearTimeout(saveNoticeTimerRef.current);
    setSaveNotice((current) => ({ id: (current?.id ?? 0) + 1, message }));
    saveNoticeTimerRef.current = setTimeout(() => setSaveNotice(null), 3200);
  }

  function draftFor(slug: string) {
    return drafts.find((section) => section.slug === slug);
  }

  function selectSection(slug: string) {
    setSelectedSlug(slug);
    setActiveTab("content");
    setEditingItemId(null);
    setAddingItemForSlug(null);
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

  function updateNewItem(slug: string, patch: Partial<CreateAboutItemRequest>) {
    setNewItems((current) => ({
      ...current,
      [slug]: { ...EMPTY_ITEM, ...(current[slug] ?? {}), ...patch },
    }));
  }

  async function run(key: string, action: () => Promise<unknown>) {
    setBusyKey(key);
    setError(null);
    try {
      await action();
      await refresh();
      showSaved();
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

  if (sections.length === 0 && !error) {
    return <p className="text-sm text-soft-brown">Loading atelier content...</p>;
  }

  return (
    <div className="space-y-5">
      <header className="rounded-brand border border-admin-border/50 bg-admin-surface p-4 shadow-sm sm:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-wide text-admin-muted">Page builder</p>
            <h1 className="mt-1 font-heading text-2xl font-semibold text-charcoal">Atelier story</h1>
            <p className="mt-1 text-sm leading-6 text-soft-brown">
              Edit one public page section at a time. Keep English and Bulgarian copy aligned before publishing.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/atelier" className="inline-flex min-h-10 items-center justify-center rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm font-medium text-charcoal transition-colors hover:bg-champagne-beige/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2">
              Preview page
            </Link>
            <Link href="/admin/site-media" className="inline-flex min-h-10 items-center justify-center rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm font-medium text-charcoal transition-colors hover:bg-champagne-beige/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2">
              Edit media
            </Link>
          </div>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <OverviewTile label="Sections" value={`${overview.publishedSections}/${overview.totalSections}`} detail="published" />
          <OverviewTile label="Translation gaps" value={String(overview.translationGaps)} detail="need review" warning={overview.translationGaps > 0} />
          <OverviewTile label="Story items" value={String(overview.totalItems)} detail="cards and steps" />
          <OverviewTile label="Images" value={String(overview.imageCount)} detail="section or item photos" />
        </div>
      </header>

      {error && <div className="rounded-brand border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
      {saveNotice && <SaveConfirmation key={saveNotice.id} message={saveNotice.message} />}

      <div className="grid gap-5 xl:grid-cols-[21rem_minmax(0,1fr)]">
        <aside className="space-y-3 xl:sticky xl:top-24 xl:self-start">
          <div className="flex items-center justify-between gap-3">
            <h2 className="font-heading text-xl font-semibold text-charcoal">Page sections</h2>
            <span className="rounded-brand bg-admin-surface px-2 py-1 text-xs font-medium text-soft-brown">{sections.length} total</span>
          </div>
          <div className="space-y-2">
            {sections.map((section, index) => {
              const draft = draftFor(section.slug) ?? section;
              return (
                <SectionNavCard
                  key={section.slug}
                  section={draft}
                  index={index}
                  selected={selectedSection?.slug === section.slug}
                  onSelect={() => selectSection(section.slug)}
                />
              );
            })}
          </div>
        </aside>

        {selectedSection && selectedDraft ? (
          <section className="rounded-brand border border-admin-border/50 bg-admin-surface shadow-sm">
            <EditorHeader section={selectedDraft} activeTab={activeTab} onTabChange={setActiveTab} />

            <div className="p-4 sm:p-5">
              {activeTab === "content" ? (
                <ContentTab
                  section={selectedSection}
                  draft={selectedDraft}
                  busyKey={busyKey}
                  onSectionChange={updateSectionDraft}
                  onSave={() => run(`section-save-${selectedSection.slug}`, () => updateAboutSection(selectedSection.slug, {
                    heading_en: selectedDraft.heading_en,
                    heading_bg: selectedDraft.heading_bg,
                    subheading_en: selectedDraft.subheading_en,
                    subheading_bg: selectedDraft.subheading_bg,
                    body_en: selectedDraft.body_en,
                    body_bg: selectedDraft.body_bg,
                    cta_label_en: selectedDraft.cta_label_en,
                    cta_label_bg: selectedDraft.cta_label_bg,
                    cta_href: selectedDraft.cta_href,
                  }))}
                  onUploadImage={(file) => run(`section-image-${selectedSection.slug}`, () => uploadAboutSectionImage(selectedSection.slug, file))}
                  onClearImage={() => run(`section-image-clear-${selectedSection.slug}`, () => clearAboutSectionImage(selectedSection.slug))}
                />
              ) : null}

              {activeTab === "items" ? (
                <ItemsTab
                  section={selectedSection}
                  draft={selectedDraft}
                  editingItemId={editingItemId}
                  addingItemForSlug={addingItemForSlug}
                  newItem={newItems[selectedSection.slug] ?? EMPTY_ITEM}
                  busyKey={busyKey}
                  onEditItem={setEditingItemId}
                  onAddItem={() => setAddingItemForSlug(selectedSection.slug)}
                  onCancelAdd={() => setAddingItemForSlug(null)}
                  onItemChange={updateItemDraft}
                  onNewItemChange={(patch) => updateNewItem(selectedSection.slug, patch)}
                  onMoveItem={(itemId, direction) => moveItem(selectedSection, itemId, direction)}
                  onToggleItem={(item) => run(`item-publish-${item.id}`, () => setAboutItemPublished(selectedSection.slug, item.id, !item.is_published))}
                  onDeleteItem={(item) => run(`item-delete-${item.id}`, () => deleteAboutItem(selectedSection.slug, item.id))}
                  onSaveItem={(item) => run(`item-save-${item.id}`, () => updateAboutItem(selectedSection.slug, item.id, item))}
                  onUploadItemImage={(item, file) => run(`item-image-${item.id}`, () => uploadAboutItemImage(selectedSection.slug, item.id, file))}
                  onClearItemImage={(item) => run(`item-image-clear-${item.id}`, () => clearAboutItemImage(selectedSection.slug, item.id))}
                  onCreateItem={() => run(`item-create-${selectedSection.slug}`, async () => {
                    const newItem = newItems[selectedSection.slug] ?? EMPTY_ITEM;
                    await createAboutItem(selectedSection.slug, {
                      ...newItem,
                      title_bg: newItem.title_bg || null,
                      text_en: newItem.text_en || null,
                      text_bg: newItem.text_bg || null,
                      link_href: newItem.link_href || null,
                    });
                    setNewItems((current) => ({ ...current, [selectedSection.slug]: { ...EMPTY_ITEM } }));
                    setAddingItemForSlug(null);
                  })}
                />
              ) : null}

              {activeTab === "settings" ? (
                <SettingsTab
                  section={selectedSection}
                  index={selectedIndex}
                  totalSections={sections.length}
                  busyKey={busyKey}
                  onMoveSection={(direction) => moveSection(selectedSection.slug, direction)}
                  onToggleSection={() => run(`section-publish-${selectedSection.slug}`, () => setAboutSectionPublished(selectedSection.slug, !selectedSection.is_published))}
                />
              ) : null}
            </div>
          </section>
        ) : null}
      </div>
    </div>
  );
}

function OverviewTile({ label, value, detail, warning = false }: { label: string; value: string; detail: string; warning?: boolean }) {
  return (
    <div className="rounded-brand border border-champagne-beige bg-warm-ivory px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-soft-brown">{label}</p>
      <div className="mt-1 flex items-end gap-2">
        <span className={cn("font-heading text-2xl font-semibold", warning ? "text-amber-700" : "text-charcoal")}>{value}</span>
        <span className="pb-1 text-xs text-soft-brown">{detail}</span>
      </div>
    </div>
  );
}

function SectionNavCard({ section, index, selected, onSelect }: { section: AboutSectionAdmin; index: number; selected: boolean; onSelect: () => void }) {
  const translationGaps = translationGapCount(section);
  return (
    <article className={cn("rounded-brand border bg-admin-surface p-3 transition-colors", selected ? "border-admin-primary shadow-md" : "border-admin-border/45 hover:border-admin-accent")}>
      <button type="button" onClick={onSelect} className="block w-full text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-admin-focus focus-visible:ring-offset-2 focus-visible:ring-offset-admin-surface" aria-current={selected ? "true" : undefined}>
        <div className="flex items-start gap-3">
          <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-admin-surface-muted text-xs font-semibold text-charcoal">
            {String(index + 1).padStart(2, "0")}
          </span>
          <div className="min-w-0 flex-1">
            <h3 className="truncate font-heading text-lg text-charcoal">{section.heading_en || section.slug}</h3>
            <p className="mt-0.5 text-xs text-soft-brown">{SECTION_TYPE_LABELS[section.type]}</p>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <StatusBadge active={section.is_published} activeLabel="Published" inactiveLabel="Hidden" />
          <span className={cn("rounded-pill border px-2 py-1 text-xs font-semibold", translationGaps > 0 ? "border-amber-200 bg-amber-50 text-amber-700" : "border-green-200 bg-green-50 text-green-700")}>
            {translationGaps > 0 ? `${translationGaps} BG gap${translationGaps === 1 ? "" : "s"}` : "EN/BG ready"}
          </span>
          {section.items.length > 0 ? (
            <span className="rounded-pill border border-champagne-beige bg-warm-ivory px-2 py-1 text-xs font-semibold text-soft-brown">
              {section.items.length} item{section.items.length === 1 ? "" : "s"}
            </span>
          ) : null}
        </div>
      </button>
    </article>
  );
}

function EditorHeader({ section, activeTab, onTabChange }: { section: AboutSectionAdmin; activeTab: EditorTab; onTabChange: (tab: EditorTab) => void }) {
  return (
    <div className="border-b border-admin-border/40 p-4 sm:p-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-heading text-2xl font-semibold text-charcoal">{section.heading_en || section.slug}</h2>
            <StatusBadge active={section.is_published} activeLabel="Published" inactiveLabel="Hidden" />
          </div>
          <p className="mt-1 text-sm text-soft-brown">{SECTION_TYPE_LABELS[section.type]} section</p>
        </div>
        <div className="rounded-brand bg-admin-surface-muted px-3 py-2 text-xs text-soft-brown">{section.slug}</div>
      </div>
      <div className="mt-4 flex gap-2 overflow-x-auto" role="tablist" aria-label="Atelier editor sections">
        <TabButton active={activeTab === "content"} onClick={() => onTabChange("content")}>Content</TabButton>
        <TabButton active={activeTab === "items"} onClick={() => onTabChange("items")}>Items</TabButton>
        <TabButton active={activeTab === "settings"} onClick={() => onTabChange("settings")}>Visibility & order</TabButton>
      </div>
    </div>
  );
}

function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" role="tab" aria-selected={active} onClick={onClick} className={cn("min-h-10 whitespace-nowrap rounded-brand px-3 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-admin-focus focus-visible:ring-offset-2 focus-visible:ring-offset-admin-surface", active ? "bg-charcoal text-white" : "bg-warm-ivory text-soft-brown hover:bg-champagne-beige/50 hover:text-charcoal")}>
      {children}
    </button>
  );
}

function ContentTab({ section, draft, busyKey, onSectionChange, onSave, onUploadImage, onClearImage }: {
  section: AboutSectionAdmin;
  draft: AboutSectionAdmin;
  busyKey: string | null;
  onSectionChange: (slug: string, field: keyof AboutSectionAdmin, value: string | boolean | null) => void;
  onSave: () => void;
  onUploadImage: (file: File) => void;
  onClearImage: () => void;
}) {
  return (
    <div className="space-y-5">
      <div className="grid gap-4 lg:grid-cols-2">
        <LanguagePanel title="English" detail="Primary customer copy">
          <Field label="Heading" value={draft.heading_en} onChange={(value) => onSectionChange(section.slug, "heading_en", value)} />
          <Field label="Subheading" value={draft.subheading_en ?? ""} onChange={(value) => onSectionChange(section.slug, "subheading_en", value || null)} />
          <Area label="Body" value={draft.body_en ?? ""} onChange={(value) => onSectionChange(section.slug, "body_en", value || null)} />
        </LanguagePanel>

        <LanguagePanel title="Bulgarian" detail="Keep close to the English meaning">
          <Field label="Heading" value={draft.heading_bg ?? ""} onChange={(value) => onSectionChange(section.slug, "heading_bg", value || null)} />
          <Field label="Subheading" value={draft.subheading_bg ?? ""} onChange={(value) => onSectionChange(section.slug, "subheading_bg", value || null)} />
          <Area label="Body" value={draft.body_bg ?? ""} onChange={(value) => onSectionChange(section.slug, "body_bg", value || null)} />
        </LanguagePanel>
      </div>

      <div className="rounded-brand border border-champagne-beige bg-warm-ivory p-4">
        <h3 className="font-heading text-lg font-semibold text-charcoal">Call to action</h3>
        <div className="mt-3 grid gap-3 lg:grid-cols-3">
          <Field label="CTA label EN" value={draft.cta_label_en ?? ""} onChange={(value) => onSectionChange(section.slug, "cta_label_en", value || null)} />
          <Field label="CTA label BG" value={draft.cta_label_bg ?? ""} onChange={(value) => onSectionChange(section.slug, "cta_label_bg", value || null)} />
          <Field label="CTA href" value={draft.cta_href ?? ""} onChange={(value) => onSectionChange(section.slug, "cta_href", value || null)} />
        </div>
      </div>

      <div className="rounded-brand border border-champagne-beige bg-warm-ivory p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="font-heading text-lg font-semibold text-charcoal">Section image</h3>
            <p className="mt-1 text-sm text-soft-brown">Use this for section-specific photos. Shared fallback images live in Site media.</p>
          </div>
          <Link href="/admin/site-media" className="text-sm font-semibold text-charcoal underline underline-offset-4">Open media library</Link>
        </div>
        <div className="mt-3">
          <ImageControl image={section.image} onUpload={onUploadImage} onClear={onClearImage} />
        </div>
      </div>

      <div className="sticky bottom-3 z-10 flex flex-wrap items-center gap-3 rounded-brand border border-admin-border/50 bg-admin-surface/95 p-3 shadow-lg backdrop-blur sm:static sm:border-0 sm:bg-transparent sm:p-0 sm:shadow-none">
        <Button type="button" isLoading={busyKey === `section-save-${section.slug}`} onClick={onSave}>Save content</Button>
        <Link href="/atelier" className="inline-flex min-h-10 items-center justify-center rounded-brand border border-champagne-beige px-4 text-sm font-medium text-soft-brown hover:bg-champagne-beige/40">Preview page</Link>
      </div>
    </div>
  );
}

function ItemsTab({ section, draft, editingItemId, addingItemForSlug, newItem, busyKey, onEditItem, onAddItem, onCancelAdd, onItemChange, onNewItemChange, onMoveItem, onToggleItem, onDeleteItem, onSaveItem, onUploadItemImage, onClearItemImage, onCreateItem }: {
  section: AboutSectionAdmin;
  draft: AboutSectionAdmin;
  editingItemId: number | null;
  addingItemForSlug: string | null;
  newItem: CreateAboutItemRequest;
  busyKey: string | null;
  onEditItem: (itemId: number | null) => void;
  onAddItem: () => void;
  onCancelAdd: () => void;
  onItemChange: (slug: string, itemId: number, field: keyof AboutItemAdmin, value: string | boolean | null) => void;
  onNewItemChange: (patch: Partial<CreateAboutItemRequest>) => void;
  onMoveItem: (itemId: number, direction: -1 | 1) => void;
  onToggleItem: (item: AboutItemAdmin) => void;
  onDeleteItem: (item: AboutItemAdmin) => void;
  onSaveItem: (item: AboutItemAdmin) => void;
  onUploadItemImage: (item: AboutItemAdmin, file: File) => void;
  onClearItemImage: (item: AboutItemAdmin) => void;
  onCreateItem: () => void;
}) {
  const supportsItems = draft.items.length > 0 || ITEM_SECTION_TYPES.has(draft.type);

  if (!supportsItems) {
    return <div className="rounded-brand border border-dashed border-champagne-beige bg-warm-ivory p-5 text-sm leading-6 text-soft-brown">This section type does not use cards, collection links, or timeline steps.</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="font-heading text-xl font-semibold text-charcoal">Items</h3>
          <p className="text-sm text-soft-brown">Edit cards, timeline steps, or collection links one at a time.</p>
        </div>
        {addingItemForSlug !== section.slug ? <Button type="button" variant="secondary" onClick={onAddItem}>Add item</Button> : null}
      </div>

      {draft.items.length === 0 ? <div className="rounded-brand border border-dashed border-champagne-beige bg-warm-ivory p-5 text-sm text-soft-brown">No items yet.</div> : null}

      <div className="space-y-3">
        {draft.items.map((item, itemIndex) => {
          const editing = editingItemId === item.id;
          return (
            <article key={item.id} className="rounded-brand border border-champagne-beige bg-warm-ivory p-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full bg-admin-surface px-2 py-1 text-xs font-semibold text-soft-brown">{String(itemIndex + 1).padStart(2, "0")}</span>
                    <StatusBadge active={item.is_published} activeLabel="Published" inactiveLabel="Hidden" />
                  </div>
                  <h4 className="mt-2 font-heading text-xl text-charcoal">{item.title_en || `Item #${item.id}`}</h4>
                  {item.text_en ? <p className="mt-1 line-clamp-2 text-sm leading-6 text-soft-brown">{item.text_en}</p> : null}
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button type="button" variant="ghost" disabled={itemIndex === 0} onClick={() => onMoveItem(item.id, -1)}>Up</Button>
                  <Button type="button" variant="ghost" disabled={itemIndex === draft.items.length - 1} onClick={() => onMoveItem(item.id, 1)}>Down</Button>
                  <Button type="button" variant="secondary" onClick={() => onToggleItem(item)}>{item.is_published ? "Hide" : "Publish"}</Button>
                  <Button type="button" variant={editing ? "secondary" : "primary"} onClick={() => onEditItem(editing ? null : item.id)}>{editing ? "Close" : "Edit"}</Button>
                  <DeleteIconButton label={`Delete item #${item.id}`} onClick={() => onDeleteItem(item)} />
                </div>
              </div>

              {editing ? (
                <div className="mt-4 space-y-4 border-t border-champagne-beige pt-4">
                  <ItemFields item={item} onChange={(field, value) => onItemChange(section.slug, item.id, field, value)} />
                  <div className="flex flex-wrap items-center gap-3">
                    <Button type="button" isLoading={busyKey === `item-save-${item.id}`} onClick={() => onSaveItem(item)}>Save item</Button>
                    <ImageControl image={item.image} onUpload={(file) => onUploadItemImage(item, file)} onClear={() => onClearItemImage(item)} />
                  </div>
                </div>
              ) : null}
            </article>
          );
        })}
      </div>

      {addingItemForSlug === section.slug ? (
        <div className="rounded-brand border border-dashed border-muted-gold bg-admin-surface p-4">
          <div className="flex items-center justify-between gap-3">
            <h3 className="font-heading text-lg font-semibold text-charcoal">New item</h3>
            <Button type="button" variant="ghost" onClick={onCancelAdd}>Cancel</Button>
          </div>
          <div className="mt-4 grid gap-3 lg:grid-cols-2">
            <Field label="Title EN" value={newItem.title_en} onChange={(value) => onNewItemChange({ title_en: value })} />
            <Field label="Title BG" value={newItem.title_bg ?? ""} onChange={(value) => onNewItemChange({ title_bg: value })} />
            <Area label="Text EN" value={newItem.text_en ?? ""} onChange={(value) => onNewItemChange({ text_en: value })} />
            <Area label="Text BG" value={newItem.text_bg ?? ""} onChange={(value) => onNewItemChange({ text_bg: value })} />
            <Field label="Link href" value={newItem.link_href ?? ""} onChange={(value) => onNewItemChange({ link_href: value })} />
          </div>
          <Button type="button" className="mt-3" disabled={!newItem.title_en.trim()} onClick={onCreateItem}>Create item</Button>
        </div>
      ) : null}
    </div>
  );
}

function SettingsTab({ section, index, totalSections, busyKey, onMoveSection, onToggleSection }: {
  section: AboutSectionAdmin;
  index: number;
  totalSections: number;
  busyKey: string | null;
  onMoveSection: (direction: -1 | 1) => void;
  onToggleSection: () => void;
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="rounded-brand border border-champagne-beige bg-warm-ivory p-4">
        <h3 className="font-heading text-lg font-semibold text-charcoal">Visibility</h3>
        <p className="mt-1 text-sm leading-6 text-soft-brown">Hidden sections stay in the admin, but customers do not see them on the public Atelier page.</p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <StatusBadge active={section.is_published} activeLabel="Published" inactiveLabel="Hidden" />
          <Button type="button" variant="secondary" isLoading={busyKey === `section-publish-${section.slug}`} onClick={onToggleSection}>{section.is_published ? "Hide section" : "Publish section"}</Button>
        </div>
      </div>

      <div className="rounded-brand border border-champagne-beige bg-warm-ivory p-4">
        <h3 className="font-heading text-lg font-semibold text-charcoal">Order</h3>
        <p className="mt-1 text-sm leading-6 text-soft-brown">Move this section up or down in the public page flow.</p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button type="button" variant="secondary" disabled={index <= 0} isLoading={busyKey === `section-order-${section.slug}`} onClick={() => onMoveSection(-1)}>Move up</Button>
          <Button type="button" variant="secondary" disabled={index < 0 || index >= totalSections - 1} isLoading={busyKey === `section-order-${section.slug}`} onClick={() => onMoveSection(1)}>Move down</Button>
        </div>
      </div>

      <div className="rounded-brand border border-champagne-beige bg-warm-ivory p-4 lg:col-span-2">
        <h3 className="font-heading text-lg font-semibold text-charcoal">Details</h3>
        <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-3">
          <Detail term="Slug" value={section.slug} />
          <Detail term="Type" value={SECTION_TYPE_LABELS[section.type]} />
          <Detail term="Sort order" value={String(section.sort_order)} />
        </dl>
      </div>
    </div>
  );
}

function LanguagePanel({ title, detail, children }: { title: string; detail: string; children: React.ReactNode }) {
  return (
    <section className="rounded-brand border border-champagne-beige bg-warm-ivory p-4">
      <div className="mb-4">
        <h3 className="font-heading text-lg font-semibold text-charcoal">{title}</h3>
        <p className="mt-1 text-xs text-soft-brown">{detail}</p>
      </div>
      <div className="space-y-3">{children}</div>
    </section>
  );
}

function ItemFields({ item, onChange }: { item: AboutItemAdmin; onChange: (field: keyof AboutItemAdmin, value: string | boolean | null) => void }) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <LanguagePanel title="English" detail="Item text shown to customers">
        <Field label="Title" value={item.title_en} onChange={(value) => onChange("title_en", value)} />
        <Area label="Text" value={item.text_en ?? ""} onChange={(value) => onChange("text_en", value || null)} />
      </LanguagePanel>
      <LanguagePanel title="Bulgarian" detail="Matching translation">
        <Field label="Title" value={item.title_bg ?? ""} onChange={(value) => onChange("title_bg", value || null)} />
        <Area label="Text" value={item.text_bg ?? ""} onChange={(value) => onChange("text_bg", value || null)} />
      </LanguagePanel>
      <div className="lg:col-span-2">
        <Field label="Link href" value={item.link_href ?? ""} onChange={(value) => onChange("link_href", value || null)} />
      </div>
    </div>
  );
}

function Detail({ term, value }: { term: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase tracking-wide text-soft-brown">{term}</dt>
      <dd className="mt-1 break-words font-mono text-sm text-charcoal">{value}</dd>
    </div>
  );
}

function StatusBadge({ active, activeLabel, inactiveLabel }: { active: boolean; activeLabel: string; inactiveLabel: string }) {
  return (
    <span className={cn("rounded-pill border px-2 py-1 text-xs font-semibold", active ? "border-green-200 bg-green-50 text-green-700" : "border-red-200 bg-red-50 text-red-700")}>
      {active ? activeLabel : inactiveLabel}
    </span>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block text-sm font-medium text-charcoal">
      {label}
      <input className="mt-1 w-full rounded-brand border border-champagne-beige bg-admin-surface px-3 py-2 text-sm text-charcoal focus:border-muted-gold focus:outline-none focus:ring-2 focus:ring-muted-gold/20" value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function Area({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block text-sm font-medium text-charcoal">
      {label}
      <textarea className="mt-1 min-h-32 w-full rounded-brand border border-champagne-beige bg-admin-surface px-3 py-2 text-sm leading-6 text-charcoal focus:border-muted-gold focus:outline-none focus:ring-2 focus:ring-muted-gold/20" value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function ImageControl({ image, onUpload, onClear }: { image: string | null; onUpload: (file: File) => void; onClear: () => void }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {image ? <img src={image} alt="" className="h-14 w-14 rounded-brand border border-champagne-beige object-cover" /> : (
        <div className="flex h-14 w-14 items-center justify-center rounded-brand border border-dashed border-champagne-beige bg-admin-surface px-2 text-center text-[11px] leading-4 text-soft-brown">No image</div>
      )}
      <label className="inline-flex min-h-10 cursor-pointer items-center rounded-brand border border-champagne-beige bg-admin-surface px-3 text-sm font-medium text-soft-brown hover:bg-champagne-beige/40">
        Upload
        <input type="file" accept="image/jpeg,image/png" className="sr-only" onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) onUpload(file);
          event.target.value = "";
        }} />
      </label>
      {image ? <DeleteIconButton label="Clear image" onClick={onClear} /> : null}
    </div>
  );
}

function summarizeSections(sections: AboutSectionAdmin[]) {
  return sections.reduce(
    (summary, section) => ({
      totalSections: summary.totalSections + 1,
      publishedSections: summary.publishedSections + (section.is_published ? 1 : 0),
      translationGaps: summary.translationGaps + translationGapCount(section),
      totalItems: summary.totalItems + section.items.length,
      imageCount: summary.imageCount + (section.image ? 1 : 0) + section.items.filter((item) => item.image).length,
    }),
    { totalSections: 0, publishedSections: 0, translationGaps: 0, totalItems: 0, imageCount: 0 },
  );
}

function translationGapCount(section: AboutSectionAdmin) {
  let gaps = 0;
  if (isBlank(section.heading_bg)) gaps += 1;
  if (!isBlank(section.subheading_en) && isBlank(section.subheading_bg)) gaps += 1;
  if (!isBlank(section.body_en) && isBlank(section.body_bg)) gaps += 1;
  if (!isBlank(section.cta_label_en) && isBlank(section.cta_label_bg)) gaps += 1;
  section.items.forEach((item) => {
    if (isBlank(item.title_bg)) gaps += 1;
    if (!isBlank(item.text_en) && isBlank(item.text_bg)) gaps += 1;
  });
  return gaps;
}

function isBlank(value: string | null | undefined) {
  return !value || value.trim().length === 0;
}
