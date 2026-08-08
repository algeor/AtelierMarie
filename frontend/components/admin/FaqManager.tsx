"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { AdminMobileTargetSelect } from "@/components/admin/AdminMobileTargetSelect";
import { AdminTranslationGapButton, MissingBgLabel, isMissingTranslation, type AdminTranslationGap } from "@/components/admin/AdminTranslationGaps";
import {
  createFaqItem,
  deleteFaqItem,
  getAdminFaq,
  reorderFaqItems,
  updateFaqItem,
  updateFaqSection,
} from "@/lib/api";
import { SaveConfirmation } from "@/components/admin/SaveConfirmation";
import { DeleteIconButton } from "@/components/ui/DeleteIconButton";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import type {
  FaqAdminResponse,
  FaqItemAdminResponse,
  FaqSectionAdminResponse,
} from "@/lib/types";

type Draft = {
  question_en: string;
  question_bg: string;
  answer_en: string;
  answer_bg: string;
};

type FaqTab = "questions" | "settings";

const EMPTY_DRAFT: Draft = {
  question_en: "",
  question_bg: "",
  answer_en: "",
  answer_bg: "",
};

function isFaqTab(value: string | null): value is FaqTab {
  return value === "questions" || value === "settings";
}

export function FaqManager() {
  const t = useTranslations("admin.faq");
  const tCommon = useTranslations("common");
  const searchParams = useSearchParams();
  const [faq, setFaq] = useState<FaqAdminResponse | null>(null);
  const [selectedSectionSlug, setSelectedSectionSlug] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<FaqTab>("questions");
  const [editingItemId, setEditingItemId] = useState<number | null>(null);
  const [addingForSection, setAddingForSection] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const [error, setError] = useState<string | null>(null);
  const [validation, setValidation] = useState<Record<string, string>>({});
  const [saveNotice, setSaveNotice] = useState<{ id: number; message: string } | null>(null);
  const saveNoticeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let cancelled = false;
    getAdminFaq()
      .then((data) => {
        if (cancelled) return;
        setFaq(data);
        setSelectedSectionSlug((current) => current ?? data.sections[0]?.slug ?? null);
      })
      .catch(() => {
        if (!cancelled) setError(t("loadError"));
      });
    return () => {
      cancelled = true;
    };
  }, [t]);

  useEffect(() => {
    return () => {
      if (saveNoticeTimerRef.current) clearTimeout(saveNoticeTimerRef.current);
    };
  }, []);

  useEffect(() => {
    if (!faq || faq.sections.length === 0) return;
    const requestedSlug = searchParams?.get("section") ?? null;
    const requestedPart = searchParams?.get("part") ?? null;
    const requestedSection = requestedSlug ? faq.sections.find((section) => section.slug === requestedSlug) : null;

    if (requestedSection) {
      setSelectedSectionSlug(requestedSection.slug);
      if (isFaqTab(requestedPart)) setActiveTab(requestedPart);
      return;
    }

    if (!selectedSectionSlug || !faq.sections.some((section) => section.slug === selectedSectionSlug)) {
      setSelectedSectionSlug(faq.sections[0]!.slug);
    }
  }, [faq, selectedSectionSlug, searchParams]);

  const selectedSection = faq?.sections.find((section) => section.slug === selectedSectionSlug) ?? faq?.sections[0] ?? null;
  const overview = useMemo(() => summarizeFaq(faq), [faq]);
  const allTranslationGaps = (faq?.sections ?? []).flatMap((section) => faqSectionTranslationGaps(section, {
    onSectionField: () => selectFaqPart(section.slug, "settings"),
    onItemField: (itemId) => {
      setSelectedSectionSlug(section.slug);
      setActiveTab("questions");
      setEditingItemId(itemId);
      setAddingForSection(null);
      setValidation({});
    },
  }));
  const mobileTargetValue = selectedSectionSlug ? `${activeTab}:${selectedSectionSlug}` : "";
  const mobileTargetOptions = (faq?.sections ?? []).flatMap((section) => {
    const group = `${section.icon ? `${section.icon} ` : ""}${section.title_en}`;
    const published = section.items.filter((item) => item.is_published).length;
    return [
      {
        value: `questions:${section.slug}`,
        label: "Questions",
        group,
        description: `${published}/${section.items.length} published`,
      },
      {
        value: `settings:${section.slug}`,
        label: "Section settings",
        group,
        description: section.slug,
      },
    ];
  });

  function showSaved(message = tCommon("saved")) {
    if (saveNoticeTimerRef.current) clearTimeout(saveNoticeTimerRef.current);
    setSaveNotice((current) => ({ id: (current?.id ?? 0) + 1, message }));
    saveNoticeTimerRef.current = setTimeout(() => setSaveNotice(null), 3200);
  }

  function selectSection(slug: string) {
    setSelectedSectionSlug(slug);
    setActiveTab("questions");
    setEditingItemId(null);
    setAddingForSection(null);
    setValidation({});
  }

  function selectFaqPart(slug: string, tab: FaqTab) {
    setSelectedSectionSlug(slug);
    setActiveTab(tab);
    setEditingItemId(null);
    setAddingForSection(null);
    setValidation({});
  }

  function replaceSection(section: FaqSectionAdminResponse) {
    setFaq((current) =>
      current
        ? {
            sections: current.sections.map((candidate) =>
              candidate.slug === section.slug ? section : candidate
            ),
          }
        : current
    );
  }

  function replaceItem(item: FaqItemAdminResponse) {
    setFaq((current) =>
      current
        ? {
            sections: current.sections.map((section) => ({
              ...section,
              items: section.items.map((candidate) =>
                candidate.id === item.id ? item : candidate
              ),
            })),
          }
        : current
    );
  }

  function updateItemField(itemId: number, field: keyof Draft, value: string) {
    setFaq((current) =>
      current
        ? {
            sections: current.sections.map((section) => ({
              ...section,
              items: section.items.map((item) =>
                item.id === itemId ? { ...item, [field]: value } : item
              ),
            })),
          }
        : current
    );
  }

  function updateSectionField(slug: string, field: "title_en" | "title_bg" | "icon", value: string) {
    setFaq((current) =>
      current
        ? {
            sections: current.sections.map((section) =>
              section.slug === slug ? { ...section, [field]: value } : section
            ),
          }
        : current
    );
  }

  async function saveSection(section: FaqSectionAdminResponse) {
    setError(null);
    try {
      replaceSection(
        await updateFaqSection(section.slug, {
          title_en: section.title_en,
          title_bg: section.title_bg || null,
          icon: section.icon || null,
          sort_order: section.sort_order,
        })
      );
      showSaved();
    } catch {
      setError(t("saveError"));
    }
  }

  async function saveItem(item: FaqItemAdminResponse) {
    const key = `item-${item.id}`;
    if (!item.question_en.trim()) {
      setValidation({ [key]: t("questionEnRequired") });
      return;
    }
    if (!item.answer_en.trim()) {
      setValidation({ [key]: t("answerEnRequired") });
      return;
    }
    setValidation({});
    setError(null);
    try {
      replaceItem(
        await updateFaqItem(item.id, {
          question_en: item.question_en,
          question_bg: item.question_bg || null,
          answer_en: item.answer_en,
          answer_bg: item.answer_bg || null,
          is_published: item.is_published,
          sort_order: item.sort_order,
        })
      );
      showSaved();
    } catch {
      setError(t("saveError"));
    }
  }

  async function togglePublished(item: FaqItemAdminResponse) {
    try {
      replaceItem(await updateFaqItem(item.id, { is_published: !item.is_published }));
      showSaved();
    } catch {
      setError(t("saveError"));
    }
  }

  async function removeItem(itemId: number) {
    setError(null);
    try {
      await deleteFaqItem(itemId);
      showSaved();
      setFaq((current) =>
        current
          ? {
              sections: current.sections.map((section) => ({
                ...section,
                items: section.items.filter((item) => item.id !== itemId),
              })),
            }
          : current
      );
      if (editingItemId === itemId) setEditingItemId(null);
    } catch {
      setError(t("saveError"));
    }
  }

  async function moveItem(section: FaqSectionAdminResponse, itemId: number, delta: -1 | 1) {
    const index = section.items.findIndex((item) => item.id === itemId);
    const nextIndex = index + delta;
    if (index < 0 || nextIndex < 0 || nextIndex >= section.items.length) return;
    const ordered = [...section.items];
    const [item] = ordered.splice(index, 1);
    ordered.splice(nextIndex, 0, item!);
    try {
      setFaq(await reorderFaqItems({ section: section.slug, ordered_ids: ordered.map((item) => item.id) }));
      showSaved();
    } catch {
      setError(t("saveError"));
    }
  }

  async function moveSection(slug: string, delta: -1 | 1) {
    if (!faq) return;
    const ordered = [...faq.sections].sort((a, b) => a.sort_order - b.sort_order || a.slug.localeCompare(b.slug));
    const index = ordered.findIndex((section) => section.slug === slug);
    const nextIndex = index + delta;
    if (index < 0 || nextIndex < 0 || nextIndex >= ordered.length) return;
    const [section] = ordered.splice(index, 1);
    ordered.splice(nextIndex, 0, section!);
    setError(null);
    try {
      await Promise.all(ordered.map((candidate, sortOrder) => updateFaqSection(candidate.slug, { sort_order: sortOrder })));
      setFaq({ sections: ordered.map((candidate, sort_order) => ({ ...candidate, sort_order })) });
      showSaved();
    } catch {
      setError(t("saveError"));
    }
  }

  async function createItem(sectionSlug: string) {
    const draft = drafts[sectionSlug] ?? EMPTY_DRAFT;
    const key = `new-${sectionSlug}`;
    if (!draft.question_en.trim()) {
      setValidation({ [key]: t("questionEnRequired") });
      return;
    }
    if (!draft.answer_en.trim()) {
      setValidation({ [key]: t("answerEnRequired") });
      return;
    }
    setValidation({});
    try {
      const item = await createFaqItem({
        section: sectionSlug,
        question_en: draft.question_en,
        question_bg: draft.question_bg || null,
        answer_en: draft.answer_en,
        answer_bg: draft.answer_bg || null,
      });
      setFaq((current) =>
        current
          ? {
              sections: current.sections.map((section) =>
                section.slug === sectionSlug
                  ? { ...section, items: [...section.items, item] }
                  : section
              ),
            }
          : current
      );
      setDrafts((current) => ({ ...current, [sectionSlug]: EMPTY_DRAFT }));
      setAddingForSection(null);
      setEditingItemId(item.id);
      showSaved();
    } catch {
      setError(t("saveError"));
    }
  }

  if (!faq && !error) return <p className="text-sm text-soft-brown">{t("loading")}</p>;

  return (
    <div className="min-w-0 space-y-5">
      <header className="rounded-brand border border-admin-border/50 bg-admin-surface p-4 shadow-sm sm:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-wide text-admin-muted">Question workspace</p>
            <h1 className="mt-1 font-heading text-2xl font-semibold text-charcoal">{t("title")}</h1>
            <p className="mt-1 text-sm leading-6 text-soft-brown">{t("subtitle")}</p>
          </div>
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <OverviewTile label="Sections" value={String(overview.sections)} detail="categories" />
          <OverviewTile label="Questions" value={String(overview.items)} detail="total" />
          <OverviewTile label="Published" value={`${overview.published}/${overview.items}`} detail="visible" />
          <OverviewTile label="Translation gaps" value={<AdminTranslationGapButton gaps={allTranslationGaps} label="FAQ translation gaps" />} detail="need review" warning={overview.translationGaps > 0} />
        </div>
      </header>

      {error && <p className="rounded-brand bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
      {saveNotice && <SaveConfirmation key={saveNotice.id} message={saveNotice.message} />}

      <div className="grid min-w-0 gap-5 xl:grid-cols-[21rem_minmax(0,1fr)]">
        <AdminMobileTargetSelect
          label="FAQ part"
          value={mobileTargetValue}
          onChange={(value) => {
            const [tab, slug] = value.split(":") as [FaqTab | undefined, string | undefined];
            if (!slug) return;
            selectFaqPart(slug, tab ?? "questions");
          }}
          options={mobileTargetOptions}
        />

        <aside className="hidden min-w-0 space-y-3 xl:sticky xl:top-24 xl:block xl:self-start">
          <div className="flex items-center justify-between gap-3">
            <h2 className="font-heading text-xl font-semibold text-charcoal">FAQ sections</h2>
            <span className="rounded-brand bg-admin-surface px-2 py-1 text-xs font-medium text-soft-brown">{faq?.sections.length ?? 0} total</span>
          </div>
          <div className="space-y-2">
            {faq?.sections.map((section, index) => {
              const gaps = faqSectionTranslationGaps(section, {
                onSectionField: () => selectFaqPart(section.slug, "settings"),
                onItemField: (itemId) => {
                  setSelectedSectionSlug(section.slug);
                  setActiveTab("questions");
                  setEditingItemId(itemId);
                  setAddingForSection(null);
                  setValidation({});
                },
              });
              return (
                <SectionNavCard
                  key={section.slug}
                  section={section}
                  index={index}
                  totalSections={faq.sections.length}
                  selected={selectedSection?.slug === section.slug}
                  activeTab={activeTab}
                  translationGaps={gaps}
                  onSelect={() => selectSection(section.slug)}
                  onSelectPart={(tab) => selectFaqPart(section.slug, tab)}
                  onMove={(delta) => moveSection(section.slug, delta)}
                />
              );
            })}
          </div>
        </aside>

        {selectedSection ? (
          <section className="min-w-0 overflow-hidden rounded-brand border border-admin-border/50 bg-admin-surface shadow-sm">
            <div className="border-b border-admin-border/40 p-4 sm:p-5">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    {selectedSection.icon ? <span className="text-xl" aria-hidden="true">{selectedSection.icon}</span> : null}
                    <h2 className="min-w-0 break-words font-heading text-2xl font-semibold text-charcoal">{selectedSection.title_en}</h2>
                  </div>
                  <p className="mt-1 text-sm text-soft-brown">{selectedSection.items.length} question{selectedSection.items.length === 1 ? "" : "s"}</p>
                </div>
                <span className="break-words rounded-brand bg-admin-surface-muted px-3 py-2 text-xs text-soft-brown">{selectedSection.slug}</span>
              </div>
              <div className="mt-4 flex gap-2 overflow-x-auto" role="tablist" aria-label="FAQ editor sections">
                <TabButton active={activeTab === "questions"} onClick={() => setActiveTab("questions")}>Questions</TabButton>
                <TabButton active={activeTab === "settings"} onClick={() => setActiveTab("settings")}>Section settings</TabButton>
              </div>
            </div>

            <div className="p-4 sm:p-5">
              {activeTab === "questions" ? (
                <QuestionsTab
                  section={selectedSection}
                  editingItemId={editingItemId}
                  addingForSection={addingForSection}
                  draft={drafts[selectedSection.slug] ?? EMPTY_DRAFT}
                  validation={validation}
                  onEditItem={setEditingItemId}
                  onAddItem={() => setAddingForSection(selectedSection.slug)}
                  onCancelAdd={() => {
                    setAddingForSection(null);
                    setValidation({});
                  }}
                  onChangeItem={updateItemField}
                  onChangeDraft={(field, value) =>
                    setDrafts((current) => ({
                      ...current,
                      [selectedSection.slug]: { ...(current[selectedSection.slug] ?? EMPTY_DRAFT), [field]: value },
                    }))
                  }
                  onSaveItem={saveItem}
                  onDeleteItem={removeItem}
                  onToggleItem={togglePublished}
                  onMoveItem={(itemId, delta) => moveItem(selectedSection, itemId, delta)}
                  onCreateItem={() => createItem(selectedSection.slug)}
                />
              ) : null}

              {activeTab === "settings" ? (
                <SettingsTab
                  section={selectedSection}
                  onSectionChange={updateSectionField}
                  onSaveSection={saveSection}
                />
              ) : null}
            </div>
          </section>
        ) : null}
      </div>
    </div>
  );
}

function QuestionsTab({
  section,
  editingItemId,
  addingForSection,
  draft,
  validation,
  onEditItem,
  onAddItem,
  onCancelAdd,
  onChangeItem,
  onChangeDraft,
  onSaveItem,
  onDeleteItem,
  onToggleItem,
  onMoveItem,
  onCreateItem,
}: {
  section: FaqSectionAdminResponse;
  editingItemId: number | null;
  addingForSection: string | null;
  draft: Draft;
  validation: Record<string, string>;
  onEditItem: (itemId: number | null) => void;
  onAddItem: () => void;
  onCancelAdd: () => void;
  onChangeItem: (itemId: number, field: keyof Draft, value: string) => void;
  onChangeDraft: (field: keyof Draft, value: string) => void;
  onSaveItem: (item: FaqItemAdminResponse) => void;
  onDeleteItem: (itemId: number) => void;
  onToggleItem: (item: FaqItemAdminResponse) => void;
  onMoveItem: (itemId: number, delta: -1 | 1) => void;
  onCreateItem: () => void;
}) {
  const t = useTranslations("admin.faq");

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <h3 className="font-heading text-xl font-semibold text-charcoal">Questions</h3>
          <p className="text-sm text-soft-brown">Open one question to edit its bilingual answer.</p>
        </div>
        {addingForSection !== section.slug ? <Button type="button" variant="secondary" onClick={onAddItem}>{t("newItem")}</Button> : null}
      </div>

      {section.items.length === 0 ? <p className="rounded-brand border border-dashed border-champagne-beige bg-warm-ivory p-4 text-sm text-soft-brown">{t("empty")}</p> : null}

      <div className="space-y-3">
        {section.items.map((item, index) => {
          const editing = editingItemId === item.id;
          return (
            <article key={item.id} className="rounded-brand border border-champagne-beige bg-warm-ivory p-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full bg-admin-surface px-2 py-1 text-xs font-semibold text-soft-brown">{String(index + 1).padStart(2, "0")}</span>
                    <StatusBadge active={item.is_published} activeLabel={t("published")} inactiveLabel={t("hidden")} />
                    <AdminTranslationGapButton
                      gaps={faqItemTranslationGaps(section.slug, item, { onItemField: () => onEditItem(item.id) })}
                      label={`${item.question_en || `Question ${index + 1}`} translation gaps`}
                    />
                  </div>
                  <h4 className="mt-2 break-words font-heading text-xl text-charcoal">{item.question_en}</h4>
                  <p className="mt-1 line-clamp-2 text-sm leading-6 text-soft-brown">{item.answer_en}</p>
                </div>
                <div className="grid w-full grid-cols-2 gap-2 sm:flex sm:w-auto sm:flex-wrap">
                  <Button type="button" size="sm" variant="ghost" disabled={index === 0} onClick={() => onMoveItem(item.id, -1)}>{t("moveUp")}</Button>
                  <Button type="button" size="sm" variant="ghost" disabled={index === section.items.length - 1} onClick={() => onMoveItem(item.id, 1)}>{t("moveDown")}</Button>
                  <Button type="button" size="sm" variant="secondary" onClick={() => onToggleItem(item)}>{item.is_published ? t("hide") : t("show")}</Button>
                  <Button type="button" size="sm" variant={editing ? "secondary" : "primary"} onClick={() => onEditItem(editing ? null : item.id)}>{editing ? "Close" : "Edit"}</Button>
                  <DeleteIconButton label={t("deleteItem")} onClick={() => onDeleteItem(item.id)} />
                </div>
              </div>

              {editing ? (
                <div className="mt-4 space-y-4 border-t border-champagne-beige pt-4">
                  <EditorFields
                    values={{
                      question_en: item.question_en,
                      question_bg: item.question_bg ?? "",
                      answer_en: item.answer_en,
                      answer_bg: item.answer_bg ?? "",
                    }}
                    fieldIds={{
                      question_bg: faqItemFieldId(section.slug, item.id, "question-bg"),
                      answer_bg: faqItemFieldId(section.slug, item.id, "answer-bg"),
                    }}
                    missing={{
                      question_bg: isMissingTranslation(item.question_en, item.question_bg),
                      answer_bg: isMissingTranslation(item.answer_en, item.answer_bg),
                    }}
                    onChange={(field, value) => onChangeItem(item.id, field, value)}
                  />
                  {validation[`item-${item.id}`] && <p className="text-sm text-red-700">{validation[`item-${item.id}`]}</p>}
                  <div className="sticky bottom-3 z-10 flex flex-wrap items-center gap-3 rounded-brand border border-admin-border/50 bg-admin-surface/95 p-3 shadow-lg backdrop-blur sm:static sm:border-0 sm:bg-transparent sm:p-0 sm:shadow-none">
                    <Button type="button" onClick={() => onSaveItem(item)}>{t("saveItem")}</Button>
                  </div>
                </div>
              ) : null}
            </article>
          );
        })}
      </div>

      {addingForSection === section.slug ? (
        <div className="rounded-brand border border-dashed border-muted-gold bg-admin-surface p-4">
          <div className="flex items-center justify-between gap-3">
            <h3 className="font-heading text-lg font-semibold text-charcoal">{t("newItem")}</h3>
            <Button type="button" variant="ghost" onClick={onCancelAdd}>Cancel</Button>
          </div>
          <div className="mt-4">
            <EditorFields values={draft} onChange={onChangeDraft} />
          </div>
          {validation[`new-${section.slug}`] && <p className="mt-2 text-sm text-red-700">{validation[`new-${section.slug}`]}</p>}
          <Button type="button" className="mt-3" onClick={onCreateItem}>{t("createItem")}</Button>
        </div>
      ) : null}
    </div>
  );
}

function SettingsTab({ section, onSectionChange, onSaveSection }: {
  section: FaqSectionAdminResponse;
  onSectionChange: (slug: string, field: "title_en" | "title_bg" | "icon", value: string) => void;
  onSaveSection: (section: FaqSectionAdminResponse) => void;
}) {
  const t = useTranslations("admin.faq");
  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-[1fr_1fr_8rem]">
        <TextInput label={t("titleEn")} value={section.title_en} onChange={(value) => onSectionChange(section.slug, "title_en", value)} />
        <TextInput id={faqSectionFieldId(section.slug, "title-bg")} label={<>{t("titleBg")}<MissingBgLabel show={isMissingTranslation(section.title_en, section.title_bg)} /></>} value={section.title_bg ?? ""} onChange={(value) => onSectionChange(section.slug, "title_bg", value)} />
        <TextInput label={t("icon")} value={section.icon ?? ""} onChange={(value) => onSectionChange(section.slug, "icon", value)} />
      </div>
      <div className="sticky bottom-3 z-10 flex flex-wrap items-center gap-3 rounded-brand border border-admin-border/50 bg-admin-surface/95 p-3 shadow-lg backdrop-blur sm:static sm:border-0 sm:bg-transparent sm:p-0 sm:shadow-none">
        <Button type="button" onClick={() => onSaveSection(section)}>{t("saveSection")}</Button>
      </div>
    </div>
  );
}

function SectionNavCard({ section, index, totalSections, selected, activeTab, translationGaps, onSelect, onSelectPart, onMove }: {
  section: FaqSectionAdminResponse;
  index: number;
  totalSections: number;
  selected: boolean;
  activeTab: FaqTab;
  translationGaps: AdminTranslationGap[];
  onSelect: () => void;
  onSelectPart: (tab: FaqTab) => void;
  onMove: (delta: -1 | 1) => void;
}) {
  const published = section.items.filter((item) => item.is_published).length;
  return (
    <article className={cn("rounded-brand border bg-admin-surface p-3 transition-colors", selected ? "border-admin-primary shadow-md" : "border-admin-border/45 hover:border-admin-accent")}>
      <button type="button" onClick={onSelect} className="block w-full min-w-0 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-admin-focus focus-visible:ring-offset-2 focus-visible:ring-offset-admin-surface" aria-current={selected ? "true" : undefined}>
        <div className="flex items-start gap-3">
          <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-admin-surface-muted text-sm font-semibold text-charcoal">{section.icon || "?"}</span>
          <div className="min-w-0 flex-1">
            <h3 className="truncate font-heading text-lg text-charcoal">{section.title_en}</h3>
            <p className="mt-0.5 text-xs text-soft-brown">{published}/{section.items.length} published</p>
          </div>
        </div>
      </button>
      <div className="mt-3 flex flex-wrap gap-2">
        <span className="rounded-pill border border-champagne-beige bg-warm-ivory px-2 py-1 text-xs font-semibold text-soft-brown">
          {section.items.length} question{section.items.length === 1 ? "" : "s"}
        </span>
        <AdminTranslationGapButton gaps={translationGaps} label={`${section.title_en} translation gaps`} />
      </div>
      <div className="mt-3 border-t border-admin-border/35 pt-3">
        <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted-gold">FAQ parts</p>
        <div className="grid grid-cols-2 gap-2">
          <NavPartButton active={selected && activeTab === "questions"} onClick={() => onSelectPart("questions")}>Questions</NavPartButton>
          <NavPartButton active={selected && activeTab === "settings"} onClick={() => onSelectPart("settings")}>Settings</NavPartButton>
        </div>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2">
        <Button type="button" size="sm" variant="secondary" disabled={index === 0} onClick={() => onMove(-1)}>Move up</Button>
        <Button type="button" size="sm" variant="secondary" disabled={index >= totalSections - 1} onClick={() => onMove(1)}>Move down</Button>
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

function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" role="tab" aria-selected={active} onClick={onClick} className={cn("min-h-10 whitespace-nowrap rounded-brand px-3 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-admin-focus focus-visible:ring-offset-2 focus-visible:ring-offset-admin-surface", active ? "bg-charcoal text-white" : "bg-warm-ivory text-soft-brown hover:bg-champagne-beige/50 hover:text-charcoal")}>
      {children}
    </button>
  );
}

function StatusBadge({ active, activeLabel, inactiveLabel }: { active: boolean; activeLabel: string; inactiveLabel: string }) {
  return (
    <span className={cn("rounded-pill border px-2 py-1 text-xs font-semibold", active ? "border-green-200 bg-green-50 text-green-700" : "border-red-200 bg-red-50 text-red-700")}>
      {active ? activeLabel : inactiveLabel}
    </span>
  );
}

function EditorFields({ values, fieldIds = {}, missing = {}, onChange }: {
  values: Draft;
  fieldIds?: Partial<Record<keyof Draft, string>>;
  missing?: Partial<Record<keyof Draft, boolean>>;
  onChange: (field: keyof Draft, value: string) => void;
}) {
  const t = useTranslations("admin.faq");
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="space-y-3 rounded-brand border border-champagne-beige bg-admin-surface p-4">
        <h4 className="text-sm font-semibold uppercase tracking-wide text-muted-gold">English</h4>
        <TextInput label={t("questionEn")} value={values.question_en} onChange={(value) => onChange("question_en", value)} />
        <TextArea label={t("answerEn")} value={values.answer_en} rows={5} onChange={(value) => onChange("answer_en", value)} />
      </div>
      <div className="space-y-3 rounded-brand border border-champagne-beige bg-admin-surface p-4">
        <h4 className="text-sm font-semibold uppercase tracking-wide text-muted-gold">Bulgarian</h4>
        <TextInput id={fieldIds.question_bg} label={<>{t("questionBg")}<MissingBgLabel show={Boolean(missing.question_bg)} /></>} value={values.question_bg} onChange={(value) => onChange("question_bg", value)} />
        <TextArea id={fieldIds.answer_bg} label={<>{t("answerBg")}<MissingBgLabel show={Boolean(missing.answer_bg)} /></>} value={values.answer_bg} rows={5} onChange={(value) => onChange("answer_bg", value)} />
      </div>
    </div>
  );
}

function TextInput({ id, label, value, onChange }: { id?: string; label: React.ReactNode; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block text-sm font-medium text-charcoal">
      {label}
      <input id={id} value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 h-10 w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm text-charcoal focus:border-muted-gold focus:outline-none focus:ring-2 focus:ring-muted-gold/20" />
    </label>
  );
}

function TextArea({ id, label, value, rows, onChange }: { id?: string; label: React.ReactNode; value: string; rows: number; onChange: (value: string) => void }) {
  return (
    <label className="block text-sm font-medium text-charcoal">
      {label}
      <textarea id={id} value={value} rows={rows} onChange={(event) => onChange(event.target.value)} className="mt-1 w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm leading-6 text-charcoal focus:border-muted-gold focus:outline-none focus:ring-2 focus:ring-muted-gold/20" />
    </label>
  );
}

function summarizeFaq(faq: FaqAdminResponse | null) {
  const sections = faq?.sections ?? [];
  const items = sections.flatMap((section) => section.items);
  return {
    sections: sections.length,
    items: items.length,
    published: items.filter((item) => item.is_published).length,
    translationGaps: sections.reduce((total, section) => total + sectionTranslationGapCount(section), 0),
  };
}

function sectionTranslationGapCount(section: FaqSectionAdminResponse) {
  return faqSectionTranslationGaps(section).length;
}

function faqSectionTranslationGaps(section: FaqSectionAdminResponse, actions?: {
  onSectionField?: () => void;
  onItemField?: (itemId: number) => void;
}): AdminTranslationGap[] {
  const gaps: AdminTranslationGap[] = [];
  if (isMissingTranslation(section.title_en, section.title_bg)) {
    gaps.push({ id: `${section.slug}-title-bg`, label: `${section.title_en} > Title BG`, fieldId: faqSectionFieldId(section.slug, "title-bg"), onFix: actions?.onSectionField });
  }
  section.items.forEach((item, index) => {
    gaps.push(...faqItemTranslationGaps(section.slug, item, {
      onItemField: () => actions?.onItemField?.(item.id),
      prefix: `${section.title_en} > ${item.question_en || `Question ${index + 1}`}`,
    }));
  });
  return gaps;
}

function faqItemTranslationGaps(sectionSlug: string, item: FaqItemAdminResponse, options?: { onItemField?: () => void; prefix?: string }): AdminTranslationGap[] {
  const label = options?.prefix ?? item.question_en;
  const gaps: AdminTranslationGap[] = [];
  if (isMissingTranslation(item.question_en, item.question_bg)) {
    gaps.push({ id: `${sectionSlug}-item-${item.id}-question-bg`, label: `${label} > Question BG`, fieldId: faqItemFieldId(sectionSlug, item.id, "question-bg"), onFix: options?.onItemField });
  }
  if (isMissingTranslation(item.answer_en, item.answer_bg)) {
    gaps.push({ id: `${sectionSlug}-item-${item.id}-answer-bg`, label: `${label} > Answer BG`, fieldId: faqItemFieldId(sectionSlug, item.id, "answer-bg"), onFix: options?.onItemField });
  }
  return gaps;
}

function faqSectionFieldId(slug: string, field: string) {
  return `faq-${slug}-${field}`;
}

function faqItemFieldId(slug: string, itemId: number, field: string) {
  return `faq-${slug}-item-${itemId}-${field}`;
}
