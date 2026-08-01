"use client";

import { type FormEvent, type ReactNode, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { AdminFieldLabel } from "@/components/admin/AdminFieldLabel";
import { AdminInfoPopover } from "@/components/admin/AdminInfoPopover";
import {
  activateRecipe,
  archiveRecipe,
  cancelProductionBatch,
  correctProductionBatch,
  createMaterial,
  createMaterialAdjustment,
  createMaterialReceipt,
  createProductionBatch,
  createRecipe,
  createRecipeCostSnapshot,
  generateCogsRows,
  generateValuationLayers,
  getInventoryClosePreview,
  getInventoryValuationSettings,
  getMaterial,
  listCogsRows,
  listInventoryExceptions,
  listInventoryMovements,
  listMaterials,
  listProductionBatches,
  listRecipes,
  listValuationLayers,
  postProductionBatch,
  recordOpeningBalance,
  reviewRecipe,
  updateInventoryValuationSettings,
} from "@/lib/api";
import { ApiError } from "@/lib/api-client";
import { cn, formatPrice } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import type {
  CogsLedgerResponse,
  InventoryClosePreviewResponse,
  InventoryExceptionResponse,
  InventoryMovementResponse,
  InventoryValuationSettingsResponse,
  MaterialDetailResponse,
  MaterialMovementType,
  MaterialResponse,
  MaterialUom,
  ProductionBatchResponse,
  RecipeVersionResponse,
  ValuationLayerResponse,
} from "@/lib/types";

export type InventoryTab = "materials" | "recipes" | "batches" | "valuation" | "movements";

interface InventoryWorkspaceProps {
  initialTab?: InventoryTab;
}

const TABS: InventoryTab[] = ["materials", "recipes", "batches", "valuation", "movements"];
const UOMS: MaterialUom[] = ["g", "kg", "ml", "l", "piece", "pcs", "unit", "m", "cm"];
const MATERIAL_MOVEMENTS: MaterialMovementType[] = ["adjustment", "spoilage", "write_off", "stock_count_correction"];
const INVENTORY_LABEL_KEYS = new Set([
  "accountant_reviewed",
  "active",
  "adjustment",
  "allow_estimate",
  "archived",
  "below_threshold",
  "block_official",
  "blocking",
  "cancelled",
  "delivery_date",
  "draft",
  "estimate",
  "estimate_only",
  "fifo",
  "finished_good",
  "half_up_2dp",
  "half_up_4dp",
  "legacy",
  "ledger_managed",
  "material",
  "missing",
  "official",
  "ok",
  "order_date",
  "payment_date",
  "period_close",
  "piece",
  "pcs",
  "produced",
  "ready",
  "reviewed",
  "setup",
  "shipment_date",
  "spoilage",
  "stock_count_correction",
  "unit",
  "warn",
  "warning",
  "weighted_average",
  "write_off",
]);

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function monthStart(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
}

function optionalText(value: FormDataEntryValue | null): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function textValue(formData: FormData, key: string, fallback = ""): string {
  const value = formData.get(key);
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

function optionalNumber(value: FormDataEntryValue | null): number | null {
  if (typeof value !== "string" || !value.trim()) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function requiredNumber(value: FormDataEntryValue | null): number {
  return optionalNumber(value) ?? 0;
}

function statusText(value: string | null | undefined): string {
  return value ? value.replaceAll("_", " ") : "-";
}

function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError || error instanceof Error) return error.message;
  return fallback;
}

function badgeVariant(value: string | null | undefined): "default" | "accent" | "success" | "warning" {
  if (!value) return "default";
  if (["active", "reviewed", "accountant_reviewed", "ready", "official", "produced", "ok"].includes(value)) return "success";
  if (["blocking", "blocked", "missing", "invalid", "expired", "below_threshold"].includes(value)) return "warning";
  if (["ledger_managed", "estimate", "estimate_only", "setup"].includes(value)) return "accent";
  return "default";
}

function formatDate(value: string | null | undefined, locale: string): string {
  if (!value) return "-";
  return new Date(value).toLocaleDateString(locale === "bg" ? "bg-BG" : "en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function formatMoneyCents(cents: number | null | undefined): string {
  if (typeof cents !== "number" || !Number.isFinite(cents)) return "-";
  const sign = cents < 0 ? "-" : "";
  return `${sign}${formatPrice(Math.abs(cents))}`;
}

function parseComponents(text: string) {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => {
      const [materialId, quantity, uom, basis, wastage] = line.split(",").map((part) => part.trim());
      if (!materialId || !quantity || !uom) {
        throw new Error("Use component lines as material_id,quantity,uom[,basis,wastage]");
      }
      return {
        material_id: materialId,
        quantity: Number(quantity),
        uom: uom as MaterialUom,
        quantity_basis: basis === "per_unit" ? "per_unit" as const : "per_batch" as const,
        wastage_percent: wastage ? Number(wastage) : 0,
        required: true,
        sort_order: index,
      };
    });
}

function SectionTitle({ title, subtitle, info }: { title: string; subtitle?: string; info?: string }) {
  return (
    <div>
      <div className="flex items-center gap-2">
        <h2 className="font-heading text-lg font-semibold text-charcoal">{title}</h2>
        {info && <AdminInfoPopover content={info} />}
      </div>
      {subtitle && <p className="mt-1 text-sm text-soft-brown">{subtitle}</p>}
    </div>
  );
}

function StatusBadge({ value, label }: { value: string | null | undefined; label?: string }) {
  return <Badge variant={badgeVariant(value)}>{label ?? statusText(value)}</Badge>;
}

function EmptyState({ label }: { label: string }) {
  return <div className="rounded-brand border border-champagne-beige bg-cream p-6 text-sm text-soft-brown">{label}</div>;
}

function Field({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase text-soft-brown">{label}</dt>
      <dd className="mt-1 text-sm text-charcoal">{value}</dd>
    </div>
  );
}

function FormField({ label, info, help, children, className }: { label: string; info?: string; help?: string; children: ReactNode; className?: string }) {
  const content = info ?? help;
  return (
    <div className={className}>
      <AdminFieldLabel info={content}>{label}</AdminFieldLabel>
      {children}
    </div>
  );
}

function CheckboxField({ name, label, info, defaultChecked }: { name: string; label: string; info: string; defaultChecked?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2">
      <label className="inline-flex items-center gap-2">
        <input name={name} type="checkbox" defaultChecked={defaultChecked} />
        {label}
      </label>
      <AdminInfoPopover content={info} />
    </span>
  );
}

function inputClass() {
  return "h-10 w-full rounded-brand border border-champagne-beige bg-cream px-3 text-sm text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown";
}

function textareaClass() {
  return "min-h-24 w-full rounded-brand border border-champagne-beige bg-cream px-3 py-2 text-sm text-charcoal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown";
}

export function InventoryWorkspace({ initialTab = "materials" }: InventoryWorkspaceProps) {
  const t = useTranslations("admin.inventory");
  const tAdmin = useTranslations("admin");
  const locale = useLocale();
  const searchParams = useSearchParams();
  const urlItemType = searchParams.get("item_type") as "material" | "finished_good" | null;
  const urlItemId = searchParams.get("item_id") || "";
  const urlProductId = searchParams.get("product_id") || "";
  const urlOrderId = searchParams.get("order_id") || "";
  const urlSourceType = searchParams.get("source_type") || "";
  const urlSourceId = searchParams.get("source_id") || "";
  const urlTargetType = searchParams.get("target_type") || "";
  const urlTargetId = searchParams.get("target_id") || "";
  const [activeTab, setActiveTab] = useState<InventoryTab>(initialTab);
  const [materials, setMaterials] = useState<MaterialResponse[]>([]);
  const [selectedMaterialId, setSelectedMaterialId] = useState(
    searchParams.get("material_id") || (urlItemType === "material" ? urlItemId : ""),
  );
  const [materialDetail, setMaterialDetail] = useState<MaterialDetailResponse | null>(null);
  const [recipes, setRecipes] = useState<RecipeVersionResponse[]>([]);
  const [recipeStatus, setRecipeStatus] = useState("");
  const [batches, setBatches] = useState<ProductionBatchResponse[]>([]);
  const [batchStatus, setBatchStatus] = useState("");
  const [settings, setSettings] = useState<InventoryValuationSettingsResponse | null>(null);
  const [movements, setMovements] = useState<InventoryMovementResponse[]>([]);
  const [movementTotal, setMovementTotal] = useState(0);
  const [movementFilters, setMovementFilters] = useState<{
    itemType: "" | "material" | "finished_good";
    itemId: string;
    sourceType: string;
    sourceId: string;
    orderId: string;
    movementType: string;
  }>({
    itemType: urlItemType || "",
    itemId: urlItemId,
    sourceType: urlSourceType,
    sourceId: urlSourceId,
    orderId: urlOrderId,
    movementType: searchParams.get("movement_type") || "",
  });
  const [valuationLayers, setValuationLayers] = useState<ValuationLayerResponse[]>([]);
  const [cogsRows, setCogsRows] = useState<CogsLedgerResponse[]>([]);
  const [exceptions, setExceptions] = useState<InventoryExceptionResponse[]>([]);
  const [closePreview, setClosePreview] = useState<InventoryClosePreviewResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const selectedMaterial = useMemo(
    () => materials.find((material) => material.id === selectedMaterialId) ?? null,
    [materials, selectedMaterialId],
  );

  const labelFor = useCallback(
    (value: string | null | undefined): string => {
      if (!value) return "-";
      return INVENTORY_LABEL_KEYS.has(value) ? t(`labels.${value}`) : statusText(value);
    },
    [t],
  );

  const fieldInfo = useCallback(
    (key: string): string => t(`fieldHelp.${key}` as Parameters<typeof t>[0]),
    [t],
  );

  const uomOptions = useMemo(
    () => UOMS.map((uom) => <option key={uom} value={uom}>{labelFor(uom)}</option>),
    [labelFor],
  );

  const loadWorkspace = useCallback(async (soft = false) => {
    if (soft) setIsRefreshing(true);
    else setIsLoading(true);
    setError(null);
    try {
      const [materialData, recipeData, batchData, settingsData, movementData, layerData, cogsData, exceptionData] = await Promise.all([
        listMaterials({ limit: 250 }),
        listRecipes({ status: recipeStatus || undefined }),
        listProductionBatches({ status: batchStatus || undefined }),
        getInventoryValuationSettings(),
        listInventoryMovements({
          itemType: movementFilters.itemType || undefined,
          itemId: movementFilters.itemId || undefined,
          sourceType: movementFilters.sourceType || undefined,
          sourceId: movementFilters.sourceId || undefined,
          orderId: movementFilters.orderId || undefined,
          movementType: movementFilters.movementType || undefined,
          limit: 100,
        }),
        listValuationLayers({
          itemType: urlItemType || undefined,
          itemId: urlItemId || undefined,
        }),
        listCogsRows({
          productId: urlProductId || undefined,
          orderId: urlOrderId || undefined,
        }),
        listInventoryExceptions({
          targetType: urlTargetType || undefined,
          targetId: urlTargetId || undefined,
          sourceType: urlSourceType || undefined,
          sourceId: urlSourceId || undefined,
          orderId: urlOrderId || undefined,
        }),
      ]);
      setMaterials(materialData.materials);
      setRecipes(recipeData.recipes);
      setBatches(batchData.batches);
      setSettings(settingsData);
      setMovements(movementData.movements);
      setMovementTotal(movementData.total);
      setValuationLayers(layerData.layers);
      setCogsRows(cogsData.rows);
      setExceptions(exceptionData);
    } catch (err) {
      setError(errorMessage(err, t("loadError")));
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [batchStatus, movementFilters, recipeStatus, t, urlItemId, urlItemType, urlOrderId, urlProductId, urlSourceId, urlSourceType, urlTargetId, urlTargetType]);

  useEffect(() => {
    loadWorkspace(false);
  }, [loadWorkspace]);

  useEffect(() => {
    let cancelled = false;
    if (!selectedMaterialId) {
      setMaterialDetail(null);
      return;
    }
    getMaterial(selectedMaterialId)
      .then((data) => {
        if (!cancelled) setMaterialDetail(data);
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err, t("loadError")));
      });
    return () => {
      cancelled = true;
    };
  }, [selectedMaterialId, t]);

  async function runAction(actionKey: string, action: () => Promise<void>, message = t("saved")) {
    setBusyAction(actionKey);
    setError(null);
    setSuccess(null);
    try {
      await action();
      await loadWorkspace(true);
      if (selectedMaterialId) {
        setMaterialDetail(await getMaterial(selectedMaterialId));
      }
      setSuccess(message);
    } catch (err) {
      setError(errorMessage(err, t("saveError")));
    } finally {
      setBusyAction(null);
    }
  }

  async function handleCreateMaterial(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    await runAction("create-material", async () => {
      const material = await createMaterial({
        sku: optionalText(formData.get("sku")),
        name: textValue(formData, "name"),
        category: textValue(formData, "category", "material"),
        stock_uom: textValue(formData, "stock_uom", "g") as MaterialUom,
        purchase_uom: optionalText(formData.get("purchase_uom")) as MaterialUom | null,
        purchase_to_stock_factor: optionalNumber(formData.get("purchase_to_stock_factor")),
        preferred_supplier_name: optionalText(formData.get("preferred_supplier_name")),
        preferred_supplier_sku: optionalText(formData.get("preferred_supplier_sku")),
        reorder_threshold: optionalNumber(formData.get("reorder_threshold")),
        active: formData.get("active") === "on",
        lot_tracked: formData.get("lot_tracked") === "on",
        expiry_tracked: formData.get("expiry_tracked") === "on",
        evidence_required: formData.get("evidence_required") === "on",
        notes: optionalText(formData.get("notes")),
      });
      setSelectedMaterialId(material.id);
      form.reset();
    }, t("materials.created"));
  }

  async function handleReceipt(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedMaterialId || !selectedMaterial) return;
    const form = event.currentTarget;
    const formData = new FormData(form);
    await runAction("receipt", async () => {
      await createMaterialReceipt(selectedMaterialId, {
        receipt_date: textValue(formData, "receipt_date", today()),
        quantity: requiredNumber(formData.get("quantity")),
        uom: textValue(formData, "uom", selectedMaterial.stock_uom) as MaterialUom,
        unit_cost_amount: optionalText(formData.get("unit_cost_amount")),
        total_cost_cents: optionalNumber(formData.get("total_cost_cents")),
        currency: textValue(formData, "currency", "EUR"),
        supplier_name: optionalText(formData.get("supplier_name")),
        supplier_lot: optionalText(formData.get("supplier_lot")),
        expiry_date: optionalText(formData.get("expiry_date")),
        use_by_date: optionalText(formData.get("use_by_date")),
        expense_evidence_id: optionalText(formData.get("expense_evidence_id")),
        document_reference: optionalText(formData.get("document_reference")),
        notes: optionalText(formData.get("notes")),
      });
      form.reset();
    }, t("materials.receiptSaved"));
  }

  async function handleAdjustment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedMaterialId || !selectedMaterial) return;
    const form = event.currentTarget;
    const formData = new FormData(form);
    await runAction("adjustment", async () => {
      await createMaterialAdjustment(selectedMaterialId, {
        movement_type: textValue(formData, "movement_type", "adjustment") as MaterialMovementType,
        quantity_delta: requiredNumber(formData.get("quantity_delta")),
        uom: textValue(formData, "uom", selectedMaterial.stock_uom) as MaterialUom,
        reason: textValue(formData, "reason"),
        notes: optionalText(formData.get("notes")),
        occurred_at: optionalText(formData.get("occurred_at")),
      });
      form.reset();
    }, t("materials.adjustmentSaved"));
  }

  async function handleCreateRecipe(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    await runAction("create-recipe", async () => {
      await createRecipe({
        product_id: textValue(formData, "product_id"),
        version_label: textValue(formData, "version_label"),
        effective_date: textValue(formData, "effective_date", today()),
        output_quantity: requiredNumber(formData.get("output_quantity")),
        output_uom: textValue(formData, "output_uom", "unit"),
        notes: optionalText(formData.get("notes")),
        components: parseComponents(textValue(formData, "components")),
      });
      form.reset();
    }, t("recipes.created"));
  }

  async function handleCreateBatch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    await runAction("create-batch", async () => {
      await createProductionBatch({
        batch_number: textValue(formData, "batch_number"),
        product_id: textValue(formData, "product_id"),
        recipe_version_id: optionalText(formData.get("recipe_version_id")),
        planned_output_quantity: requiredNumber(formData.get("planned_output_quantity")),
        output_uom: textValue(formData, "output_uom", "unit"),
        production_date: textValue(formData, "production_date", today()),
        ready_date: optionalText(formData.get("ready_date")),
        notes: optionalText(formData.get("notes")),
      });
      form.reset();
    }, t("batches.created"));
  }

  async function quickPostBatch(batch: ProductionBatchResponse) {
    await runAction(`post-${batch.id}`, async () => {
      await postProductionBatch(batch.id, {
        actual_output_quantity: batch.planned_output_quantity,
        actual_consumption: batch.consumption.map((line) => ({
          batch_consumption_id: line.id,
          material_id: line.material_id,
          actual_quantity: line.expected_quantity ?? 0,
          waste_quantity: line.waste_quantity,
          uom: line.uom as MaterialUom,
        })),
        variance_tolerance_percent: 10,
      });
    }, t("batches.posted"));
  }

  async function handleBatchCorrection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    const batchId = textValue(formData, "batch_id");
    await runAction("batch-correction", async () => {
      await correctProductionBatch(batchId, {
        item_type: textValue(formData, "item_type", "material") as "material" | "finished_good",
        item_id: textValue(formData, "item_id"),
        quantity_delta: requiredNumber(formData.get("quantity_delta")),
        uom: textValue(formData, "uom", "unit"),
        reason: textValue(formData, "reason"),
        notes: optionalText(formData.get("notes")),
      });
      form.reset();
    }, t("batches.corrected"));
  }

  async function handleSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    await runAction("settings", async () => {
      await updateInventoryValuationSettings({
        ledger_mode: textValue(formData, "ledger_mode", "setup") as "legacy" | "setup" | "ledger_managed",
        valuation_enabled: formData.get("valuation_enabled") === "on",
        valuation_method: textValue(formData, "valuation_method", "weighted_average") as "weighted_average" | "fifo",
        effective_date: textValue(formData, "effective_date", today()),
        cogs_date_basis: textValue(formData, "cogs_date_basis", "order_date") as InventoryValuationSettingsResponse["cogs_date_basis"],
        rounding_policy: textValue(formData, "rounding_policy", "half_up_2dp") as "half_up_2dp" | "half_up_4dp",
        missing_cost_behavior: textValue(formData, "missing_cost_behavior", "block_official") as "allow_estimate" | "warn" | "block_official",
        currency: textValue(formData, "currency", "EUR"),
        accountant_reviewed: formData.get("accountant_reviewed") === "on",
        reviewed_by_name: optionalText(formData.get("reviewed_by_name")),
        review_notes: optionalText(formData.get("review_notes")),
      });
    }, t("valuation.settingsSaved"));
  }

  async function handleOpeningBalance(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    await runAction("opening-balance", async () => {
      await recordOpeningBalance({
        item_type: textValue(formData, "item_type", "material") as "material" | "finished_good",
        item_id: textValue(formData, "item_id"),
        quantity: requiredNumber(formData.get("quantity")),
        uom: textValue(formData, "uom", "unit"),
        unit_value_amount: optionalText(formData.get("unit_value_amount")),
        total_value_cents: optionalNumber(formData.get("total_value_cents")),
        reviewed: formData.get("reviewed") === "on",
        notes: optionalText(formData.get("notes")),
      });
      form.reset();
    }, t("valuation.openingSaved"));
  }

  async function handleClosePreview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    setBusyAction("close-preview");
    setError(null);
    try {
      setClosePreview(await getInventoryClosePreview(textValue(formData, "period_start", monthStart()), textValue(formData, "period_end", today())));
    } catch (err) {
      setError(errorMessage(err, t("saveError")));
    } finally {
      setBusyAction(null);
    }
  }

  async function handleMovementFilter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    setMovementFilters({
      itemType: textValue(formData, "item_type") as "" | "material" | "finished_good",
      itemId: textValue(formData, "item_id"),
      sourceType: textValue(formData, "source_type"),
      sourceId: textValue(formData, "source_id"),
      orderId: textValue(formData, "order_id"),
      movementType: textValue(formData, "movement_type"),
    });
    setActiveTab("movements");
  }

  function renderMaterials() {
    return (
      <div className="space-y-6">
        <form onSubmit={handleCreateMaterial} className="rounded-brand border border-champagne-beige bg-cream p-4">
          <SectionTitle title={t("materials.createTitle")} info={t("materials.createSubtitle")} />
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <FormField label={t("materials.name")} help={t("materials.nameHelp")}>
              <input name="name" required className={inputClass()} placeholder={t("materials.name")} />
            </FormField>
            <FormField label={t("materials.sku")} help={t("materials.skuHelp")}>
              <input name="sku" className={inputClass()} placeholder={t("materials.sku")} />
            </FormField>
            <FormField label={t("materials.category")} help={t("materials.categoryHelp")}>
              <input name="category" className={inputClass()} placeholder={t("materials.category")} defaultValue={labelFor("material")} />
            </FormField>
            <FormField label={t("materials.stockUom")} help={t("materials.stockUomHelp")}>
              <select name="stock_uom" className={inputClass()} defaultValue="g">
                {uomOptions}
              </select>
            </FormField>
            <FormField label={t("materials.purchaseUomLabel")} help={t("materials.purchaseUomHelp")}>
              <select name="purchase_uom" className={inputClass()} defaultValue="" aria-label={t("materials.purchaseUomLabel")}>
                <option value="" disabled hidden>{t("materials.purchaseUom")}</option>
                {uomOptions}
              </select>
            </FormField>
            <FormField label={t("materials.conversion")} help={t("materials.conversionHelp")}>
              <input name="purchase_to_stock_factor" type="number" min="0" step="0.000001" className={inputClass()} placeholder={t("materials.conversion")} />
            </FormField>
            <FormField label={t("materials.supplier")} help={t("materials.supplierHelp")}>
              <input name="preferred_supplier_name" className={inputClass()} placeholder={t("materials.supplier")} />
            </FormField>
            <FormField label={t("materials.supplierSku")} help={t("materials.supplierSkuHelp")}>
              <input name="preferred_supplier_sku" className={inputClass()} placeholder={t("materials.supplierSku")} />
            </FormField>
            <FormField label={t("materials.reorderThreshold")} help={t("materials.reorderThresholdHelp")}>
              <input name="reorder_threshold" type="number" min="0" step="0.001" className={inputClass()} placeholder={t("materials.reorderThreshold")} />
            </FormField>
          </div>
          <div className="mt-4 flex flex-wrap gap-4 text-sm text-soft-brown">
            <CheckboxField name="active" label={t("materials.active")} info={fieldInfo("materialActive")} defaultChecked />
            <CheckboxField name="lot_tracked" label={t("materials.lotTracked")} info={fieldInfo("lotTracked")} />
            <CheckboxField name="expiry_tracked" label={t("materials.expiryTracked")} info={fieldInfo("expiryTracked")} />
            <CheckboxField name="evidence_required" label={t("materials.evidenceRequired")} info={fieldInfo("evidenceRequired")} />
          </div>
          <FormField label={t("notes")} info={fieldInfo("notes")} className="mt-4">
            <textarea name="notes" className={textareaClass()} placeholder={t("notes")} />
          </FormField>
          <Button className="mt-4" type="submit" isLoading={busyAction === "create-material"}>{t("materials.create")}</Button>
        </form>

        <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
          <div className="overflow-x-auto rounded-brand border border-champagne-beige bg-cream">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-champagne-beige bg-champagne-beige/30">
                <tr>
                  <th className="px-4 py-3 text-charcoal">{t("materials.name")}</th>
                  <th className="px-4 py-3 text-charcoal">{t("materials.onHand")}</th>
                  <th className="px-4 py-3 text-charcoal">{t("materials.reorder")}</th>
                  <th className="px-4 py-3 text-charcoal">{t("exceptions")}</th>
                </tr>
              </thead>
              <tbody>
                {materials.map((material) => (
                  <tr key={material.id} className="border-b border-champagne-beige/50 last:border-0">
                    <td className="px-4 py-3">
                      <button type="button" className="font-medium text-charcoal underline-offset-2 hover:underline" onClick={() => setSelectedMaterialId(material.id)}>
                        {material.name}
                      </button>
                      <p className="mt-1 text-xs text-soft-brown">{material.sku || material.id} · {material.category}</p>
                    </td>
                    <td className="px-4 py-3 text-soft-brown">{material.on_hand_quantity} {material.stock_uom}</td>
                    <td className="px-4 py-3"><StatusBadge value={material.reorder_status} label={labelFor(material.reorder_status)} /></td>
                    <td className="px-4 py-3 text-soft-brown">{material.open_exception_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {materials.length === 0 && <EmptyState label={t("materials.empty")} />}
          </div>

          <div className="space-y-4">
            {!materialDetail ? (
              <EmptyState label={t("materials.selectMaterial")} />
            ) : (
              <>
                <section className="rounded-brand border border-champagne-beige bg-cream p-4">
                  <SectionTitle title={materialDetail.name} subtitle={`${materialDetail.on_hand_quantity} ${materialDetail.stock_uom}`} />
                  <dl className="mt-4 grid gap-3 sm:grid-cols-2">
                    <Field label={t("materials.supplier")} value={materialDetail.preferred_supplier_name || "-"} />
                    <Field label={t("materials.latestMovement")} value={formatDate(materialDetail.latest_movement_at, locale)} />
                    <Field label={t("materials.lots")} value={`${materialDetail.lots.length}`} />
                    <Field label={t("exceptions")} value={materialDetail.exceptions.length} />
                  </dl>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {materialDetail.lot_tracked && <StatusBadge value="active" label={t("materials.lotTracked")} />}
                    {materialDetail.expiry_tracked && <StatusBadge value="active" label={t("materials.expiryTracked")} />}
                    {materialDetail.evidence_required && <StatusBadge value="active" label={t("materials.evidenceRequired")} />}
                  </div>
                </section>

                <form onSubmit={handleReceipt} className="rounded-brand border border-champagne-beige bg-cream p-4">
                  <SectionTitle title={t("materials.receiptTitle")} />
                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    <FormField label={t("date")} info={fieldInfo("receiptDate")}>
                      <input name="receipt_date" type="date" className={inputClass()} defaultValue={today()} />
                    </FormField>
                    <FormField label={t("quantity")} info={fieldInfo("receiptQuantity")}>
                      <input name="quantity" required type="number" min="0" step="0.001" className={inputClass()} placeholder={t("quantity")} />
                    </FormField>
                    <FormField label={t("materials.stockUom")} info={fieldInfo("receiptUom")}>
                      <select name="uom" className={inputClass()} defaultValue={materialDetail.stock_uom}>{uomOptions}</select>
                    </FormField>
                    <FormField label={t("materials.unitCost")} info={fieldInfo("unitCost")}>
                      <input name="unit_cost_amount" className={inputClass()} placeholder={t("materials.unitCost")} />
                    </FormField>
                    <FormField label={t("materials.totalCostCents")} info={fieldInfo("totalCostCents")}>
                      <input name="total_cost_cents" type="number" min="0" step="1" className={inputClass()} placeholder={t("materials.totalCostCents")} />
                    </FormField>
                    <FormField label={t("currency")} info={fieldInfo("currency")}>
                      <input name="currency" className={inputClass()} defaultValue="EUR" placeholder={t("currency")} />
                    </FormField>
                    <FormField label={t("materials.supplier")} info={fieldInfo("receiptSupplier")}>
                      <input name="supplier_name" className={inputClass()} placeholder={t("materials.supplier")} />
                    </FormField>
                    <FormField label={t("materials.supplierLot")} info={fieldInfo("supplierLot")}>
                      <input name="supplier_lot" className={inputClass()} placeholder={t("materials.supplierLot")} />
                    </FormField>
                    <FormField label={t("materials.expiryDate")} info={fieldInfo("expiryDate")}>
                      <input name="expiry_date" type="date" className={inputClass()} aria-label={t("materials.expiryDate")} />
                    </FormField>
                    <FormField label={t("materials.documentReference")} info={fieldInfo("documentReference")}>
                      <input name="document_reference" className={inputClass()} placeholder={t("materials.documentReference")} />
                    </FormField>
                  </div>
                  <FormField label={t("notes")} info={fieldInfo("receiptNotes")} className="mt-3">
                    <textarea name="notes" className={textareaClass()} placeholder={t("notes")} />
                  </FormField>
                  <Button className="mt-3" type="submit" isLoading={busyAction === "receipt"}>{t("materials.recordReceipt")}</Button>
                </form>

                <form onSubmit={handleAdjustment} className="rounded-brand border border-champagne-beige bg-cream p-4">
                  <SectionTitle title={t("materials.adjustmentTitle")} />
                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    <FormField label={t("movements.movementType")} info={fieldInfo("adjustmentType")}>
                      <select name="movement_type" className={inputClass()}>{MATERIAL_MOVEMENTS.map((type) => <option key={type} value={type}>{labelFor(type)}</option>)}</select>
                    </FormField>
                    <FormField label={t("materials.quantityDelta")} info={fieldInfo("quantityDelta")}>
                      <input name="quantity_delta" required type="number" step="0.001" className={inputClass()} placeholder={t("materials.quantityDelta")} />
                    </FormField>
                    <FormField label={t("materials.stockUom")} info={fieldInfo("adjustmentUom")}>
                      <select name="uom" className={inputClass()} defaultValue={materialDetail.stock_uom}>{uomOptions}</select>
                    </FormField>
                    <FormField label={t("reason")} info={fieldInfo("reason")}>
                      <input name="reason" required className={inputClass()} placeholder={t("reason")} />
                    </FormField>
                  </div>
                  <FormField label={t("notes")} info={fieldInfo("adjustmentNotes")} className="mt-3">
                    <textarea name="notes" className={textareaClass()} placeholder={t("notes")} />
                  </FormField>
                  <Button className="mt-3" type="submit" isLoading={busyAction === "adjustment"}>{t("materials.recordAdjustment")}</Button>
                </form>

                <section className="rounded-brand border border-champagne-beige bg-cream p-4">
                  <SectionTitle title={t("materials.movementHistory")} />
                  <MovementList rows={materialDetail.recent_movements} locale={locale} />
                </section>
              </>
            )}
          </div>
        </div>
      </div>
    );
  }

  function renderRecipes() {
    return (
      <div className="space-y-6">
        <form onSubmit={handleCreateRecipe} className="rounded-brand border border-champagne-beige bg-cream p-4">
          <SectionTitle title={t("recipes.createTitle")} info={t("recipes.componentHelp")} />
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <FormField label={t("productId")} info={fieldInfo("recipeProductId")}>
              <input name="product_id" required className={inputClass()} placeholder={t("productId")} />
            </FormField>
            <FormField label={t("recipes.versionLabel")} info={fieldInfo("recipeVersionLabel")}>
              <input name="version_label" required className={inputClass()} placeholder={t("recipes.versionLabel")} />
            </FormField>
            <FormField label={t("recipes.effectiveDate")} info={fieldInfo("effectiveDate")}>
              <input name="effective_date" type="date" className={inputClass()} defaultValue={today()} />
            </FormField>
            <FormField label={t("recipes.outputQuantity")} info={fieldInfo("outputQuantity")}>
              <input name="output_quantity" required type="number" min="0" step="0.001" className={inputClass()} placeholder={t("recipes.outputQuantity")} />
            </FormField>
            <FormField label={t("recipes.outputUom")} info={fieldInfo("outputUom")}>
              <select name="output_uom" className={inputClass()} defaultValue="unit">{uomOptions}</select>
            </FormField>
            <FormField label={t("notes")} info={fieldInfo("recipeNotes")}>
              <input name="notes" className={inputClass()} placeholder={t("notes")} />
            </FormField>
          </div>
          <FormField label={t("recipes.componentsLabel")} info={fieldInfo("recipeComponents")} className="mt-3">
            <textarea name="components" className={textareaClass()} placeholder="soy-wax,500,g,per_batch,3" />
          </FormField>
          <Button className="mt-3" type="submit" isLoading={busyAction === "create-recipe"}>{t("recipes.create")}</Button>
        </form>

        <div className="flex flex-wrap gap-2">
          {["", "draft", "active", "archived"].map((status) => (
            <button key={status || "all"} type="button" onClick={() => setRecipeStatus(status)} className={cn("rounded-pill px-4 py-1.5 text-sm font-medium", recipeStatus === status ? "bg-muted-gold text-charcoal" : "bg-champagne-beige/50 text-soft-brown")}>{status ? labelFor(status) : tAdmin("all")}</button>
          ))}
        </div>

        <div className="overflow-x-auto rounded-brand border border-champagne-beige bg-cream">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-champagne-beige bg-champagne-beige/30"><tr><th className="px-4 py-3">{t("productId")}</th><th className="px-4 py-3">{t("recipes.versionLabel")}</th><th className="px-4 py-3">{t("status")}</th><th className="px-4 py-3">{t("recipes.cost")}</th><th className="px-4 py-3">{t("actions")}</th></tr></thead>
            <tbody>
              {recipes.map((recipe) => (
                <tr key={recipe.id} className="border-b border-champagne-beige/50 align-top last:border-0">
                  <td className="px-4 py-3"><span className="font-medium text-charcoal">{recipe.product_id}</span><p className="mt-1 text-xs text-soft-brown">{recipe.components.length} {t("recipes.components")}</p></td>
                  <td className="px-4 py-3 text-soft-brown">{recipe.version_label}<p className="text-xs">{formatDate(recipe.effective_date, locale)}</p></td>
                  <td className="px-4 py-3"><div className="space-y-1"><StatusBadge value={recipe.status} label={labelFor(recipe.status)} /><StatusBadge value={recipe.review_state} label={labelFor(recipe.review_state)} /></div></td>
                  <td className="px-4 py-3 text-soft-brown">{recipe.latest_cost_snapshot ? formatPrice(recipe.latest_cost_snapshot.expected_unit_cost_cents) : "-"}<p className="text-xs">{recipe.diagnostics.length} {t("recipes.diagnostics")}</p></td>
                  <td className="px-4 py-3"><div className="flex flex-wrap gap-2">
                    <Button type="button" size="sm" variant="secondary" isLoading={busyAction === `activate-${recipe.id}`} onClick={() => runAction(`activate-${recipe.id}`, () => activateRecipe(recipe.id).then(() => undefined), t("recipes.activated"))}>{t("recipes.activate")}</Button>
                    <Button type="button" size="sm" variant="secondary" isLoading={busyAction === `snapshot-${recipe.id}`} onClick={() => runAction(`snapshot-${recipe.id}`, () => createRecipeCostSnapshot(recipe.id, { currency: "EUR" }).then(() => undefined), t("recipes.snapshotCreated"))}>{t("recipes.snapshot")}</Button>
                    <Button type="button" size="sm" variant="secondary" isLoading={busyAction === `review-${recipe.id}`} onClick={() => runAction(`review-${recipe.id}`, () => reviewRecipe(recipe.id, { review_state: "reviewed" }).then(() => undefined), t("recipes.reviewed"))}>{t("recipes.review")}</Button>
                    <Button type="button" size="sm" variant="ghost" isLoading={busyAction === `archive-${recipe.id}`} onClick={() => runAction(`archive-${recipe.id}`, () => archiveRecipe(recipe.id).then(() => undefined), t("recipes.archived"))}>{t("recipes.archive")}</Button>
                  </div></td>
                </tr>
              ))}
            </tbody>
          </table>
          {recipes.length === 0 && <EmptyState label={t("recipes.empty")} />}
        </div>
      </div>
    );
  }

  function renderBatches() {
    return (
      <div className="space-y-6">
        <form onSubmit={handleCreateBatch} className="rounded-brand border border-champagne-beige bg-cream p-4">
          <SectionTitle title={t("batches.createTitle")} />
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <FormField label={t("batches.batchNumber")} info={fieldInfo("batchNumber")}>
              <input name="batch_number" required className={inputClass()} placeholder={t("batches.batchNumber")} />
            </FormField>
            <FormField label={t("productId")} info={fieldInfo("batchProductId")}>
              <input name="product_id" required className={inputClass()} placeholder={t("productId")} />
            </FormField>
            <FormField label={t("recipes.recipeId")} info={fieldInfo("recipeVersionId")}>
              <input name="recipe_version_id" className={inputClass()} placeholder={t("recipes.recipeId")} />
            </FormField>
            <FormField label={t("batches.plannedOutput")} info={fieldInfo("plannedOutput")}>
              <input name="planned_output_quantity" required type="number" min="0" step="0.001" className={inputClass()} placeholder={t("batches.plannedOutput")} />
            </FormField>
            <FormField label={t("recipes.outputUom")} info={fieldInfo("batchOutputUom")}>
              <select name="output_uom" className={inputClass()} defaultValue="unit">{uomOptions}</select>
            </FormField>
            <FormField label={t("batches.productionDate")} info={fieldInfo("productionDate")}>
              <input name="production_date" type="date" className={inputClass()} defaultValue={today()} />
            </FormField>
            <FormField label={t("batches.readyDate")} info={fieldInfo("readyDate")}>
              <input name="ready_date" type="date" className={inputClass()} aria-label={t("batches.readyDate")} />
            </FormField>
            <FormField label={t("notes")} info={fieldInfo("batchNotes")}>
              <input name="notes" className={inputClass()} placeholder={t("notes")} />
            </FormField>
          </div>
          <Button className="mt-3" type="submit" isLoading={busyAction === "create-batch"}>{t("batches.create")}</Button>
        </form>

        <div className="flex flex-wrap gap-2">
          {["", "draft", "produced", "cancelled"].map((status) => (
            <button key={status || "all"} type="button" onClick={() => setBatchStatus(status)} className={cn("rounded-pill px-4 py-1.5 text-sm font-medium", batchStatus === status ? "bg-muted-gold text-charcoal" : "bg-champagne-beige/50 text-soft-brown")}>{status ? labelFor(status) : tAdmin("all")}</button>
          ))}
        </div>

        <div className="overflow-x-auto rounded-brand border border-champagne-beige bg-cream">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-champagne-beige bg-champagne-beige/30"><tr><th className="px-4 py-3">{t("batches.batchNumber")}</th><th className="px-4 py-3">{t("productId")}</th><th className="px-4 py-3">{t("batches.output")}</th><th className="px-4 py-3">{t("status")}</th><th className="px-4 py-3">{t("actions")}</th></tr></thead>
            <tbody>
              {batches.map((batch) => (
                <tr key={batch.id} className="border-b border-champagne-beige/50 align-top last:border-0">
                  <td className="px-4 py-3"><span className="font-medium text-charcoal">{batch.batch_number}</span><p className="mt-1 text-xs text-soft-brown">{formatDate(batch.production_date, locale)}</p></td>
                  <td className="px-4 py-3 text-soft-brown">{batch.product_id}</td>
                  <td className="px-4 py-3 text-soft-brown">{batch.actual_output_quantity ?? batch.planned_output_quantity} / {batch.planned_output_quantity} {batch.output_uom}</td>
                  <td className="px-4 py-3"><div className="space-y-1"><StatusBadge value={batch.status} label={labelFor(batch.status)} /><StatusBadge value={batch.variance_review_state} label={labelFor(batch.variance_review_state)} /></div></td>
                  <td className="px-4 py-3"><div className="flex flex-wrap gap-2">
                    {batch.status === "draft" && <Button type="button" size="sm" variant="secondary" isLoading={busyAction === `post-${batch.id}`} onClick={() => quickPostBatch(batch)}>{t("batches.post")}</Button>}
                    {batch.status === "draft" && <Button type="button" size="sm" variant="ghost" isLoading={busyAction === `cancel-${batch.id}`} onClick={() => runAction(`cancel-${batch.id}`, () => cancelProductionBatch(batch.id).then(() => undefined), t("batches.cancelled"))}>{t("batches.cancel")}</Button>}
                    <Link href={`/admin/inventory/movements?source_type=production_batch&source_id=${batch.id}`} className="inline-flex h-9 items-center rounded-brand border border-champagne-beige px-3 text-sm text-soft-brown hover:bg-cream">{t("movements.title")}</Link>
                  </div></td>
                </tr>
              ))}
            </tbody>
          </table>
          {batches.length === 0 && <EmptyState label={t("batches.empty")} />}
        </div>

        <form onSubmit={handleBatchCorrection} className="rounded-brand border border-champagne-beige bg-cream p-4">
          <SectionTitle title={t("batches.correctionTitle")} />
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <FormField label={t("batches.batchId")} info={fieldInfo("correctionBatchId")}>
              <input name="batch_id" required className={inputClass()} placeholder={t("batches.batchId")} />
            </FormField>
            <FormField label={t("valuation.itemType")} info={fieldInfo("correctionItemType")}>
              <select name="item_type" className={inputClass()}><option value="material">{labelFor("material")}</option><option value="finished_good">{labelFor("finished_good")}</option></select>
            </FormField>
            <FormField label={t("batches.itemId")} info={fieldInfo("correctionItemId")}>
              <input name="item_id" required className={inputClass()} placeholder={t("batches.itemId")} />
            </FormField>
            <FormField label={t("materials.quantityDelta")} info={fieldInfo("correctionQuantityDelta")}>
              <input name="quantity_delta" required type="number" step="0.001" className={inputClass()} placeholder={t("materials.quantityDelta")} />
            </FormField>
            <FormField label={t("materials.stockUom")} info={fieldInfo("correctionUom")}>
              <select name="uom" required className={inputClass()} defaultValue="unit">{uomOptions}</select>
            </FormField>
            <FormField label={t("reason")} info={fieldInfo("correctionReason")}>
              <input name="reason" required className={inputClass()} placeholder={t("reason")} />
            </FormField>
          </div>
          <FormField label={t("notes")} info={fieldInfo("correctionNotes")} className="mt-3">
            <textarea name="notes" className={textareaClass()} placeholder={t("notes")} />
          </FormField>
          <Button className="mt-3" type="submit" isLoading={busyAction === "batch-correction"}>{t("batches.recordCorrection")}</Button>
        </form>
      </div>
    );
  }

  function renderValuation() {
    return (
      <div className="space-y-6">
        <form key={settings?.settings_version ?? "settings"} onSubmit={handleSettings} className="rounded-brand border border-champagne-beige bg-cream p-4">
          <SectionTitle title={t("valuation.settingsTitle")} info={t("valuation.settingsSubtitle")} />
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <FormField label={t("valuation.ledgerMode")} info={fieldInfo("ledgerMode")}>
              <select name="ledger_mode" className={inputClass()} defaultValue={settings?.ledger_mode ?? "setup"}><option value="legacy">{labelFor("legacy")}</option><option value="setup">{labelFor("setup")}</option><option value="ledger_managed">{labelFor("ledger_managed")}</option></select>
            </FormField>
            <FormField label={t("valuation.valuationMethod")} info={fieldInfo("valuationMethod")}>
              <select name="valuation_method" className={inputClass()} defaultValue={settings?.valuation_method ?? "weighted_average"}><option value="weighted_average">{labelFor("weighted_average")}</option><option value="fifo">{labelFor("fifo")}</option></select>
            </FormField>
            <FormField label={t("valuation.effectiveDate")} info={fieldInfo("settingsEffectiveDate")}>
              <input name="effective_date" type="date" className={inputClass()} defaultValue={settings?.effective_date ?? today()} />
            </FormField>
            <FormField label={t("valuation.cogsDateBasis")} info={fieldInfo("cogsDateBasis")}>
              <select name="cogs_date_basis" className={inputClass()} defaultValue={settings?.cogs_date_basis ?? "order_date"}><option value="order_date">{labelFor("order_date")}</option><option value="payment_date">{labelFor("payment_date")}</option><option value="shipment_date">{labelFor("shipment_date")}</option><option value="delivery_date">{labelFor("delivery_date")}</option><option value="period_close">{labelFor("period_close")}</option></select>
            </FormField>
            <FormField label={t("valuation.roundingPolicy")} info={fieldInfo("roundingPolicy")}>
              <select name="rounding_policy" className={inputClass()} defaultValue={settings?.rounding_policy ?? "half_up_2dp"}><option value="half_up_2dp">{labelFor("half_up_2dp")}</option><option value="half_up_4dp">{labelFor("half_up_4dp")}</option></select>
            </FormField>
            <FormField label={t("valuation.missingCostBehavior")} info={fieldInfo("missingCostBehavior")}>
              <select name="missing_cost_behavior" className={inputClass()} defaultValue={settings?.missing_cost_behavior ?? "block_official"}><option value="allow_estimate">{labelFor("allow_estimate")}</option><option value="warn">{labelFor("warn")}</option><option value="block_official">{labelFor("block_official")}</option></select>
            </FormField>
            <FormField label={t("currency")} info={fieldInfo("settingsCurrency")}>
              <input name="currency" className={inputClass()} defaultValue={settings?.currency ?? "EUR"} />
            </FormField>
            <FormField label={t("valuation.reviewer")} info={fieldInfo("reviewer")}>
              <input name="reviewed_by_name" className={inputClass()} defaultValue={settings?.reviewed_by_name ?? ""} placeholder={t("valuation.reviewer")} />
            </FormField>
          </div>
          <div className="mt-4 flex flex-wrap gap-4 text-sm text-soft-brown">
            <CheckboxField name="valuation_enabled" label={t("valuation.enabled")} info={fieldInfo("valuationEnabled")} defaultChecked={settings?.valuation_enabled ?? false} />
            <CheckboxField name="accountant_reviewed" label={t("valuation.accountantReviewed")} info={fieldInfo("accountantReviewed")} defaultChecked={settings?.accountant_reviewed ?? false} />
          </div>
          <FormField label={t("valuation.reviewNotes")} info={fieldInfo("reviewNotes")} className="mt-3">
            <textarea name="review_notes" className={textareaClass()} defaultValue={settings?.review_notes ?? ""} placeholder={t("valuation.reviewNotes")} />
          </FormField>
          <Button className="mt-3" type="submit" isLoading={busyAction === "settings"}>{t("valuation.saveSettings")}</Button>
        </form>

        <div className="grid gap-6 lg:grid-cols-2">
          <form onSubmit={handleOpeningBalance} className="rounded-brand border border-champagne-beige bg-cream p-4">
            <SectionTitle title={t("valuation.openingTitle")} />
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <FormField label={t("valuation.itemType")} info={fieldInfo("openingItemType")}>
                <select name="item_type" className={inputClass()}><option value="material">{labelFor("material")}</option><option value="finished_good">{labelFor("finished_good")}</option></select>
              </FormField>
              <FormField label={t("valuation.itemId")} info={fieldInfo("openingItemId")}>
                <input name="item_id" required className={inputClass()} placeholder={t("valuation.itemId")} />
              </FormField>
              <FormField label={t("quantity")} info={fieldInfo("openingQuantity")}>
                <input name="quantity" required type="number" min="0" step="0.001" className={inputClass()} placeholder={t("quantity")} />
              </FormField>
              <FormField label={t("materials.stockUom")} info={fieldInfo("openingUom")}>
                <select name="uom" required className={inputClass()} defaultValue="unit">{uomOptions}</select>
              </FormField>
              <FormField label={t("valuation.unitValue")} info={fieldInfo("unitValue")}>
                <input name="unit_value_amount" className={inputClass()} placeholder={t("valuation.unitValue")} />
              </FormField>
              <FormField label={t("valuation.totalValueCents")} info={fieldInfo("openingTotalValueCents")}>
                <input name="total_value_cents" type="number" min="0" step="1" className={inputClass()} placeholder={t("valuation.totalValueCents")} />
              </FormField>
            </div>
            <div className="mt-4 text-sm text-soft-brown">
              <CheckboxField name="reviewed" label={t("valuation.reviewed")} info={fieldInfo("openingReviewed")} />
            </div>
            <FormField label={t("notes")} info={fieldInfo("openingNotes")} className="mt-3">
              <textarea name="notes" className={textareaClass()} placeholder={t("notes")} />
            </FormField>
            <Button className="mt-3" type="submit" isLoading={busyAction === "opening-balance"}>{t("valuation.recordOpening")}</Button>
          </form>

          <form onSubmit={handleClosePreview} className="rounded-brand border border-champagne-beige bg-cream p-4">
            <SectionTitle title={t("valuation.closePreview")} />
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <FormField label={t("valuation.periodStart")} info={fieldInfo("periodStart")}>
                <input name="period_start" type="date" className={inputClass()} defaultValue={monthStart()} />
              </FormField>
              <FormField label={t("valuation.periodEnd")} info={fieldInfo("periodEnd")}>
                <input name="period_end" type="date" className={inputClass()} defaultValue={today()} />
              </FormField>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button type="submit" isLoading={busyAction === "close-preview"}>{t("valuation.preview")}</Button>
              <Button type="button" variant="secondary" isLoading={busyAction === "generate-layers"} onClick={() => runAction("generate-layers", () => generateValuationLayers().then(() => undefined), t("valuation.layersGenerated"))}>{t("valuation.generateLayers")}</Button>
              <Button type="button" variant="secondary" isLoading={busyAction === "generate-cogs"} onClick={() => runAction("generate-cogs", () => generateCogsRows().then(() => undefined), t("valuation.cogsGenerated"))}>{t("valuation.generateCogs")}</Button>
            </div>
            {closePreview && <dl className="mt-4 grid gap-3 sm:grid-cols-2"><Field label={t("valuation.endingValue")} value={formatMoneyCents(closePreview.ending_value_cents)} /><Field label={t("valuation.cogs") } value={formatMoneyCents(closePreview.sales_cogs_value_cents)} /><Field label={t("exceptions")} value={closePreview.exception_count} /><Field label={t("valuation.official")} value={closePreview.official ? t("yes") : t("no")} /></dl>}
          </form>
        </div>

        <div className="grid gap-6 xl:grid-cols-2">
          <section className="rounded-brand border border-champagne-beige bg-cream p-4"><SectionTitle title={t("valuation.layers")} /><ValuationLayerList rows={valuationLayers} locale={locale} /></section>
          <section className="rounded-brand border border-champagne-beige bg-cream p-4"><SectionTitle title={t("valuation.cogsRows")} /><CogsList rows={cogsRows} locale={locale} /></section>
          <section className="rounded-brand border border-champagne-beige bg-cream p-4 xl:col-span-2"><SectionTitle title={t("valuation.exceptions")} /><ExceptionList rows={exceptions} locale={locale} /></section>
        </div>
      </div>
    );
  }

  function renderMovements() {
    return (
      <div className="space-y-6">
        <form onSubmit={handleMovementFilter} className="rounded-brand border border-champagne-beige bg-cream p-4">
          <SectionTitle title={t("movements.filters")} />
          <div className="mt-4 grid gap-3 md:grid-cols-6">
            <FormField label={t("valuation.itemType")} info={fieldInfo("movementItemType")}>
              <select name="item_type" className={inputClass()} defaultValue={movementFilters.itemType}><option value="">{tAdmin("all")}</option><option value="material">{labelFor("material")}</option><option value="finished_good">{labelFor("finished_good")}</option></select>
            </FormField>
            <FormField label={t("movements.itemId")} info={fieldInfo("movementItemId")}>
              <input name="item_id" className={inputClass()} defaultValue={movementFilters.itemId} placeholder={t("movements.itemId")} />
            </FormField>
            <FormField label={t("movements.sourceType")} info={fieldInfo("sourceType")}>
              <input name="source_type" className={inputClass()} defaultValue={movementFilters.sourceType} placeholder={t("movements.sourceType")} />
            </FormField>
            <FormField label={t("movements.sourceId")} info={fieldInfo("sourceId")}>
              <input name="source_id" className={inputClass()} defaultValue={movementFilters.sourceId} placeholder={t("movements.sourceId")} />
            </FormField>
            <FormField label={t("orderId")} info={fieldInfo("orderId")}>
              <input name="order_id" className={inputClass()} defaultValue={movementFilters.orderId} placeholder={t("orderId")} />
            </FormField>
            <FormField label={t("movements.movementType")} info={fieldInfo("movementType")}>
              <input name="movement_type" className={inputClass()} defaultValue={movementFilters.movementType} placeholder={t("movements.movementType")} />
            </FormField>
          </div>
          <Button className="mt-3" type="submit">{t("movements.apply")}</Button>
        </form>
        <section className="rounded-brand border border-champagne-beige bg-cream p-4">
          <SectionTitle title={t("movements.title")} subtitle={t("movements.count", { count: movementTotal })} />
          <MovementList rows={movements} locale={locale} />
        </section>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex items-center gap-2">
          <h1 className="font-heading text-2xl font-semibold text-charcoal">{t("title")}</h1>
        </div>
        {isRefreshing && <span className="text-sm text-soft-brown">{t("refreshing")}</span>}
      </div>

      {error && <div className="rounded-brand border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}
      {success && <div className="rounded-brand border border-green-200 bg-green-50 p-4 text-sm text-green-800">{success}</div>}

      <div className="flex flex-wrap gap-2">
        {TABS.map((tab) => (
          <button key={tab} type="button" onClick={() => setActiveTab(tab)} className={cn("rounded-pill px-4 py-2 text-sm font-medium transition-colors", activeTab === tab ? "bg-muted-gold text-charcoal" : "bg-champagne-beige/50 text-soft-brown hover:bg-champagne-beige")} aria-pressed={activeTab === tab}>
            {t(`tabs.${tab}` as Parameters<typeof t>[0])}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="space-y-4"><Skeleton className="h-32 w-full" /><Skeleton className="h-64 w-full" /></div>
      ) : (
        <>
          {activeTab === "materials" && renderMaterials()}
          {activeTab === "recipes" && renderRecipes()}
          {activeTab === "batches" && renderBatches()}
          {activeTab === "valuation" && renderValuation()}
          {activeTab === "movements" && renderMovements()}
        </>
      )}
    </div>
  );
}

function MovementList({ rows, locale }: { rows: InventoryMovementResponse[]; locale: string }) {
  const t = useTranslations("admin.inventory");
  const labelFor = (value: string | null | undefined): string => {
    if (!value) return "-";
    return INVENTORY_LABEL_KEYS.has(value) ? t(`labels.${value}`) : statusText(value);
  };
  if (rows.length === 0) return <EmptyState label={t("movements.empty")} />;
  return (
    <div className="mt-4 overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-champagne-beige"><tr><th className="px-3 py-2">{t("movements.movementType")}</th><th className="px-3 py-2">{t("movements.itemId")}</th><th className="px-3 py-2">{t("quantity")}</th><th className="px-3 py-2">{t("status")}</th><th className="px-3 py-2">{t("date")}</th></tr></thead>
        <tbody>{rows.map((row) => <tr key={row.id} className="border-b border-champagne-beige/50 last:border-0"><td className="px-3 py-2 text-charcoal">{labelFor(row.movement_type)}<p className="text-xs text-soft-brown">{labelFor(row.source_type)} {row.source_id || ""}</p></td><td className="px-3 py-2 font-mono text-xs text-soft-brown">{labelFor(row.item_type)}: {row.item_id}</td><td className="px-3 py-2 text-soft-brown">{row.quantity_delta} {labelFor(row.uom)}</td><td className="px-3 py-2"><StatusBadge value={row.review_state} label={labelFor(row.review_state)} /></td><td className="px-3 py-2 text-soft-brown">{formatDate(row.occurred_at, locale)}</td></tr>)}</tbody>
      </table>
    </div>
  );
}

function ValuationLayerList({ rows, locale }: { rows: ValuationLayerResponse[]; locale: string }) {
  const t = useTranslations("admin.inventory");
  const labelFor = (value: string | null | undefined): string => {
    if (!value) return "-";
    return INVENTORY_LABEL_KEYS.has(value) ? t(`labels.${value}`) : statusText(value);
  };
  if (rows.length === 0) return <EmptyState label={t("valuation.noLayers")} />;
  return <div className="mt-4 overflow-x-auto"><table className="w-full text-left text-sm"><thead className="border-b border-champagne-beige"><tr><th className="px-3 py-2">{t("valuation.itemId")}</th><th className="px-3 py-2">{t("quantity")}</th><th className="px-3 py-2">{t("valuation.value")}</th><th className="px-3 py-2">{t("status")}</th><th className="px-3 py-2">{t("date")}</th></tr></thead><tbody>{rows.map((row) => <tr key={row.id} className="border-b border-champagne-beige/50 last:border-0"><td className="px-3 py-2 font-mono text-xs text-soft-brown">{labelFor(row.item_type)}: {row.item_id}</td><td className="px-3 py-2 text-soft-brown">{row.quantity}</td><td className="px-3 py-2 text-soft-brown">{formatMoneyCents(row.total_value_cents)}</td><td className="px-3 py-2"><StatusBadge value={row.review_state} label={labelFor(row.review_state)} /></td><td className="px-3 py-2 text-soft-brown">{formatDate(row.valuation_date, locale)}</td></tr>)}</tbody></table></div>;
}

function CogsList({ rows, locale }: { rows: CogsLedgerResponse[]; locale: string }) {
  const t = useTranslations("admin.inventory");
  const labelFor = (value: string | null | undefined): string => {
    if (!value) return "-";
    return INVENTORY_LABEL_KEYS.has(value) ? t(`labels.${value}`) : statusText(value);
  };
  if (rows.length === 0) return <EmptyState label={t("valuation.noCogs")} />;
  return <div className="mt-4 overflow-x-auto"><table className="w-full text-left text-sm"><thead className="border-b border-champagne-beige"><tr><th className="px-3 py-2">{t("orderId")}</th><th className="px-3 py-2">{t("productId")}</th><th className="px-3 py-2">{t("quantity")}</th><th className="px-3 py-2">{t("valuation.cogs")}</th><th className="px-3 py-2">{t("status")}</th><th className="px-3 py-2">{t("date")}</th></tr></thead><tbody>{rows.map((row) => <tr key={row.id} className="border-b border-champagne-beige/50 last:border-0"><td className="px-3 py-2 font-mono text-xs text-soft-brown">{row.order_number || row.order_id || "-"}</td><td className="px-3 py-2 text-soft-brown">{row.product_id || "-"}</td><td className="px-3 py-2 text-soft-brown">{row.quantity_sold}</td><td className="px-3 py-2 text-soft-brown">{formatMoneyCents(row.total_cost_cents)}</td><td className="px-3 py-2"><StatusBadge value={row.review_state} label={labelFor(row.review_state)} /></td><td className="px-3 py-2 text-soft-brown">{formatDate(row.cogs_date, locale)}</td></tr>)}</tbody></table></div>;
}

function ExceptionList({ rows, locale }: { rows: InventoryExceptionResponse[]; locale: string }) {
  const t = useTranslations("admin.inventory");
  const labelFor = (value: string | null | undefined): string => {
    if (!value) return "-";
    return INVENTORY_LABEL_KEYS.has(value) ? t(`labels.${value}`) : statusText(value);
  };
  if (rows.length === 0) return <EmptyState label={t("valuation.noExceptions")} />;
  return <div className="mt-4 overflow-x-auto"><table className="w-full text-left text-sm"><thead className="border-b border-champagne-beige"><tr><th className="px-3 py-2">{t("type")}</th><th className="px-3 py-2">{t("severity")}</th><th className="px-3 py-2">{t("message")}</th><th className="px-3 py-2">{t("date")}</th></tr></thead><tbody>{rows.map((row) => <tr key={row.id} className="border-b border-champagne-beige/50 last:border-0"><td className="px-3 py-2 text-charcoal">{labelFor(row.exception_type)}<p className="text-xs text-soft-brown">{labelFor(row.target_type || row.source_type)}: {row.target_id || row.source_id || "-"}</p></td><td className="px-3 py-2"><StatusBadge value={row.severity} label={labelFor(row.severity)} /></td><td className="px-3 py-2 text-soft-brown">{row.message}</td><td className="px-3 py-2 text-soft-brown">{formatDate(row.created_at, locale)}</td></tr>)}</tbody></table></div>;
}
