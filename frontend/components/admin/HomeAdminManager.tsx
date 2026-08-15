"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AdminTranslationGapButton, MissingBgLabel, isMissingTranslation, type AdminTranslationGap } from "@/components/admin/AdminTranslationGaps";
import { SaveConfirmation } from "@/components/admin/SaveConfirmation";
import { Button } from "@/components/ui/Button";
import { DeleteIconButton } from "@/components/ui/DeleteIconButton";
import { Link } from "@/i18n/navigation";
import {
  clearHomeItemImage,
  clearHomeSectionImage,
  createHomeItem,
  deleteHomeItem,
  getAdminHome,
  reorderHomeItems,
  reorderHomeSections,
  setHomeItemPublished,
  setHomeSectionPublished,
  updateHomeItem,
  updateHomeSection,
  uploadHomeItemImage,
  uploadHomeSectionImage,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import type { CreateHomeItemRequest, HomeItemAdmin, HomeSectionAdmin } from "@/lib/types";

type EditorTab = "content" | "items" | "settings";

const EMPTY_ITEM: CreateHomeItemRequest = {
  title_en: "",
  title_bg: "",
  text_en: "",
  text_bg: "",
  link_href: "",
};

const ITEM_SECTION_TYPES = new Set<HomeSectionAdmin["type"]>(["cards", "timeline", "collections", "category_links"]);

const SECTION_TYPE_LABELS: Record<HomeSectionAdmin["type"], string> = {
  hero: "Hero",
  featured_products: "Featured products",
  text_image: "Story with image",
  text_band: "Text band",
  cards: "Cards",
  timeline: "Timeline",
  collections: "Collections",
  category_links: "Dynamic categories",
  cta_band: "CTA band",
};

function supportsSectionItems(section: HomeSectionAdmin) {
  return section.items.length > 0 || ITEM_SECTION_TYPES.has(section.type);
}

function isEditorTab(value: string | null): value is EditorTab {
  return value === "content" || value === "items" || value === "settings";
}

function homeItemPatch(item: HomeItemAdmin): CreateHomeItemRequest {
  return {
    title_en: item.title_en,
    title_bg: item.title_bg,
    text_en: item.text_en,
    text_bg: item.text_bg,
    link_href: item.link_href,
    is_published: item.is_published,
  };
}

export function HomeAdminManager() {
  const searchParams = useSearchParams();
  const [sections, setSections] = useState<HomeSectionAdmin[]>([]);
  const [drafts, setDrafts] = useState<HomeSectionAdmin[]>([]);
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<EditorTab>("content");
  const [editingItemId, setEditingItemId] = useState<number | null>(null);
  const [addingItemForSlug, setAddingItemForSlug] = useState<string | null>(null);
  const [newItems, setNewItems] = useState<Record<string, CreateHomeItemRequest>>({});
  const [error, setError] = useState<string | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [saveNotice, setSaveNotice] = useState<{ id: number; message: string } | null>(null);
  const saveNoticeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  async function refresh() {
    const data = await getAdminHome();
    setSections(data.sections);
    setDrafts(data.sections.map((section) => ({ ...section, items: section.items.map((item) => ({ ...item })) })));
  }

  useEffect(() => {
    refresh().catch((err) => {
      const detail = err instanceof Error ? err.message : "Unknown error";
      setError(`Could not load homepage content: ${detail}`);
    });
  }, []);

  useEffect(() => {
    if (sections.length === 0) return;
    const requestedSlug = searchParams?.get("section") ?? null;
    const requestedPart = searchParams?.get("part") ?? null;
    const requestedSection = requestedSlug ? sections.find((section) => section.slug === requestedSlug) : null;

    setSelectedSlug((current) => {
      if (requestedSection) return requestedSection.slug;
      if (!current || !sections.some((section) => section.slug === current)) return sections[0]!.slug;
      return current;
    });

    if (requestedSection && isEditorTab(requestedPart)) {
      setActiveTab(requestedPart === "items" && !supportsSectionItems(requestedSection) ? "content" : requestedPart);
    }
  }, [sections, searchParams]);

  useEffect(() => {
    return () => {
      if (saveNoticeTimerRef.current) clearTimeout(saveNoticeTimerRef.current);
    };
  }, []);

  const selectedSection = sections.find((section) => section.slug === selectedSlug) ?? sections[0] ?? null;
  const selectedDraft = selectedSection ? draftFor(selectedSection.slug) ?? selectedSection : null;
  const selectedIndex = selectedSection ? sections.findIndex((section) => section.slug === selectedSection.slug) : -1;
  const overview = useMemo(() => summarizeSections(drafts.length > 0 ? drafts : sections), [drafts, sections]);
  const allTranslationGaps = (drafts.length > 0 ? drafts : sections).flatMap((section) => translationGapsForSection(section, {
    onSectionField: () => selectPagePart(section.slug, "content"),
    onItemField: (itemId) => {
      setSelectedSlug(section.slug);
      setActiveTab("items");
      setEditingItemId(itemId);
      setAddingItemForSlug(null);
    },
  }));

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

  function selectPagePart(slug: string, tab: EditorTab) {
    setSelectedSlug(slug);
    setActiveTab(tab);
    setEditingItemId(null);
    setAddingItemForSlug(null);
  }

  function updateSectionDraft(slug: string, field: keyof HomeSectionAdmin, value: string | boolean | null) {
    setDrafts((current) => current.map((section) => section.slug === slug ? { ...section, [field]: value } : section));
  }

  function updateItemDraft(slug: string, itemId: number, field: keyof HomeItemAdmin, value: string | boolean | null) {
    setDrafts((current) => current.map((section) => section.slug !== slug ? section : {
      ...section,
      items: section.items.map((item) => item.id === itemId ? { ...item, [field]: value } : item),
    }));
  }

  function updateNewItem(slug: string, patch: Partial<CreateHomeItemRequest>) {
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
      setError(err instanceof Error ? err.message : "Could not save homepage content.");
    } finally {
      setBusyKey(null);
    }
  }

  async function moveSection(slug: string, direction: -1 | 1) {
    const current = sections.map((section) => section.slug);
    const index = current.indexOf(slug);
    const target = index + direction;
    if (index < 0 || target < 0 || target >= current.length) return;
    const next = [...current];
    [next[index], next[target]] = [next[target]!, next[index]!];
    await run(`section-order-${slug}`, () => reorderHomeSections(next));
  }

  async function moveItem(section: HomeSectionAdmin, itemId: number, direction: -1 | 1) {
    const current = section.items.map((item) => item.id);
    const index = current.indexOf(itemId);
    const target = index + direction;
    if (index < 0 || target < 0 || target >= current.length) return;
    const next = [...current];
    [next[index], next[target]] = [next[target]!, next[index]!];
    await run(`item-order-${itemId}`, () => reorderHomeItems(section.slug, next));
  }

  if (!selectedSection || !selectedDraft) {
    if (error) {
      return (
        <div className="rounded-brand border border-red-200 bg-red-50 p-4 text-sm leading-6 text-red-700">
          {error}
        </div>
      );
    }
    return <div className="rounded-brand border border-champagne-beige bg-admin-surface p-4 text-sm text-soft-brown">Loading homepage content...</div>;
  }

  return (
    <div className="space-y-6">
      <header className="rounded-brand border border-admin-border/50 bg-admin-surface p-4 shadow-sm sm:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-admin-muted">Homepage builder</p>
            <h1 className="mt-1 font-heading text-2xl font-semibold text-charcoal">Homepage</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-soft-brown">Edit public homepage sections, images, ordering, publish state, and translations.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/" className="inline-flex min-h-10 items-center justify-center rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm font-medium text-charcoal transition-colors hover:bg-champagne-beige/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2">View homepage</Link>
            <Link href="/admin/site-media" className="inline-flex min-h-10 items-center justify-center rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm font-medium text-charcoal transition-colors hover:bg-champagne-beige/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2">Site media</Link>
          </div>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          <OverviewTile label="Sections" value={`${overview.publishedSections}/${overview.totalSections}`} detail="published" />
          <OverviewTile label="Items" value={`${overview.publishedItems}/${overview.totalItems}`} detail="published" />
          <OverviewTile label="Translation gaps" value={<AdminTranslationGapButton gaps={allTranslationGaps} label="Homepage translation gaps" />} detail="need review" warning={overview.translationGaps > 0} />
        </div>
      </header>

      {error ? <div className="rounded-brand border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}
      {saveNotice ? <SaveConfirmation key={saveNotice.id} message={saveNotice.message} /> : null}

      <div className="grid gap-5 xl:grid-cols-[18rem_minmax(0,1fr)]">
        <aside className="hidden min-w-0 space-y-3 xl:sticky xl:top-24 xl:block xl:self-start">
          <div className="rounded-brand border border-admin-border/50 bg-admin-surface p-3 shadow-sm">
            <div className="mb-2 flex items-center justify-between gap-2">
              <h2 className="text-sm font-semibold text-charcoal">Page sections</h2>
              <span className="rounded-brand bg-admin-surface px-2 py-1 text-xs font-medium text-soft-brown">{sections.length} total</span>
            </div>
            <div className="space-y-2">
              {sections.map((section, index) => (
                <SectionCard key={section.slug} section={section} index={index} selected={section.slug === selectedSection.slug} onSelect={() => selectSection(section.slug)} />
              ))}
            </div>
          </div>
        </aside>

        <section className="min-w-0 overflow-hidden rounded-brand border border-admin-border/50 bg-admin-surface shadow-sm">
          <EditorHeader
            section={selectedDraft}
            activeTab={activeTab}
            index={selectedIndex}
            totalSections={sections.length}
            busyKey={busyKey}
            onAddItem={supportsSectionItems(selectedDraft) ? () => {
              setActiveTab("items");
              setAddingItemForSlug(selectedSection.slug);
            } : undefined}
            onMoveSection={(direction) => moveSection(selectedSection.slug, direction)}
            onToggleSection={() => run(`section-publish-${selectedSection.slug}`, () => setHomeSectionPublished(selectedSection.slug, !selectedSection.is_published))}
            onTabChange={setActiveTab}
          />

          <div className="p-4 sm:p-5">
            {activeTab === "content" ? (
              <ContentTab
                section={selectedSection}
                draft={selectedDraft}
                busyKey={busyKey}
                onSectionChange={updateSectionDraft}
                onSave={() => run(`section-save-${selectedSection.slug}`, () => updateHomeSection(selectedSection.slug, {
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
                onUploadImage={(file) => run(`section-image-${selectedSection.slug}`, () => uploadHomeSectionImage(selectedSection.slug, file))}
                onClearImage={() => run(`section-image-clear-${selectedSection.slug}`, () => clearHomeSectionImage(selectedSection.slug))}
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
                onToggleItem={(item) => run(`item-publish-${item.id}`, () => setHomeItemPublished(selectedSection.slug, item.id, !item.is_published))}
                onDeleteItem={(item) => run(`item-delete-${item.id}`, () => deleteHomeItem(selectedSection.slug, item.id))}
                onSaveItem={(item) => run(`item-save-${item.id}`, () => updateHomeItem(selectedSection.slug, item.id, homeItemPatch(item)))}
                onUploadItemImage={(item, file) => run(`item-image-${item.id}`, () => uploadHomeItemImage(selectedSection.slug, item.id, file))}
                onClearItemImage={(item) => run(`item-image-clear-${item.id}`, () => clearHomeItemImage(selectedSection.slug, item.id))}
                onCreateItem={() => run(`item-create-${selectedSection.slug}`, async () => {
                  const newItem = newItems[selectedSection.slug] ?? EMPTY_ITEM;
                  await createHomeItem(selectedSection.slug, {
                    title_en: newItem.title_en,
                    title_bg: newItem.title_bg || null,
                    text_en: newItem.text_en || null,
                    text_bg: newItem.text_bg || null,
                    link_href: newItem.link_href || null,
                    is_published: newItem.is_published ?? true,
                  });
                  setNewItems((current) => ({ ...current, [selectedSection.slug]: EMPTY_ITEM }));
                  setAddingItemForSlug(null);
                })}
              />
            ) : null}

            {activeTab === "settings" ? (
              <SettingsTab
                section={selectedSection}
                busyKey={busyKey}
                onMoveSection={(direction) => moveSection(selectedSection.slug, direction)}
                onToggleSection={() => run(`section-publish-${selectedSection.slug}`, () => setHomeSectionPublished(selectedSection.slug, !selectedSection.is_published))}
              />
            ) : null}
          </div>
        </section>
      </div>
    </div>
  );
}

function EditorHeader({ section, activeTab, index, totalSections, busyKey, onAddItem, onMoveSection, onToggleSection, onTabChange }: {
  section: HomeSectionAdmin;
  activeTab: EditorTab;
  index: number;
  totalSections: number;
  busyKey: string | null;
  onAddItem?: () => void;
  onMoveSection: (direction: -1 | 1) => void;
  onToggleSection: () => void;
  onTabChange: (tab: EditorTab) => void;
}) {
  return (
    <div className="border-b border-admin-border/40 p-4 sm:p-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge active={section.is_published} activeLabel="Published" inactiveLabel="Hidden" />
            <span className="rounded-brand bg-admin-surface-muted px-2 py-1 text-xs font-semibold text-soft-brown">{SECTION_TYPE_LABELS[section.type]}</span>
          </div>
          <h2 className="mt-2 break-words font-heading text-2xl text-charcoal">{section.heading_en || section.slug}</h2>
          <p className="mt-1 text-sm text-soft-brown">Order and visibility for this public homepage section.</p>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
          {onAddItem ? <Button type="button" size="sm" onClick={onAddItem}>Add item</Button> : null}
          <Button type="button" size="sm" variant="secondary" disabled={index <= 0} isLoading={busyKey === `section-order-${section.slug}`} onClick={() => onMoveSection(-1)}>Move up</Button>
          <Button type="button" size="sm" variant="secondary" disabled={index < 0 || index >= totalSections - 1} isLoading={busyKey === `section-order-${section.slug}`} onClick={() => onMoveSection(1)}>Move down</Button>
          <Button type="button" size="sm" variant="secondary" className="col-span-2" isLoading={busyKey === `section-publish-${section.slug}`} onClick={onToggleSection}>{section.is_published ? "Hide section" : "Publish section"}</Button>
        </div>
      </div>
      <div className="mt-4 flex gap-2 overflow-x-auto" role="tablist" aria-label="Homepage editor sections">
        <TabButton active={activeTab === "content"} onClick={() => onTabChange("content")}>Content</TabButton>
        <TabButton active={activeTab === "items"} onClick={() => onTabChange("items")} disabled={!supportsSectionItems(section)}>Items</TabButton>
        <TabButton active={activeTab === "settings"} onClick={() => onTabChange("settings")}>Visibility & order</TabButton>
      </div>
    </div>
  );
}

function ContentTab({ section, draft, busyKey, onSectionChange, onSave, onUploadImage, onClearImage }: {
  section: HomeSectionAdmin;
  draft: HomeSectionAdmin;
  busyKey: string | null;
  onSectionChange: (slug: string, field: keyof HomeSectionAdmin, value: string | boolean | null) => void;
  onSave: () => void;
  onUploadImage: (file: File) => void;
  onClearImage: () => void;
}) {
  return (
    <div className="space-y-5">
      <div className="grid gap-4 lg:grid-cols-2">
        <LanguagePanel title="English" detail="Primary customer copy">
          <Field id={homeSectionFieldId(section.slug, "heading-en")} label="Heading" value={draft.heading_en} onChange={(value) => onSectionChange(section.slug, "heading_en", value)} />
          <Field id={homeSectionFieldId(section.slug, "subheading-en")} label="Subheading" value={draft.subheading_en ?? ""} onChange={(value) => onSectionChange(section.slug, "subheading_en", value || null)} />
          <Area id={homeSectionFieldId(section.slug, "body-en")} label="Body" value={draft.body_en ?? ""} onChange={(value) => onSectionChange(section.slug, "body_en", value || null)} />
          <Field id={homeSectionFieldId(section.slug, "cta-label-en")} label="CTA label EN" value={draft.cta_label_en ?? ""} onChange={(value) => onSectionChange(section.slug, "cta_label_en", value || null)} />
        </LanguagePanel>
        <LanguagePanel title="Bulgarian" detail="Customer copy fallback uses English when empty">
          <Field id={homeSectionFieldId(section.slug, "heading-bg")} label={<>Heading<MissingBgLabel show={isMissingTranslation(draft.heading_en, draft.heading_bg)} /></>} value={draft.heading_bg ?? ""} onChange={(value) => onSectionChange(section.slug, "heading_bg", value || null)} />
          <Field id={homeSectionFieldId(section.slug, "subheading-bg")} label={<>Subheading<MissingBgLabel show={isMissingTranslation(draft.subheading_en, draft.subheading_bg)} /></>} value={draft.subheading_bg ?? ""} onChange={(value) => onSectionChange(section.slug, "subheading_bg", value || null)} />
          <Area id={homeSectionFieldId(section.slug, "body-bg")} label={<>Body<MissingBgLabel show={isMissingTranslation(draft.body_en, draft.body_bg)} /></>} value={draft.body_bg ?? ""} onChange={(value) => onSectionChange(section.slug, "body_bg", value || null)} />
          <Field id={homeSectionFieldId(section.slug, "cta-label-bg")} label={<>CTA label BG<MissingBgLabel show={isMissingTranslation(draft.cta_label_en, draft.cta_label_bg)} /></>} value={draft.cta_label_bg ?? ""} onChange={(value) => onSectionChange(section.slug, "cta_label_bg", value || null)} />
        </LanguagePanel>
      </div>
      <Field id={homeSectionFieldId(section.slug, "cta-href")} label="CTA href" value={draft.cta_href ?? ""} onChange={(value) => onSectionChange(section.slug, "cta_href", value || null)} />
      <MediaControls image={section.image} busy={busyKey === `section-image-${section.slug}` || busyKey === `section-image-clear-${section.slug}`} onUpload={onUploadImage} onClear={onClearImage} />
      <Button type="button" isLoading={busyKey === `section-save-${section.slug}`} onClick={onSave}>Save content</Button>
    </div>
  );
}

function ItemsTab({ section, draft, editingItemId, addingItemForSlug, newItem, busyKey, onEditItem, onAddItem, onCancelAdd, onItemChange, onNewItemChange, onMoveItem, onToggleItem, onDeleteItem, onSaveItem, onUploadItemImage, onClearItemImage, onCreateItem }: {
  section: HomeSectionAdmin;
  draft: HomeSectionAdmin;
  editingItemId: number | null;
  addingItemForSlug: string | null;
  newItem: CreateHomeItemRequest;
  busyKey: string | null;
  onEditItem: (id: number | null) => void;
  onAddItem: () => void;
  onCancelAdd: () => void;
  onItemChange: (slug: string, itemId: number, field: keyof HomeItemAdmin, value: string | boolean | null) => void;
  onNewItemChange: (patch: Partial<CreateHomeItemRequest>) => void;
  onMoveItem: (itemId: number, direction: -1 | 1) => void;
  onToggleItem: (item: HomeItemAdmin) => void;
  onDeleteItem: (item: HomeItemAdmin) => void;
  onSaveItem: (item: HomeItemAdmin) => void;
  onUploadItemImage: (item: HomeItemAdmin, file: File) => void;
  onClearItemImage: (item: HomeItemAdmin) => void;
  onCreateItem: () => void;
}) {
  if (!supportsSectionItems(draft)) {
    return <div className="rounded-brand border border-dashed border-muted-gold bg-admin-surface p-4 text-sm text-soft-brown">This section does not use child items.</div>;
  }
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="font-heading text-xl text-charcoal">Items</h3>
          <p className="mt-1 text-sm text-soft-brown">Add, edit, hide, reorder, and upload item images.</p>
        </div>
        <Button type="button" size="sm" onClick={onAddItem}>Add item</Button>
      </div>
      {addingItemForSlug === section.slug ? (
        <ItemEditor
          title="New item"
          values={newItem}
          busy={busyKey === `item-create-${section.slug}`}
          onChange={onNewItemChange}
          onSave={onCreateItem}
          onCancel={onCancelAdd}
        />
      ) : null}
      {draft.items.map((item, index) => {
        const editing = editingItemId === item.id;
        return (
          <article key={item.id} className="rounded-brand border border-champagne-beige bg-warm-ivory p-4">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-full bg-admin-surface px-2 py-1 text-xs font-semibold text-soft-brown">{String(index + 1).padStart(2, "0")}</span>
                  <StatusBadge active={item.is_published} activeLabel="Published" inactiveLabel="Hidden" />
                  <AdminTranslationGapButton gaps={itemTranslationGaps(section.slug, item, () => onEditItem(item.id))} label={`${item.title_en || `Item ${index + 1}`} translation gaps`} />
                </div>
                <h4 className="mt-2 break-words font-heading text-xl text-charcoal">{item.title_en}</h4>
                {item.text_en ? <p className="mt-1 line-clamp-2 text-sm leading-6 text-soft-brown">{item.text_en}</p> : null}
              </div>
              <div className="grid w-full grid-cols-2 gap-2 sm:flex sm:w-auto sm:flex-wrap">
                <Button type="button" size="sm" variant="ghost" disabled={index === 0} onClick={() => onMoveItem(item.id, -1)}>Move up</Button>
                <Button type="button" size="sm" variant="ghost" disabled={index === draft.items.length - 1} onClick={() => onMoveItem(item.id, 1)}>Move down</Button>
                <Button type="button" size="sm" variant="secondary" onClick={() => onToggleItem(item)}>{item.is_published ? "Hide" : "Publish"}</Button>
                <Button type="button" size="sm" variant={editing ? "secondary" : "primary"} onClick={() => onEditItem(editing ? null : item.id)}>{editing ? "Close" : "Edit"}</Button>
                <DeleteIconButton label="Delete item" onClick={() => onDeleteItem(item)} />
              </div>
            </div>
            {editing ? (
              <div className="mt-4 border-t border-champagne-beige pt-4">
                <ItemEditor
                  title="Edit item"
                  values={item}
                  busy={busyKey === `item-save-${item.id}`}
                  onChange={(patch) => Object.entries(patch).forEach(([key, value]) => onItemChange(section.slug, item.id, key as keyof HomeItemAdmin, value ?? null))}
                  onSave={() => onSaveItem(item)}
                  onCancel={() => onEditItem(null)}
                />
                <div className="mt-4">
                  <MediaControls image={item.image} busy={busyKey === `item-image-${item.id}` || busyKey === `item-image-clear-${item.id}`} onUpload={(file) => onUploadItemImage(item, file)} onClear={() => onClearItemImage(item)} />
                </div>
              </div>
            ) : null}
          </article>
        );
      })}
    </div>
  );
}

function ItemEditor({ title, values, busy, onChange, onSave, onCancel }: {
  title: string;
  values: CreateHomeItemRequest | HomeItemAdmin;
  busy: boolean;
  onChange: (patch: Partial<CreateHomeItemRequest>) => void;
  onSave: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="space-y-4 rounded-brand border border-champagne-beige bg-admin-surface p-4">
      <h4 className="font-heading text-lg text-charcoal">{title}</h4>
      <div className="grid gap-4 lg:grid-cols-2">
        <LanguagePanel title="English" detail="Primary item text">
          <Field id="home-item-title-en" label="Title" value={values.title_en ?? ""} onChange={(value) => onChange({ title_en: value })} />
          <Area id="home-item-text-en" label="Text" value={values.text_en ?? ""} onChange={(value) => onChange({ text_en: value || null })} />
        </LanguagePanel>
        <LanguagePanel title="Bulgarian" detail="Fallback uses English when empty">
          <Field id="home-item-title-bg" label={<>Title<MissingBgLabel show={isMissingTranslation(values.title_en, values.title_bg)} /></>} value={values.title_bg ?? ""} onChange={(value) => onChange({ title_bg: value || null })} />
          <Area id="home-item-text-bg" label={<>Text<MissingBgLabel show={isMissingTranslation(values.text_en, values.text_bg)} /></>} value={values.text_bg ?? ""} onChange={(value) => onChange({ text_bg: value || null })} />
        </LanguagePanel>
      </div>
      <Field id="home-item-link" label="Link href" value={values.link_href ?? ""} onChange={(value) => onChange({ link_href: value || null })} />
      <div className="flex flex-wrap gap-2">
        <Button type="button" isLoading={busy} onClick={onSave}>Save item</Button>
        <Button type="button" variant="secondary" onClick={onCancel}>Cancel</Button>
      </div>
    </div>
  );
}

function SettingsTab({ section, busyKey, onMoveSection, onToggleSection }: {
  section: HomeSectionAdmin;
  busyKey: string | null;
  onMoveSection: (direction: -1 | 1) => void;
  onToggleSection: () => void;
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="rounded-brand border border-champagne-beige bg-warm-ivory p-4">
        <h3 className="font-heading text-lg font-semibold text-charcoal">Visibility</h3>
        <p className="mt-1 text-sm leading-6 text-soft-brown">Hidden sections stay in admin, but customers do not see them on the homepage.</p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <StatusBadge active={section.is_published} activeLabel="Published" inactiveLabel="Hidden" />
          <Button type="button" variant="secondary" isLoading={busyKey === `section-publish-${section.slug}`} onClick={onToggleSection}>{section.is_published ? "Hide section" : "Publish section"}</Button>
        </div>
      </div>
      <div className="rounded-brand border border-champagne-beige bg-warm-ivory p-4">
        <h3 className="font-heading text-lg font-semibold text-charcoal">Order</h3>
        <p className="mt-1 text-sm leading-6 text-soft-brown">Move this section up or down in the public homepage flow.</p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button type="button" variant="secondary" onClick={() => onMoveSection(-1)}>Move up</Button>
          <Button type="button" variant="secondary" onClick={() => onMoveSection(1)}>Move down</Button>
        </div>
      </div>
    </div>
  );
}

function MediaControls({ image, busy, onUpload, onClear }: { image: string | null; busy: boolean; onUpload: (file: File) => void; onClear: () => void }) {
  return (
    <div className="rounded-brand border border-champagne-beige bg-warm-ivory p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="font-heading text-lg text-charcoal">Image</h3>
          <p className="mt-1 text-sm text-soft-brown">Upload a section or item image. Empty images fall back to Site media where supported.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <label className="inline-flex min-h-10 cursor-pointer items-center rounded-brand border border-champagne-beige px-3 text-sm text-soft-brown hover:bg-champagne-beige/40">
            Upload
            <input type="file" accept="image/png,image/jpeg,image/webp" className="sr-only" disabled={busy} onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) onUpload(file);
              event.currentTarget.value = "";
            }} />
          </label>
          <Button type="button" size="sm" variant="secondary" disabled={!image || busy} onClick={onClear}>Clear</Button>
        </div>
      </div>
      {image ? <img src={image} alt="" className="mt-3 aspect-[16/9] w-full max-w-md rounded-brand object-cover" /> : null}
    </div>
  );
}

function SectionCard({ section, index, selected, onSelect }: { section: HomeSectionAdmin; index: number; selected: boolean; onSelect: () => void }) {
  return (
    <button type="button" onClick={onSelect} className={cn("block w-full rounded-brand border p-3 text-left transition-colors", selected ? "border-admin-primary bg-warm-ivory shadow-sm" : "border-admin-border/45 bg-admin-surface hover:border-admin-accent")} aria-current={selected ? "true" : undefined}>
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-admin-surface-muted text-sm font-semibold text-charcoal">{String(index + 1).padStart(2, "0")}</span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-semibold text-charcoal">{section.heading_en || section.slug}</span>
          <span className="mt-1 block text-xs text-soft-brown">{SECTION_TYPE_LABELS[section.type]}</span>
        </span>
        <StatusBadge active={section.is_published} activeLabel="" inactiveLabel="" />
      </div>
    </button>
  );
}

function OverviewTile({ label, value, detail, warning = false }: { label: string; value: React.ReactNode; detail: string; warning?: boolean }) {
  return <div className={cn("rounded-brand border bg-warm-ivory p-3", warning ? "border-amber-200" : "border-champagne-beige")}><p className="text-xs font-semibold uppercase tracking-wide text-admin-muted">{label}</p><div className="mt-1 text-xl font-semibold text-charcoal">{value}</div><p className="mt-1 text-xs text-soft-brown">{detail}</p></div>;
}

function LanguagePanel({ title, detail, children }: { title: string; detail: string; children: React.ReactNode }) {
  return <div className="space-y-3 rounded-brand border border-champagne-beige bg-warm-ivory p-4"><div><h3 className="font-heading text-lg font-semibold text-charcoal">{title}</h3><p className="mt-1 text-xs text-soft-brown">{detail}</p></div>{children}</div>;
}

function Field({ id, label, value, onChange }: { id: string; label: React.ReactNode; value: string; onChange: (value: string) => void }) {
  return <label className="block text-sm font-medium text-charcoal" htmlFor={id}>{label}<input id={id} value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 h-10 w-full rounded-brand border border-champagne-beige bg-admin-surface px-3 text-sm text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown" /></label>;
}

function Area({ id, label, value, onChange }: { id: string; label: React.ReactNode; value: string; onChange: (value: string) => void }) {
  return <label className="block text-sm font-medium text-charcoal" htmlFor={id}>{label}<textarea id={id} value={value} rows={5} onChange={(event) => onChange(event.target.value)} className="mt-1 w-full rounded-brand border border-champagne-beige bg-admin-surface px-3 py-2 text-sm leading-6 text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown" /></label>;
}

function TabButton({ active, disabled, onClick, children }: { active: boolean; disabled?: boolean; onClick: () => void; children: React.ReactNode }) {
  return <button type="button" role="tab" aria-selected={active} disabled={disabled} onClick={onClick} className={cn("min-h-10 whitespace-nowrap rounded-brand px-3 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-admin-focus", active ? "bg-charcoal text-white" : "bg-warm-ivory text-soft-brown hover:bg-champagne-beige/50 hover:text-charcoal", disabled && "cursor-not-allowed opacity-50")}>{children}</button>;
}

function StatusBadge({ active, activeLabel, inactiveLabel }: { active: boolean; activeLabel: string; inactiveLabel: string }) {
  return <span className={cn("inline-flex min-h-6 items-center rounded-full px-2 py-1 text-xs font-semibold", active ? "bg-green-50 text-green-800" : "bg-amber-50 text-amber-800")}>{active ? activeLabel || "Published" : inactiveLabel || "Hidden"}</span>;
}

function homeSectionFieldId(slug: string, field: string) {
  return `home-section-${slug}-${field}`;
}

function summarizeSections(sections: HomeSectionAdmin[]) {
  return sections.reduce((summary, section) => {
    const gaps = translationGapsForSection(section).length;
    return {
      totalSections: summary.totalSections + 1,
      publishedSections: summary.publishedSections + (section.is_published ? 1 : 0),
      totalItems: summary.totalItems + section.items.length,
      publishedItems: summary.publishedItems + section.items.filter((item) => item.is_published).length,
      translationGaps: summary.translationGaps + gaps,
    };
  }, { totalSections: 0, publishedSections: 0, totalItems: 0, publishedItems: 0, translationGaps: 0 });
}

function translationGapsForSection(section: HomeSectionAdmin, options?: { onSectionField?: () => void; onItemField?: (itemId: number) => void }): AdminTranslationGap[] {
  const gaps: AdminTranslationGap[] = [];
  if (isMissingTranslation(section.heading_en, section.heading_bg)) gaps.push({ id: `home-section-${section.slug}-heading-bg`, fieldId: homeSectionFieldId(section.slug, "heading-bg"), label: `${section.heading_en} heading`, onFix: options?.onSectionField });
  if (isMissingTranslation(section.subheading_en, section.subheading_bg)) gaps.push({ id: `home-section-${section.slug}-subheading-bg`, fieldId: homeSectionFieldId(section.slug, "subheading-bg"), label: `${section.heading_en} subheading`, onFix: options?.onSectionField });
  if (isMissingTranslation(section.body_en, section.body_bg)) gaps.push({ id: `home-section-${section.slug}-body-bg`, fieldId: homeSectionFieldId(section.slug, "body-bg"), label: `${section.heading_en} body`, onFix: options?.onSectionField });
  if (isMissingTranslation(section.cta_label_en, section.cta_label_bg)) gaps.push({ id: `home-section-${section.slug}-cta-label-bg`, fieldId: homeSectionFieldId(section.slug, "cta-label-bg"), label: `${section.heading_en} CTA`, onFix: options?.onSectionField });
  for (const item of section.items) {
    gaps.push(...itemTranslationGaps(section.slug, item, () => options?.onItemField?.(item.id)));
  }
  return gaps;
}

function itemTranslationGaps(sectionSlug: string, item: HomeItemAdmin, onFix?: () => void): AdminTranslationGap[] {
  const gaps: AdminTranslationGap[] = [];
  if (isMissingTranslation(item.title_en, item.title_bg)) gaps.push({ id: `home-item-${sectionSlug}-${item.id}-title-bg`, fieldId: `home-item-${sectionSlug}-${item.id}-title-bg`, label: `${item.title_en} title`, onFix });
  if (isMissingTranslation(item.text_en, item.text_bg)) gaps.push({ id: `home-item-${sectionSlug}-${item.id}-text-bg`, fieldId: `home-item-${sectionSlug}-${item.id}-text-bg`, label: `${item.title_en} text`, onFix });
  return gaps;
}
