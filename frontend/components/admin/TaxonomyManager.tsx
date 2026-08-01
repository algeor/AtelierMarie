"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { SaveConfirmation } from "@/components/admin/SaveConfirmation";
import { Button } from "@/components/ui/Button";
import { DeleteIconButton } from "@/components/ui/DeleteIconButton";
import { Input } from "@/components/ui/Input";
import { ApiError } from "@/lib/api-client";
import {
  createTaxonomyTerm,
  deleteTaxonomyTerm,
  getAdminTaxonomy,
  updateTaxonomyTerm,
} from "@/lib/api";
import { useLocalizedError } from "@/lib/useLocalizedError";
import type { AdminTaxonomyTerm, TaxonomyKind } from "@/lib/types";

interface TaxonomyManagerProps {
  kind: TaxonomyKind;
}

/**
 * CRUD manager for one taxonomy kind (product types, categories, or labels).
 * Sourced entirely from the taxonomy API — no hardcoded term lists.
 */
export function TaxonomyManager({ kind }: TaxonomyManagerProps) {
  const t = useTranslations("admin");
  const tCommon = useTranslations("common");
  const getLocalizedError = useLocalizedError();
  const [terms, setTerms] = useState<AdminTaxonomyTerm[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saveNotice, setSaveNotice] = useState<{ id: number; message: string } | null>(null);
  const saveNoticeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [newNameEn, setNewNameEn] = useState("");
  const [newNameBg, setNewNameBg] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [isReordering, setIsReordering] = useState(false);

  // Inline rename state (replaces window.prompt).
  const [editingSlug, setEditingSlug] = useState<string | null>(null);
  const [editEn, setEditEn] = useState("");
  const [editBg, setEditBg] = useState("");
  // Inline delete confirmation state (replaces window.confirm).
  const [confirmDeleteSlug, setConfirmDeleteSlug] = useState<string | null>(null);

  async function refresh() {
    try {
      setTerms(await getAdminTaxonomy(kind));
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? getLocalizedError(err.code) : t("taxonomy.loadError"));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    setIsLoading(true);
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kind]);

  useEffect(() => {
    return () => {
      if (saveNoticeTimerRef.current) clearTimeout(saveNoticeTimerRef.current);
    };
  }, []);

  function showSaved(message = tCommon("saved")) {
    if (saveNoticeTimerRef.current) clearTimeout(saveNoticeTimerRef.current);
    setSaveNotice((current) => ({
      id: (current?.id ?? 0) + 1,
      message,
    }));
    saveNoticeTimerRef.current = setTimeout(() => {
      setSaveNotice(null);
    }, 3200);
  }

  async function handleCreate() {
    if (!newNameEn.trim()) return;
    setIsCreating(true);
    setError(null);
    try {
      await createTaxonomyTerm(kind, {
        name_en: newNameEn.trim(),
        name_bg: newNameBg.trim() || null,
        sort_order: terms.length,
      });
      setNewNameEn("");
      setNewNameBg("");
      await refresh();
      showSaved();
    } catch (err) {
      setError(err instanceof ApiError ? getLocalizedError(err.code) : t("taxonomy.saveError"));
    } finally {
      setIsCreating(false);
    }
  }

  async function patch(slug: string, data: Parameters<typeof updateTaxonomyTerm>[2]) {
    setError(null);
    try {
      await updateTaxonomyTerm(kind, slug, data);
      await refresh();
      showSaved();
    } catch (err) {
      setError(err instanceof ApiError ? getLocalizedError(err.code) : t("taxonomy.saveError"));
    }
  }

  function startRename(term: AdminTaxonomyTerm) {
    setConfirmDeleteSlug(null);
    setEditingSlug(term.slug);
    setEditEn(term.name_en);
    setEditBg(term.name_bg ?? "");
  }

  function cancelRename() {
    setEditingSlug(null);
  }

  async function saveRename(term: AdminTaxonomyTerm) {
    if (!editEn.trim()) return;
    await patch(term.slug, { name_en: editEn.trim(), name_bg: editBg.trim() || null });
    setEditingSlug(null);
  }

  async function handleReorder(index: number, direction: -1 | 1) {
    const other = index + direction;
    if (other < 0 || other >= terms.length || isReordering) return;
    const a = terms[index];
    const b = terms[other];
    if (!a || !b) return;
    setIsReordering(true);
    setError(null);
    try {
      // If both share a sort_order, synthesize a gap so the swap is observable.
      const aOrder = a.sort_order;
      const bOrder = b.sort_order === a.sort_order ? a.sort_order + direction : b.sort_order;
      // Apply both updates, then refresh once (avoids the transient mid-swap
      // state a per-call refresh would render).
      await updateTaxonomyTerm(kind, a.slug, { sort_order: bOrder });
      await updateTaxonomyTerm(kind, b.slug, { sort_order: aOrder });
      await refresh();
      showSaved();
    } catch (err) {
      setError(err instanceof ApiError ? getLocalizedError(err.code) : t("taxonomy.saveError"));
      await refresh(); // resync after a partial failure
    } finally {
      setIsReordering(false);
    }
  }

  async function handleDelete(term: AdminTaxonomyTerm) {
    setConfirmDeleteSlug(null);
    setError(null);
    try {
      await deleteTaxonomyTerm(kind, term.slug);
      await refresh();
      showSaved();
    } catch (err) {
      if (err instanceof ApiError && err.code === "TAXONOMY_IN_USE") {
        setError(t("taxonomy.inUse", { name: term.name_en }));
        return;
      }
      setError(err instanceof ApiError ? getLocalizedError(err.code) : t("taxonomy.saveError"));
    }
  }

  if (isLoading) {
    return <p className="text-sm text-soft-brown">{t("taxonomy.loading")}</p>;
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="rounded-brand border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}
      {saveNotice && <SaveConfirmation key={saveNotice.id} message={saveNotice.message} />}

      {/* Create form */}
      <div className="flex flex-wrap items-end gap-3 rounded-brand border border-champagne-beige bg-warm-ivory p-4">
        <div className="w-48">
          <Input
            label={t("taxonomy.nameEn")}
            value={newNameEn}
            onChange={(e) => setNewNameEn(e.target.value)}
          />
        </div>
        <div className="w-48">
          <Input
            label={t("taxonomy.nameBg")}
            value={newNameBg}
            onChange={(e) => setNewNameBg(e.target.value)}
          />
        </div>
        <Button type="button" onClick={handleCreate} isLoading={isCreating} disabled={!newNameEn.trim()}>
          {t("taxonomy.add")}
        </Button>
      </div>

      {/* Term list */}
      {terms.length === 0 ? (
        <p className="text-sm text-soft-brown">{t("taxonomy.empty")}</p>
      ) : (
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-champagne-beige text-left text-soft-brown">
              <th className="py-2 pr-3 font-medium">{t("taxonomy.colName")}</th>
              <th className="py-2 pr-3 font-medium">{t("taxonomy.colSlug")}</th>
              <th className="py-2 pr-3 font-medium">{t("taxonomy.colCount")}</th>
              <th className="py-2 pr-3 font-medium">{t("taxonomy.colStatus")}</th>
              <th className="py-2 font-medium">{t("taxonomy.colActions")}</th>
            </tr>
          </thead>
          <tbody>
            {terms.map((term, index) => {
              const isEditing = editingSlug === term.slug;
              const isConfirmingDelete = confirmDeleteSlug === term.slug;
              return (
                <tr key={term.slug} className="border-b border-champagne-beige/60">
                  <td className="py-2 pr-3 text-charcoal">
                    {isEditing ? (
                      <div className="flex flex-wrap gap-2">
                        <input
                          aria-label={t("taxonomy.nameEn")}
                          value={editEn}
                          onChange={(e) => setEditEn(e.target.value)}
                          placeholder={t("taxonomy.nameEn")}
                          className="w-32 rounded-brand border border-champagne-beige bg-warm-ivory px-2 py-1 text-sm text-charcoal focus:border-muted-gold focus:outline-none"
                        />
                        <input
                          aria-label={t("taxonomy.nameBg")}
                          value={editBg}
                          onChange={(e) => setEditBg(e.target.value)}
                          placeholder={t("taxonomy.nameBg")}
                          className="w-32 rounded-brand border border-champagne-beige bg-warm-ivory px-2 py-1 text-sm text-charcoal focus:border-muted-gold focus:outline-none"
                        />
                      </div>
                    ) : (
                      <>
                        {term.name_en}
                        {term.name_bg ? (
                          <span className="text-soft-brown/70"> / {term.name_bg}</span>
                        ) : null}
                      </>
                    )}
                  </td>
                  <td className="py-2 pr-3 font-mono text-xs text-soft-brown">{term.slug}</td>
                  <td className="py-2 pr-3 text-soft-brown">{term.product_count}</td>
                  <td className="py-2 pr-3">
                    <span
                      className={
                        term.is_active
                          ? "rounded-pill bg-green-100 px-2 py-0.5 text-xs text-green-800"
                          : "rounded-pill bg-champagne-beige px-2 py-0.5 text-xs text-soft-brown"
                      }
                    >
                      {term.is_active ? t("taxonomy.active") : t("taxonomy.inactive")}
                    </span>
                  </td>
                  <td className="flex flex-wrap items-center gap-1.5 py-2">
                    {isEditing ? (
                      <>
                        <Button
                          type="button"
                          onClick={() => saveRename(term)}
                          disabled={!editEn.trim()}
                        >
                          {t("taxonomy.save")}
                        </Button>
                        <Button type="button" variant="ghost" onClick={cancelRename}>
                          {t("taxonomy.cancel")}
                        </Button>
                      </>
                    ) : isConfirmingDelete ? (
                      <>
                        <span className="text-xs text-soft-brown">
                          {t("taxonomy.deleteConfirm", { name: term.name_en })}
                        </span>
                        <DeleteIconButton
                          label={t("taxonomy.confirmDelete")}
                          onClick={() => handleDelete(term)}
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          onClick={() => setConfirmDeleteSlug(null)}
                        >
                          {t("taxonomy.cancel")}
                        </Button>
                      </>
                    ) : (
                      <>
                        <Button
                          type="button"
                          variant="ghost"
                          onClick={() => handleReorder(index, -1)}
                          disabled={index === 0 || isReordering}
                        >
                          ↑
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          onClick={() => handleReorder(index, 1)}
                          disabled={index === terms.length - 1 || isReordering}
                        >
                          ↓
                        </Button>
                        <Button type="button" variant="secondary" onClick={() => startRename(term)}>
                          {t("taxonomy.rename")}
                        </Button>
                        <Button
                          type="button"
                          variant="secondary"
                          onClick={() => patch(term.slug, { is_active: !term.is_active })}
                        >
                          {term.is_active ? t("taxonomy.deactivate") : t("taxonomy.activate")}
                        </Button>
                        <DeleteIconButton
                          label={t("taxonomy.delete")}
                          onClick={() => {
                            setEditingSlug(null);
                            setConfirmDeleteSlug(term.slug);
                          }}
                          disabled={term.product_count > 0}
                        />
                      </>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
