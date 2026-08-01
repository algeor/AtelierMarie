import React from "react";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithIntl } from "../../test-utils";
import type {
  CogsLedgerListResponse,
  InventoryClosePreviewResponse,
  InventoryMovementListResponse,
  InventoryValuationSettingsResponse,
  MaterialDetailResponse,
  MaterialListResponse,
  ProductionBatchListResponse,
  RecipeVersionListResponse,
  ValuationLayerListResponse,
} from "@/lib/types";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a>,
}));

vi.mock("@/lib/api", () => ({
  activateRecipe: vi.fn(),
  archiveRecipe: vi.fn(),
  cancelProductionBatch: vi.fn(),
  correctProductionBatch: vi.fn(),
  createMaterial: vi.fn(),
  createMaterialAdjustment: vi.fn(),
  createMaterialReceipt: vi.fn(),
  createProductionBatch: vi.fn(),
  createRecipe: vi.fn(),
  createRecipeCostSnapshot: vi.fn(),
  generateCogsRows: vi.fn(),
  generateValuationLayers: vi.fn(),
  getInventoryClosePreview: vi.fn(),
  getInventoryValuationSettings: vi.fn(),
  getMaterial: vi.fn(),
  listCogsRows: vi.fn(),
  listInventoryExceptions: vi.fn(),
  listInventoryMovements: vi.fn(),
  listMaterials: vi.fn(),
  listProductionBatches: vi.fn(),
  listRecipes: vi.fn(),
  listValuationLayers: vi.fn(),
  postProductionBatch: vi.fn(),
  recordOpeningBalance: vi.fn(),
  reviewRecipe: vi.fn(),
  updateInventoryValuationSettings: vi.fn(),
}));

import {
  activateRecipe,
  createMaterialAdjustment,
  createMaterialReceipt,
  createProductionBatch,
  createRecipe,
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
  updateInventoryValuationSettings,
} from "@/lib/api";
import { InventoryWorkspace } from "@/components/admin/inventory/InventoryWorkspace";

const materialList: MaterialListResponse = {
  materials: [
    {
      id: "mat-wax",
      sku: "WAX-SOY",
      name: "Soy wax",
      category: "wax",
      stock_uom: "g",
      purchase_uom: "kg",
      purchase_to_stock_factor: 1000,
      preferred_supplier_name: "Candle Supplier",
      preferred_supplier_sku: null,
      reorder_threshold: 1000,
      active: true,
      lot_tracked: true,
      expiry_tracked: false,
      evidence_required: true,
      on_hand_quantity: 500,
      reorder_status: "below_threshold",
      open_exception_count: 1,
      latest_movement_at: "2026-08-01T10:00:00Z",
      notes: null,
      created_at: "2026-08-01T10:00:00Z",
      updated_at: "2026-08-01T10:00:00Z",
    },
  ],
  total: 1,
};

const materialDetail: MaterialDetailResponse = {
  ...materialList.materials[0]!,
  lots: [
    {
      id: "lot-1",
      material_id: "mat-wax",
      receipt_id: "receipt-1",
      supplier_lot: "LOT-1",
      expiry_date: null,
      use_by_date: null,
      received_quantity: 500,
      stock_uom: "g",
      remaining_quantity_snapshot: 500,
      unit_cost_amount: "0.02",
      currency: "EUR",
      supplier_name: "Candle Supplier",
      review_state: "needs_review",
      lot_status: "unknown",
      created_at: "2026-08-01T10:00:00Z",
      updated_at: "2026-08-01T10:00:00Z",
    },
  ],
  recent_movements: [
    {
      id: "mov-1",
      item_type: "material",
      item_id: "mat-wax",
      movement_type: "receipt",
      quantity_delta: 500,
      uom: "g",
      source_type: "material_receipt",
      source_id: "receipt-1",
      material_lot_id: "lot-1",
      actor_user_id: null,
      actor_email: null,
      reason: null,
      notes: null,
      review_state: "estimate",
      occurred_at: "2026-08-01T10:00:00Z",
      created_at: "2026-08-01T10:00:00Z",
    },
  ],
  exceptions: [
    {
      id: "exc-1",
      exception_type: "missing_receipt_evidence",
      severity: "blocking",
      target_type: "material",
      target_id: "mat-wax",
      source_type: "material_receipt",
      source_id: "receipt-1",
      status: "open",
      message: "Missing receipt evidence",
      created_at: "2026-08-01T10:00:00Z",
    },
  ],
};

const recipeList: RecipeVersionListResponse = {
  recipes: [
    {
      id: "recipe-1",
      product_id: "lavender-candle",
      version_label: "v1",
      status: "draft",
      effective_date: "2026-08-01",
      output_quantity: 24,
      output_uom: "unit",
      review_state: "estimate",
      accountant_reviewed: false,
      reviewed_by_admin_id: null,
      reviewed_at: null,
      notes: null,
      created_by_admin_id: null,
      updated_by_admin_id: null,
      components: [],
      latest_cost_snapshot: null,
      diagnostics: [],
      created_at: "2026-08-01T10:00:00Z",
      updated_at: "2026-08-01T10:00:00Z",
    },
  ],
  total: 1,
};

const batchList: ProductionBatchListResponse = {
  batches: [
    {
      id: "batch-1",
      batch_number: "B-001",
      product_id: "lavender-candle",
      recipe_version_id: "recipe-1",
      planned_output_quantity: 24,
      actual_output_quantity: null,
      output_uom: "unit",
      status: "draft",
      production_date: "2026-08-01",
      ready_date: null,
      cost_snapshot_id: null,
      variance_review_state: "not_reviewed",
      actor_user_id: null,
      notes: null,
      consumption: [
        {
          id: "cons-1",
          production_batch_id: "batch-1",
          recipe_component_id: null,
          material_id: "mat-wax",
          material_name: "Soy wax",
          material_lot_id: null,
          expected_quantity: 500,
          actual_quantity: null,
          waste_quantity: 0,
          uom: "g",
          unit_cost_amount: "0.02",
          currency: "EUR",
          movement_id: null,
          review_state: "draft",
          created_at: "2026-08-01T10:00:00Z",
          updated_at: "2026-08-01T10:00:00Z",
        },
      ],
      outputs: [],
      exceptions: [],
      created_by_admin_id: null,
      updated_by_admin_id: null,
      created_at: "2026-08-01T10:00:00Z",
      updated_at: "2026-08-01T10:00:00Z",
    },
  ],
  total: 1,
};

const settings: InventoryValuationSettingsResponse = {
  id: "default",
  ledger_mode: "setup",
  valuation_enabled: false,
  valuation_method: "weighted_average",
  effective_date: "2026-08-01",
  cogs_date_basis: "order_date",
  rounding_policy: "half_up_2dp",
  missing_cost_behavior: "block_official",
  included_cost_components: null,
  write_off_mapping: null,
  currency: "EUR",
  settings_version: 1,
  accountant_reviewed: false,
  reviewed_by_admin_id: null,
  reviewed_by_name: null,
  reviewed_at: null,
  review_notes: null,
  created_at: "2026-08-01T10:00:00Z",
  updated_at: "2026-08-01T10:00:00Z",
};

const movements: InventoryMovementListResponse = {
  movements: materialDetail.recent_movements,
  total: 1,
};

const layers: ValuationLayerListResponse = {
  layers: [
    {
      id: "layer-1",
      movement_id: "mov-1",
      item_type: "material",
      item_id: "mat-wax",
      quantity: 500,
      unit_value_amount: "0.02",
      total_value_cents: 1000,
      currency: "EUR",
      valuation_method: "weighted_average",
      source_type: "material_receipt",
      source_id: "receipt-1",
      valuation_date: "2026-08-01",
      review_state: "estimate",
      method_metadata_json: null,
      reversal_layer_id: null,
      created_at: "2026-08-01T10:00:00Z",
    },
  ],
  total: 1,
};

const cogs: CogsLedgerListResponse = {
  rows: [
    {
      id: "cogs-1",
      order_id: "order-1",
      order_number: "AM-001",
      order_item_key: "order-1:lavender-candle",
      product_id: "lavender-candle",
      quantity_sold: 1,
      cogs_date: "2026-08-01",
      unit_cost_amount: "2.50",
      total_cost_cents: 250,
      currency: "EUR",
      valuation_method: "weighted_average",
      source_movement_id: "mov-sale",
      source_valuation_layer_id: "layer-1",
      source_finished_batch_id: "batch-1",
      review_state: "estimate",
      reversal_cogs_id: null,
      created_at: "2026-08-01T10:00:00Z",
    },
  ],
  total: 1,
};

const closePreview: InventoryClosePreviewResponse = {
  period_start: "2026-08-01",
  period_end: "2026-08-31",
  currency: "EUR",
  valuation_method: "weighted_average",
  official: false,
  opening_value_cents: 0,
  receipts_value_cents: 1000,
  production_consumption_value_cents: -500,
  finished_output_value_cents: 750,
  sales_cogs_value_cents: -250,
  returns_value_cents: 0,
  adjustments_value_cents: 0,
  ending_value_cents: 1000,
  exception_count: 1,
  policy_snapshot: {},
};

function mockInventoryApi() {
  vi.mocked(listMaterials).mockResolvedValue(materialList);
  vi.mocked(getMaterial).mockResolvedValue(materialDetail);
  vi.mocked(listRecipes).mockResolvedValue(recipeList);
  vi.mocked(listProductionBatches).mockResolvedValue(batchList);
  vi.mocked(getInventoryValuationSettings).mockResolvedValue(settings);
  vi.mocked(listInventoryMovements).mockResolvedValue(movements);
  vi.mocked(listValuationLayers).mockResolvedValue(layers);
  vi.mocked(listCogsRows).mockResolvedValue(cogs);
  vi.mocked(listInventoryExceptions).mockResolvedValue(materialDetail.exceptions);
  vi.mocked(createMaterialReceipt).mockResolvedValue({} as never);
  vi.mocked(createMaterialAdjustment).mockResolvedValue(materialDetail.recent_movements[0]!);
  vi.mocked(createRecipe).mockResolvedValue(recipeList.recipes[0]!);
  vi.mocked(activateRecipe).mockResolvedValue(recipeList.recipes[0]!);
  vi.mocked(createProductionBatch).mockResolvedValue(batchList.batches[0]!);
  vi.mocked(postProductionBatch).mockResolvedValue(batchList.batches[0]!);
  vi.mocked(updateInventoryValuationSettings).mockResolvedValue(settings);
  vi.mocked(recordOpeningBalance).mockResolvedValue(layers.layers[0]!);
  vi.mocked(generateValuationLayers).mockResolvedValue(layers);
  vi.mocked(generateCogsRows).mockResolvedValue(cogs);
  vi.mocked(getInventoryClosePreview).mockResolvedValue(closePreview);
}

describe("Admin inventory workspace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockInventoryApi();
  });

  it("shows material detail and records receipt plus write-off movement", async () => {
    renderWithIntl(<InventoryWorkspace initialTab="materials" />);

    fireEvent.click(await screen.findByRole("button", { name: "Soy wax" }));
    expect(await screen.findByText("Movement history")).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("Quantity"), { target: { value: "1000" } });
    fireEvent.click(screen.getByRole("button", { name: "Record receipt" }));
    await waitFor(() => expect(createMaterialReceipt).toHaveBeenCalledWith("mat-wax", expect.objectContaining({ quantity: 1000 })));

    fireEvent.change(screen.getByPlaceholderText("Quantity delta"), { target: { value: "-50" } });
    fireEvent.change(screen.getByPlaceholderText("Reason"), { target: { value: "Spoiled wax" } });
    fireEvent.click(screen.getByRole("button", { name: "Save stock change" }));
    await waitFor(() => expect(createMaterialAdjustment).toHaveBeenCalledWith("mat-wax", expect.objectContaining({ quantity_delta: -50 })));
  });

  it("creates recipe components and supports activation", async () => {
    renderWithIntl(<InventoryWorkspace initialTab="recipes" />);

    expect(await screen.findByText("lavender-candle")).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText("Product code"), { target: { value: "lavender-candle" } });
    fireEvent.change(screen.getByPlaceholderText("Version label"), { target: { value: "v2" } });
    fireEvent.change(screen.getByPlaceholderText("Output quantity"), { target: { value: "24" } });
    fireEvent.change(screen.getByPlaceholderText("soy-wax,500,g,per_batch,3"), { target: { value: "mat-wax,500,g,per_batch,3" } });
    fireEvent.click(screen.getByRole("button", { name: "Create recipe" }));

    await waitFor(() => expect(createRecipe).toHaveBeenCalledWith(expect.objectContaining({ product_id: "lavender-candle" })));
    fireEvent.click(screen.getByRole("button", { name: "Activate" }));
    await waitFor(() => expect(activateRecipe).toHaveBeenCalledWith("recipe-1"));
  });

  it("creates and posts production batches", async () => {
    renderWithIntl(<InventoryWorkspace initialTab="batches" />);

    expect(await screen.findByText("B-001")).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText("Batch number"), { target: { value: "B-002" } });
    fireEvent.change(screen.getByPlaceholderText("Product code"), { target: { value: "lavender-candle" } });
    fireEvent.change(screen.getByPlaceholderText("Planned output"), { target: { value: "24" } });
    fireEvent.click(screen.getByRole("button", { name: "Create batch" }));

    await waitFor(() => expect(createProductionBatch).toHaveBeenCalledWith(expect.objectContaining({ batch_number: "B-002" })));
    fireEvent.click(screen.getByRole("button", { name: "Mark produced" }));
    await waitFor(() => expect(postProductionBatch).toHaveBeenCalledWith("batch-1", expect.objectContaining({ actual_output_quantity: 24 })));
  });

  it("updates valuation settings, previews close, and generates layers and COGS", async () => {
    renderWithIntl(<InventoryWorkspace initialTab="valuation" />);

    expect(await screen.findByText("Stock value settings")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Save settings" }));
    await waitFor(() => expect(updateInventoryValuationSettings).toHaveBeenCalled());

    fireEvent.change(screen.getByPlaceholderText("Item code"), { target: { value: "mat-wax" } });
    fireEvent.change(screen.getByPlaceholderText("Quantity"), { target: { value: "500" } });
    fireEvent.click(screen.getByRole("button", { name: "Record opening balance" }));
    await waitFor(() => expect(recordOpeningBalance).toHaveBeenCalledWith(expect.objectContaining({ item_id: "mat-wax" })));

    fireEvent.click(screen.getByRole("button", { name: "Preview close" }));
    await waitFor(() => expect(getInventoryClosePreview).toHaveBeenCalled());
    expect(await screen.findByText("Ending value")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Calculate stock value" }));
    await waitFor(() => expect(generateValuationLayers).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("button", { name: "Calculate sold cost" }));
    await waitFor(() => expect(generateCogsRows).toHaveBeenCalled());
  });

  it("filters movement ledger rows", async () => {
    renderWithIntl(<InventoryWorkspace initialTab="movements" />);

    expect(await screen.findByText("receipt")).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText("Item code"), { target: { value: "mat-wax" } });
    fireEvent.click(screen.getByRole("button", { name: "Apply filters" }));

    await waitFor(() => expect(listInventoryMovements).toHaveBeenLastCalledWith(expect.objectContaining({ itemId: "mat-wax" })));
  });
});
