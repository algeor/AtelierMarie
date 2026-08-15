"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AdminMobileTargetSelect } from "@/components/admin/AdminMobileTargetSelect";
import { ImageCropEditor } from "@/components/admin/ImageCropEditor";
import { AdminTranslationGapButton, MissingBgLabel, isMissingTranslation, type AdminTranslationGap } from "@/components/admin/AdminTranslationGaps";
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
  getTaxonomy,
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
import type { AboutItemAdmin, AboutSectionAdmin, CreateAboutItemRequest, PatchAboutItemRequest, TaxonomyResponse, TaxonomyTerm } from "@/lib/types";

type EditorTab = "content" | "items" | "settings";
type ProductFilterKind = "product_type" | "category" | "labels";

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

const ITEM_LABELS: Partial<Record<AboutSectionAdmin["type"], { plural: string; singular: string }>> = {
  cards: { plural: "Cards", singular: "card" },
  timeline: { plural: "Timeline steps", singular: "step" },
  collections: { plural: "Collection links", singular: "link" },
};

function supportsSectionItems(section: AboutSectionAdmin) {
  return section.items.length > 0 || ITEM_SECTION_TYPES.has(section.type);
}

function isEditorTab(value: string | null): value is EditorTab {
  return value === "content" || value === "items" || value === "settings";
}

function cropAspectForSectionType(type: AboutSectionAdmin["type"]) {
  if (type === "hero") return 16 / 9;
  if (type === "collections") return 4 / 3;
  return 4 / 5;
}

function cropAspectForItemSectionType(type: AboutSectionAdmin["type"]) {
  if (type === "collections") return 4 / 3;
  return 4 / 5;
}

function aboutItemPatch(item: AboutItemAdmin): PatchAboutItemRequest {
  return {
    title_en: item.title_en,
    title_bg: item.title_bg,
    text_en: item.text_en,
    text_bg: item.text_bg,
    link_href: item.link_href,
    is_published: item.is_published,
  };
}

export function AtelierAdminManager() {
  const searchParams = useSearchParams();
  const [sections, setSections] = useState<AboutSectionAdmin[]>([]);
  const [drafts, setDrafts] = useState<AboutSectionAdmin[]>([]);
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<EditorTab>("content");
  const [editingItemId, setEditingItemId] = useState<number | null>(null);
  const [addingItemForSlug, setAddingItemForSlug] = useState<string | null>(null);
  const [newItems, setNewItems] = useState<Record<string, CreateAboutItemRequest>>({});
  const [taxonomy, setTaxonomy] = useState<TaxonomyResponse | null>(null);
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
    let cancelled = false;
    getTaxonomy()
      .then((data) => {
        if (!cancelled) setTaxonomy(data);
      })
      .catch(() => {
        if (!cancelled) setTaxonomy(null);
      });
    return () => {
      cancelled = true;
    };
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
  const mobileTargetValue = selectedSlug ? `${activeTab}:${selectedSlug}` : "";
  const mobileTargetOptions = (drafts.length > 0 ? drafts : sections).flatMap((section, index) => {
    const group = `${String(index + 1).padStart(2, "0")} · ${section.heading_en || section.slug}`;
    const visibility = section.is_published ? "Published" : "Hidden";
    const labels = ITEM_LABELS[section.type] ?? { plural: "Items", singular: "item" };
    return [
      {
        value: `content:${section.slug}`,
        label: "Content",
        group,
        description: `${SECTION_TYPE_LABELS[section.type]} · ${visibility}`,
      },
      ...(supportsSectionItems(section) ? [{
        value: `items:${section.slug}`,
        label: labels.plural,
        group,
        description: `${section.items.length} ${section.items.length === 1 ? labels.singular : labels.plural.toLowerCase()}`,
      }] : []),
      {
        value: `settings:${section.slug}`,
        label: "Visibility & order",
        group,
        description: `Sort ${section.sort_order} · ${visibility}`,
      },
    ];
  });

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

  function changeTab(tab: EditorTab) {
    if (tab === "items" && selectedDraft && !supportsSectionItems(selectedDraft)) {
      const itemSection = sections.find(supportsSectionItems);
      if (itemSection) setSelectedSlug(itemSection.slug);
    }
    setActiveTab(tab);
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

  function appendCreatedItem(slug: string, item: AboutItemAdmin) {
    setSections((current) => current.map((section) => section.slug === slug ? {
      ...section,
      items: [...section.items, item],
    } : section));
    setDrafts((current) => current.map((section) => section.slug === slug ? {
      ...section,
      items: [...section.items, item],
    } : section));
  }

  async function createItemForSection(section: AboutSectionAdmin) {
    const key = `item-create-${section.slug}`;
    setBusyKey(key);
    setError(null);
    try {
      const newItem = newItems[section.slug] ?? EMPTY_ITEM;
      const created = await createAboutItem(section.slug, {
        ...newItem,
        title_bg: newItem.title_bg || null,
        text_en: newItem.text_en || null,
        text_bg: newItem.text_bg || null,
        link_href: section.type === "collections" ? newItem.link_href || null : null,
      });
      appendCreatedItem(section.slug, created);
      setNewItems((current) => ({ ...current, [section.slug]: { ...EMPTY_ITEM } }));
      setAddingItemForSlug(null);
      showSaved();
      void refresh().catch(() => undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save atelier content.");
    } finally {
      setBusyKey(null);
    }
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
    <div className="min-w-0 space-y-5">
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
          <OverviewTile label="Translation gaps" value={<AdminTranslationGapButton gaps={allTranslationGaps} label="Atelier translation gaps" />} detail="need review" warning={overview.translationGaps > 0} />
          <OverviewTile label="Story items" value={String(overview.totalItems)} detail="cards and steps" />
          <OverviewTile label="Images" value={String(overview.imageCount)} detail="section or item photos" />
        </div>
      </header>

      {error && <div className="rounded-brand border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
      {saveNotice && <SaveConfirmation key={saveNotice.id} message={saveNotice.message} />}

      <div className="grid min-w-0 gap-5 xl:grid-cols-[21rem_minmax(0,1fr)]">
        <AdminMobileTargetSelect
          label="Page part"
          value={mobileTargetValue}
          onChange={(value) => {
            const [tab, slug] = value.split(":") as [EditorTab | undefined, string | undefined];
            if (!slug) return;
            selectPagePart(slug, tab ?? "content");
          }}
          options={mobileTargetOptions}
        />

        <aside className="hidden min-w-0 space-y-3 xl:sticky xl:top-24 xl:block xl:self-start">
          <div className="flex items-center justify-between gap-3">
            <h2 className="font-heading text-xl font-semibold text-charcoal">Page sections</h2>
            <span className="rounded-brand bg-admin-surface px-2 py-1 text-xs font-medium text-soft-brown">{sections.length} total</span>
          </div>
          <div className="space-y-2">
            {sections.map((section, index) => {
              const draft = draftFor(section.slug) ?? section;
              const gaps = translationGapsForSection(draft, {
                onSectionField: () => selectPagePart(section.slug, "content"),
                onItemField: (itemId) => {
                  setSelectedSlug(section.slug);
                  setActiveTab("items");
                  setEditingItemId(itemId);
                  setAddingItemForSlug(null);
                },
              });
              return (
                <SectionNavCard
                  key={section.slug}
                  section={draft}
                  index={index}
                  selected={selectedSection?.slug === section.slug}
                  activeTab={activeTab}
                  translationGaps={gaps}
                  onSelect={() => selectSection(section.slug)}
                  onSelectPart={(tab) => selectPagePart(section.slug, tab)}
                />
              );
            })}
          </div>
        </aside>

        {selectedSection && selectedDraft ? (
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
              onToggleSection={() => run(`section-publish-${selectedSection.slug}`, () => setAboutSectionPublished(selectedSection.slug, !selectedSection.is_published))}
              onTabChange={changeTab}
            />

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
                  taxonomy={taxonomy}
                  busyKey={busyKey}
                  onEditItem={setEditingItemId}
                  onAddItem={() => setAddingItemForSlug(selectedSection.slug)}
                  onCancelAdd={() => setAddingItemForSlug(null)}
                  onItemChange={updateItemDraft}
                  onNewItemChange={(patch) => updateNewItem(selectedSection.slug, patch)}
                  onMoveItem={(itemId, direction) => moveItem(selectedSection, itemId, direction)}
                  onToggleItem={(item) => run(`item-publish-${item.id}`, () => setAboutItemPublished(selectedSection.slug, item.id, !item.is_published))}
                  onDeleteItem={(item) => run(`item-delete-${item.id}`, () => deleteAboutItem(selectedSection.slug, item.id))}
                  onSaveItem={(item) => run(`item-save-${item.id}`, () => updateAboutItem(selectedSection.slug, item.id, aboutItemPatch(item)))}
                  onUploadItemImage={(item, file) => run(`item-image-${item.id}`, () => uploadAboutItemImage(selectedSection.slug, item.id, file))}
                  onClearItemImage={(item) => run(`item-image-clear-${item.id}`, () => clearAboutItemImage(selectedSection.slug, item.id))}
                  onCreateItem={() => void createItemForSection(selectedSection)}
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

function OverviewTile({ label, value, detail, warning = false }: { label: string; value: React.ReactNode; detail: string; warning?: boolean }) {
  return (
    <div className="rounded-brand border border-champagne-beige bg-warm-ivory px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-soft-brown">{label}</p>
      <div className="mt-1 flex items-end gap-2">
        <div className={cn("font-heading text-2xl font-semibold", warning ? "text-amber-700" : "text-charcoal")}>{value}</div>
        <span className="pb-1 text-xs text-soft-brown">{detail}</span>
      </div>
    </div>
  );
}

function SectionNavCard({ section, index, selected, activeTab, translationGaps, onSelect, onSelectPart }: {
  section: AboutSectionAdmin;
  index: number;
  selected: boolean;
  activeTab: EditorTab;
  translationGaps: AdminTranslationGap[];
  onSelect: () => void;
  onSelectPart: (tab: EditorTab) => void;
}) {
  const itemLabels = ITEM_LABELS[section.type] ?? { plural: "Items", singular: "item" };
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
      </button>
      <div className="mt-3 flex flex-wrap gap-2">
        <StatusBadge active={section.is_published} activeLabel="Published" inactiveLabel="Hidden" />
        <AdminTranslationGapButton gaps={translationGaps} label={`${section.heading_en || section.slug} translation gaps`} />
        {section.items.length > 0 ? (
          <span className="rounded-pill border border-champagne-beige bg-warm-ivory px-2 py-1 text-xs font-semibold text-soft-brown">
            {section.items.length} item{section.items.length === 1 ? "" : "s"}
          </span>
        ) : null}
      </div>
      <div className="mt-3 border-t border-admin-border/35 pt-3">
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-gold">Page parts</p>
        <div className="grid grid-cols-2 gap-2">
          <NavPartButton active={selected && activeTab === "content"} onClick={() => onSelectPart("content")}>Content</NavPartButton>
          {supportsSectionItems(section) ? (
            <NavPartButton active={selected && activeTab === "items"} onClick={() => onSelectPart("items")}>{itemLabels.plural}</NavPartButton>
          ) : null}
          <NavPartButton active={selected && activeTab === "settings"} onClick={() => onSelectPart("settings")}>Order</NavPartButton>
        </div>
      </div>
    </article>
  );
}

function NavPartButton({ active, children, onClick }: { active: boolean; children: string; onClick: () => void }) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={cn(
        "min-h-9 rounded-brand border px-2 py-1.5 text-xs font-semibold transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-admin-focus focus-visible:ring-offset-2 focus-visible:ring-offset-admin-surface",
        active
          ? "border-admin-primary bg-warm-ivory text-charcoal shadow-sm"
          : "border-champagne-beige bg-admin-surface-muted/55 text-soft-brown hover:border-admin-accent hover:bg-warm-ivory hover:text-charcoal",
      )}
    >
      {children}
    </button>
  );
}

function EditorHeader({ section, activeTab, index, totalSections, busyKey, onAddItem, onMoveSection, onToggleSection, onTabChange }: {
  section: AboutSectionAdmin;
  activeTab: EditorTab;
  index: number;
  totalSections: number;
  busyKey: string | null;
  onAddItem?: () => void;
  onMoveSection: (direction: -1 | 1) => void;
  onToggleSection: () => void;
  onTabChange: (tab: EditorTab) => void;
}) {
  const itemLabel = ITEM_LABELS[section.type]?.singular ?? "item";
  return (
    <div className="border-b border-admin-border/40 p-4 sm:p-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="min-w-0 break-words font-heading text-2xl font-semibold text-charcoal">{section.heading_en || section.slug}</h2>
            <StatusBadge active={section.is_published} activeLabel="Published" inactiveLabel="Hidden" />
          </div>
          <p className="mt-1 text-sm text-soft-brown">{SECTION_TYPE_LABELS[section.type]} section</p>
        </div>
        <div className="min-w-0 rounded-brand bg-admin-surface-muted px-3 py-2 text-xs text-soft-brown">
          <span className="break-words">{section.slug}</span>
        </div>
      </div>
      <div className="mt-4 flex flex-col gap-2 rounded-brand border border-admin-border/45 bg-admin-surface-muted/40 p-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
        <p className="min-w-0 text-sm text-soft-brown">Order and visibility for this public section.</p>
        <div className="grid grid-cols-2 gap-2 sm:flex sm:flex-wrap">
          {onAddItem ? <Button type="button" size="sm" onClick={onAddItem}>Add {itemLabel}</Button> : null}
          <Button type="button" size="sm" variant="secondary" disabled={index <= 0} isLoading={busyKey === `section-order-${section.slug}`} onClick={() => onMoveSection(-1)}>Move up</Button>
          <Button type="button" size="sm" variant="secondary" disabled={index < 0 || index >= totalSections - 1} isLoading={busyKey === `section-order-${section.slug}`} onClick={() => onMoveSection(1)}>Move down</Button>
          <Button type="button" size="sm" variant="secondary" className="col-span-2" isLoading={busyKey === `section-publish-${section.slug}`} onClick={onToggleSection}>{section.is_published ? "Hide section" : "Publish section"}</Button>
        </div>
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
          <Field id={aboutSectionFieldId(section.slug, "heading-bg")} label={<>Heading<MissingBgLabel show={isMissingTranslation(draft.heading_en, draft.heading_bg)} /></>} value={draft.heading_bg ?? ""} onChange={(value) => onSectionChange(section.slug, "heading_bg", value || null)} />
          <Field id={aboutSectionFieldId(section.slug, "subheading-bg")} label={<>Subheading<MissingBgLabel show={isMissingTranslation(draft.subheading_en, draft.subheading_bg)} /></>} value={draft.subheading_bg ?? ""} onChange={(value) => onSectionChange(section.slug, "subheading_bg", value || null)} />
          <Area id={aboutSectionFieldId(section.slug, "body-bg")} label={<>Body<MissingBgLabel show={isMissingTranslation(draft.body_en, draft.body_bg)} /></>} value={draft.body_bg ?? ""} onChange={(value) => onSectionChange(section.slug, "body_bg", value || null)} />
        </LanguagePanel>
      </div>

      <div className="rounded-brand border border-champagne-beige bg-warm-ivory p-4">
        <h3 className="font-heading text-lg font-semibold text-charcoal">Call to action</h3>
        <div className="mt-3 grid gap-3 lg:grid-cols-3">
          <Field label="CTA label EN" value={draft.cta_label_en ?? ""} onChange={(value) => onSectionChange(section.slug, "cta_label_en", value || null)} />
          <Field id={aboutSectionFieldId(section.slug, "cta-label-bg")} label={<>CTA label BG<MissingBgLabel show={isMissingTranslation(draft.cta_label_en, draft.cta_label_bg)} /></>} value={draft.cta_label_bg ?? ""} onChange={(value) => onSectionChange(section.slug, "cta_label_bg", value || null)} />
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
          <ImageControl image={section.image} aspect={cropAspectForSectionType(section.type)} title={`Adjust ${section.heading_en} image`} hint={`Drag to reposition, zoom, or rotate. The frame matches the ${section.heading_en} layout on the public Atelier page.`} onUpload={onUploadImage} onClear={onClearImage} />
        </div>
      </div>

      <div className="sticky bottom-3 z-10 flex flex-wrap items-center gap-3 rounded-brand border border-admin-border/50 bg-admin-surface/95 p-3 shadow-lg backdrop-blur sm:static sm:border-0 sm:bg-transparent sm:p-0 sm:shadow-none">
        <Button type="button" isLoading={busyKey === `section-save-${section.slug}`} onClick={onSave}>Save content</Button>
        <Link href="/atelier" className="inline-flex min-h-10 items-center justify-center rounded-brand border border-champagne-beige px-4 text-sm font-medium text-soft-brown hover:bg-champagne-beige/40">Preview page</Link>
      </div>
    </div>
  );
}

function ItemsTab({ section, draft, editingItemId, addingItemForSlug, newItem, taxonomy, busyKey, onEditItem, onAddItem, onCancelAdd, onItemChange, onNewItemChange, onMoveItem, onToggleItem, onDeleteItem, onSaveItem, onUploadItemImage, onClearItemImage, onCreateItem }: {
  section: AboutSectionAdmin;
  draft: AboutSectionAdmin;
  editingItemId: number | null;
  addingItemForSlug: string | null;
  newItem: CreateAboutItemRequest;
  taxonomy: TaxonomyResponse | null;
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
  const supportsItems = supportsSectionItems(draft);
  const labels = ITEM_LABELS[draft.type] ?? { plural: "Items", singular: "item" };

  if (!supportsItems) {
    return <div className="rounded-brand border border-dashed border-champagne-beige bg-warm-ivory p-5 text-sm leading-6 text-soft-brown">This section type does not use cards, collection links, or timeline steps.</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="font-heading text-xl font-semibold text-charcoal">{labels.plural}</h3>
          <p className="text-sm text-soft-brown">Edit {labels.plural.toLowerCase()} one at a time.</p>
        </div>
        {addingItemForSlug !== section.slug ? <Button type="button" variant="secondary" onClick={onAddItem}>Add {labels.singular}</Button> : null}
      </div>

      {draft.items.length === 0 ? <div className="rounded-brand border border-dashed border-champagne-beige bg-warm-ivory p-5 text-sm text-soft-brown">No {labels.plural.toLowerCase()} yet.</div> : null}

      <div className="space-y-3">
        {draft.items.map((item, itemIndex) => {
          const editing = editingItemId === item.id;
          return (
            <article key={item.id} className="rounded-brand border border-champagne-beige bg-warm-ivory p-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full bg-admin-surface px-2 py-1 text-xs font-semibold text-soft-brown">{String(itemIndex + 1).padStart(2, "0")}</span>
                    <StatusBadge active={item.is_published} activeLabel="Published" inactiveLabel="Hidden" />
                  </div>
                  <h4 className="mt-2 break-words font-heading text-xl text-charcoal">{item.title_en || `Item #${item.id}`}</h4>
                  {item.text_en ? <p className="mt-1 line-clamp-2 text-sm leading-6 text-soft-brown">{item.text_en}</p> : null}
                </div>
                <div className="grid w-full grid-cols-2 gap-2 sm:flex sm:w-auto sm:flex-wrap">
                  <Button type="button" size="sm" variant="ghost" disabled={itemIndex === 0} onClick={() => onMoveItem(item.id, -1)}>Up</Button>
                  <Button type="button" size="sm" variant="ghost" disabled={itemIndex === draft.items.length - 1} onClick={() => onMoveItem(item.id, 1)}>Down</Button>
                  <Button type="button" size="sm" variant="secondary" onClick={() => onToggleItem(item)}>{item.is_published ? "Hide" : "Publish"}</Button>
                  <Button type="button" size="sm" variant={editing ? "secondary" : "primary"} onClick={() => onEditItem(editing ? null : item.id)}>{editing ? "Close" : "Edit"}</Button>
                  <DeleteIconButton label={`Delete item #${item.id}`} onClick={() => onDeleteItem(item)} />
                </div>
              </div>

              {editing ? (
                <div className="mt-4 space-y-4 border-t border-champagne-beige pt-4">
                  <ItemFields sectionSlug={section.slug} sectionType={draft.type} item={item} taxonomy={taxonomy} onChange={(field, value) => onItemChange(section.slug, item.id, field, value)} />
                  <div className="flex flex-wrap items-center gap-3">
                    <Button type="button" isLoading={busyKey === `item-save-${item.id}`} onClick={() => onSaveItem(item)}>Save item</Button>
                    <ImageControl image={item.image} aspect={cropAspectForItemSectionType(draft.type)} title={`Adjust ${item.title_en || `Item #${item.id}`} image`} hint="Drag to reposition, zoom, or rotate. The frame matches the public item card preview." onUpload={(file) => onUploadItemImage(item, file)} onClear={() => onClearItemImage(item)} />
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
            <h3 className="font-heading text-lg font-semibold text-charcoal">New {labels.singular}</h3>
            <Button type="button" variant="ghost" onClick={onCancelAdd}>Cancel</Button>
          </div>
          <div className="mt-4 grid gap-3 lg:grid-cols-2">
            <Field label="Title EN" value={newItem.title_en} onChange={(value) => onNewItemChange({ title_en: value })} />
            <Field label="Title BG" value={newItem.title_bg ?? ""} onChange={(value) => onNewItemChange({ title_bg: value })} />
            <Area label="Text EN" value={newItem.text_en ?? ""} onChange={(value) => onNewItemChange({ text_en: value })} />
            <Area label="Text BG" value={newItem.text_bg ?? ""} onChange={(value) => onNewItemChange({ text_bg: value })} />
            {draft.type === "collections" ? (
              <div className="lg:col-span-2">
                <CollectionLinkFields linkHref={newItem.link_href ?? ""} taxonomy={taxonomy} onChange={(value) => onNewItemChange({ link_href: value })} />
              </div>
            ) : null}
          </div>
          <Button type="button" className="mt-3" disabled={!newItem.title_en.trim()} onClick={onCreateItem}>Create {labels.singular}</Button>
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

function ItemFields({ sectionSlug, sectionType, item, taxonomy, onChange }: {
  sectionSlug: string;
  sectionType: AboutSectionAdmin["type"];
  item: AboutItemAdmin;
  taxonomy: TaxonomyResponse | null;
  onChange: (field: keyof AboutItemAdmin, value: string | boolean | null) => void;
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <LanguagePanel title="English" detail="Item text shown to customers">
        <Field label="Title" value={item.title_en} onChange={(value) => onChange("title_en", value)} />
        <Area label="Text" value={item.text_en ?? ""} onChange={(value) => onChange("text_en", value || null)} />
      </LanguagePanel>
      <LanguagePanel title="Bulgarian" detail="Matching translation">
        <Field id={aboutItemFieldId(sectionSlug, item.id, "title-bg")} label={<>Title<MissingBgLabel show={isMissingTranslation(item.title_en, item.title_bg)} /></>} value={item.title_bg ?? ""} onChange={(value) => onChange("title_bg", value || null)} />
        <Area id={aboutItemFieldId(sectionSlug, item.id, "text-bg")} label={<>Text<MissingBgLabel show={isMissingTranslation(item.text_en, item.text_bg)} /></>} value={item.text_bg ?? ""} onChange={(value) => onChange("text_bg", value || null)} />
      </LanguagePanel>
      {sectionType === "collections" ? (
        <div className="lg:col-span-2">
          <CollectionLinkFields linkHref={item.link_href ?? ""} taxonomy={taxonomy} onChange={(value) => onChange("link_href", value || null)} />
        </div>
      ) : null}
    </div>
  );
}

function CollectionLinkFields({ linkHref, taxonomy, onChange }: { linkHref: string; taxonomy: TaxonomyResponse | null; onChange: (value: string) => void }) {
  const selectedTarget = selectedProductFilterValue(linkHref, taxonomy);
  const notice = collectionLinkNotice(linkHref, taxonomy);

  return (
    <div className="space-y-3">
      {taxonomy ? (
        <label className="block text-sm font-medium text-charcoal">
          Product filter target
          <select
            className="mt-1 w-full rounded-brand border border-champagne-beige bg-admin-surface px-3 py-2 text-sm text-charcoal focus:border-muted-gold focus:outline-none focus:ring-2 focus:ring-muted-gold/20"
            value={selectedTarget}
            onChange={(event) => {
              const href = hrefForProductFilterValue(event.target.value);
              if (href) onChange(href);
            }}
          >
            <option value="">Custom link</option>
            <TaxonomyOptionGroup label="Product types" kind="product_type" terms={taxonomy.product_types} />
            <TaxonomyOptionGroup label="Categories" kind="category" terms={taxonomy.categories} />
            <TaxonomyOptionGroup label="Labels" kind="labels" terms={taxonomy.labels} />
          </select>
        </label>
      ) : null}
      {notice ? <p className="rounded-brand border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-800">{notice}</p> : null}
      <Field label="Link href" value={linkHref} onChange={onChange} />
    </div>
  );
}

function TaxonomyOptionGroup({ label, kind, terms }: { label: string; kind: ProductFilterKind; terms: TaxonomyTerm[] }) {
  if (terms.length === 0) return null;
  return (
    <optgroup label={label}>
      {terms.map((term) => (
        <option key={`${kind}:${term.slug}`} value={`${kind}:${term.slug}`}>
          {term.name}
        </option>
      ))}
    </optgroup>
  );
}

function hrefForProductFilterValue(value: string) {
  const [kind, slug] = value.split(":") as [ProductFilterKind | undefined, string | undefined];
  if (!kind || !slug) return "";
  if (kind === "product_type") return `/products?type=${encodeURIComponent(slug)}`;
  if (kind === "category") return `/products?category=${encodeURIComponent(slug)}`;
  return `/products?labels=${encodeURIComponent(slug)}`;
}

function selectedProductFilterValue(linkHref: string, taxonomy: TaxonomyResponse | null) {
  if (!taxonomy) return "";
  const parsed = parseProductFilterHref(linkHref);
  if (!parsed || parsed.slugs.length !== 1) return "";
  const slug = parsed.slugs[0]!;
  if (parsed.kind === "product_type" && termExists(taxonomy.product_types, slug)) return `product_type:${slug}`;
  if (parsed.kind === "category" && termExists(taxonomy.categories, slug)) return `category:${slug}`;
  if (parsed.kind === "labels" && termExists(taxonomy.labels, slug)) return `labels:${slug}`;
  return "";
}

function collectionLinkNotice(linkHref: string, taxonomy: TaxonomyResponse | null) {
  if (!taxonomy || !linkHref.trim()) return null;
  const parsed = parseProductFilterHref(linkHref);
  if (!parsed) return null;
  const [firstSlug] = parsed.slugs;
  if (!firstSlug) return null;

  if (parsed.kind === "category" && !termExists(taxonomy.categories, firstSlug)) {
    if (termExists(taxonomy.labels, firstSlug)) {
      return `${firstSlug} is a product label. Use /products?labels=${firstSlug} so customers see that collection.`;
    }
    return `${firstSlug} is not an active product category.`;
  }

  if (parsed.kind === "labels") {
    const missing = parsed.slugs.filter((slug) => !termExists(taxonomy.labels, slug));
    return missing.length ? `${missing.join(", ")} ${missing.length === 1 ? "is" : "are"} not active product labels.` : null;
  }

  if (parsed.kind === "product_type" && !termExists(taxonomy.product_types, firstSlug)) {
    return `${firstSlug} is not an active product type.`;
  }

  return null;
}

function parseProductFilterHref(linkHref: string): { kind: ProductFilterKind; slugs: string[] } | null {
  const trimmed = linkHref.trim();
  if (!trimmed || /^[a-z][a-z\d+.-]*:/i.test(trimmed)) return null;

  try {
    const url = new URL(trimmed, "https://atelier.local");
    if (!url.pathname.endsWith("/products")) return null;

    const labels = [
      ...url.searchParams.getAll("label"),
      ...(url.searchParams.get("labels")?.split(",") ?? []),
    ].map((slug) => slug.trim()).filter(Boolean);
    if (labels.length) return { kind: "labels", slugs: Array.from(new Set(labels)) };

    const category = url.searchParams.get("category")?.trim();
    if (category) return { kind: "category", slugs: [category] };

    const productType = (url.searchParams.get("type") ?? url.searchParams.get("product_type"))?.trim();
    if (productType) return { kind: "product_type", slugs: [productType] };
  } catch {
    return null;
  }

  return null;
}

function termExists(terms: TaxonomyTerm[], slug: string) {
  return terms.some((term) => term.slug === slug);
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

function Field({ id, label, value, onChange }: { id?: string; label: React.ReactNode; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block text-sm font-medium text-charcoal">
      {label}
      <input id={id} className="mt-1 w-full rounded-brand border border-champagne-beige bg-admin-surface px-3 py-2 text-sm text-charcoal focus:border-muted-gold focus:outline-none focus:ring-2 focus:ring-muted-gold/20" value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function Area({ id, label, value, onChange }: { id?: string; label: React.ReactNode; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block text-sm font-medium text-charcoal">
      {label}
      <textarea id={id} className="mt-1 min-h-32 w-full rounded-brand border border-champagne-beige bg-admin-surface px-3 py-2 text-sm leading-6 text-charcoal focus:border-muted-gold focus:outline-none focus:ring-2 focus:ring-muted-gold/20" value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function ImageControl({ image, aspect = 4 / 5, title, hint, onUpload, onClear }: { image: string | null; aspect?: number; title?: string; hint?: string; onUpload: (file: File) => void; onClear: () => void }) {
  const [cropFile, setCropFile] = useState<File | null>(null);

  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        {image ? <img src={image} alt="" className="h-14 w-14 rounded-brand border border-champagne-beige object-cover" /> : (
          <div className="flex h-14 w-14 items-center justify-center rounded-brand border border-dashed border-champagne-beige bg-admin-surface px-2 text-center text-[11px] leading-4 text-soft-brown">No image</div>
        )}
        <label className="inline-flex min-h-10 cursor-pointer items-center rounded-brand border border-champagne-beige bg-admin-surface px-3 text-sm font-medium text-soft-brown hover:bg-champagne-beige/40">
          Upload
          <input type="file" accept="image/jpeg,image/png" className="sr-only" onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) setCropFile(file);
            event.target.value = "";
          }} />
        </label>
        {image ? <DeleteIconButton label="Clear image" onClick={onClear} /> : null}
      </div>
      {cropFile ? (
        <ImageCropEditor
          file={cropFile}
          aspect={aspect}
          title={title}
          hint={hint}
          onConfirm={(framedFile) => {
            setCropFile(null);
            onUpload(framedFile);
          }}
          onCancel={() => setCropFile(null)}
        />
      ) : null}
    </>
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
  return translationGapsForSection(section).length;
}

function translationGapsForSection(section: AboutSectionAdmin, actions?: {
  onSectionField?: () => void;
  onItemField?: (itemId: number) => void;
}): AdminTranslationGap[] {
  const title = section.heading_en || section.slug;
  const gaps: AdminTranslationGap[] = [];
  if (isMissingTranslation(section.heading_en, section.heading_bg)) {
    gaps.push({ id: `${section.slug}-heading-bg`, label: `${title} > Heading BG`, fieldId: aboutSectionFieldId(section.slug, "heading-bg"), onFix: actions?.onSectionField });
  }
  if (isMissingTranslation(section.subheading_en, section.subheading_bg)) {
    gaps.push({ id: `${section.slug}-subheading-bg`, label: `${title} > Subheading BG`, fieldId: aboutSectionFieldId(section.slug, "subheading-bg"), onFix: actions?.onSectionField });
  }
  if (isMissingTranslation(section.body_en, section.body_bg)) {
    gaps.push({ id: `${section.slug}-body-bg`, label: `${title} > Body BG`, fieldId: aboutSectionFieldId(section.slug, "body-bg"), onFix: actions?.onSectionField });
  }
  if (isMissingTranslation(section.cta_label_en, section.cta_label_bg)) {
    gaps.push({ id: `${section.slug}-cta-label-bg`, label: `${title} > CTA label BG`, fieldId: aboutSectionFieldId(section.slug, "cta-label-bg"), onFix: actions?.onSectionField });
  }
  section.items.forEach((item, index) => {
    const itemLabel = item.title_en || `Item ${index + 1}`;
    if (isMissingTranslation(item.title_en, item.title_bg)) {
      gaps.push({ id: `${section.slug}-item-${item.id}-title-bg`, label: `${title} > ${itemLabel} > Title BG`, fieldId: aboutItemFieldId(section.slug, item.id, "title-bg"), onFix: () => actions?.onItemField?.(item.id) });
    }
    if (isMissingTranslation(item.text_en, item.text_bg)) {
      gaps.push({ id: `${section.slug}-item-${item.id}-text-bg`, label: `${title} > ${itemLabel} > Text BG`, fieldId: aboutItemFieldId(section.slug, item.id, "text-bg"), onFix: () => actions?.onItemField?.(item.id) });
    }
  });
  return gaps;
}

function aboutSectionFieldId(slug: string, field: string) {
  return `about-${slug}-${field}`;
}

function aboutItemFieldId(slug: string, itemId: number, field: string) {
  return `about-${slug}-item-${itemId}-${field}`;
}

function isBlank(value: string | null | undefined) {
  return !value || value.trim().length === 0;
}
