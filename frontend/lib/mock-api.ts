/**
 * Mock API layer — returns hardcoded data matching TypeScript types.
 * Used when NEXT_PUBLIC_USE_MOCK_API is true (the default in development).
 */

import type {
  AdminProductFilters,
  AdminProductListResponse,
  AdminProductResponse,
  AdminStats,
  AdminTaxonomyTerm,
  AboutAdminResponse,
  AboutItemAdmin,
  AboutPublicResponse,
  AboutSectionAdmin,
  AuthTokenResponse,
  BannerAdminResponse,
  BannerUpdateRequest,
  BulkDiscountRequest,
  BulkDiscountResponse,
  BulkResultItem,
  CalculateShippingRequest,
  CalculateShippingResponse,
  CallbackOutcome,
  CampaignCreateRequest,
  CampaignListResponse,
  CampaignResponse,
  CampaignUpdateRequest,
  CartItemResponse,
  CartResponse,
  CommentCreateRequest,
  CommentListResponse,
  CommentResponse,
  CommentSort,
  ContactRequest,
  ContactResponse,
  CookieInventoryAdminResponse,
  CookieSectionAdminResponse,
  CookiesAdminResponse,
  CookiesPageAdminResponse,
  CookiesResponse,
  CodSettlementResponse,
  Courier,
  CourierClaimStatus,
  CreateStripeRefundRequest,
  DeliveryConfigResponse,
  DeliverySettingsResponse,
  DeliverySettingsUpdate,
  EcontConnectionTestResponse,
  EcontFulfillmentActionResponse,
  EcontManualStatusRequest,
  EcontOrderFulfillmentResponse,
  EcontOrderRepairRequest,
  EcontSettingsResponse,
  EcontSettingsUpdate,
  SpeedyActionResponse,
  SpeedyAdminOverviewResponse,
  SpeedyCancelShipmentRequest,
  SpeedyEventResponse,
  SpeedyPickupRequest,
  SpeedyPickupResponse,
  SpeedyPickupTermsRequest,
  SpeedyPickupTermsResponse,
  SpeedyShipmentInfoRequest,
  SpeedyShipmentInfoResponse,
  SpeedyShipmentSearchRequest,
  SpeedyShipmentSearchResponse,
  AdminOrderDetailResponse,
  CityPlace,
  CreateOrderRequest,
  CreateReturnCaseRequest,
  CreateAboutItemRequest,
  CreateFaqItemRequest,
  CreateProductRequest,
  CreateTaxonomyTermRequest,
  FaqAdminResponse,
  FaqItemAdminResponse,
  FaqResponse,
  FaqSectionAdminResponse,
  ImageUploadResponse,
  LegalIdentityResponse,
  InspectReturnCaseRequest,
  OfficeResponse,
  OfficeType,
  CustomerOrderFilters,
  OrderListResponse,
  OrderResponse,
  OrderStatus,
  PaymentRefundResponse,
  PaymentMethod,
  PaymentSettingsResponse,
  PaymentSettingsUpdate,
  PaymentStatus,
  ManualPaymentAction,
  PatchAboutItemRequest,
  PatchAboutSectionRequest,
  ProductListQuery,
  ProductListResponse,
  ProductImage,
  SavedProductListResponse,
  SavedProductStatusResponse,
  PrivacyAdminResponse,
  PrivacyPageAdminResponse,
  PrivacyResponse,
  PrivacySectionAdminResponse,
  PublicPaymentSettingsResponse,
  RecordCodSettlementRequest,
  ReturnCaseResponse,
  ShippingQuote,
  ProductResponse,
  ProductVideo,
  PublicBannerResponse,
  PublicSiteMediaResponse,
  ReactionCountsResponse,
  ReactionToggleRequest,
  ReactionToggleResponse,
  SiteMediaAdminResponse,
  SiteMediaAssetAdmin,
  SiteMediaKey,
  TaxonomyKind,
  TaxonomyResponse,
  TermsAdminResponse,
  TermsPageAdminResponse,
  TermsResponse,
  TermsSectionAdminResponse,
  ReorderFaqItemsRequest,
  UpdateTermsPageRequest,
  UpdateTermsSectionRequest,
  UpdatePrivacyPageRequest,
  UpdatePrivacySectionRequest,
  UpdateCookieInventoryRequest,
  UpdateCookieSectionRequest,
  UpdateCookiesPageRequest,
  UpdateFaqItemRequest,
  UpdateFaqSectionRequest,
  UpdateProductRequest,
  UpdateReturnAccountingRequest,
  UpdateTaxonomyTermRequest,
  UserResponse,
  VideoUploadResponse,
} from "./types";
import type {
  AccountantAcceptanceRequest,
  AccountingConfigurationResponse,
  AccountingDocumentListResponse,
  AccountingDocumentRequest,
  AccountingDocumentResponse,
  AccountingLedgerName,
  AccountingLedgerResponse,
  AdminOrderAccountingFilter,
  CategoryMappingRequest,
  CategoryMappingResponse,
  ExportSchemaSettingsRequest,
  ExportSchemaSettingsResponse,
  ExpenseEvidenceListResponse,
  ExpenseEvidenceRequest,
  ExpenseEvidenceResponse,
  ExpenseEvidenceSettingsRequest,
  ExpenseEvidenceSettingsResponse,
  ExpensePaymentStatusRequest,
  FinanceExceptionActionRequest,
  FinanceExceptionListResponse,
  FinanceExceptionResponse,
  FinanceExceptionStatus,
  FinanceExportPackageListResponse,
  FinanceExportPackageResponse,
  FinancePeriodActionRequest,
  FinancePeriodCreateRequest,
  FinancePeriodListResponse,
  FinancePeriodResponse,
  MissingProductCostDiagnosticsResponse,
  ProductCostSettingsRequest,
  ProductCostSettingsResponse,
  ProductCostVersionListResponse,
  ProductCostVersionRequest,
  ProductCostVersionResponse,
  SellerLegalProfileRequest,
  SellerLegalProfileResponse,
  StripeBalanceImportResponse,
  StripePayoutImportStatusResponse,
  VatFiscalSettingsRequest,
  VatFiscalSettingsResponse,
} from "./types";
import { ApiError } from "./api-client";
import { buildTrackingUrl } from "./tracking";
import enMessages from "@/messages/en.json";
import bgMessages from "@/messages/bg.json";

// --- Helpers ---

function mockError(code: string, message: string): never {
  throw new ApiError({ error: { code, message, details: null } });
}

function cloneMock<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function stringField(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function formatMockAddress(
  address: Record<string, unknown> | null | undefined,
): string | null {
  if (!address) return null;
  const formatted =
    stringField(address.formatted) ?? stringField(address.formatted_address);
  if (formatted) return formatted;
  const cityLine = [stringField(address.postal_code), stringField(address.city)]
    .filter(Boolean)
    .join(" ");
  const parts = [
    stringField(address.line1),
    stringField(address.line2),
    cityLine || null,
    stringField(address.country),
  ].filter(Boolean);
  return parts.join(", ") || null;
}

/** Simulate network latency (50–150ms). */
function delay(): Promise<void> {
  const ms = 50 + Math.floor(Math.random() * 100);
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** Generate a UUID-like identifier for orders. */
function generateOrderId(): string {
  const hex = () => Math.floor(Math.random() * 16).toString(16);
  const seg = (n: number) => Array.from({ length: n }, hex).join("");
  return `${seg(8)}-${seg(4)}-4${seg(3)}-${seg(4)}-${seg(12)}`;
}

// --- Mock Data ---

const MOCK_NOW = "2026-08-01T10:00:00Z";

let mockAccountingConfig: AccountingConfigurationResponse = {
  seller_profile: {
    id: 1,
    effective_date: "2026-08-01",
    reviewed: true,
    company_display_name: "Atelier Marie",
    legal_name: "Atelier Marie EOOD",
    uic_eik: "000000000",
    vat_identification_number: null,
    registered_address: { country: "BG", city: "Sofia" },
    contact_email: "accounting@theateliermarie.com",
    bank_details: { iban: "REDACTED" },
    default_currency: "EUR",
    bank_details_configured: true,
    created_by_admin_id: "mock-admin",
    created_at: MOCK_NOW,
  },
  vat_fiscal_settings: {
    id: 1,
    effective_date: "2026-08-01",
    reviewed: true,
    vat_mode: "not_registered",
    oss_mode: "not_applicable",
    default_domestic_vat_treatment: "BG domestic review",
    fiscal_document_mode: "external_reference",
    document_rules: {
      cod: "fiscal_receipt_required",
      card: "invoice_reference_optional",
    },
    threshold_warnings: { review_before_registration_threshold: true },
    tolerance_cents: 1,
    warning_text: "Configuration must be reviewed by the accountant.",
    created_by_admin_id: "mock-admin",
    created_at: MOCK_NOW,
  },
  category_mappings: [
    {
      id: 1,
      mapping_key: "sales_revenue",
      category_code: "701",
      category_label: "Sales revenue",
      is_required: true,
      reviewed: true,
      created_at: MOCK_NOW,
      updated_at: MOCK_NOW,
    },
    {
      id: 2,
      mapping_key: "materials",
      category_code: "601",
      category_label: "Materials and wax",
      is_required: true,
      reviewed: false,
      created_at: MOCK_NOW,
      updated_at: MOCK_NOW,
    },
  ],
  export_schema: {
    id: "default",
    workbook_language: "en",
    date_format: "yyyy-mm-dd",
    decimal_separator: ".",
    default_period_range: "monthly",
    included_tabs: [
      "summary",
      "sales",
      "payments",
      "expenses",
      "product_costs",
      "exceptions",
    ],
    custom_columns: null,
    reviewed: true,
    updated_at: MOCK_NOW,
  },
  expense_settings: {
    id: "default",
    required_document_categories: ["materials", "packaging"],
    allowed_payment_statuses: [
      "unpaid",
      "paid",
      "partially_paid",
      "reimbursed",
    ],
    default_category_mappings: { materials: "601", packaging: "602" },
    close_behavior: "block",
    reviewed: true,
    updated_at: MOCK_NOW,
  },
  product_cost_settings: {
    id: "default",
    enabled: true,
    costing_basis: "recipe_bom",
    include_labor: true,
    include_overhead: false,
    missing_cost_policy: "warning",
    reviewed: false,
    estimate_label: "management_estimate",
    updated_at: MOCK_NOW,
  },
  setup_exceptions: [],
};

const mockFinancePeriods: FinancePeriodResponse[] = [
  {
    id: "period-2026-08",
    period_start: "2026-08-01",
    period_end: "2026-08-31",
    currency: "EUR",
    status: "review",
    summary_totals: {
      gross_sales_cents: 17800,
      discounts_cents: 1200,
      returns_cents: 2800,
      net_sales_cents: 13800,
      shipping_charged_cents: 0,
      tax_amount_cents: 0,
      total_customer_payments_cents: 14600,
      stripe_fees_cents: 420,
      courier_cod_fees_cents: 310,
      net_provider_payouts_cents: 9300,
      cod_receivable_cents: 5600,
      refunds_pending_cents: 1200,
      recorded_expenses_cents: 4600,
      material_packaging_expenses_cents: 3800,
      estimated_product_cost_cents: 6200,
      estimated_gross_margin_cents: 7600,
      review_required_item_count: 3,
    },
    open_exception_count: 3,
    blocking_exception_count: 2,
    created_by_admin_id: "mock-admin",
    updated_by_admin_id: "mock-admin",
    closed_by_admin_id: null,
    closed_at: null,
    accepted_at: null,
    reopened_from_export_id: null,
    reopen_reason: null,
    created_at: MOCK_NOW,
    updated_at: MOCK_NOW,
  },
];

const mockFinanceExceptions: FinanceExceptionResponse[] = [
  {
    id: "exception-missing-doc",
    period_id: "period-2026-08",
    exception_type: "missing_document_reference",
    severity: "blocking",
    target_type: "order",
    target_id: "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e",
    status: "open",
    message: "COD order needs fiscal receipt or external document reference.",
    details: { order_number: "AM-COD01", payment_method: "cod" },
    created_at: MOCK_NOW,
    updated_at: MOCK_NOW,
  },
  {
    id: "exception-stripe-payout",
    period_id: "period-2026-08",
    exception_type: "stripe_payout_mismatch",
    severity: "warning",
    target_type: "payout",
    target_id: "po_mock_001",
    status: "open",
    message: "Stripe payout differs from matched payments by EUR 4.20.",
    details: { tolerance_cents: 1, difference_cents: 420 },
    created_at: MOCK_NOW,
    updated_at: MOCK_NOW,
  },
  {
    id: "exception-expense-receipt",
    period_id: "period-2026-08",
    exception_type: "expense_document_missing",
    severity: "blocking",
    target_type: "expense",
    target_id: "expense-wax-001",
    status: "open",
    message:
      "Material expense is missing supplier invoice or receipt evidence.",
    details: { category_key: "materials" },
    created_at: MOCK_NOW,
    updated_at: MOCK_NOW,
  },
];

const mockAccountingDocuments: AccountingDocumentResponse[] = [
  {
    id: "doc-invoice-001",
    document_type: "invoice",
    source_system: "external_accountant",
    document_number: "INV-2026-0001",
    issue_date: "2026-08-01",
    order_id: "c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f",
    refund_id: null,
    period_id: "period-2026-08",
    currency: "EUR",
    net_amount_cents: 3200,
    tax_amount_cents: 0,
    gross_amount_cents: 3200,
    vat_summary: null,
    original_document_id: null,
    file_reference: "accountant-drive/INV-2026-0001.pdf",
    status: "recorded",
    notes: "External accountant invoice reference.",
    created_by_admin_id: "mock-admin",
    updated_by_admin_id: "mock-admin",
    created_at: MOCK_NOW,
    updated_at: MOCK_NOW,
  },
];

const mockExpenseEvidence: ExpenseEvidenceResponse[] = [
  {
    id: "expense-wax-001",
    supplier_name: "Wax Supplier Ltd",
    supplier_identifier: "BG123456789",
    document_number: null,
    document_date: null,
    purchase_date: "2026-08-01",
    payment_date: null,
    payment_status: "unpaid",
    category_key: "materials",
    net_amount_cents: 3200,
    tax_amount_cents: 640,
    gross_amount_cents: 3840,
    currency: "EUR",
    attachment_reference: null,
    linked_product_id: "lavender-dreams-300ml",
    linked_material_name: "Soy wax and fragrance oil",
    linked_courier: null,
    linked_order_id: null,
    review_status: "missing_document",
    notes: "Awaiting supplier invoice upload.",
    created_by_admin_id: "mock-admin",
    updated_by_admin_id: "mock-admin",
    created_at: MOCK_NOW,
    updated_at: MOCK_NOW,
  },
  {
    id: "expense-packaging-001",
    supplier_name: "Packaging Studio",
    supplier_identifier: null,
    document_number: "PKG-778",
    document_date: "2026-08-01",
    purchase_date: "2026-08-01",
    payment_date: "2026-08-01",
    payment_status: "paid",
    category_key: "packaging",
    net_amount_cents: 760,
    tax_amount_cents: 0,
    gross_amount_cents: 760,
    currency: "EUR",
    attachment_reference: "receipts/pkg-778.pdf",
    linked_product_id: null,
    linked_material_name: "Gift boxes",
    linked_courier: null,
    linked_order_id: null,
    review_status: "reviewed",
    notes: null,
    created_by_admin_id: "mock-admin",
    updated_by_admin_id: "mock-admin",
    created_at: MOCK_NOW,
    updated_at: MOCK_NOW,
  },
];

const mockProductCosts: ProductCostVersionResponse[] = [
  {
    id: "cost-lavender-001",
    product_id: "lavender-dreams-300ml",
    sku: "LAV-300",
    product_name: "Lavender Dreams",
    effective_date: "2026-08-01",
    costing_basis: "recipe_bom",
    material_cost_cents: 620,
    packaging_cost_cents: 180,
    labor_cost_cents: 240,
    overhead_cost_cents: 0,
    estimated_unit_cost_cents: 1040,
    currency: "EUR",
    reviewed: true,
    accountant_reviewed: false,
    review_status: "reviewed",
    source_expense_ids: ["expense-wax-001", "expense-packaging-001"],
    notes: "Management estimate; accountant review pending.",
    components: [
      {
        id: "component-wax-001",
        cost_version_id: "cost-lavender-001",
        component_type: "material",
        description: "Wax and fragrance",
        quantity: 0.28,
        unit: "kg",
        unit_cost_cents: 1800,
        total_cost_cents: 620,
        source_expense_id: "expense-wax-001",
        created_at: MOCK_NOW,
      },
      {
        id: "component-packaging-001",
        cost_version_id: "cost-lavender-001",
        component_type: "packaging",
        description: "Gift box and label",
        quantity: 1,
        unit: "set",
        unit_cost_cents: 180,
        total_cost_cents: 180,
        source_expense_id: "expense-packaging-001",
        created_at: MOCK_NOW,
      },
    ],
    created_by_admin_id: "mock-admin",
    updated_by_admin_id: "mock-admin",
    created_at: MOCK_NOW,
    updated_at: MOCK_NOW,
  },
];

const mockAccountingExports: FinanceExportPackageResponse[] = [
  {
    id: "export-2026-08-v1",
    period_id: "period-2026-08",
    version: 1,
    schema_version: "accounting-finance-hub.v1",
    xlsx_path: "private-exports/accounting/period-2026-08/v1/accounting.xlsx",
    csv_dir_path: "private-exports/accounting/period-2026-08/v1/csv",
    manifest_path: "private-exports/accounting/period-2026-08/v1/manifest.json",
    manifest: {
      row_counts: {
        sales: 4,
        payments: 3,
        expenses: 2,
        product_costs: 1,
        exceptions: 3,
      },
      totals: { net_sales_cents: 13800, recorded_expenses_cents: 4600 },
      files: [
        "accounting.xlsx",
        "sales.csv",
        "payments.csv",
        "expenses.csv",
        "manifest.json",
      ],
    },
    generated_by_admin_id: "mock-admin",
    generated_at: MOCK_NOW,
    accepted_by_admin_id: null,
    accepted_at: null,
    accountant_name: null,
    accountant_reference: null,
    acceptance_note: null,
    current_final: true,
  },
];

const mockLedgerRows: Record<AccountingLedgerName, Record<string, unknown>[]> =
  {
    sales: [
      {
        order_number: "AM-1001",
        order_date: "2026-08-01",
        product_name: "Lavender Dreams",
        quantity: 1,
        gross_amount_cents: 3200,
        document_reference_status: "recorded",
      },
      {
        order_number: "AM-COD01",
        order_date: "2026-08-01",
        product_name: "Citrus Garden",
        quantity: 2,
        gross_amount_cents: 5600,
        document_reference_status: "missing",
      },
    ],
    payments: [
      {
        order_number: "AM-1001",
        event_date: "2026-08-01",
        provider: "stripe",
        gross_amount_cents: 3200,
        reconciliation_status: "matched",
      },
      {
        order_number: "AM-COD01",
        event_date: "2026-08-01",
        provider: "cod",
        gross_amount_cents: 5600,
        reconciliation_status: "pending",
      },
    ],
    stripe_payouts: [
      {
        balance_transaction_id: "txn_mock_001",
        payout_id: "po_mock_001",
        gross_amount_cents: 3200,
        fee_amount_cents: 120,
        net_amount_cents: 3080,
        match_status: "mismatch",
      },
    ],
    cod_settlements: [
      {
        order_number: "AM-COD01",
        state: "unsettled",
        cod_amount_cents: 5600,
        courier_reference: null,
      },
    ],
    refunds: [
      {
        order_number: "AM-1002",
        refund_date: "2026-08-01",
        refund_amount_cents: -1200,
        document_reference_status: "review_required",
      },
    ],
    courier_claims: [
      {
        claim_id: "claim-001",
        order_number: "AM-1002",
        claim_status: "filed",
        claim_amount_cents: 600,
      },
    ],
    return_reasons: [
      {
        order_number: "AM-1002",
        reason: "customer_return",
        status: "received",
      },
    ],
    inventory_adjustments: [
      {
        order_number: "AM-1002",
        product_id: "lavender-dreams-300ml",
        restock_decision: "partial",
        quantity: 1,
      },
    ],
    inventory_movements: [
      {
        item_type: "finished_good",
        item_id: "lavender-dreams-300ml",
        movement_type: "sale_issue",
        quantity_delta: -1,
      },
    ],
    documents: mockAccountingDocuments as unknown as Record<string, unknown>[],
    expenses: mockExpenseEvidence as unknown as Record<string, unknown>[],
    product_costs: mockProductCosts as unknown as Record<string, unknown>[],
  };

function withMockAccountingFlags(order: OrderResponse): OrderResponse {
  if (order.id === "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e") {
    return {
      ...order,
      order_number: order.order_number ?? "AM-COD01",
      finance_period_id: "period-2026-08",
      accounting_readiness_status: "blocked",
      accounting_classification_state: "manual_review_required",
      document_reference_status: "missing",
      payment_reconciliation_status: "pending",
      payout_reconciliation_status: "not_applicable",
      cod_settlement_status: "pending",
      blocking_exception_count: 1,
      finance_hub_links: {
        period_id: "period-2026-08",
        period_href: "/admin/accounting?period=period-2026-08",
        exceptions_href:
          "/admin/accounting?period=period-2026-08&tab=exceptions",
        ledger_href:
          "/admin/accounting?period=period-2026-08&tab=ledgers&ledger=cod_settlements",
        documents_href: "/admin/accounting?period=period-2026-08&tab=documents",
      },
    };
  }
  if (order.id === "c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f") {
    return {
      ...order,
      order_number: order.order_number ?? "AM-1001",
      finance_period_id: "period-2026-08",
      accounting_readiness_status: "review_required",
      document_reference_status: "recorded",
      payment_reconciliation_status: "matched",
      payout_reconciliation_status: "mismatch",
      cod_settlement_status: "not_applicable",
      blocking_exception_count: 0,
      finance_hub_links: {
        period_id: "period-2026-08",
        period_href: "/admin/accounting?period=period-2026-08",
        exceptions_href:
          "/admin/accounting?period=period-2026-08&tab=exceptions",
        ledger_href:
          "/admin/accounting?period=period-2026-08&tab=ledgers&ledger=stripe_payouts",
        documents_href: "/admin/accounting?period=period-2026-08&tab=documents",
      },
    };
  }
  return {
    ...order,
    accounting_readiness_status:
      order.accounting_readiness_status ?? "unreviewed",
    document_reference_status:
      order.document_reference_status ?? "not_required",
    payment_reconciliation_status:
      order.payment_reconciliation_status ?? "not_applicable",
    payout_reconciliation_status:
      order.payout_reconciliation_status ?? "not_applicable",
    cod_settlement_status: order.cod_settlement_status ?? "not_applicable",
    blocking_exception_count: order.blocking_exception_count ?? 0,
    finance_hub_links: order.finance_hub_links ?? null,
  };
}

// The mock store carries admin-only fields even though ProductResponse omits them.
type MockProduct = ProductResponse & {
  safety_warnings_en: string | null;
  safety_warnings_bg: string | null;
  care_instructions_en: string | null;
  care_instructions_bg: string | null;
  weight_grams: number;
  discount_starts_at: string | null;
  discount_ends_at: string | null;
};

/** Strip admin-only fields so public responses match the real API. */
function toPublicProduct(product: MockProduct, locale = "en"): ProductResponse {
  const {
    safety_warnings_en,
    safety_warnings_bg,
    care_instructions_en,
    care_instructions_bg,
    weight_grams: _weight_grams,
    discount_starts_at: _discount_starts_at,
    discount_ends_at: _discount_ends_at,
    ...pub
  } = product;
  const preferredWarnings =
    locale === "bg" ? safety_warnings_bg : safety_warnings_en;
  const fallbackWarnings =
    locale === "bg" ? safety_warnings_en : safety_warnings_bg;
  const preferredCare =
    locale === "bg" ? care_instructions_bg : care_instructions_en;
  const fallbackCare =
    locale === "bg" ? care_instructions_en : care_instructions_bg;
  return {
    ...pub,
    safety_warnings: preferredWarnings ?? fallbackWarnings,
    care_instructions: preferredCare ?? fallbackCare,
  };
}

function mockProductImage(
  productId: string,
  sortOrder = 0,
  isPrimary = true,
): ProductImage {
  const imageUrl = `/static/products/${productId}.webp`;
  return {
    id: `${productId}-${sortOrder}`,
    image_url: imageUrl,
    thumbnail_url: imageUrl,
    zoom_url: imageUrl,
    sort_order: sortOrder,
    is_primary: isPrimary,
  };
}

function mockProductVideo(productId: string, sortOrder = 1): ProductVideo {
  return {
    id: `${productId}-video`,
    product_id: productId,
    status: "queued",
    video_url: null,
    poster_url: `/static/products/${productId}.webp`,
    sort_order: sortOrder,
    duration_secs: null,
    failure_reason: null,
    created_at: "2024-06-01T10:00:00Z",
    updated_at: "2024-06-01T10:00:00Z",
  };
}

function primaryImageUrl(images: ProductImage[]): string | null {
  return images.find((image) => image.is_primary)?.image_url ?? null;
}

function primaryThumbnailUrl(images: ProductImage[]): string | null {
  return images.find((image) => image.is_primary)?.thumbnail_url ?? null;
}

/** Recompute discount_active + effective_price_cents from the raw config (mirrors backend). */
function applyMockPricing(product: MockProduct): MockProduct {
  const percent = product.discount_percent;
  const now = new Date();
  const active =
    percent != null &&
    (!product.discount_starts_at ||
      now >= new Date(product.discount_starts_at)) &&
    (!product.discount_ends_at || now <= new Date(product.discount_ends_at));
  product.discount_active = active;
  product.effective_price_cents =
    active && percent != null
      ? Math.max(
          1,
          Math.floor((product.price_cents * (100 - percent) + 50) / 100),
        )
      : product.price_cents;
  return product;
}
const MOCK_PRODUCTS: MockProduct[] = [
  {
    id: "lavender-dreams-300ml",
    name: "Lavender Dreams",
    description: "Hand-poured soy candle with French lavender essential oil.",
    safety_warnings:
      "Never leave a burning candle unattended. Keep away from children, pets, and flammable materials.",
    care_instructions:
      "Burn on a stable, heat-resistant surface. Trim the wick before each use.",
    safety_warnings_en:
      "Never leave a burning candle unattended. Keep away from children, pets, and flammable materials.",
    safety_warnings_bg:
      "Never leave a burning candle unattended. Keep away from children, pets, and flammable materials.",
    care_instructions_en:
      "Burn on a stable, heat-resistant surface. Trim the wick before each use.",
    care_instructions_bg:
      "Burn on a stable, heat-resistant surface. Trim the wick before each use.",
    materials: "Soy wax, French lavender essential oil, cotton wick",
    days_to_craft: 3,
    price_cents: 3200,
    effective_price_cents: 2560,
    discount_percent: 20,
    discount_active: true,
    discount_starts_at: null,
    discount_ends_at: null,
    category: "medium",
    category_name: "Medium",
    product_type: "candles",
    product_type_name: "Candles",
    labels: [{ slug: "floral", name: "Floral" }],
    images: [
      mockProductImage("lavender-dreams-300ml", 0, true),
      mockProductImage("lavender-dreams-300ml", 1, false),
      mockProductImage("lavender-dreams-300ml", 3, false),
    ],
    video: mockProductVideo("lavender-dreams-300ml", 2),
    primary_image_url: "/static/products/lavender-dreams-300ml.webp",
    primary_thumbnail_url: "/static/products/lavender-dreams-300ml.webp",
    stock: 24,
    weight_grams: 300,
    is_active: true,
    is_featured: true,
    created_at: "2024-06-01T10:00:00Z",
    updated_at: "2024-06-01T10:00:00Z",
  },
  {
    id: "midnight-amber-300ml",
    name: "Midnight Amber",
    description: "Warm amber and sandalwood in a black ceramic vessel.",
    safety_warnings:
      "Never leave a burning candle unattended. Ceramic vessel may become hot during use.",
    care_instructions:
      "Place on a heat-resistant surface and allow wax to cool before handling.",
    safety_warnings_en:
      "Never leave a burning candle unattended. Ceramic vessel may become hot during use.",
    safety_warnings_bg: null,
    care_instructions_en:
      "Place on a heat-resistant surface and allow wax to cool before handling.",
    care_instructions_bg: null,
    materials: "Coconut wax, amber resin, sandalwood oil",
    days_to_craft: 5,
    price_cents: 4500,
    effective_price_cents: 4500,
    discount_percent: null,
    discount_active: false,
    discount_starts_at: null,
    discount_ends_at: null,
    category: "premium",
    category_name: "Premium",
    product_type: "candles",
    product_type_name: "Candles",
    labels: [
      { slug: "woody", name: "Woody" },
      { slug: "gift", name: "Gift" },
    ],
    images: [mockProductImage("midnight-amber-300ml")],
    video: null,
    primary_image_url: "/static/products/midnight-amber-300ml.webp",
    primary_thumbnail_url: "/static/products/midnight-amber-300ml.webp",
    stock: 12,
    weight_grams: 450,
    is_active: true,
    is_featured: true,
    created_at: "2024-06-02T11:00:00Z",
    updated_at: "2024-06-02T11:00:00Z",
  },
  {
    id: "citrus-garden-200ml",
    name: "Citrus Garden",
    description: "Bright blend of bergamot, lemon, and grapefruit.",
    safety_warnings: null,
    care_instructions: null,
    safety_warnings_en: null,
    safety_warnings_bg: null,
    care_instructions_en: null,
    care_instructions_bg: null,
    materials: null,
    days_to_craft: 2,
    price_cents: 2800,
    effective_price_cents: 2800,
    discount_percent: null,
    discount_active: false,
    discount_starts_at: null,
    discount_ends_at: null,
    category: "small",
    category_name: "Small",
    product_type: "candles",
    product_type_name: "Candles",
    labels: [
      { slug: "fresh", name: "Fresh" },
      { slug: "citrus", name: "Citrus" },
    ],
    images: [],
    video: null,
    primary_image_url: null,
    primary_thumbnail_url: null,
    stock: 36,
    weight_grams: 250,
    is_active: true,
    is_featured: false,
    created_at: "2024-06-03T09:00:00Z",
    updated_at: "2024-06-03T09:00:00Z",
  },
  {
    id: "vanilla-bourbon-300ml",
    name: "Vanilla Bourbon",
    description: null,
    safety_warnings: null,
    care_instructions: null,
    safety_warnings_en: null,
    safety_warnings_bg: null,
    care_instructions_en: null,
    care_instructions_bg: null,
    materials: null,
    days_to_craft: null,
    price_cents: 3800,
    effective_price_cents: 3800,
    discount_percent: null,
    discount_active: false,
    discount_starts_at: null,
    discount_ends_at: null,
    category: null,
    category_name: null,
    product_type: "candles",
    product_type_name: "Candles",
    labels: [{ slug: "gourmand", name: "Gourmand" }],
    images: [mockProductImage("vanilla-bourbon-300ml")],
    video: null,
    primary_image_url: "/static/products/vanilla-bourbon-300ml.webp",
    primary_thumbnail_url: "/static/products/vanilla-bourbon-300ml.webp",
    stock: 0,
    weight_grams: 500,
    is_active: false,
    is_featured: false,
    created_at: "2024-06-04T14:00:00Z",
    updated_at: "2024-06-05T08:00:00Z",
  },
];

const nowIso = () => new Date().toISOString();

let nextAboutItemId = 18;

const MOCK_ABOUT_SECTIONS: AboutSectionAdmin[] = [
  mockAboutSection(
    "hero",
    "hero",
    0,
    "The Atelier Marie",
    "The Atelier Marie",
    "Handcrafted Elegance for Beautiful Spaces",
    "Ръчно изработена елегантност за красиви пространства",
    "At The Atelier Marie, we create handcrafted candles designed to bring beauty, warmth, and a touch of luxury into your home.",
    "В The Atelier Marie създаваме ръчно изработени свещи, замислени да внесат красота, топлина и лек досег на лукс във вашия дом.",
    "Explore our collection",
    "Разгледайте нашата колекция",
    "/products",
  ),
  mockAboutSection(
    "story",
    "text_image",
    1,
    "Our Story",
    "Нашата история",
    "From a Creative Idea to a Handmade Atelier",
    "От творческа идея до ръчно ателие",
    "The Atelier Marie began with a simple thought:\n\n> I want something this beautiful in my own home.",
    "The Atelier Marie започна с една проста мисъл:\n\n> Искам нещо толкова красиво в собствения си дом.",
  ),
  mockAboutSection(
    "philosophy",
    "text_band",
    2,
    "Our Philosophy",
    "Нашата философия",
    "Candles Designed to Be Admired",
    "Свещи, създадени, за да им се възхищавате",
    "We believe candles can be more than a source of light or fragrance.",
    "Вярваме, че свещите могат да бъдат повече от източник на светлина или аромат.",
  ),
  mockAboutSection(
    "differentiators",
    "cards",
    3,
    "What Makes Our Candles Different",
    "Какво отличава нашите свещи",
    "More Than a Candle — A Piece of Art for Your Home",
    "Повече от свещ — произведение на изкуството за вашия дом",
    null,
    null,
  ),
  mockAboutSection(
    "process",
    "timeline",
    4,
    "The Art of Making",
    "Изкуството на създаването",
    "Crafted Slowly, Made With Care",
    "Изработени бавно, създадени с грижа",
    "Every creation begins with an idea.\n\nBefore a candle reaches your home, it goes through a careful process of design and craftsmanship.",
    "Всяко творение започва с идея.\n\nПреди една свещ да стигне до вашия дом, тя преминава през внимателен процес на проектиране и изработка.",
  ),
  mockAboutSection(
    "atelier",
    "text_image",
    5,
    "Inside Our Atelier",
    "Вътре в нашето ателие",
    "Where Every Candle Comes to Life",
    "Където всяка свещ оживява",
    "Behind every creation are countless small details.",
    "Зад всяко творение стоят безброй малки детайли.",
  ),
  mockAboutSection(
    "values",
    "cards",
    6,
    "Our Values",
    "Нашите ценности",
    "The Principles Behind Every Creation",
    "Принципите зад всяко творение",
    null,
    null,
  ),
  mockAboutSection(
    "collections",
    "collections",
    7,
    "Our Collections",
    "Нашите колекции",
    "Designed to Suit Every Space and Story",
    "Създадени да подхождат на всяко пространство и история",
    null,
    null,
  ),
  mockAboutSection(
    "emotional",
    "text_band",
    8,
    "A Little Beauty for Everyday Moments",
    "Малко красота за ежедневните мигове",
    "Designed to Become Part of Your Story",
    "Създадени да станат част от вашата история",
    "We believe the most beautiful objects are the ones that create a feeling.",
    "Вярваме, че най-красивите предмети са тези, които създават усещане.",
    "Discover the collection",
    "Открийте колекцията",
    "/products",
  ),
  mockAboutSection(
    "custom_cta",
    "cta_band",
    9,
    "Looking for Something Unique?",
    "Търсите нещо уникално?",
    null,
    null,
    "Create a personalised candle designed especially for you — a bespoke piece for a meaningful moment, or a truly one-of-a-kind gift.",
    "Създайте персонализирана свещ, замислена специално за вас — изделие по поръчка за значим миг или наистина уникален подарък.",
    "Request a Custom Order",
    "Заявете индивидуална поръчка",
    "/contact",
  ),
];

MOCK_ABOUT_SECTIONS.find((s) => s.slug === "differentiators")!.items = [
  mockAboutItem(
    1,
    "differentiators",
    0,
    "Handcrafted With Attention to Detail",
    "Ръчна изработка с внимание към детайла",
    "Every candle is individually created in our atelier.",
    "Всяка свещ се създава индивидуално в нашето ателие.",
  ),
  mockAboutItem(
    2,
    "differentiators",
    1,
    "Designed as Home Décor",
    "Замислени като декор за дома",
    "Our candles are created to complement beautiful interiors.",
    "Нашите свещи са създадени да допълват красивите интериори.",
  ),
  mockAboutItem(
    3,
    "differentiators",
    2,
    "A Luxury Fragrance Experience",
    "Луксозно ароматно изживяване",
    "Beautiful design deserves a beautiful scent.",
    "Красивият дизайн заслужава красив аромат.",
  ),
  mockAboutItem(
    4,
    "differentiators",
    3,
    "Personalised Creations",
    "Персонализирани творения",
    "Some moments deserve something truly unique.",
    "Някои мигове заслужават нещо наистина уникално.",
  ),
];
MOCK_ABOUT_SECTIONS.find((s) => s.slug === "process")!.items = [
  mockAboutItem(
    5,
    "process",
    0,
    "Design",
    "Дизайн",
    "Every creation begins with an idea, a shape, and a vision.",
    "Всяко творение започва с идея, форма и визия.",
  ),
  mockAboutItem(
    6,
    "process",
    1,
    "Moulds",
    "Калъпи",
    "Each shape is carefully prepared.",
    "Всяка форма се подготвя грижливо.",
  ),
  mockAboutItem(
    7,
    "process",
    2,
    "Colours",
    "Цветове",
    "Shades are selected and blended by hand.",
    "Нюансите се подбират и смесват на ръка.",
  ),
];
MOCK_ABOUT_SECTIONS.find((s) => s.slug === "values")!.items = [
  mockAboutItem(
    11,
    "values",
    0,
    "Craftsmanship",
    "Майсторство",
    "True beauty comes from attention to detail.",
    "Истинската красота идва от вниманието към детайла.",
  ),
  mockAboutItem(
    12,
    "values",
    1,
    "Elegance",
    "Елегантност",
    "Our creations are inspired by timeless aesthetics.",
    "Нашите творения са вдъхновени от вечната естетика.",
  ),
];
MOCK_ABOUT_SECTIONS.find((s) => s.slug === "collections")!.items = [
  mockAboutItem(
    15,
    "collections",
    0,
    "Floral Collection",
    "Флорална колекция",
    "Romantic designs inspired by nature.",
    "Романтични дизайни, вдъхновени от природата.",
    "/products?labels=floral",
  ),
  mockAboutItem(
    16,
    "collections",
    1,
    "Sculptural Collection",
    "Скулптурна колекция",
    "Statement pieces designed to decorate your space.",
    "Акцентни изделия, създадени да украсят вашето пространство.",
    "/products?labels=sculptural",
  ),
  mockAboutItem(
    17,
    "collections",
    2,
    "Bespoke Collection",
    "Колекция по поръчка",
    "Custom creations made for meaningful moments.",
    "Творения по поръчка за значими мигове.",
    "/products?labels=bespoke",
  ),
];

function mockAboutSection(
  slug: AboutSectionAdmin["slug"],
  type: AboutSectionAdmin["type"],
  sortOrder: number,
  headingEn: string,
  headingBg: string | null,
  subheadingEn: string | null,
  subheadingBg: string | null,
  bodyEn: string | null,
  bodyBg: string | null,
  ctaLabelEn: string | null = null,
  ctaLabelBg: string | null = null,
  ctaHref: string | null = null,
): AboutSectionAdmin {
  const timestamp = nowIso();
  return {
    slug,
    type,
    heading_en: headingEn,
    heading_bg: headingBg,
    subheading_en: subheadingEn,
    subheading_bg: subheadingBg,
    body_en: bodyEn,
    body_bg: bodyBg,
    cta_label_en: ctaLabelEn,
    cta_label_bg: ctaLabelBg,
    cta_href: ctaHref,
    image_id: null,
    image: null,
    sort_order: sortOrder,
    is_published: true,
    created_at: timestamp,
    updated_at: timestamp,
    items: [],
  };
}

function mockAboutItem(
  id: number,
  section: string,
  sortOrder: number,
  titleEn: string,
  titleBg: string | null,
  textEn: string | null,
  textBg: string | null,
  linkHref: string | null = null,
): AboutItemAdmin {
  const timestamp = nowIso();
  return {
    id,
    section,
    title_en: titleEn,
    title_bg: titleBg,
    text_en: textEn,
    text_bg: textBg,
    image_id: null,
    image: null,
    link_href: linkHref,
    sort_order: sortOrder,
    is_published: true,
    created_at: timestamp,
    updated_at: timestamp,
  };
}

function publicAbout(locale: string = "en"): AboutPublicResponse {
  return {
    sections: MOCK_ABOUT_SECTIONS.filter((section) => section.is_published)
      .sort((a, b) => a.sort_order - b.sort_order)
      .map((section) => ({
        slug: section.slug,
        type: section.type,
        heading:
          locale === "bg"
            ? section.heading_bg || section.heading_en
            : section.heading_en,
        subheading:
          locale === "bg"
            ? section.subheading_bg || section.subheading_en
            : section.subheading_en,
        body:
          locale === "bg"
            ? section.body_bg || section.body_en
            : section.body_en,
        cta:
          section.cta_href &&
          (locale === "bg"
            ? section.cta_label_bg || section.cta_label_en
            : section.cta_label_en)
            ? {
                label:
                  (locale === "bg"
                    ? section.cta_label_bg || section.cta_label_en
                    : section.cta_label_en) || "",
                href: section.cta_href,
              }
            : null,
        image: section.image,
        items: section.items
          .filter((item) => item.is_published)
          .sort((a, b) => a.sort_order - b.sort_order)
          .map((item) => ({
            id: item.id,
            title:
              locale === "bg" ? item.title_bg || item.title_en : item.title_en,
            text: locale === "bg" ? item.text_bg || item.text_en : item.text_en,
            image: item.image,
            link: item.link_href,
          })),
      })),
  };
}

// --- In-Memory Taxonomy State (mock) ---

interface MockTerm {
  slug: string;
  name_en: string;
  name_bg: string | null;
  sort_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

function mockTerm(
  slug: string,
  name_en: string,
  name_bg: string,
  sort_order: number,
): MockTerm {
  return {
    slug,
    name_en,
    name_bg,
    sort_order,
    is_active: true,
    created_at: "2024-06-01T10:00:00Z",
    updated_at: "2024-06-01T10:00:00Z",
  };
}

const MOCK_TAXONOMY: Record<TaxonomyKind, MockTerm[]> = {
  "product-types": [
    mockTerm("candles", "Candles", "Свещи", 0),
    mockTerm("boxes", "Boxes", "Кутии", 1),
  ],
  categories: [
    mockTerm("small", "Small", "Малка", 0),
    mockTerm("medium", "Medium", "Средна", 1),
    mockTerm("premium", "Premium", "Премиум", 2),
  ],
  labels: [
    mockTerm("floral", "Floral", "Флорални", 0),
    mockTerm("woody", "Woody", "Дървесни", 1),
    mockTerm("fresh", "Fresh", "Свежи", 2),
    mockTerm("gourmand", "Gourmand", "Гурме", 3),
    mockTerm("citrus", "Citrus", "Цитрусови", 4),
    mockTerm("winter", "Winter", "Зима", 5),
    mockTerm("gift", "Gift", "Подарък", 6),
    mockTerm("sculptural", "Sculptural", "Скулптурни", 7),
    mockTerm("bespoke", "Bespoke", "По поръчка", 8),
  ],
};

const MOCK_USER: UserResponse = {
  id: "user-001",
  email: "marie@ateliermarie.com",
  name: "Marie",
  avatar_url: "https://lh3.googleusercontent.com/example",
  is_admin: true,
};

// --- In-Memory FAQ State ---

const mockFaqTimestamp = "2024-06-01T10:00:00Z";

let mockFaqNextId = 8;

const mockFaqSections: FaqSectionAdminResponse[] = [
  {
    slug: "candles",
    title_en: "About Our Candles",
    title_bg: "За нашите свещи",
    icon: "🕯",
    sort_order: 0,
    created_at: mockFaqTimestamp,
    updated_at: mockFaqTimestamp,
    items: [
      {
        id: 1,
        section: "candles",
        question_en: "Are your candles handmade?",
        question_bg: "Ръчно изработени ли са вашите свещи?",
        answer_en: "Yes. Every candle is lovingly handcrafted in our atelier.",
        answer_bg:
          "Да. Всяка свещ е изработена с любов на ръка в нашето ателие.",
        sort_order: 0,
        is_published: true,
        created_at: mockFaqTimestamp,
        updated_at: mockFaqTimestamp,
      },
    ],
  },
  {
    slug: "care",
    title_en: "Candle Care & Safety",
    title_bg: "Грижа и безопасност",
    icon: "✨",
    sort_order: 1,
    created_at: mockFaqTimestamp,
    updated_at: mockFaqTimestamp,
    items: [
      {
        id: 2,
        section: "care",
        question_en: "Candle Safety",
        question_bg: "Безопасност при работа със свещи",
        answer_en:
          "* Never leave a burning candle unattended.\n* Keep candles away from children and pets.",
        answer_bg:
          "* Никога не оставяйте горяща свещ без надзор.\n* Дръжте свещите далеч от деца и домашни любимци.",
        sort_order: 0,
        is_published: true,
        created_at: mockFaqTimestamp,
        updated_at: mockFaqTimestamp,
      },
    ],
  },
  {
    slug: "custom",
    title_en: "Custom Orders & Gifts",
    title_bg: "Поръчки по заявка и подаръци",
    icon: "🎁",
    sort_order: 2,
    created_at: mockFaqTimestamp,
    updated_at: mockFaqTimestamp,
    items: [
      {
        id: 3,
        section: "custom",
        question_en: "Can I customise my candle?",
        question_bg: "Мога ли да персонализирам свещта си?",
        answer_en: "Yes. We love bringing our customers' ideas to life.",
        answer_bg: "Да. Обичаме да претворяваме идеите на нашите клиенти.",
        sort_order: 0,
        is_published: true,
        created_at: mockFaqTimestamp,
        updated_at: mockFaqTimestamp,
      },
    ],
  },
  {
    slug: "shipping",
    title_en: "Orders, Shipping & Returns",
    title_bg: "Поръчки, доставка и връщане",
    icon: "📦",
    sort_order: 3,
    created_at: mockFaqTimestamp,
    updated_at: mockFaqTimestamp,
    items: [
      {
        id: 4,
        section: "shipping",
        question_en: "How long does it take to prepare my order?",
        question_bg: "Колко време отнема подготовката на поръчката ми?",
        answer_en: "Preparation times vary depending on the product.",
        answer_bg: "Времето за подготовка варира в зависимост от продукта.",
        sort_order: 0,
        is_published: true,
        created_at: mockFaqTimestamp,
        updated_at: mockFaqTimestamp,
      },
      {
        id: 7,
        section: "shipping",
        question_en: "Do you accept returns?",
        question_bg: "Приемате ли връщания?",
        answer_en:
          "Uncollected or refused courier parcels are reviewed before refund timing, refund amount, or next steps are confirmed. See the [Terms & Conditions returns section](/en/terms#returns) for the full policy.",
        answer_bg:
          "Непотърсените или отказани куриерски пратки се преглеждат, преди да потвърдим срок, сума за възстановяване или следваща стъпка. Вижте [раздела за връщания в Общите условия](/bg/terms#returns) за пълната политика.",
        sort_order: 1,
        is_published: true,
        created_at: mockFaqTimestamp,
        updated_at: mockFaqTimestamp,
      },
    ],
  },
];

function cloneAdminFaq(): FaqAdminResponse {
  return {
    sections: mockFaqSections.map((section) => ({
      ...section,
      items: section.items.map((item) => ({ ...item })),
    })),
  };
}

function findFaqSection(slug: string): FaqSectionAdminResponse | undefined {
  return mockFaqSections.find((section) => section.slug === slug);
}

function findFaqItem(itemId: number): FaqItemAdminResponse | undefined {
  return mockFaqSections
    .flatMap((section) => section.items)
    .find((item) => item.id === itemId);
}

// --- Terms Mock ---

type StaticTerms = typeof enMessages.terms;
type StaticTermsSection = StaticTerms["sections"][number];

const mockTermsTimestamp = "2026-07-29T00:00:00Z";
const mockTermsEn = enMessages.terms as StaticTerms;
const mockTermsBg = bgMessages.terms as StaticTerms;

function findStaticBgTermsSection(
  slug: string,
): StaticTermsSection | undefined {
  return mockTermsBg.sections.find((section) => section.id === slug);
}

let mockTermsPage: TermsPageAdminResponse = {
  id: "terms",
  meta_title_en: mockTermsEn.metaTitle,
  meta_title_bg: mockTermsBg.metaTitle,
  meta_description_en: mockTermsEn.metaDescription,
  meta_description_bg: mockTermsBg.metaDescription,
  eyebrow_en: mockTermsEn.eyebrow,
  eyebrow_bg: mockTermsBg.eyebrow,
  title_en: mockTermsEn.title,
  title_bg: mockTermsBg.title,
  subtitle_en: mockTermsEn.subtitle,
  subtitle_bg: mockTermsBg.subtitle,
  last_updated_en: mockTermsEn.lastUpdated,
  last_updated_bg: mockTermsBg.lastUpdated,
  identity_intro_en: mockTermsEn.identityIntro,
  identity_intro_bg: mockTermsBg.identityIntro,
  policy_links_title_en: mockTermsEn.policyLinksTitle,
  policy_links_title_bg: mockTermsBg.policyLinksTitle,
  privacy_link_en: mockTermsEn.privacyLink,
  privacy_link_bg: mockTermsBg.privacyLink,
  cookies_link_en: mockTermsEn.cookiesLink,
  cookies_link_bg: mockTermsBg.cookiesLink,
  nav_label_en: mockTermsEn.navLabel,
  nav_label_bg: mockTermsBg.navLabel,
  back_to_top_en: mockTermsEn.backToTop,
  back_to_top_bg: mockTermsBg.backToTop,
  created_at: mockTermsTimestamp,
  updated_at: mockTermsTimestamp,
};

let mockTermsSections: TermsSectionAdminResponse[] = mockTermsEn.sections.map(
  (section, index) => {
    const bgSection = findStaticBgTermsSection(section.id);
    return {
      slug: section.id,
      title_en: section.title,
      title_bg: bgSection?.title ?? null,
      nav_en: section.nav,
      nav_bg: bgSection?.nav ?? null,
      body_en: [...section.body],
      body_bg: bgSection ? [...bgSection.body] : null,
      model_form_title_en:
        "modelFormTitle" in section ? (section.modelFormTitle ?? null) : null,
      model_form_title_bg:
        bgSection && "modelFormTitle" in bgSection
          ? (bgSection.modelFormTitle ?? null)
          : null,
      model_form_intro_en:
        "modelFormIntro" in section ? (section.modelFormIntro ?? null) : null,
      model_form_intro_bg:
        bgSection && "modelFormIntro" in bgSection
          ? (bgSection.modelFormIntro ?? null)
          : null,
      model_form_lines_en:
        "modelFormLines" in section
          ? [...(section.modelFormLines ?? [])]
          : null,
      model_form_lines_bg:
        bgSection && "modelFormLines" in bgSection
          ? [...(bgSection.modelFormLines ?? [])]
          : null,
      sort_order: index,
      created_at: mockTermsTimestamp,
      updated_at: mockTermsTimestamp,
    };
  },
);

function localizedTermsValue(
  en: string,
  bg: string | null,
  locale?: string,
): string {
  return locale === "bg" ? (bg ?? en) : en;
}

function localizedTermsLines(
  en: string[] | null,
  bg: string[] | null,
  locale?: string,
): string[] | null {
  if (locale === "bg" && bg?.length) return [...bg];
  return en ? [...en] : null;
}

function cloneAdminTerms(): TermsAdminResponse {
  return {
    page: { ...mockTermsPage },
    sections: mockTermsSections.map((section) => ({
      ...section,
      body_en: [...section.body_en],
      body_bg: section.body_bg ? [...section.body_bg] : null,
      model_form_lines_en: section.model_form_lines_en
        ? [...section.model_form_lines_en]
        : null,
      model_form_lines_bg: section.model_form_lines_bg
        ? [...section.model_form_lines_bg]
        : null,
    })),
  };
}

// --- Privacy Policy Mock ---

type StaticPrivacy = typeof enMessages.privacy;
type StaticPrivacySection = StaticPrivacy["sections"][number];

const mockPrivacyTimestamp = "2026-07-29T00:00:00Z";
const mockPrivacyEn = enMessages.privacy as StaticPrivacy;
const mockPrivacyBg = bgMessages.privacy as StaticPrivacy;

function findStaticBgPrivacySection(
  slug: string,
): StaticPrivacySection | undefined {
  return mockPrivacyBg.sections.find((section) => section.id === slug);
}

let mockPrivacyPage: PrivacyPageAdminResponse = {
  id: "privacy",
  meta_title_en: mockPrivacyEn.metaTitle,
  meta_title_bg: mockPrivacyBg.metaTitle,
  meta_description_en: mockPrivacyEn.metaDescription,
  meta_description_bg: mockPrivacyBg.metaDescription,
  eyebrow_en: mockPrivacyEn.eyebrow,
  eyebrow_bg: mockPrivacyBg.eyebrow,
  title_en: mockPrivacyEn.title,
  title_bg: mockPrivacyBg.title,
  subtitle_en: mockPrivacyEn.subtitle,
  subtitle_bg: mockPrivacyBg.subtitle,
  last_updated_en: mockPrivacyEn.lastUpdated,
  last_updated_bg: mockPrivacyBg.lastUpdated,
  controller_title_en: mockPrivacyEn.controllerTitle,
  controller_title_bg: mockPrivacyBg.controllerTitle,
  created_at: mockPrivacyTimestamp,
  updated_at: mockPrivacyTimestamp,
};

let mockPrivacySections: PrivacySectionAdminResponse[] =
  mockPrivacyEn.sections.map((section, index) => {
    const bgSection = findStaticBgPrivacySection(section.id);
    return {
      slug: section.id,
      title_en: section.title,
      title_bg: bgSection?.title ?? null,
      nav_en: section.nav,
      nav_bg: bgSection?.nav ?? null,
      body_en: [...section.body],
      body_bg: bgSection ? [...bgSection.body] : null,
      sort_order: index,
      created_at: mockPrivacyTimestamp,
      updated_at: mockPrivacyTimestamp,
    };
  });

function cloneAdminPrivacy(): PrivacyAdminResponse {
  return {
    page: { ...mockPrivacyPage },
    sections: mockPrivacySections.map((section) => ({
      ...section,
      body_en: [...section.body_en],
      body_bg: section.body_bg ? [...section.body_bg] : null,
    })),
  };
}

// --- Cookie Policy Mock ---

type StaticCookies = typeof enMessages.cookies;
type StaticCookieSection = StaticCookies["sections"][number];

const mockCookiesTimestamp = "2026-07-29T00:00:00Z";
const mockCookiesEn = enMessages.cookies as StaticCookies;
const mockCookiesBg = bgMessages.cookies as StaticCookies;

function findStaticBgCookieSection(
  slug: string,
): StaticCookieSection | undefined {
  return mockCookiesBg.sections.find((section) => section.id === slug);
}

let mockCookiesPage: CookiesPageAdminResponse = {
  id: "cookies",
  meta_title_en: mockCookiesEn.metaTitle,
  meta_title_bg: mockCookiesBg.metaTitle,
  meta_description_en: mockCookiesEn.metaDescription,
  meta_description_bg: mockCookiesBg.metaDescription,
  eyebrow_en: mockCookiesEn.eyebrow,
  eyebrow_bg: mockCookiesBg.eyebrow,
  title_en: mockCookiesEn.title,
  title_bg: mockCookiesBg.title,
  subtitle_en: mockCookiesEn.subtitle,
  subtitle_bg: mockCookiesBg.subtitle,
  last_updated_en: mockCookiesEn.lastUpdated,
  last_updated_bg: mockCookiesBg.lastUpdated,
  inventory_title_en: mockCookiesEn.inventoryTitle,
  inventory_title_bg: mockCookiesBg.inventoryTitle,
  header_name_en: mockCookiesEn.headers.name,
  header_name_bg: mockCookiesBg.headers.name,
  header_purpose_en: mockCookiesEn.headers.purpose,
  header_purpose_bg: mockCookiesBg.headers.purpose,
  header_type_en: mockCookiesEn.headers.type,
  header_type_bg: mockCookiesBg.headers.type,
  header_duration_en: mockCookiesEn.headers.duration,
  header_duration_bg: mockCookiesBg.headers.duration,
  created_at: mockCookiesTimestamp,
  updated_at: mockCookiesTimestamp,
};

let mockCookieInventory: CookieInventoryAdminResponse[] =
  mockCookiesEn.cookies.map((item, index) => {
    const bgItem = mockCookiesBg.cookies.find(
      (candidate) => candidate.name === item.name,
    );
    return {
      name: item.name,
      purpose_en: item.purpose,
      purpose_bg: bgItem?.purpose ?? null,
      type_en: item.type,
      type_bg: bgItem?.type ?? null,
      duration_en: item.duration,
      duration_bg: bgItem?.duration ?? null,
      source: "mock_registry",
      first_seen_at: mockCookiesTimestamp,
      last_seen_at: mockCookiesTimestamp,
      last_audited_at: mockCookiesTimestamp,
      observed_on: ["mock://storefront"],
      is_active: true,
      auto_detected: true,
      sort_order: index,
      created_at: mockCookiesTimestamp,
      updated_at: mockCookiesTimestamp,
    };
  });

let mockCookieSections: CookieSectionAdminResponse[] =
  mockCookiesEn.sections.map((section, index) => {
    const bgSection = findStaticBgCookieSection(section.id);
    return {
      slug: section.id,
      title_en: section.title,
      title_bg: bgSection?.title ?? null,
      body_en: [...section.body],
      body_bg: bgSection ? [...bgSection.body] : null,
      sort_order: index,
      created_at: mockCookiesTimestamp,
      updated_at: mockCookiesTimestamp,
    };
  });

function cloneAdminCookies(): CookiesAdminResponse {
  return {
    page: { ...mockCookiesPage },
    cookies: mockCookieInventory.map((item) => ({
      ...item,
      observed_on: [...item.observed_on],
    })),
    sections: mockCookieSections.map((section) => ({
      ...section,
      body_en: [...section.body_en],
      body_bg: section.body_bg ? [...section.body_bg] : null,
    })),
  };
}

// --- In-Memory Cart State ---

interface MockCartItem {
  product_id: string;
  quantity: number;
  added_at: string;
}

let mockCartItems: MockCartItem[] = [];

// --- In-Memory Saved Products State ---

let mockSavedProductIds = new Set<string>();

// --- In-Memory Auth State ---

let mockIsAuthenticated = true;

// --- In-Memory Order Store ---

const mockOrders: OrderResponse[] = [];
const mockReturnCases: ReturnCaseResponse[] = [];
const mockRefundRecords: PaymentRefundResponse[] = [];
const mockCodSettlements: CodSettlementResponse[] = [];

function mockNow(): string {
  return new Date().toISOString();
}

function mockUuid(prefix: string): string {
  return `${prefix}-${Math.random().toString(16).slice(2)}-${Date.now()}`;
}

// --- Cart Helpers ---

function buildCartResponse(): CartResponse {
  const unavailable_items = mockCartItems
    .map((ci) => {
      const product = MOCK_PRODUCTS.find((p) => p.id === ci.product_id);
      if (product?.is_active) return null;
      return {
        product_id: ci.product_id,
        product_name: product?.name ?? ci.product_id,
        reason: product ? "inactive" : "removed",
      };
    })
    .filter((item): item is NonNullable<typeof item> => item !== null);
  const items: CartItemResponse[] = mockCartItems
    .map((ci) => {
      const product = MOCK_PRODUCTS.find((p) => p.id === ci.product_id);
      if (!product?.is_active) return null;
      return {
        product_id: ci.product_id,
        product,
        quantity: ci.quantity,
        added_at: ci.added_at,
      };
    })
    .filter((item): item is NonNullable<typeof item> => item !== null);

  const total_cents = items.reduce(
    (sum, item) => sum + item.product.effective_price_cents * item.quantity,
    0,
  );
  return {
    items,
    total_cents,
    item_count: items.reduce((sum, item) => sum + item.quantity, 0),
    unavailable_items,
  };
}

// --- Mock Functions ---

export async function getProducts(
  page = 1,
  limit = 20,
  _locale?: string,
  query: ProductListQuery = {},
): Promise<ProductListResponse> {
  await delay();
  if (limit > 100)
    mockError("VALIDATION_ERROR", "Limit exceeds maximum of 100");
  const search = query.q?.trim().toLowerCase();
  let active = MOCK_PRODUCTS.filter((p) => p.is_active);
  if (query.product_type) {
    active = active.filter((p) => p.product_type === query.product_type);
  }
  if (query.category) {
    active = active.filter((p) => p.category === query.category);
  }
  if (query.labels?.length) {
    active = active.filter((p) =>
      query.labels!.every((label) => p.labels.some((pl) => pl.slug === label)),
    );
  }
  if (query.in_stock) {
    active = active.filter((p) => p.stock > 0);
  }
  if (search) {
    active = active.filter((p) =>
      `${p.name} ${p.description ?? ""}`.toLowerCase().includes(search),
    );
  }

  active = [...active];
  switch (query.sort) {
    case "price_asc":
      active.sort((a, b) => a.effective_price_cents - b.effective_price_cents);
      break;
    case "price_desc":
      active.sort((a, b) => b.effective_price_cents - a.effective_price_cents);
      break;
    case "name":
      active.sort((a, b) => a.name.localeCompare(b.name));
      break;
    case "newest":
    default:
      active.sort((a, b) => b.created_at.localeCompare(a.created_at));
      break;
  }

  const start = (page - 1) * limit;
  const slice = active.slice(start, start + limit);
  return {
    products: slice.map((product) => toPublicProduct(product, _locale)),
    total: active.length,
    page,
    limit,
  };
}

export async function submitContact(
  data: ContactRequest,
): Promise<ContactResponse> {
  await delay();
  if (data.website?.trim()) return { status: "received", message_id: null };
  if (!data.name.trim() || !data.email.trim() || !data.message.trim()) {
    mockError("VALIDATION_ERROR", "Please check your input and try again");
  }
  return { status: "received", message_id: Date.now() };
}

export async function getProduct(
  productId: string,
  _locale?: string,
): Promise<ProductResponse> {
  await delay();
  const product = MOCK_PRODUCTS.find((p) => p.id === productId && p.is_active);
  if (!product) mockError("NOT_FOUND", `Product ${productId} not found`);
  return toPublicProduct(product, _locale);
}

export async function getSavedProducts(
  locale?: string,
  page = 1,
  limit = 100,
): Promise<SavedProductListResponse> {
  await delay();
  if (!mockIsAuthenticated) mockError("NOT_AUTHENTICATED", "Not authenticated");
  if (limit > 100)
    mockError("VALIDATION_ERROR", "Limit exceeds maximum of 100");

  const saved = Array.from(mockSavedProductIds)
    .map((id) =>
      MOCK_PRODUCTS.find((product) => product.id === id && product.is_active),
    )
    .filter(Boolean) as MockProduct[];
  const start = (page - 1) * limit;
  const slice = saved.slice(start, start + limit);
  return {
    products: slice.map((product) => toPublicProduct(product, locale)),
    product_ids: saved.map((product) => product.id),
    total: saved.length,
    page,
    limit,
  };
}

export async function saveProduct(
  productId: string,
): Promise<SavedProductStatusResponse> {
  await delay();
  if (!mockIsAuthenticated) mockError("NOT_AUTHENTICATED", "Not authenticated");
  const product = MOCK_PRODUCTS.find((p) => p.id === productId && p.is_active);
  if (!product) mockError("NOT_FOUND", `Product ${productId} not found`);
  mockSavedProductIds = new Set([productId, ...mockSavedProductIds]);
  return { product_id: productId, saved: true };
}

export async function unsaveProduct(
  productId: string,
): Promise<SavedProductStatusResponse> {
  await delay();
  if (!mockIsAuthenticated) mockError("NOT_AUTHENTICATED", "Not authenticated");
  mockSavedProductIds.delete(productId);
  return { product_id: productId, saved: false };
}

export async function getCart(): Promise<CartResponse> {
  await delay();
  return buildCartResponse();
}

export async function addToCart(
  productId: string,
  quantity = 1,
): Promise<CartResponse> {
  await delay();
  const product = MOCK_PRODUCTS.find((p) => p.id === productId && p.is_active);
  if (!product) mockError("NOT_FOUND", `Product ${productId} not found`);

  if (!Number.isInteger(quantity) || quantity < 1 || quantity > 99) {
    mockError("VALIDATION_ERROR", "Quantity must be between 1 and 99");
  }

  const existing = mockCartItems.find((ci) => ci.product_id === productId);
  const currentQty = existing ? existing.quantity : 0;
  const requestedTotal = currentQty + quantity;

  if (requestedTotal > product.stock) {
    mockError("CONFLICT", `Insufficient stock for ${productId}`);
  }

  if (existing) {
    existing.quantity = requestedTotal;
  } else {
    mockCartItems.push({
      product_id: productId,
      quantity,
      added_at: new Date().toISOString(),
    });
  }
  return buildCartResponse();
}

export async function updateCartItem(
  productId: string,
  quantity: number,
): Promise<CartResponse> {
  await delay();
  const existing = mockCartItems.find((ci) => ci.product_id === productId);
  if (!existing) mockError("NOT_FOUND", `Cart item ${productId} not found`);

  if (quantity === 0) {
    mockCartItems = mockCartItems.filter((ci) => ci.product_id !== productId);
  } else {
    const product = MOCK_PRODUCTS.find((p) => p.id === productId);
    if (product && quantity > product.stock) {
      mockError("CONFLICT", `Insufficient stock for ${productId}`);
    }
    existing.quantity = quantity;
  }
  return buildCartResponse();
}

export async function removeFromCart(productId: string): Promise<CartResponse> {
  await delay();
  const existing = mockCartItems.find((ci) => ci.product_id === productId);
  if (!existing) mockError("NOT_FOUND", `Cart item ${productId} not found`);

  mockCartItems = mockCartItems.filter((ci) => ci.product_id !== productId);
  return buildCartResponse();
}

// --- Mock Delivery Data ---

const MOCK_OFFICES: Record<Courier, OfficeResponse[]> = {
  speedy: [
    {
      id: "speedy-sf-001",
      name: "Speedy офис София Център - бул. Витоша 50",
      type: "office",
      city: "София",
      address: "бул. Витоша 50",
      working_hours: "Mon-Fri 09:00-18:00, Sat 09:00-14:00",
    },
    {
      id: "speedy-sf-002",
      name: "Speedy офис София Младост",
      type: "office",
      city: "София",
      address: "бул. Александър Малинов 12",
      working_hours: "Mon-Fri 09:00-18:00",
    },
    {
      id: "speedy-apt-sf-01",
      name: "Speedy Автомат Витоша Мол",
      type: "apt",
      city: "София",
      address: "Витоша Мол, паркинг",
      working_hours: "24/7",
    },
    {
      id: "speedy-plovdiv-001",
      name: "Speedy офис Пловдив Централ",
      type: "office",
      city: "Пловдив",
      address: "бул. Мария Луиза 5",
      working_hours: "Mon-Fri 09:00-18:00",
    },
    {
      id: "speedy-varna-001",
      name: "Speedy офис Варна Център",
      type: "office",
      city: "Варна",
      address: "бул. Сливница 10",
      working_hours: "Mon-Fri 09:00-18:00",
    },
  ],
  econt: [
    {
      id: "econt-sf-001",
      code: "1001",
      name: "Econt София Център",
      type: "office",
      city: "София",
      address: "ул. Раковски 100",
      working_hours: "Mon-Fri 09:00-19:00, Sat 09:00-15:00",
    },
    {
      id: "econt-apt-sf-01",
      code: "1002",
      name: "Econt Автомат Люлин",
      type: "apt",
      city: "София",
      address: "ж.к. Люлин, до Билла",
      working_hours: "24/7",
    },
    {
      id: "econt-plovdiv-001",
      code: "4001",
      name: "Econt Пловдив Централ",
      type: "office",
      city: "Пловдив",
      address: "бул. Шести септември 20",
      working_hours: "Mon-Fri 09:00-19:00",
    },
    {
      id: "econt-burgas-001",
      code: "8001",
      name: "Econt Бургас Център",
      type: "office",
      city: "Бургас",
      address: "ул. Александровска 45",
      working_hours: "Mon-Fri 09:00-18:00",
    },
  ],
};

export async function getDeliveryConfig(): Promise<DeliveryConfigResponse> {
  await delay();
  return {
    econt: {
      office_locator_enabled: false,
      office_locator_url: "https://delivery-demo.econt.com/customer_info.php",
      office_locator_origins: ["https://delivery-demo.econt.com"],
    },
  };
}

export async function getDeliveryOffices(
  courier: Courier,
  city: string,
  type?: OfficeType,
): Promise<OfficeResponse[]> {
  await delay();
  if (!deliveryEnabled(courier, "office")) return [];
  const cityLc = city.toLowerCase();
  return MOCK_OFFICES[courier].filter(
    (o) => o.city.toLowerCase() === cityLc && (!type || o.type === type),
  );
}

export async function getDeliveryCities(
  courier: Courier,
  query?: string,
): Promise<string[]> {
  await delay();
  if (!deliveryEnabled(courier, "office")) return [];
  const cities = Array.from(
    new Set(MOCK_OFFICES[courier].map((o) => o.city)),
  ).sort();
  if (!query) return cities;
  const q = query.toLowerCase();
  return cities.filter((c) => c.toLowerCase().startsWith(q));
}

// Fixtures include the ambiguous "Садово" (three towns, distinct postcodes) so
// the place-picker + postcode-autofill flow can be exercised without a backend.
const MOCK_PLACES: Record<Courier, CityPlace[]> = {
  econt: [
    { name: "София", region: "София (столица)", postal_code: "1000" },
    { name: "Пловдив", region: "Пловдив", postal_code: "4000" },
    { name: "Садово", region: "Пловдив", postal_code: "4122" },
    { name: "Садово", region: "Благоевград", postal_code: "2922" },
    { name: "Садово", region: "Бургас", postal_code: "8463" },
    { name: "Нови Пазар", region: "Шумен", postal_code: "9900" },
    { name: "Искър", region: "Плевен", postal_code: "5868" },
    { name: "Искър", region: "Плевен", postal_code: "5972" },
    { name: "Згориград", region: "Враца", postal_code: "3042" },
  ],
  speedy: [
    { name: "София", region: "София (столица)", postal_code: "1000" },
    { name: "Пловдив", region: "Пловдив", postal_code: "4000" },
    { name: "Садово", region: "Пловдив", postal_code: "4122" },
    { name: "Садово", region: "Благоевград", postal_code: "2922" },
    { name: "Садово", region: "Бургас", postal_code: "8463" },
    { name: "Нови Пазар", region: "Шумен", postal_code: "9900" },
    { name: "Искър", region: "Плевен", postal_code: "5868" },
    { name: "Искър", region: "Плевен", postal_code: "5972" },
    { name: "Згориград", region: "Враца", postal_code: "3042" },
    { name: "Роман", region: "Враца", postal_code: "3130" },
    { name: "Батак", region: null, postal_code: null },
  ],
};

function foldPlaceSearch(value?: string | null): string {
  return (value ?? "").toLowerCase().trim().replace(/\s+/g, " ");
}

function placeSearchTokens(value: string): string[] {
  return value ? value.split(/[^\p{L}\p{N}_]+/u).filter(Boolean) : [];
}

function placeMatchScore(place: CityPlace, query: string): number | null {
  if (!query) return 0;

  const fields = [place.name, place.region, place.postal_code]
    .map(foldPlaceSearch)
    .filter(Boolean);
  const name = foldPlaceSearch(place.name);
  const postalCode = foldPlaceSearch(place.postal_code);
  const tokens = placeSearchTokens(query);

  if (query === name || query === postalCode) return 0;
  if (name.startsWith(query)) return 1;
  if (
    tokens.length === 1 &&
    tokens.some((token) =>
      name.split(/\s+/).some((part) => part.startsWith(token)),
    )
  ) {
    return 2;
  }
  if (fields.some((field) => field.includes(query))) return 3;
  if (
    tokens.length > 0 &&
    tokens.every((token) => fields.some((field) => field.includes(token)))
  ) {
    return 4;
  }
  return null;
}

export async function getDeliveryPlaces(
  courier: Courier,
  query?: string,
): Promise<CityPlace[]> {
  await delay();
  if (!deliveryEnabled(courier, "door")) return [];
  const places = MOCK_PLACES[courier] ?? [];
  const q = foldPlaceSearch(query);
  return places
    .map((place) => ({ place, score: placeMatchScore(place, q) }))
    .filter(
      (entry): entry is { place: CityPlace; score: number } =>
        entry.score !== null,
    )
    .sort((a, b) => {
      if (a.score !== b.score) return a.score - b.score;
      return `${a.place.name}|${a.place.region ?? ""}|${a.place.postal_code ?? ""}`.localeCompare(
        `${b.place.name}|${b.place.region ?? ""}|${b.place.postal_code ?? ""}`,
      );
    })
    .map((entry) => entry.place);
}

const MOCK_FREE_SHIPPING_THRESHOLD_CENTS = 5000;
const MOCK_FALLBACK_SHIPPING_CENTS = 500;
const MOCK_INTERNAL_DELIVERY_CENTS = 350;

let mockDeliverySettings: DeliverySettingsResponse = {
  speedy_office_enabled: true,
  speedy_door_enabled: true,
  econt_office_enabled: true,
  econt_door_enabled: true,
  cod_enabled: true,
  card_enabled: true,
  bank_transfer_enabled: true,
  updated_at: new Date().toISOString(),
};

let mockEcontSettings: EcontSettingsResponse = {
  enabled: false,
  environment: "demo",
  shop_id: null,
  credential_source: "env",
  sender_delivery_mode: "office",
  sender_office_code: null,
  sender_city: null,
  sender_post_code: null,
  sender_address: null,
  sender_quarter: null,
  sender_street: null,
  sender_num: null,
  sender_other: null,
  default_pack_count: 1,
  shipment_description: "Atelier Marie order",
  declared_value_enabled: false,
  default_payment_side: "receiver",
  return_parcel_destination: "sender",
  days_until_return: 7,
  return_parcel_payment_side: "sender",
  reject_action: "return_to_sender",
  reject_payment_side: "sender",
  reject_return_payment_side: "sender",
  courier_currency: "EUR",
  currency_conversion_rate: null,
  office_locator_enabled: false,
  auto_confirm_on_label: false,
  auto_delivered_on_trace: false,
  base_url: "https://delivery-demo.econt.com/services/",
  office_locator_url: "https://delivery-demo.econt.com/customer_info.php",
  office_locator_origins: ["https://delivery-demo.econt.com"],
  secret_state: {
    credential_source: "env",
    private_key_configured: false,
    shop_id_configured: false,
    encryption_key_configured: false,
  },
  last_health_status: null,
  last_health_checked_at: null,
  last_health_error: null,
  updated_at: new Date().toISOString(),
};

let mockPaymentSettings: PublicPaymentSettingsResponse = {
  card_payments_enabled: true,
  pay_on_delivery_enabled: true,
  pay_on_delivery_max_cents: 5000,
  bank_transfer_enabled: false,
  available_payment_methods: ["card", "cod"],
};

let mockAdminPaymentSettings: PaymentSettingsResponse = {
  card_payments_enabled: true,
  pay_on_delivery_enabled: true,
  pay_on_delivery_max_cents: 5000,
  stripe: {
    mode: "test",
    secret_key_configured: true,
    webhook_secret_configured: true,
    publishable_key_configured: true,
    ready_for_card_payments: true,
    problems: [],
  },
};

function syncPublicPaymentSettings(): void {
  mockPaymentSettings = {
    card_payments_enabled: mockAdminPaymentSettings.card_payments_enabled,
    pay_on_delivery_enabled: mockAdminPaymentSettings.pay_on_delivery_enabled,
    pay_on_delivery_max_cents:
      mockAdminPaymentSettings.pay_on_delivery_max_cents,
    bank_transfer_enabled: false,
    available_payment_methods: [
      ...(mockAdminPaymentSettings.card_payments_enabled
        ? ["card" as const]
        : []),
      ...(mockAdminPaymentSettings.pay_on_delivery_enabled
        ? ["cod" as const]
        : []),
    ],
  };
}

function deliveryEnabled(courier: Courier, method: "office" | "door"): boolean {
  const key = `${courier}_${method}_enabled` as keyof DeliverySettingsUpdate;
  return mockDeliverySettings[key];
}

function paymentEnabled(method: PaymentMethod): boolean {
  const key = `${method}_enabled` as keyof DeliverySettingsUpdate;
  return mockDeliverySettings[key];
}

/** Base live prices per courier (cents) + delivery estimate (days). */
const MOCK_LIVE_QUOTES: Record<Courier, { cents: number; days: number }> = {
  speedy: { cents: 650, days: 2 },
  econt: { cents: 590, days: 3 },
};

/**
 * Mock the shipping calculator.
 * - Free shipping (0¢, live) when items_total_cents >= threshold.
 * - Otherwise returns live quotes for each requested courier.
 * - Set `address.city` to "fallback" (case-insensitive) or `office_id` to
 *   "fallback" to simulate a courier outage → flat fallback quotes.
 */
export async function calculateShipping(
  payload: CalculateShippingRequest,
): Promise<CalculateShippingResponse> {
  await delay();
  if (
    payload.couriers.some(
      (courier) => !deliveryEnabled(courier, payload.method),
    )
  ) {
    mockError(
      "DELIVERY_METHOD_UNAVAILABLE",
      "Delivery method is currently unavailable",
    );
  }
  const now = new Date().toISOString();
  const couriers =
    payload.couriers.length > 0
      ? payload.couriers
      : (["speedy", "econt"] as Courier[]);

  if (payload.items_total_cents >= MOCK_FREE_SHIPPING_THRESHOLD_CENTS) {
    return {
      quotes: couriers.map((courier) => ({
        courier,
        cents: 0,
        estimated_delivery_days: MOCK_LIVE_QUOTES[courier].days,
        is_fallback: false,
        price_source: "live",
        quoted_at: now,
      })),
    };
  }

  const simulateFallback =
    payload.city.toLowerCase() === "fallback" ||
    payload.office_id === "fallback";

  const quotes: ShippingQuote[] = couriers.map((courier) => {
    if (simulateFallback) {
      return {
        courier,
        cents: MOCK_FALLBACK_SHIPPING_CENTS,
        estimated_delivery_days: null,
        is_fallback: true,
        price_source: "flat",
        quoted_at: null,
      };
    }
    return {
      courier,
      cents: MOCK_LIVE_QUOTES[courier].cents,
      estimated_delivery_days: MOCK_LIVE_QUOTES[courier].days,
      is_fallback: false,
      price_source: "live",
      quoted_at: now,
    };
  });

  return { quotes };
}

export async function createOrder(
  data: CreateOrderRequest,
): Promise<OrderResponse> {
  await delay();
  const customerName = data.customer_name.trim();
  if (!customerName) {
    mockError("VALIDATION_ERROR", "Name is required");
  }
  const courier =
    data.delivery.method === "office"
      ? data.delivery.office?.courier
      : data.delivery.door?.courier;
  if (
    courier &&
    data.delivery.method !== "internal" &&
    !deliveryEnabled(courier, data.delivery.method)
  ) {
    mockError(
      "DELIVERY_METHOD_UNAVAILABLE",
      "Delivery method is currently unavailable",
    );
  }
  if (!paymentEnabled(data.payment_method ?? "cod")) {
    mockError(
      "PAYMENT_METHOD_UNAVAILABLE",
      "Payment method is currently unavailable",
    );
  }
  if (mockCartItems.length === 0) {
    mockError("VALIDATION_ERROR", "Cart is empty");
  }

  const cart = buildCartResponse();
  const now = new Date().toISOString();

  // Server-side free-shipping enforcement mirror: total >= threshold → 0¢, live.
  const freeShipping = cart.total_cents >= MOCK_FREE_SHIPPING_THRESHOLD_CENTS;
  const shipping_cents = freeShipping
    ? 0
    : data.delivery.method === "internal"
      ? MOCK_INTERNAL_DELIVERY_CENTS
      : (data.shipping_cents ?? 0);
  const shipping_price_source = freeShipping
    ? "live"
    : (data.shipping_price_source ?? "live");
  const shipping_is_fallback = freeShipping
    ? false
    : (data.shipping_is_fallback ?? false);
  const paymentMethod =
    data.payment_method === "card"
      ? "card"
      : data.payment_method === "bank_transfer"
        ? "bank_transfer"
        : "cod";
  const invoiceProfile = data.invoice_profile ?? null;
  const accountingClassificationState =
    invoiceProfile?.vat_identification_number
      ? "business_vat_id_provided"
      : invoiceProfile?.billing_country &&
          invoiceProfile.billing_country.toUpperCase() !== "BG"
        ? "cross_border_candidate"
        : "domestic_default";

  const order: OrderResponse = {
    id: generateOrderId(),
    status: "pending",
    payment_method: paymentMethod,
    payment_status: paymentMethod === "cod" ? "cod_pending" : "pending",
    stripe_checkout_url: null,
    invoice_profile: invoiceProfile,
    accounting_currency: "EUR",
    seller_legal_profile_version_id: null,
    vat_fiscal_settings_version_id: null,
    accounting_classification_state: accountingClassificationState,
    accounting_snapshot: {
      currency: "EUR",
      seller_legal_profile_version_id: null,
      vat_fiscal_settings_version_id: null,
      payment_method: paymentMethod,
      delivery_country: "BG",
      customer_country: invoiceProfile?.billing_country ?? null,
      shipping_cents,
      shipping_price_source,
      discounts_captured_in_effective_prices: true,
      invoice_profile: invoiceProfile,
      items: cart.items.map((item) => ({
        product_id: item.product_id,
        product_name: item.product.name,
        quantity: item.quantity,
        unit_price_cents: item.product.effective_price_cents,
      })),
    },
    accounting_readiness_status: "review_required",
    finance_period_id: null,
    analytics_consent: data.analytics_consent ?? false,
    items_total_cents: cart.total_cents,
    shipping_cents,
    shipping_price_source,
    shipping_is_fallback,
    total_cents: cart.total_cents + shipping_cents,
    customer_email: data.customer_email,
    customer_name: customerName,
    delivery_method: data.delivery.method,
    delivery_courier:
      data.delivery.method === "office"
        ? (data.delivery.office?.courier ?? null)
        : data.delivery.method === "internal"
          ? null
        : (data.delivery.door?.courier ?? null),
    delivery_details:
      data.delivery.method === "office"
        ? (data.delivery.office ?? null)
        : data.delivery.method === "internal"
          ? (data.delivery.internal ?? null)
        : (data.delivery.door ?? null),
    notes: data.notes ?? null,
    items: cart.items.map((item) => ({
      product_id: item.product_id,
      product_name: item.product.name,
      price_cents: item.product.effective_price_cents,
      quantity: item.quantity,
    })),
    tracking_number: null,
    tracking_carrier: null,
    tracking_url: null,
    courier_status: null,
    label_url: null,
    courier_provider: null,
    courier_order_id: null,
    courier_shipment_number: null,
    courier_label_url: null,
    courier_label_created_at: null,
    courier_sync_status: null,
    courier_last_error: null,
    courier_last_synced_at: null,
    created_at: now,
    updated_at: now,
  };

  mockOrders.push(order);
  mockCartItems = [];

  return order;
}

export async function getDeliverySettings(): Promise<DeliverySettingsResponse> {
  await delay();
  return { ...mockDeliverySettings };
}

export async function getPublicPaymentSettings(): Promise<PublicPaymentSettingsResponse> {
  await delay();
  syncPublicPaymentSettings();
  return {
    ...mockPaymentSettings,
    available_payment_methods: [
      ...mockPaymentSettings.available_payment_methods,
    ],
  };
}

export async function getAdminPaymentSettings(): Promise<PaymentSettingsResponse> {
  await delay();
  return {
    ...mockAdminPaymentSettings,
    stripe: {
      ...mockAdminPaymentSettings.stripe,
      problems: [...mockAdminPaymentSettings.stripe.problems],
    },
  };
}

export async function updateAdminPaymentSettings(
  data: PaymentSettingsUpdate,
): Promise<PaymentSettingsResponse> {
  await delay();
  if (!data.card_payments_enabled && !data.pay_on_delivery_enabled) {
    mockError(
      "PAYMENT_SETTINGS_INVALID",
      "At least one payment method must be enabled",
    );
  }
  mockAdminPaymentSettings = {
    ...mockAdminPaymentSettings,
    ...data,
  };
  syncPublicPaymentSettings();
  return getAdminPaymentSettings();
}

export async function getAdminDeliverySettings(): Promise<DeliverySettingsResponse> {
  await delay();
  return { ...mockDeliverySettings };
}

export async function updateAdminDeliverySettings(
  data: DeliverySettingsUpdate,
): Promise<DeliverySettingsResponse> {
  await delay();
  mockDeliverySettings = {
    ...data,
    updated_at: new Date().toISOString(),
  };
  return { ...mockDeliverySettings };
}

export async function getEcontSettings(): Promise<EcontSettingsResponse> {
  await delay();
  return {
    ...mockEcontSettings,
    auto_confirm_on_label: false,
    auto_delivered_on_trace: false,
    office_locator_origins: [...mockEcontSettings.office_locator_origins],
    secret_state: { ...mockEcontSettings.secret_state },
  };
}

export async function updateEcontSettings(
  data: EcontSettingsUpdate,
): Promise<EcontSettingsResponse> {
  await delay();
  const safeData = { ...data };
  delete safeData.auto_confirm_on_label;
  delete safeData.auto_delivered_on_trace;
  mockEcontSettings = {
    ...mockEcontSettings,
    ...safeData,
    auto_confirm_on_label: false,
    auto_delivered_on_trace: false,
    updated_at: new Date().toISOString(),
  };
  return getEcontSettings();
}

export async function testEcontConnection(): Promise<EcontConnectionTestResponse> {
  await delay();
  const ok = Boolean(
    mockEcontSettings.enabled &&
    (mockEcontSettings.shop_id ||
      mockEcontSettings.secret_state.shop_id_configured) &&
    mockEcontSettings.secret_state.private_key_configured,
  );
  mockEcontSettings.last_health_status = ok
    ? "success"
    : "missing_configuration";
  mockEcontSettings.last_health_checked_at = new Date().toISOString();
  mockEcontSettings.last_health_error = ok ? null : "missing configuration";
  return {
    status: ok ? "success" : "missing_configuration",
    ok,
    message: ok
      ? "Econt configuration reached the safe API validation path."
      : "Econt configuration is incomplete.",
    checked_at: mockEcontSettings.last_health_checked_at,
    details: { blockers: ok ? [] : ["private_key_missing", "shop_id_missing"] },
  };
}

function findMockOrder(orderId: string): OrderResponse {
  const allOrders = [...MOCK_ORDERS_SEEDED, ...mockOrders];
  const order = allOrders.find((o) => o.id === orderId);
  if (!order) mockError("NOT_FOUND", `Order ${orderId} not found`);
  return order;
}

function econtReadiness(order: OrderResponse): EcontOrderFulfillmentResponse {
  const details = (order.delivery_details ?? {}) as Record<string, unknown>;
  const blockers: string[] = [];
  if (!mockEcontSettings.enabled) blockers.push("settings_disabled");
  if (order.delivery_courier !== "econt") blockers.push("order_not_econt");
  if (order.status !== "confirmed") {
    blockers.push("order_status_not_supported");
  }
  if (order.delivery_method === "office" && !details.office_code) {
    blockers.push("order_office_code_missing");
  }
  if (!details.phone) blockers.push("order_recipient_phone_missing");
  return {
    order_id: order.id,
    ready: blockers.length === 0,
    blockers,
    courier_provider: order.courier_provider ?? null,
    courier_order_id: order.courier_order_id ?? null,
    courier_shipment_number: order.courier_shipment_number ?? null,
    courier_label_url: order.courier_label_url ?? null,
    courier_sync_status: order.courier_sync_status ?? null,
    courier_last_error: order.courier_last_error ?? null,
    courier_last_synced_at: order.courier_last_synced_at ?? null,
    tracking_number: order.tracking_number,
    tracking_url: order.tracking_url,
  };
}

export async function getEcontOrderReadiness(
  orderId: string,
): Promise<EcontOrderFulfillmentResponse> {
  await delay();
  return econtReadiness(findMockOrder(orderId));
}

export async function repairEcontOrder(
  orderId: string,
  data: EcontOrderRepairRequest,
): Promise<EcontOrderFulfillmentResponse> {
  await delay();
  const order = findMockOrder(orderId);
  const details = {
    ...((order.delivery_details ?? {}) as Record<string, unknown>),
  };
  if (data.office_code !== undefined) details.office_code = data.office_code;
  if (data.recipient_phone !== undefined) details.phone = data.recipient_phone;
  details.econt_overrides = {
    ...((details.econt_overrides as Record<string, unknown> | undefined) ?? {}),
    ...(data.pack_count ? { pack_count: data.pack_count } : {}),
    ...(data.shipment_description
      ? { shipment_description: data.shipment_description }
      : {}),
    ...(data.payment_side ? { payment_side: data.payment_side } : {}),
  };
  order.delivery_details =
    details as unknown as OrderResponse["delivery_details"];
  order.courier_sync_status = "repaired";
  order.courier_last_synced_at = new Date().toISOString();
  return econtReadiness(order);
}

export async function syncEcontOrder(
  orderId: string,
): Promise<EcontFulfillmentActionResponse> {
  await delay();
  const order = findMockOrder(orderId);
  order.courier_provider = "econt";
  order.courier_order_id = `mock-econt-${order.id.slice(0, 8)}`;
  order.courier_sync_status = "synced";
  order.courier_last_synced_at = new Date().toISOString();
  return {
    order_id: order.id,
    action: "sync_order",
    status: "synced",
    courier_order_id: order.courier_order_id,
    shipment_number: order.courier_shipment_number ?? null,
    label_url: order.courier_label_url ?? null,
    tracking_url: order.tracking_url,
    courier_status: order.courier_status ?? null,
  };
}

export async function createEcontLabel(
  orderId: string,
): Promise<EcontFulfillmentActionResponse> {
  await delay();
  const order = findMockOrder(orderId);
  const readiness = econtReadiness(order);
  if (!readiness.ready) {
    mockError(
      "ECONT_NOT_READY",
      `Econt order is not ready: ${readiness.blockers.join(", ")}`,
    );
  }
  const shipment = order.courier_shipment_number ?? `EC${Date.now()}`;
  order.courier_provider = "econt";
  order.courier_shipment_number = shipment;
  order.courier_label_url = `https://delivery-demo.econt.com/labels/${shipment}.pdf`;
  order.courier_label_created_at = new Date().toISOString();
  order.courier_sync_status = "label_created";
  order.courier_last_synced_at = order.courier_label_created_at;
  order.tracking_number = shipment;
  order.tracking_carrier = "econt";
  order.tracking_url = buildTrackingUrl("econt", shipment);
  return {
    order_id: order.id,
    action: "create_label",
    status: "created",
    courier_order_id: order.courier_order_id ?? null,
    shipment_number: shipment,
    label_url: order.courier_label_url,
    tracking_url: order.tracking_url,
    courier_status: order.courier_status ?? null,
  };
}

export async function createAndShipEcontOrder(
  orderId: string,
): Promise<EcontFulfillmentActionResponse> {
  const order = findMockOrder(orderId);
  if (order.status !== "confirmed") {
    mockError(
      "ECONT_NOT_READY",
      "Econt order must be confirmed before shipping",
    );
  }
  const result = await createEcontLabel(orderId);
  order.status = "shipped";
  order.updated_at = new Date().toISOString();
  return {
    ...result,
    action: "create_label_and_ship",
    status: "shipped",
    status_updated_to: "shipped",
  };
}

export async function deleteEcontLabel(
  orderId: string,
): Promise<EcontFulfillmentActionResponse> {
  await delay();
  const order = findMockOrder(orderId);
  order.courier_shipment_number = null;
  order.courier_label_url = null;
  order.courier_label_created_at = null;
  order.courier_sync_status = "label_deleted";
  order.courier_last_synced_at = new Date().toISOString();
  order.tracking_number = null;
  order.tracking_carrier = null;
  order.tracking_url = null;
  return {
    order_id: order.id,
    action: "delete_label",
    status: "deleted",
    courier_order_id: order.courier_order_id ?? null,
    shipment_number: null,
    label_url: null,
    tracking_url: null,
    courier_status: order.courier_status ?? null,
  };
}

export async function refreshEcontTrace(
  orderId: string,
): Promise<EcontFulfillmentActionResponse> {
  await delay();
  const order = findMockOrder(orderId);
  order.courier_sync_status = "trace_synced";
  order.courier_last_synced_at = new Date().toISOString();
  return {
    order_id: order.id,
    action: "refresh_trace",
    status: "trace_synced",
    courier_order_id: order.courier_order_id ?? null,
    shipment_number: order.courier_shipment_number ?? order.tracking_number,
    label_url: order.courier_label_url ?? null,
    tracking_url: order.tracking_url,
    courier_status: order.courier_status ?? null,
  };
}

const mockSpeedyEvents: SpeedyEventResponse[] = [
  {
    id: 1,
    order_id: "c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f",
    action: "refresh_tracking",
    status: "success",
    request: { shipmentNumber: "1234567890" },
    response: { courier_status: "in_transit" },
    error: null,
    actor_user_id: null,
    created_at: new Date(Date.now() - 3600000).toISOString(),
  },
];

function addSpeedyEvent(
  orderId: string,
  action: string,
  status: string,
  response: Record<string, unknown> | null,
  error: Record<string, unknown> | null = null,
): void {
  mockSpeedyEvents.unshift({
    id: mockSpeedyEvents.length + 1,
    order_id: orderId,
    action,
    status,
    request: { order_id: orderId },
    response,
    error,
    actor_user_id: "mock-admin",
    created_at: new Date().toISOString(),
  });
}

function speedyDeliveryLabel(order: OrderResponse): string | null {
  const details = order.delivery_details;
  if (!details) return null;
  if ("office_name" in details) return details.office_name;
  if ("street" in details) return `${details.street}, ${details.city}`;
  return null;
}

function speedySummary(order: OrderResponse) {
  return {
    order_id: order.id,
    order_number: order.order_number ?? null,
    status: order.status,
    customer_email: order.customer_email,
    customer_name: order.customer_name,
    delivery_method: order.delivery_method,
    delivery_label: speedyDeliveryLabel(order),
    total_cents: order.total_cents,
    tracking_number: order.tracking_number,
    tracking_url: order.tracking_url,
    courier_status: order.courier_status,
    courier_sync_status: order.courier_sync_status ?? null,
    courier_last_error: order.courier_last_error ?? null,
    courier_last_synced_at: order.courier_last_synced_at ?? null,
    created_at: order.created_at,
    updated_at: order.updated_at,
  };
}

export async function recordEcontManualStatus(
  orderId: string,
  data: EcontManualStatusRequest,
): Promise<EcontFulfillmentActionResponse> {
  await delay();
  const order = findMockOrder(orderId);
  order.courier_provider = "econt";
  order.courier_status = data.courier_status;
  order.courier_sync_status = "manual_status";
  order.courier_last_synced_at = new Date().toISOString();
  if (data.tracking_number) {
    order.courier_shipment_number = data.tracking_number;
    order.tracking_number = data.tracking_number;
    order.tracking_carrier = "econt";
    order.tracking_url =
      data.tracking_url ?? buildTrackingUrl("econt", data.tracking_number);
  }
  return {
    order_id: order.id,
    action: "manual_status",
    status: "manual_status_recorded",
    courier_order_id: order.courier_order_id ?? null,
    shipment_number: order.courier_shipment_number ?? null,
    label_url: order.courier_label_url ?? null,
    tracking_url: order.tracking_url,
    courier_status: order.courier_status ?? null,
  };
}

export async function getSpeedyAdminOverview(
  orderId?: string | null,
): Promise<SpeedyAdminOverviewResponse> {
  await delay();
  const allOrders = [...MOCK_ORDERS_SEEDED, ...mockOrders].map(
    withMockAccountingFlags,
  );
  const scoped = orderId
    ? allOrders.filter((order) => order.id === orderId)
    : allOrders;
  const ready = scoped.filter(
    (order) =>
      order.delivery_courier === "speedy" &&
      order.status === "confirmed" &&
      !order.tracking_number &&
      !order.courier_shipment_number,
  );
  const shipped = scoped.filter(
    (order) =>
      order.status === "shipped" &&
      (order.tracking_carrier === "speedy" ||
        order.courier_provider === "speedy") &&
      Boolean(order.tracking_number || order.courier_shipment_number),
  );
  const failuresByCategory = mockSpeedyEvents.reduce<Record<string, number>>(
    (acc, event) => {
      const category = event.error?.category;
      if (event.status === "failed" && typeof category === "string") {
        acc[category] = (acc[category] ?? 0) + 1;
      }
      return acc;
    },
    {},
  );
  return {
    health: {
      status: "healthy",
      ok: true,
      message: "Speedy configuration is healthy.",
      username_configured: true,
      password_configured: true,
      client_id_configured: true,
      client_id_numeric: true,
      configured_client_id: "123456789",
      verified_client_id: "123456789",
      client_id_matches: true,
      blockers: [],
      circuit: {
        name: "speedy_operational",
        state: "closed",
        failure_count: 0,
        failure_threshold: 3,
      },
      last_failure_category: null,
      last_successful_check_at: new Date(Date.now() - 600000).toISOString(),
      checked_at: new Date().toISOString(),
    },
    queues: {
      ready_to_ship: ready.map(speedySummary),
      shipped: shipped.map(speedySummary),
    },
    events: mockSpeedyEvents.slice(0, 25),
    metrics: {
      recent_successes: mockSpeedyEvents.filter(
        (event) => event.status === "success",
      ).length,
      recent_failures: mockSpeedyEvents.filter(
        (event) => event.status === "failed",
      ).length,
      failures_by_category: failuresByCategory,
      cancellation_count: mockSpeedyEvents.filter(
        (event) =>
          event.action === "cancel_shipment" && event.status === "success",
      ).length,
      pickup_request_count: mockSpeedyEvents.filter(
        (event) =>
          event.action === "request_pickup" && event.status === "success",
      ).length,
      last_successful_health_check_at: new Date(
        Date.now() - 600000,
      ).toISOString(),
    },
    office_refresh: {
      status: "success",
      refreshed_at: new Date(Date.now() - 86400000).toISOString(),
      records: 1284,
      error: null,
    },
  };
}

export async function createSpeedyWaybill(
  orderId: string,
): Promise<SpeedyActionResponse> {
  await delay();
  const order = findMockOrder(orderId);
  if (order.delivery_courier !== "speedy")
    mockError("SPEEDY_NOT_READY", "Order is not assigned to Speedy");
  if (order.status !== "confirmed" && !order.tracking_number) {
    mockError(
      "SPEEDY_NOT_READY",
      "Speedy waybill can only be created for confirmed orders",
    );
  }
  const shipment =
    order.tracking_number ?? `63689${Date.now().toString().slice(-6)}`;
  order.status = "shipped";
  order.tracking_number = shipment;
  order.tracking_carrier = "speedy";
  order.tracking_url = buildTrackingUrl("speedy", shipment);
  order.courier_provider = "speedy";
  order.courier_shipment_number = shipment;
  order.courier_sync_status = "waybill_created";
  order.courier_last_synced_at = new Date().toISOString();
  order.updated_at = order.courier_last_synced_at;
  addSpeedyEvent(order.id, "create_waybill", "success", {
    shipment_number: shipment,
  });
  return {
    order_id: order.id,
    action: "create_waybill",
    status: "created",
    shipment_number: shipment,
    tracking_url: order.tracking_url,
    courier_status: order.courier_status,
    status_updated_to: "shipped",
    details: null,
  };
}

export async function refreshSpeedyTracking(
  orderId: string,
): Promise<SpeedyActionResponse> {
  await delay();
  const order = findMockOrder(orderId);
  const shipment = order.tracking_number ?? order.courier_shipment_number;
  if (!shipment || order.tracking_carrier !== "speedy")
    mockError("SPEEDY_NOT_READY", "Order has no Speedy waybill");
  order.courier_status =
    order.courier_status === "in_transit" ? "out_for_delivery" : "in_transit";
  order.courier_sync_status = "track_synced";
  order.courier_last_synced_at = new Date().toISOString();
  addSpeedyEvent(order.id, "refresh_tracking", "success", {
    courier_status: order.courier_status,
  });
  return {
    order_id: order.id,
    action: "refresh_tracking",
    status: "success",
    shipment_number: shipment,
    tracking_url: order.tracking_url,
    courier_status: order.courier_status,
    status_updated_to: null,
    details: null,
  };
}

export async function searchSpeedyShipments(
  data: SpeedyShipmentSearchRequest,
): Promise<SpeedyShipmentSearchResponse> {
  await delay();
  const ref = data.reference.trim();
  if (!ref) mockError("SPEEDY_VALIDATION", "reference is required");
  const allOrders = [...MOCK_ORDERS_SEEDED, ...mockOrders].map(
    withMockAccountingFlags,
  );
  const matches = allOrders
    .filter((order) => order.id === ref || order.order_number === ref)
    .map((order) => order.tracking_number ?? order.courier_shipment_number)
    .filter((value): value is string => Boolean(value));
  return {
    reference: ref,
    barcodes: matches.length ? matches : ["1234567890"],
  };
}

export async function getSpeedyShipmentInfo(
  data: SpeedyShipmentInfoRequest,
): Promise<SpeedyShipmentInfoResponse> {
  await delay();
  return {
    shipments: data.shipment_ids.map((id) => ({
      id,
      serviceId: 505,
      status: "accepted",
    })),
  };
}

export async function cancelSpeedyShipment(
  orderId: string,
  _data: SpeedyCancelShipmentRequest = {},
): Promise<SpeedyActionResponse> {
  await delay();
  const order = findMockOrder(orderId);
  const shipment = order.tracking_number ?? order.courier_shipment_number;
  if (!shipment || order.status === "delivered")
    mockError("SPEEDY_NOT_READY", "Speedy shipment cannot be cancelled");
  order.courier_provider = "speedy";
  order.courier_status = "cancelled";
  order.courier_sync_status = "shipment_cancelled";
  order.courier_last_synced_at = new Date().toISOString();
  addSpeedyEvent(order.id, "cancel_shipment", "success", {
    shipment_id: shipment,
  });
  return {
    order_id: order.id,
    action: "cancel_shipment",
    status: "cancelled",
    shipment_number: shipment,
    tracking_url: order.tracking_url,
    courier_status: "cancelled",
    status_updated_to: null,
    details: { cancelled: true },
  };
}

export async function getSpeedyPickupTerms(
  data: SpeedyPickupTermsRequest,
): Promise<SpeedyPickupTermsResponse> {
  await delay();
  if (data.shipment_ids.length === 0)
    mockError("SPEEDY_NOT_READY", "Select at least one shipment");
  return {
    cutoffs: [
      new Date(Date.now() + 7200000).toISOString(),
      new Date(Date.now() + 10800000).toISOString(),
    ],
  };
}

export async function requestSpeedyPickup(
  data: SpeedyPickupRequest,
): Promise<SpeedyPickupResponse> {
  await delay();
  for (const shipmentId of data.shipment_ids) {
    const order = [...MOCK_ORDERS_SEEDED, ...mockOrders].find(
      (item) =>
        item.tracking_number === shipmentId ||
        item.courier_shipment_number === shipmentId,
    );
    if (order)
      addSpeedyEvent(order.id, "request_pickup", "success", {
        shipment_ids: data.shipment_ids,
      });
  }
  return {
    orders: [
      {
        id: Date.now(),
        shipmentIds: data.shipment_ids,
        pickupPeriodFrom: data.pickup_datetime,
        pickupPeriodTo: data.visit_end_time,
      },
    ],
  };
}

export async function getOrders(
  page = 1,
  limit = 20,
  filters: CustomerOrderFilters = {},
): Promise<OrderListResponse> {
  await delay();
  if (limit > 100)
    mockError("VALIDATION_ERROR", "Limit exceeds maximum of 100");

  const now = Date.now();
  const filtered = mockOrders.filter((order) => {
    const q = filters.q?.trim().replace(/^#/, "").toLowerCase();
    if (q) {
      const haystack = [
        order.id,
        order.order_number,
        ...order.items.map((item) => item.product_name),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      if (!haystack.includes(q)) return false;
    }
    if (
      filters.view === "active" &&
      !["pending", "confirmed", "shipped"].includes(order.status)
    ) {
      return false;
    }
    if (filters.view === "delivered" && order.status !== "delivered")
      return false;
    if (filters.view === "needs_action") {
      const paymentNeedsAction = [
        "pending",
        "failed",
        "review_required",
        "refund_pending",
        "dispute_open",
      ].includes(order.payment_status);
      if (order.status !== "return_in_transit" && !paymentNeedsAction)
        return false;
    }
    if (filters.date_range && filters.date_range !== "all") {
      const days = filters.date_range === "last_30_days" ? 30 : 183;
      const threshold = now - days * 24 * 60 * 60 * 1000;
      if (new Date(order.created_at).getTime() < threshold) return false;
    }
    return true;
  });

  filtered.sort((a, b) => {
    if (filters.sort === "oldest")
      return a.created_at.localeCompare(b.created_at);
    if (filters.sort === "highest") return b.total_cents - a.total_cents;
    return b.created_at.localeCompare(a.created_at);
  });

  const start = (page - 1) * limit;
  const slice = filtered.slice(start, start + limit);
  return {
    items: slice,
    total: filtered.length,
    page,
    limit,
  };
}

export async function getOrder(orderId: string): Promise<OrderResponse> {
  await delay();
  const order = mockOrders.find((o) => o.id === orderId);
  if (!order) mockError("NOT_FOUND", `Order ${orderId} not found`);
  return order;
}

export async function getCurrentUser(): Promise<UserResponse | null> {
  await delay();
  return mockIsAuthenticated ? MOCK_USER : null;
}

export async function login(
  _code: string,
  _redirectUri: string,
): Promise<AuthTokenResponse> {
  await delay();
  mockIsAuthenticated = true;
  return {
    access_token: "mock-jwt-token",
    token_type: "bearer",
    user: MOCK_USER,
  };
}

export function mockLogout(): void {
  mockIsAuthenticated = false;
  window.dispatchEvent(new Event("session-rotated"));
}

export function mockLogin(): void {
  mockIsAuthenticated = true;
}

// --- Admin Functions ---

const MOCK_ORDERS_SEEDED: OrderResponse[] = [
  {
    id: "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
    status: "pending",
    payment_method: "bank_transfer",
    payment_status: "pending",
    stripe_checkout_url: null,
    analytics_consent: true,
    items_total_cents: 7700,
    shipping_cents: 0,
    shipping_price_source: "live",
    shipping_is_fallback: false,
    total_cents: 7700,
    customer_email: "alice@example.com",
    customer_name: "Alice Johnson",
    delivery_method: "office",
    delivery_courier: "speedy",
    delivery_details: {
      courier: "speedy",
      office_id: "speedy-sf-001",
      office_name: "Speedy офис София Център",
      office_type: "office",
      city: "София",
      phone: "+359888123456",
    },
    notes: null,
    items: [
      {
        product_id: "lavender-dreams-300ml",
        product_name: "Lavender Dreams",
        price_cents: 3200,
        quantity: 1,
      },
      {
        product_id: "midnight-amber-300ml",
        product_name: "Midnight Amber",
        price_cents: 4500,
        quantity: 1,
      },
    ],
    tracking_number: null,
    tracking_carrier: null,
    tracking_url: null,
    courier_status: null,
    label_url: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e",
    status: "confirmed",
    payment_method: "cod",
    payment_status: "cod_pending",
    stripe_checkout_url: null,
    analytics_consent: false,
    items_total_cents: 5600,
    shipping_cents: 0,
    shipping_price_source: "live",
    shipping_is_fallback: false,
    total_cents: 5600,
    customer_email: "bob@example.com",
    customer_name: "Bob Smith",
    delivery_method: "door",
    delivery_courier: "econt",
    delivery_details: {
      courier: "econt",
      city: "София",
      postal_code: "1000",
      street: "ул. Оборище 5",
      building: "А",
      apartment: "12",
      phone: "+359888654321",
    },
    notes: "Gift wrapping please",
    items: [
      {
        product_id: "citrus-garden-200ml",
        product_name: "Citrus Garden",
        price_cents: 2800,
        quantity: 2,
      },
    ],
    tracking_number: null,
    tracking_carrier: null,
    tracking_url: null,
    courier_status: null,
    label_url: null,
    created_at: new Date(Date.now() - 86400000).toISOString(),
    updated_at: new Date(Date.now() - 43200000).toISOString(),
  },
  {
    id: "c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f",
    status: "shipped",
    payment_method: "card",
    payment_status: "paid",
    stripe_checkout_url: null,
    analytics_consent: true,
    items_total_cents: 3200,
    shipping_cents: 0,
    shipping_price_source: "live",
    shipping_is_fallback: false,
    total_cents: 3200,
    customer_email: "carol@example.com",
    customer_name: "Carol Davis",
    delivery_method: "office",
    delivery_courier: "econt",
    delivery_details: {
      courier: "econt",
      office_id: "econt-plovdiv-001",
      office_name: "Econt Пловдив Централ",
      office_type: "office",
      city: "Пловдив",
      phone: "+359877111222",
    },
    notes: null,
    items: [
      {
        product_id: "lavender-dreams-300ml",
        product_name: "Lavender Dreams",
        price_cents: 3200,
        quantity: 1,
      },
    ],
    tracking_number: "1234567890",
    tracking_carrier: "speedy",
    tracking_url:
      "https://www.speedy.bg/en/track-shipment?shipmentNumber=1234567890",
    courier_status: "in_transit",
    label_url: null,
    created_at: new Date(Date.now() - 172800000).toISOString(),
    updated_at: new Date(Date.now() - 86400000).toISOString(),
  },
  {
    id: "d4e5f6a7-b8c9-4d0e-1f2a-3b4c5d6e7f8a",
    status: "delivered",
    payment_method: "cod",
    payment_status: "paid",
    stripe_checkout_url: null,
    analytics_consent: true,
    items_total_cents: 9000,
    shipping_cents: 0,
    shipping_price_source: "live",
    shipping_is_fallback: false,
    total_cents: 9000,
    customer_email: "dave@example.com",
    customer_name: "Dave Wilson",
    delivery_method: "office",
    delivery_courier: "speedy",
    delivery_details: {
      courier: "speedy",
      office_id: "speedy-apt-sf-01",
      office_name: "Speedy Автомат Витоша Мол",
      office_type: "apt",
      city: "София",
      phone: "+359899555000",
    },
    notes: null,
    items: [
      {
        product_id: "midnight-amber-300ml",
        product_name: "Midnight Amber",
        price_cents: 4500,
        quantity: 2,
      },
    ],
    tracking_number: "JD014600003922222222",
    tracking_carrier: "dhl",
    tracking_url:
      "https://www.dhl.com/en/express/tracking.html?AWB=JD014600003922222222",
    courier_status: "delivered",
    label_url: null,
    created_at: new Date(Date.now() - 604800000).toISOString(),
    updated_at: new Date(Date.now() - 259200000).toISOString(),
  },
];

export async function getAdminStats(): Promise<AdminStats> {
  await delay();
  const today = new Date().toISOString().split("T")[0]!;
  const allOrders = [...MOCK_ORDERS_SEEDED, ...mockOrders].map(
    withMockAccountingFlags,
  );
  const ordersToday = allOrders.filter((o) =>
    o.created_at.startsWith(today),
  ).length;
  const weekAgo = Date.now() - 7 * 86400000;
  const revenueThisWeek = allOrders
    .filter(
      (o) =>
        new Date(o.created_at).getTime() > weekAgo &&
        o.payment_status === "paid",
    )
    .reduce((sum, o) => sum + o.total_cents, 0);
  const activeProducts = MOCK_PRODUCTS.filter((p) => p.is_active).length;
  const byStatus = allOrders.reduce<Record<string, number>>((acc, order) => {
    acc[order.status] = (acc[order.status] ?? 0) + 1;
    return acc;
  }, {});
  const byPaymentStatus = allOrders.reduce<Record<string, number>>(
    (acc, order) => {
      acc[order.payment_status] = (acc[order.payment_status] ?? 0) + 1;
      return acc;
    },
    {},
  );
  return {
    orders_today: ordersToday,
    revenue_this_week_cents: revenueThisWeek,
    active_product_count: activeProducts,
    low_stock_count: MOCK_PRODUCTS.filter((p) => p.is_active && p.stock <= 5)
      .length,
    contact_messages_needing_attention: 0,
    orders: {
      total: allOrders.length,
      revenue_cents: allOrders
        .filter((order) => order.payment_status === "paid")
        .reduce((sum, order) => sum + order.total_cents, 0),
      by_status: byStatus,
      by_payment_status: byPaymentStatus,
    },
    products: {
      total: MOCK_PRODUCTS.length,
      active: activeProducts,
    },
  };
}

/** Convert a mock product to an AdminProductResponse for mock admin endpoints. */
function toAdminProduct(product: MockProduct): AdminProductResponse {
  return {
    id: product.id,
    name_en: product.name,
    name_bg: null,
    description_en: product.description,
    description_bg: null,
    safety_warnings_en: product.safety_warnings_en,
    safety_warnings_bg: product.safety_warnings_bg,
    care_instructions_en: product.care_instructions_en,
    care_instructions_bg: product.care_instructions_bg,
    materials: product.materials,
    days_to_craft: product.days_to_craft,
    price_cents: product.price_cents,
    discount_percent: product.discount_percent,
    discount_starts_at: product.discount_starts_at,
    discount_ends_at: product.discount_ends_at,
    effective_price_cents: product.effective_price_cents,
    discount_active: product.discount_active,
    category: product.category,
    product_type: product.product_type,
    labels: product.labels.map((l) => l.slug),
    images: product.images,
    video: product.video,
    primary_image_url: product.primary_image_url,
    primary_thumbnail_url: product.primary_thumbnail_url,
    stock: product.stock,
    weight_grams: product.weight_grams,
    is_active: product.is_active,
    is_featured: product.is_featured,
    translation_stale_bg: false,
    translation_stale_en: false,
    created_at: product.created_at,
    updated_at: product.updated_at,
  };
}

export async function getAdminProducts(
  page = 1,
  limit = 20,
  filters: AdminProductFilters = {},
): Promise<AdminProductListResponse> {
  await delay();
  const query = filters.q?.trim().toLowerCase() ?? "";
  const filtered = MOCK_PRODUCTS.filter((product) => {
    if (query) {
      const haystack = [product.id, product.name, product.description]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      if (!haystack.includes(query)) return false;
    }
    if (filters.status === "active" && !product.is_active) return false;
    if (filters.status === "inactive" && product.is_active) return false;
    if (filters.media === "ready" && product.images.length === 0) return false;
    if (filters.media === "missing_image" && product.images.length > 0)
      return false;
    if (filters.media === "has_video" && !product.video) return false;
    if (filters.media === "missing_video" && product.video) return false;
    if (filters.stock === "in_stock" && product.stock <= 0) return false;
    if (filters.stock === "out_of_stock" && product.stock !== 0) return false;
    if (
      filters.stock === "low" &&
      product.stock > (filters.low_stock_threshold ?? 5)
    )
      return false;
    if (filters.product_type && product.product_type !== filters.product_type)
      return false;
    if (filters.category && product.category !== filters.category) return false;
    if (filters.label?.length) {
      const productLabels = new Set(product.labels.map((label) => label.slug));
      if (!filters.label.every((label) => productLabels.has(label)))
        return false;
    }
    if (
      filters.featured !== null &&
      filters.featured !== undefined &&
      product.is_featured !== filters.featured
    )
      return false;
    if (filters.discount === "active" && !product.discount_active) return false;
    if (filters.discount === "scheduled") {
      if (!product.discount_percent || !product.discount_starts_at)
        return false;
      if (new Date(product.discount_starts_at) <= new Date()) return false;
    }
    if (filters.discount === "none" && product.discount_percent != null)
      return false;
    if (filters.inventory_mode && filters.inventory_mode !== "legacy")
      return false;
    if (filters.recipe_status && filters.recipe_status !== "missing")
      return false;
    if (filters.has_inventory_exceptions === true) return false;
    return true;
  });
  filtered.sort((a, b) => {
    switch (filters.sort) {
      case "name_asc":
        return a.name.localeCompare(b.name);
      case "name_desc":
        return b.name.localeCompare(a.name);
      case "price_asc":
        return a.price_cents - b.price_cents;
      case "price_desc":
        return b.price_cents - a.price_cents;
      case "stock_asc":
        return a.stock - b.stock;
      case "stock_desc":
        return b.stock - a.stock;
      case "updated_asc":
        return a.updated_at.localeCompare(b.updated_at);
      case "created_asc":
        return a.created_at.localeCompare(b.created_at);
      case "updated_desc":
        return b.updated_at.localeCompare(a.updated_at);
      default:
        return b.created_at.localeCompare(a.created_at);
    }
  });
  const start = (page - 1) * limit;
  const slice = filtered.slice(start, start + limit);
  return {
    products: slice.map(toAdminProduct),
    total: filtered.length,
    page,
    limit,
  };
}

export async function getAdminProduct(
  productId: string,
): Promise<AdminProductResponse> {
  await delay();
  const product = MOCK_PRODUCTS.find((p) => p.id === productId);
  if (!product) mockError("NOT_FOUND", `Product ${productId} not found`);
  return toAdminProduct(product);
}

function mockTermName(kind: TaxonomyKind, slug: string | null): string | null {
  if (!slug) return null;
  const term = MOCK_TAXONOMY[kind].find((t) => t.slug === slug);
  return term ? term.name_en : slug;
}

function mockLabelRefs(
  slugs: string[] | undefined,
): { slug: string; name: string }[] {
  return (slugs ?? []).map((slug) => ({
    slug,
    name: mockTermName("labels", slug) ?? slug,
  }));
}

export async function createProduct(
  data: CreateProductRequest,
): Promise<AdminProductResponse> {
  await delay();
  const existing = MOCK_PRODUCTS.find((p) => p.id === data.id);
  if (existing) mockError("CONFLICT", `Product ${data.id} already exists`);
  const now = new Date().toISOString();
  const product: MockProduct = {
    id: data.id,
    name: data.name_en,
    description: data.description_en ?? null,
    safety_warnings: data.safety_warnings_en ?? data.safety_warnings_bg ?? null,
    care_instructions:
      data.care_instructions_en ?? data.care_instructions_bg ?? null,
    safety_warnings_en: data.safety_warnings_en ?? null,
    safety_warnings_bg: data.safety_warnings_bg ?? null,
    care_instructions_en: data.care_instructions_en ?? null,
    care_instructions_bg: data.care_instructions_bg ?? null,
    materials: data.materials ?? null,
    days_to_craft: data.days_to_craft ?? null,
    price_cents: data.price_cents,
    effective_price_cents: data.price_cents,
    discount_percent: data.discount_percent ?? null,
    discount_active: false,
    discount_starts_at: data.discount_starts_at ?? null,
    discount_ends_at: data.discount_ends_at ?? null,
    category: data.category ?? null,
    category_name: mockTermName("categories", data.category ?? null),
    product_type: data.product_type ?? "candles",
    product_type_name:
      mockTermName("product-types", data.product_type ?? "candles") ??
      data.product_type ??
      "candles",
    labels: mockLabelRefs(data.labels),
    images: [],
    video: null,
    primary_image_url: null,
    primary_thumbnail_url: null,
    stock: data.stock,
    weight_grams: data.weight_grams ?? 300,
    is_active: data.is_active ?? true,
    is_featured: data.is_featured ?? false,
    created_at: now,
    updated_at: now,
  };
  applyMockPricing(product);
  MOCK_PRODUCTS.push(product);
  return toAdminProduct(product);
}

export async function updateProduct(
  productId: string,
  data: UpdateProductRequest,
): Promise<AdminProductResponse> {
  await delay();
  const product = MOCK_PRODUCTS.find((p) => p.id === productId);
  if (!product) mockError("NOT_FOUND", `Product ${productId} not found`);
  // Map bilingual fields to the mock's single-language store
  if (data.name_en !== undefined) product.name = data.name_en;
  if (data.description_en !== undefined)
    product.description = data.description_en;
  if (data.safety_warnings_en !== undefined)
    product.safety_warnings_en = data.safety_warnings_en;
  if (data.safety_warnings_bg !== undefined)
    product.safety_warnings_bg = data.safety_warnings_bg;
  if (data.care_instructions_en !== undefined)
    product.care_instructions_en = data.care_instructions_en;
  if (data.care_instructions_bg !== undefined)
    product.care_instructions_bg = data.care_instructions_bg;
  product.safety_warnings =
    product.safety_warnings_en ?? product.safety_warnings_bg;
  product.care_instructions =
    product.care_instructions_en ?? product.care_instructions_bg;
  if (data.materials !== undefined) product.materials = data.materials;
  if (data.days_to_craft !== undefined)
    product.days_to_craft = data.days_to_craft;
  if (data.price_cents !== undefined) product.price_cents = data.price_cents;
  if (data.category !== undefined) {
    product.category = data.category;
    product.category_name = mockTermName("categories", data.category);
  }
  if (data.product_type !== undefined) {
    product.product_type = data.product_type;
    product.product_type_name =
      mockTermName("product-types", data.product_type) ?? data.product_type;
  }
  if (data.labels !== undefined) product.labels = mockLabelRefs(data.labels);
  if (data.stock !== undefined) product.stock = data.stock;
  if (data.weight_grams !== undefined) product.weight_grams = data.weight_grams;
  if (data.is_active !== undefined) product.is_active = data.is_active;
  if (data.is_featured !== undefined) product.is_featured = data.is_featured;
  // Discount merge: percent = null clears all bounds together.
  if (data.discount_percent === null) {
    product.discount_percent = null;
    product.discount_starts_at = null;
    product.discount_ends_at = null;
  } else {
    if (data.discount_percent !== undefined)
      product.discount_percent = data.discount_percent;
    if (data.discount_starts_at !== undefined)
      product.discount_starts_at = data.discount_starts_at;
    if (data.discount_ends_at !== undefined)
      product.discount_ends_at = data.discount_ends_at;
  }
  applyMockPricing(product);
  product.updated_at = new Date().toISOString();
  return toAdminProduct(product);
}

export async function deleteProduct(
  productId: string,
): Promise<AdminProductResponse> {
  await delay();
  const product = MOCK_PRODUCTS.find((p) => p.id === productId);
  if (!product) mockError("NOT_FOUND", `Product ${productId} not found`);
  product.is_active = false;
  product.video = null;
  product.updated_at = new Date().toISOString();
  return toAdminProduct(product);
}

export async function uploadProductImage(
  productId: string,
  file: File,
): Promise<ImageUploadResponse> {
  await delay();
  const product = MOCK_PRODUCTS.find((p) => p.id === productId);
  if (!product)
    mockError("product_not_found", `Product ${productId} not found`);
  if (!/^image\/(jpeg|png)$/.test(file.type)) {
    mockError("invalid_image_type", "Only JPEG and PNG images are accepted");
  }
  if (product.images.length >= 6) {
    mockError(
      "max_product_images",
      "Product already has the maximum number of images",
    );
  }
  const imageId = `${productId}-${Date.now()}`;
  const imageUrl =
    product.primary_image_url ?? "/static/products/vanilla-bourbon-300ml.webp";
  const image: ProductImage = {
    id: imageId,
    image_url: imageUrl,
    thumbnail_url: imageUrl,
    zoom_url: imageUrl,
    sort_order: product.images.length,
    is_primary: product.images.length === 0,
  };
  product.images.push(image);
  product.primary_image_url = primaryImageUrl(product.images);
  product.primary_thumbnail_url = primaryThumbnailUrl(product.images);
  product.updated_at = new Date().toISOString();
  return image;
}

export async function deleteProductImage(
  productId: string,
  imageId: string,
): Promise<void> {
  await delay();
  const product = MOCK_PRODUCTS.find((p) => p.id === productId);
  if (!product)
    mockError("product_not_found", `Product ${productId} not found`);
  const image = product.images.find((item) => item.id === imageId);
  if (!image) mockError("image_not_found", `Image ${imageId} not found`);
  product.images = product.images.filter((item) => item.id !== imageId);
  if (image.is_primary && product.images.length > 0) {
    product.images = product.images.map((item, index) => ({
      ...item,
      is_primary: index === 0,
    }));
  }
  product.images = product.images.map((item, index) => ({
    ...item,
    sort_order: index,
  }));
  product.primary_image_url = primaryImageUrl(product.images);
  product.primary_thumbnail_url = primaryThumbnailUrl(product.images);
}

export async function reorderProductImages(
  productId: string,
  orderedIds: string[],
): Promise<ProductImage[]> {
  await delay();
  const product = MOCK_PRODUCTS.find((p) => p.id === productId);
  if (!product)
    mockError("product_not_found", `Product ${productId} not found`);
  if (new Set(orderedIds).size !== product.images.length) {
    mockError(
      "invalid_image_order",
      "ordered_ids must match all images for the product",
    );
  }
  product.images = orderedIds.map((id, index) => {
    const image = product.images.find((item) => item.id === id);
    if (!image)
      mockError(
        "invalid_image_order",
        "ordered_ids must match all images for the product",
      );
    return { ...image, sort_order: index };
  });
  return product.images;
}

export async function setPrimaryProductImage(
  productId: string,
  imageId: string,
): Promise<ProductImage> {
  await delay();
  const product = MOCK_PRODUCTS.find((p) => p.id === productId);
  if (!product)
    mockError("product_not_found", `Product ${productId} not found`);
  let primary: ProductImage | undefined;
  product.images = product.images.map((image) => {
    const next = { ...image, is_primary: image.id === imageId };
    if (next.is_primary) primary = next;
    return next;
  });
  if (!primary) mockError("image_not_found", `Image ${imageId} not found`);
  product.primary_image_url = primaryImageUrl(product.images);
  product.primary_thumbnail_url = primaryThumbnailUrl(product.images);
  return primary;
}

export async function uploadProductVideo(
  productId: string,
  file: File,
): Promise<VideoUploadResponse> {
  await delay();
  const product = MOCK_PRODUCTS.find((p) => p.id === productId);
  if (!product)
    mockError("product_not_found", `Product ${productId} not found`);
  if (!file.type.startsWith("video/")) {
    mockError("invalid_video", "Upload a valid video file");
  }
  const now = new Date().toISOString();
  const video: ProductVideo = {
    id: `${productId}-${Date.now()}`,
    product_id: productId,
    status: "queued",
    video_url: null,
    poster_url: product.primary_thumbnail_url,
    sort_order: product.video?.sort_order ?? Math.min(1, product.images.length),
    duration_secs: null,
    failure_reason: null,
    created_at: now,
    updated_at: now,
  };
  product.video = video;
  return video;
}

export async function getProductVideo(
  productId: string,
): Promise<ProductVideo> {
  await delay();
  const product = MOCK_PRODUCTS.find((p) => p.id === productId);
  if (!product)
    mockError("product_not_found", `Product ${productId} not found`);
  if (!product.video) mockError("video_not_found", "Product video not found");
  return product.video;
}

export async function deleteProductVideo(productId: string): Promise<void> {
  await delay();
  const product = MOCK_PRODUCTS.find((p) => p.id === productId);
  if (!product)
    mockError("product_not_found", `Product ${productId} not found`);
  if (!product.video) mockError("video_not_found", "Product video not found");
  product.video = null;
}

export async function updateProductVideoSortOrder(
  productId: string,
  sortOrder: number,
): Promise<ProductVideo> {
  await delay();
  const product = MOCK_PRODUCTS.find((p) => p.id === productId);
  if (!product)
    mockError("product_not_found", `Product ${productId} not found`);
  if (!product.video) mockError("video_not_found", "Product video not found");
  product.video = {
    ...product.video,
    sort_order: sortOrder,
    updated_at: new Date().toISOString(),
  };
  return product.video;
}

export async function getAdminOrders(
  page = 1,
  limit = 20,
  status?: string,
  paymentStatus?: PaymentStatus | "",
  paymentMethod?: PaymentMethod | "",
  accountingFilter?: AdminOrderAccountingFilter | "",
  financePeriodId?: string,
): Promise<OrderListResponse> {
  await delay();
  const allOrders = [...MOCK_ORDERS_SEEDED, ...mockOrders].map(
    withMockAccountingFlags,
  );
  const filtered = allOrders.filter((order) => {
    if (status && order.status !== status) return false;
    if (paymentStatus && order.payment_status !== paymentStatus) return false;
    if (paymentMethod && order.payment_method !== paymentMethod) return false;
    if (financePeriodId && order.finance_period_id !== financePeriodId)
      return false;
    if (
      accountingFilter === "missing_document_reference" &&
      order.document_reference_status !== "missing"
    )
      return false;
    if (
      accountingFilter === "unresolved_exception" &&
      !order.blocking_exception_count
    )
      return false;
    if (
      accountingFilter === "payout_mismatch" &&
      order.payout_reconciliation_status !== "mismatch"
    )
      return false;
    if (
      accountingFilter === "cod_settlement_pending" &&
      order.cod_settlement_status !== "pending"
    )
      return false;
    if (
      accountingFilter === "refund_document_missing" &&
      order.document_reference_status !== "review_required"
    )
      return false;
    if (
      accountingFilter === "vat_review_required" &&
      order.accounting_classification_state !== "manual_review_required"
    )
      return false;
    return true;
  });
  const start = (page - 1) * limit;
  const slice = filtered.slice(start, start + limit);
  return {
    items: slice,
    total: filtered.length,
    page,
    limit,
  };
}

export async function getAdminOrder(
  orderId: string,
): Promise<AdminOrderDetailResponse> {
  await delay();
  const allOrders = [...MOCK_ORDERS_SEEDED, ...mockOrders].map(
    withMockAccountingFlags,
  );
  const order = allOrders.find((o) => o.id === orderId);
  if (!order) mockError("NOT_FOUND", `Order ${orderId} not found`);
  return {
    ...order,
    payment_events: [
      {
        id: `evt-${order.id}`,
        order_id: order.id,
        payment_id: null,
        event_type: "manual_mark_collected",
        source: "admin",
        provider: order.payment_method,
        provider_status: order.payment_status,
        processing_status: "processed",
        admin_email: "marie@ateliermarie.com",
        admin_note: "Mock payment note",
        request_id: "mock-request",
        created_at: order.updated_at,
      },
    ],
    return_cases: mockReturnCases.filter(
      (returnCase) => returnCase.order_id === order.id,
    ),
    return_events: [],
    refund_records: mockRefundRecords.filter(
      (refund) => refund.order_id === order.id,
    ),
    cod_settlement:
      mockCodSettlements.find(
        (settlement) => settlement.order_id === order.id,
      ) ?? null,
    cod_settlement_required:
      order.payment_method === "cod" &&
      order.status === "delivered" &&
      !mockCodSettlements.some(
        (settlement) => settlement.order_id === order.id,
      ),
    econt_cod_evidence: null,
  };
}

export async function getAccountingConfig(): Promise<AccountingConfigurationResponse> {
  await delay();
  return cloneMock(mockAccountingConfig);
}

export async function getLegalIdentity(): Promise<LegalIdentityResponse> {
  await delay();
  const seller = mockAccountingConfig.seller_profile;
  const address = formatMockAddress(seller?.registered_address ?? null);
  const identity: LegalIdentityResponse = {
    trading_name: seller?.company_display_name || "Atelier Marie",
    legal_name: seller?.legal_name ?? null,
    country: stringField(seller?.registered_address?.country) ?? "Bulgaria",
    geographic_address: address || null,
    contact_email: seller?.contact_email || "contacts@theateliermarie.com",
    registration_number: seller?.uic_eik ?? null,
    vat_number: seller?.vat_identification_number ?? null,
    responsible_party_name: seller?.company_display_name || "Atelier Marie",
    responsible_party_address: address || null,
    responsible_party_email:
      seller?.contact_email || "contacts@theateliermarie.com",
  };
  return cloneMock(identity);
}

export async function createSellerLegalProfile(
  data: SellerLegalProfileRequest,
): Promise<SellerLegalProfileResponse> {
  await delay();
  const profile: SellerLegalProfileResponse = {
    ...data,
    id: Date.now(),
    reviewed: Boolean(data.reviewed),
    default_currency: data.default_currency ?? "EUR",
    bank_details_configured: Boolean(data.bank_details),
    created_by_admin_id: "mock-admin",
    created_at: new Date().toISOString(),
  };
  mockAccountingConfig = { ...mockAccountingConfig, seller_profile: profile };
  return cloneMock(profile);
}

export async function createVatFiscalSettings(
  data: VatFiscalSettingsRequest,
): Promise<VatFiscalSettingsResponse> {
  await delay();
  const settings: VatFiscalSettingsResponse = {
    ...data,
    id: Date.now(),
    reviewed: Boolean(data.reviewed),
    vat_mode: data.vat_mode ?? "unknown",
    oss_mode: data.oss_mode ?? "not_applicable",
    fiscal_document_mode: data.fiscal_document_mode ?? "external_reference",
    tolerance_cents: data.tolerance_cents ?? 1,
    created_by_admin_id: "mock-admin",
    created_at: new Date().toISOString(),
  };
  mockAccountingConfig = {
    ...mockAccountingConfig,
    vat_fiscal_settings: settings,
  };
  return cloneMock(settings);
}

export async function upsertAccountingCategoryMapping(
  mappingKey: string,
  data: CategoryMappingRequest,
): Promise<CategoryMappingResponse> {
  await delay();
  const now = new Date().toISOString();
  const existing = mockAccountingConfig.category_mappings.find(
    (item) => item.mapping_key === mappingKey,
  );
  const mapping: CategoryMappingResponse = {
    id: existing?.id ?? Date.now(),
    mapping_key: mappingKey,
    category_code: data.category_code ?? null,
    category_label: data.category_label,
    is_required: Boolean(data.is_required),
    reviewed: Boolean(data.reviewed),
    created_at: existing?.created_at ?? now,
    updated_at: now,
  };
  mockAccountingConfig = {
    ...mockAccountingConfig,
    category_mappings: [
      ...mockAccountingConfig.category_mappings.filter(
        (item) => item.mapping_key !== mappingKey,
      ),
      mapping,
    ],
  };
  return cloneMock(mapping);
}

export async function updateAccountingExportSchema(
  data: ExportSchemaSettingsRequest,
): Promise<ExportSchemaSettingsResponse> {
  await delay();
  const next: ExportSchemaSettingsResponse = {
    ...mockAccountingConfig.export_schema,
    ...data,
    updated_at: new Date().toISOString(),
  };
  mockAccountingConfig = { ...mockAccountingConfig, export_schema: next };
  return cloneMock(next);
}

export async function updateExpenseEvidenceSettings(
  data: ExpenseEvidenceSettingsRequest,
): Promise<ExpenseEvidenceSettingsResponse> {
  await delay();
  const next: ExpenseEvidenceSettingsResponse = {
    ...mockAccountingConfig.expense_settings,
    ...data,
    updated_at: new Date().toISOString(),
  };
  mockAccountingConfig = { ...mockAccountingConfig, expense_settings: next };
  return cloneMock(next);
}

export async function updateProductCostSettings(
  data: ProductCostSettingsRequest,
): Promise<ProductCostSettingsResponse> {
  await delay();
  const next: ProductCostSettingsResponse = {
    ...mockAccountingConfig.product_cost_settings,
    ...data,
    updated_at: new Date().toISOString(),
  };
  mockAccountingConfig = {
    ...mockAccountingConfig,
    product_cost_settings: next,
  };
  return cloneMock(next);
}

export async function listFinancePeriods(
  status?: string,
): Promise<FinancePeriodListResponse> {
  await delay();
  const items = status
    ? mockFinancePeriods.filter((period) => period.status === status)
    : mockFinancePeriods;
  return { items: cloneMock(items), total: items.length };
}

export async function createFinancePeriod(
  data: FinancePeriodCreateRequest,
): Promise<FinancePeriodResponse> {
  await delay();
  const now = new Date().toISOString();
  const period: FinancePeriodResponse = {
    id: `period-${data.period_start}`,
    period_start: data.period_start,
    period_end: data.period_end,
    currency: data.currency ?? "EUR",
    status: "open",
    summary_totals: null,
    open_exception_count: 0,
    blocking_exception_count: 0,
    created_by_admin_id: "mock-admin",
    updated_by_admin_id: "mock-admin",
    closed_by_admin_id: null,
    closed_at: null,
    accepted_at: null,
    reopened_from_export_id: null,
    reopen_reason: null,
    created_at: now,
    updated_at: now,
  };
  mockFinancePeriods.unshift(period);
  return cloneMock(period);
}

function findMockPeriod(periodId: string): FinancePeriodResponse {
  const period = mockFinancePeriods.find((item) => item.id === periodId);
  if (!period)
    mockError("FINANCE_PERIOD_NOT_FOUND", "Finance period not found");
  return period;
}

export async function reviewFinancePeriod(
  periodId: string,
): Promise<FinancePeriodResponse> {
  await delay();
  const period = findMockPeriod(periodId);
  period.status = "review";
  period.updated_at = new Date().toISOString();
  return cloneMock(period);
}

export async function closeFinancePeriod(
  periodId: string,
): Promise<FinancePeriodResponse> {
  await delay();
  const period = findMockPeriod(periodId);
  if (period.blocking_exception_count > 0) {
    mockError(
      "FINANCE_PERIOD_CLOSE_BLOCKED",
      "Blocking accounting exceptions remain open",
    );
  }
  period.status = "closed";
  period.closed_at = new Date().toISOString();
  period.updated_at = period.closed_at;
  return cloneMock(period);
}

export async function reopenFinancePeriod(
  periodId: string,
  data: FinancePeriodActionRequest,
): Promise<FinancePeriodResponse> {
  await delay();
  if (!data.reason?.trim())
    mockError("REASON_REQUIRED", "A reopen reason is required");
  const period = findMockPeriod(periodId);
  period.status = "reopened";
  period.reopen_reason = data.reason;
  period.updated_at = new Date().toISOString();
  return cloneMock(period);
}

export async function acceptFinancePeriod(
  periodId: string,
  data: FinancePeriodActionRequest,
): Promise<FinancePeriodResponse> {
  await delay();
  const period = findMockPeriod(periodId);
  period.status = "accepted";
  period.accepted_at = new Date().toISOString();
  period.updated_at = period.accepted_at;
  void data;
  return cloneMock(period);
}

export async function listFinanceExceptions(
  periodId: string,
  status?: FinanceExceptionStatus | "",
): Promise<FinanceExceptionListResponse> {
  await delay();
  const items = mockFinanceExceptions.filter(
    (item) =>
      item.period_id === periodId && (!status || item.status === status),
  );
  return { items: cloneMock(items), total: items.length };
}

function applyExceptionAction(
  exceptionId: string,
  data: FinanceExceptionActionRequest,
  status: "resolved" | "waived",
): FinanceExceptionResponse {
  if (!data.reason.trim()) mockError("REASON_REQUIRED", "A reason is required");
  const item = mockFinanceExceptions.find(
    (exception) => exception.id === exceptionId,
  );
  if (!item)
    mockError("FINANCE_EXCEPTION_NOT_FOUND", "Finance exception not found");
  item.status = status;
  item.updated_at = new Date().toISOString();
  if (status === "resolved") item.resolved_at = item.updated_at;
  if (status === "waived") {
    item.waiver_reason = data.reason;
    item.waived_at = item.updated_at;
    item.waived_by_admin_id = "mock-admin";
  }
  const period = item.period_id
    ? mockFinancePeriods.find((periodItem) => periodItem.id === item.period_id)
    : null;
  if (period) {
    const open = mockFinanceExceptions.filter(
      (exception) =>
        exception.period_id === period.id && exception.status === "open",
    );
    period.open_exception_count = open.length;
    period.blocking_exception_count = open.filter(
      (exception) => exception.severity === "blocking",
    ).length;
  }
  return item;
}

export async function resolveFinanceException(
  exceptionId: string,
  data: FinanceExceptionActionRequest,
): Promise<FinanceExceptionResponse> {
  await delay();
  return cloneMock(applyExceptionAction(exceptionId, data, "resolved"));
}

export async function waiveFinanceException(
  exceptionId: string,
  data: FinanceExceptionActionRequest,
): Promise<FinanceExceptionResponse> {
  await delay();
  return cloneMock(applyExceptionAction(exceptionId, data, "waived"));
}

export async function getAccountingLedger(
  periodId: string,
  ledger: AccountingLedgerName,
  options: { dateBasis?: string; page?: number; limit?: number } = {},
): Promise<AccountingLedgerResponse> {
  await delay();
  findMockPeriod(periodId);
  const rows = mockLedgerRows[ledger] ?? [];
  const page = options.page ?? 1;
  const limit = options.limit ?? 100;
  const start = (page - 1) * limit;
  const slice = rows.slice(start, start + limit);
  return {
    period_id: periodId,
    ledger,
    date_basis: options.dateBasis ?? "default",
    rows: cloneMock(slice),
    totals: { row_count: rows.length },
    total: rows.length,
    page,
    limit,
  };
}

export async function listAccountingDocuments(
  filters: {
    orderId?: string;
    refundId?: string;
    periodId?: string;
  } = {},
): Promise<AccountingDocumentListResponse> {
  await delay();
  const items = mockAccountingDocuments.filter((document) => {
    if (filters.orderId && document.order_id !== filters.orderId) return false;
    if (filters.refundId && document.refund_id !== filters.refundId)
      return false;
    if (filters.periodId && document.period_id !== filters.periodId)
      return false;
    return true;
  });
  return { items: cloneMock(items), total: items.length };
}

export async function listOrderAccountingDocuments(
  orderId: string,
): Promise<AccountingDocumentListResponse> {
  return listAccountingDocuments({ orderId });
}

export async function createAccountingDocument(
  data: AccountingDocumentRequest,
): Promise<AccountingDocumentResponse> {
  await delay();
  const now = new Date().toISOString();
  const document: AccountingDocumentResponse = {
    ...data,
    id: `doc-${Date.now()}`,
    source_system: data.source_system ?? "external",
    currency: data.currency ?? "EUR",
    status: data.status ?? "recorded",
    created_by_admin_id: "mock-admin",
    updated_by_admin_id: "mock-admin",
    created_at: now,
    updated_at: now,
  };
  mockAccountingDocuments.unshift(document);
  mockLedgerRows.documents = mockAccountingDocuments as unknown as Record<
    string,
    unknown
  >[];
  return cloneMock(document);
}

export async function updateAccountingDocument(
  documentId: string,
  data: AccountingDocumentRequest,
): Promise<AccountingDocumentResponse> {
  await delay();
  const index = mockAccountingDocuments.findIndex(
    (document) => document.id === documentId,
  );
  if (index < 0)
    mockError("ACCOUNTING_DOCUMENT_NOT_FOUND", "Accounting document not found");
  const next: AccountingDocumentResponse = {
    ...mockAccountingDocuments[index]!,
    ...data,
    source_system:
      data.source_system ?? mockAccountingDocuments[index]!.source_system,
    currency: data.currency ?? mockAccountingDocuments[index]!.currency,
    status: data.status ?? mockAccountingDocuments[index]!.status,
    updated_by_admin_id: "mock-admin",
    updated_at: new Date().toISOString(),
  };
  mockAccountingDocuments[index] = next;
  mockLedgerRows.documents = mockAccountingDocuments as unknown as Record<
    string,
    unknown
  >[];
  return cloneMock(next);
}

export async function listExpenseEvidence(
  filters: {
    categoryKey?: string;
    reviewStatus?: string;
  } = {},
): Promise<ExpenseEvidenceListResponse> {
  await delay();
  const items = mockExpenseEvidence.filter((expense) => {
    if (filters.categoryKey && expense.category_key !== filters.categoryKey)
      return false;
    if (filters.reviewStatus && expense.review_status !== filters.reviewStatus)
      return false;
    return true;
  });
  return { items: cloneMock(items), total: items.length };
}

export async function createExpenseEvidence(
  data: ExpenseEvidenceRequest,
): Promise<ExpenseEvidenceResponse> {
  await delay();
  const now = new Date().toISOString();
  const expense: ExpenseEvidenceResponse = {
    ...data,
    id: `expense-${Date.now()}`,
    payment_status: data.payment_status ?? "unpaid",
    tax_amount_cents: data.tax_amount_cents ?? 0,
    currency: data.currency ?? "EUR",
    review_status: data.review_status ?? "unreviewed",
    created_by_admin_id: "mock-admin",
    updated_by_admin_id: "mock-admin",
    created_at: now,
    updated_at: now,
  };
  mockExpenseEvidence.unshift(expense);
  mockLedgerRows.expenses = mockExpenseEvidence as unknown as Record<
    string,
    unknown
  >[];
  return cloneMock(expense);
}

export async function updateExpenseEvidence(
  expenseId: string,
  data: ExpenseEvidenceRequest,
): Promise<ExpenseEvidenceResponse> {
  await delay();
  const index = mockExpenseEvidence.findIndex(
    (expense) => expense.id === expenseId,
  );
  if (index < 0)
    mockError("EXPENSE_EVIDENCE_NOT_FOUND", "Expense evidence not found");
  const next: ExpenseEvidenceResponse = {
    ...mockExpenseEvidence[index]!,
    ...data,
    payment_status:
      data.payment_status ?? mockExpenseEvidence[index]!.payment_status,
    tax_amount_cents:
      data.tax_amount_cents ?? mockExpenseEvidence[index]!.tax_amount_cents,
    currency: data.currency ?? mockExpenseEvidence[index]!.currency,
    review_status:
      data.review_status ?? mockExpenseEvidence[index]!.review_status,
    updated_by_admin_id: "mock-admin",
    updated_at: new Date().toISOString(),
  };
  mockExpenseEvidence[index] = next;
  mockLedgerRows.expenses = mockExpenseEvidence as unknown as Record<
    string,
    unknown
  >[];
  return cloneMock(next);
}

export async function updateExpensePaymentStatus(
  expenseId: string,
  data: ExpensePaymentStatusRequest,
): Promise<ExpenseEvidenceResponse> {
  await delay();
  if (!data.reason.trim()) mockError("REASON_REQUIRED", "A reason is required");
  const expense = mockExpenseEvidence.find((item) => item.id === expenseId);
  if (!expense)
    mockError("EXPENSE_EVIDENCE_NOT_FOUND", "Expense evidence not found");
  expense.payment_status = data.payment_status;
  expense.payment_date = data.payment_date ?? expense.payment_date;
  expense.updated_at = new Date().toISOString();
  return cloneMock(expense);
}

export async function listProductCosts(
  productId?: string,
): Promise<ProductCostVersionListResponse> {
  await delay();
  const items = productId
    ? mockProductCosts.filter((cost) => cost.product_id === productId)
    : mockProductCosts;
  return { items: cloneMock(items), total: items.length };
}

export async function createProductCost(
  data: ProductCostVersionRequest,
): Promise<ProductCostVersionResponse> {
  await delay();
  const now = new Date().toISOString();
  const estimated =
    data.estimated_unit_cost_cents ??
    (data.material_cost_cents ?? 0) +
      (data.packaging_cost_cents ?? 0) +
      (data.labor_cost_cents ?? 0) +
      (data.overhead_cost_cents ?? 0);
  const cost: ProductCostVersionResponse = {
    ...data,
    id: `cost-${Date.now()}`,
    costing_basis: data.costing_basis ?? "manual_snapshot",
    material_cost_cents: data.material_cost_cents ?? 0,
    packaging_cost_cents: data.packaging_cost_cents ?? 0,
    labor_cost_cents: data.labor_cost_cents ?? 0,
    overhead_cost_cents: data.overhead_cost_cents ?? 0,
    estimated_unit_cost_cents: estimated,
    currency: data.currency ?? "EUR",
    reviewed: Boolean(data.reviewed),
    accountant_reviewed: Boolean(data.accountant_reviewed),
    review_status: data.review_status ?? "estimate",
    source_expense_ids: data.source_expense_ids ?? [],
    components: [],
    created_by_admin_id: "mock-admin",
    updated_by_admin_id: "mock-admin",
    created_at: now,
    updated_at: now,
  };
  mockProductCosts.unshift(cost);
  mockLedgerRows.product_costs = mockProductCosts as unknown as Record<
    string,
    unknown
  >[];
  return cloneMock(cost);
}

export async function updateProductCost(
  costVersionId: string,
  data: ProductCostVersionRequest,
): Promise<ProductCostVersionResponse> {
  await delay();
  const index = mockProductCosts.findIndex((cost) => cost.id === costVersionId);
  if (index < 0)
    mockError("PRODUCT_COST_NOT_FOUND", "Product cost version not found");
  const previous = mockProductCosts[index]!;
  const next: ProductCostVersionResponse = {
    ...previous,
    ...data,
    estimated_unit_cost_cents:
      data.estimated_unit_cost_cents ?? previous.estimated_unit_cost_cents,
    costing_basis: data.costing_basis ?? previous.costing_basis,
    material_cost_cents:
      data.material_cost_cents ?? previous.material_cost_cents,
    packaging_cost_cents:
      data.packaging_cost_cents ?? previous.packaging_cost_cents,
    labor_cost_cents: data.labor_cost_cents ?? previous.labor_cost_cents,
    overhead_cost_cents:
      data.overhead_cost_cents ?? previous.overhead_cost_cents,
    currency: data.currency ?? previous.currency,
    reviewed: data.reviewed ?? previous.reviewed,
    accountant_reviewed:
      data.accountant_reviewed ?? previous.accountant_reviewed,
    review_status: data.review_status ?? previous.review_status,
    source_expense_ids: data.source_expense_ids ?? previous.source_expense_ids,
    components: previous.components,
    updated_by_admin_id: "mock-admin",
    updated_at: new Date().toISOString(),
  };
  mockProductCosts[index] = next;
  mockLedgerRows.product_costs = mockProductCosts as unknown as Record<
    string,
    unknown
  >[];
  return cloneMock(next);
}

export async function getMissingProductCosts(
  periodId: string,
): Promise<MissingProductCostDiagnosticsResponse> {
  await delay();
  findMockPeriod(periodId);
  return {
    items: [
      {
        order_id: "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e",
        order_number: "AM-COD01",
        order_date: "2026-08-01",
        product_id: "citrus-garden-200ml",
        product_name: "Citrus Garden",
      },
    ],
    total: 1,
  };
}

export async function listAccountingExports(
  periodId?: string,
): Promise<FinanceExportPackageListResponse> {
  await delay();
  const items = periodId
    ? mockAccountingExports.filter((item) => item.period_id === periodId)
    : mockAccountingExports;
  return { items: cloneMock(items), total: items.length };
}

export async function generateAccountingExport(
  periodId: string,
): Promise<FinanceExportPackageResponse> {
  await delay();
  const period = findMockPeriod(periodId);
  if (
    period.status !== "closed" &&
    period.status !== "exported" &&
    period.status !== "accepted"
  ) {
    mockError(
      "FINANCE_PERIOD_NOT_CLOSED",
      "Period must be closed before final export",
    );
  }
  const version =
    mockAccountingExports.filter((item) => item.period_id === periodId).length +
    1;
  const exportPackage: FinanceExportPackageResponse = {
    id: `export-${periodId}-v${version}`,
    period_id: periodId,
    version,
    schema_version: "accounting-finance-hub.v1",
    xlsx_path: `private-exports/accounting/${periodId}/v${version}/accounting.xlsx`,
    csv_dir_path: `private-exports/accounting/${periodId}/v${version}/csv`,
    manifest_path: `private-exports/accounting/${periodId}/v${version}/manifest.json`,
    manifest: {
      row_counts: { sales: 2, expenses: mockExpenseEvidence.length },
      totals: period.summary_totals,
    },
    generated_by_admin_id: "mock-admin",
    generated_at: new Date().toISOString(),
    accepted_by_admin_id: null,
    accepted_at: null,
    accountant_name: null,
    accountant_reference: null,
    acceptance_note: null,
    current_final: true,
  };
  mockAccountingExports.forEach((item) => {
    if (item.period_id === periodId) item.current_final = false;
  });
  mockAccountingExports.unshift(exportPackage);
  period.status = "exported";
  return cloneMock(exportPackage);
}

export async function acceptAccountingExport(
  exportId: string,
  data: AccountantAcceptanceRequest,
): Promise<FinanceExportPackageResponse> {
  await delay();
  const exportPackage = mockAccountingExports.find(
    (item) => item.id === exportId,
  );
  if (!exportPackage)
    mockError("EXPORT_PACKAGE_NOT_FOUND", "Export package not found");
  exportPackage.accountant_name = data.accountant_name ?? null;
  exportPackage.accountant_reference = data.accountant_reference ?? null;
  exportPackage.acceptance_note = data.note ?? null;
  exportPackage.accepted_by_admin_id = "mock-admin";
  exportPackage.accepted_at = new Date().toISOString();
  const period = mockFinancePeriods.find(
    (item) => item.id === exportPackage.period_id,
  );
  if (period && exportPackage.current_final) {
    period.status = "accepted";
    period.accepted_at = exportPackage.accepted_at;
  }
  return cloneMock(exportPackage);
}

export async function getStripePayoutImportStatus(): Promise<StripePayoutImportStatusResponse> {
  await delay();
  return {
    total_rows: 3,
    matched: 1,
    unmatched: 1,
    mismatched: 1,
    duplicate: 0,
    ignored: 0,
    latest_imported_at: MOCK_NOW,
  };
}

export async function syncStripeBalanceTransactions(
  limit = 100,
): Promise<StripeBalanceImportResponse> {
  await delay();
  void limit;
  return {
    imported: 0,
    updated: 1,
    duplicate_provider_ids: 0,
    matched: 1,
    unmatched: 1,
    mismatched: 1,
    ignored: 0,
    errors: [],
  };
}

export async function importStripeBalanceCsv(
  file: File,
): Promise<StripeBalanceImportResponse> {
  await delay();
  void file;
  return {
    imported: 2,
    updated: 0,
    duplicate_provider_ids: 0,
    matched: 1,
    unmatched: 1,
    mismatched: 0,
    ignored: 0,
    errors: [],
  };
}

export async function applyManualPaymentAction(
  orderId: string,
  action: ManualPaymentAction,
  note: string,
  callbackOutcome?: CallbackOutcome | null,
): Promise<OrderResponse> {
  await delay();
  if (!note.trim()) mockError("NOTE_REQUIRED", "A note is required");
  const allOrders = [...MOCK_ORDERS_SEEDED, ...mockOrders];
  const order = allOrders.find((o) => o.id === orderId);
  if (!order) mockError("NOT_FOUND", `Order ${orderId} not found`);

  if (action === "mark_paid" || action === "mark_collected") {
    order.payment_status = "paid";
  } else if (action === "mark_refunded") {
    order.payment_status = "refunded";
  } else if (action === "mark_failed") {
    order.payment_status = "failed";
  } else if (action === "mark_review") {
    order.payment_status = "review_required";
  } else if (action === "record_callback") {
    if (!callbackOutcome)
      mockError("CALLBACK_OUTCOME_REQUIRED", "Callback outcome is required");
    order.payment_status = "review_required";
  } else if (action === "convert_to_cod") {
    order.payment_method = "cod";
    order.payment_status = "cod_pending";
  } else if (action === "cancel") {
    order.status = "cancelled";
    if (
      order.payment_status !== "paid" &&
      order.payment_status !== "refunded"
    ) {
      order.payment_status = "failed";
    }
  }
  order.updated_at = new Date().toISOString();
  return { ...order };
}

export async function createReturnCase(
  orderId: string,
  data: CreateReturnCaseRequest,
): Promise<ReturnCaseResponse> {
  await delay();
  const order = findMockOrder(orderId);
  const now = mockNow();
  const returnCase: ReturnCaseResponse = {
    id: mockUuid("return"),
    order_id: orderId,
    reason: data.reason,
    source: data.source ?? "admin",
    status: data.status ?? "requested",
    refund_amount_cents: data.refund_amount_cents ?? null,
    courier_return_fee_cents: data.courier_return_fee_cents ?? 0,
    courier_claim_id: data.courier_claim_id ?? null,
    courier_claim_status: data.courier_claim_status ?? "none",
    courier_claim_amount_cents: data.courier_claim_amount_cents ?? null,
    restock_decision: "pending",
    returned_at: data.status === "return_in_transit" ? now : null,
    received_at: null,
    inspected_at: null,
    closed_at: null,
    notes: data.notes ?? null,
    created_by_admin_id: null,
    updated_by_admin_id: null,
    created_at: now,
    updated_at: now,
  };
  if (
    data.status === "return_in_transit" &&
    ["shipped", "delivered"].includes(order.status)
  ) {
    order.status = "return_in_transit";
  }
  order.updated_at = now;
  mockReturnCases.push(returnCase);
  return returnCase;
}

export async function receiveReturnCase(
  orderId: string,
  returnId: string,
): Promise<ReturnCaseResponse> {
  await delay();
  const order = findMockOrder(orderId);
  const returnCase = mockReturnCases.find(
    (item) => item.id === returnId && item.order_id === orderId,
  );
  if (!returnCase)
    mockError("RETURN_CASE_NOT_FOUND", `Return ${returnId} not found`);
  const now = mockNow();
  returnCase.status = "received";
  returnCase.received_at = returnCase.received_at ?? now;
  returnCase.updated_at = now;
  if (order.status === "return_in_transit") order.status = "returned";
  order.updated_at = now;
  return { ...returnCase };
}

export async function inspectReturnCase(
  orderId: string,
  returnId: string,
  data: InspectReturnCaseRequest,
): Promise<ReturnCaseResponse> {
  await delay();
  findMockOrder(orderId);
  const returnCase = mockReturnCases.find(
    (item) => item.id === returnId && item.order_id === orderId,
  );
  if (!returnCase)
    mockError("RETURN_CASE_NOT_FOUND", `Return ${returnId} not found`);
  const now = mockNow();
  returnCase.status = "inspected";
  returnCase.restock_decision = data.restock_decision;
  returnCase.inspected_at = returnCase.inspected_at ?? now;
  returnCase.notes = data.notes ?? returnCase.notes;
  returnCase.updated_at = now;
  return { ...returnCase };
}

export async function closeReturnCase(
  orderId: string,
  returnId: string,
): Promise<ReturnCaseResponse> {
  await delay();
  findMockOrder(orderId);
  const returnCase = mockReturnCases.find(
    (item) => item.id === returnId && item.order_id === orderId,
  );
  if (!returnCase)
    mockError("RETURN_CASE_NOT_FOUND", `Return ${returnId} not found`);
  const now = mockNow();
  returnCase.status = "closed";
  returnCase.closed_at = returnCase.closed_at ?? now;
  returnCase.updated_at = now;
  return { ...returnCase };
}

export async function updateReturnAccounting(
  orderId: string,
  returnId: string,
  data: UpdateReturnAccountingRequest,
): Promise<ReturnCaseResponse> {
  await delay();
  findMockOrder(orderId);
  const returnCase = mockReturnCases.find(
    (item) => item.id === returnId && item.order_id === orderId,
  );
  if (!returnCase)
    mockError("RETURN_CASE_NOT_FOUND", `Return ${returnId} not found`);
  const now = mockNow();
  if (data.courier_return_fee_cents != null) {
    returnCase.courier_return_fee_cents = data.courier_return_fee_cents;
  }
  if (data.courier_claim_id !== undefined)
    returnCase.courier_claim_id = data.courier_claim_id;
  if (data.courier_claim_status)
    returnCase.courier_claim_status = data.courier_claim_status;
  if (data.courier_claim_amount_cents !== undefined) {
    returnCase.courier_claim_amount_cents = data.courier_claim_amount_cents;
  }
  if (data.notes !== undefined) returnCase.notes = data.notes;
  returnCase.updated_at = now;
  return { ...returnCase };
}

export async function createStripeRefund(
  orderId: string,
  data: CreateStripeRefundRequest,
): Promise<PaymentRefundResponse> {
  await delay();
  const order = findMockOrder(orderId);
  const existing = mockRefundRecords.find(
    (refund) =>
      refund.provider === "stripe" &&
      refund.idempotency_key === data.idempotency_key,
  );
  if (existing) return { ...existing };
  const alreadyPending = mockRefundRecords
    .filter(
      (refund) =>
        refund.order_id === orderId &&
        ["pending", "succeeded"].includes(refund.status),
    )
    .reduce((total, refund) => total + refund.amount_cents, 0);
  const amount =
    data.amount_cents ?? Math.max(0, order.total_cents - alreadyPending);
  const now = mockNow();
  const refund: PaymentRefundResponse = {
    id: mockUuid("refund"),
    order_id: orderId,
    payment_id: null,
    provider: "stripe",
    provider_refund_id: null,
    amount_cents: amount,
    status: "pending",
    reason: data.reason ?? null,
    idempotency_key: data.idempotency_key,
    failure_reason: null,
    created_by_admin_id: null,
    created_at: now,
    confirmed_at: null,
  };
  mockRefundRecords.push(refund);
  order.payment_status = "refund_pending";
  order.updated_at = now;
  return { ...refund };
}

export async function recordCodSettlement(
  orderId: string,
  data: RecordCodSettlementRequest,
): Promise<CodSettlementResponse> {
  await delay();
  const order = findMockOrder(orderId);
  const now = mockNow();
  const existingIndex = mockCodSettlements.findIndex(
    (settlement) => settlement.order_id === orderId,
  );
  const settlement: CodSettlementResponse = {
    id:
      existingIndex >= 0
        ? mockCodSettlements[existingIndex]!.id
        : mockUuid("cod"),
    order_id: orderId,
    amount_cents: data.amount_cents,
    settlement_date: data.settlement_date,
    courier_reference: data.courier_reference ?? null,
    notes: data.notes ?? null,
    mismatch_review: data.amount_cents !== order.total_cents,
    created_by_admin_id: null,
    created_at:
      existingIndex >= 0 ? mockCodSettlements[existingIndex]!.created_at : now,
    updated_at: now,
  };
  if (existingIndex >= 0) mockCodSettlements[existingIndex] = settlement;
  else mockCodSettlements.push(settlement);
  return { ...settlement };
}

export async function updateOrderStatus(
  orderId: string,
  status: OrderStatus,
  tracking?: {
    tracking_number?: string;
    tracking_carrier?: string;
    tracking_url?: string;
  },
): Promise<OrderResponse> {
  await delay();
  const allOrders = [...MOCK_ORDERS_SEEDED, ...mockOrders];
  const order = allOrders.find((o) => o.id === orderId);
  if (!order) mockError("NOT_FOUND", `Order ${orderId} not found`);

  const validTransitions: Record<OrderStatus, OrderStatus[]> = {
    pending: ["confirmed", "cancelled"],
    confirmed: ["shipped", "cancelled"],
    shipped: ["delivered", "return_in_transit"],
    delivered: ["return_in_transit"],
    return_in_transit: ["returned"],
    returned: [],
    cancelled: [],
  };

  if (!validTransitions[order.status].includes(status)) {
    mockError(
      "VALIDATION_ERROR",
      `Cannot transition from ${order.status} to ${status}`,
    );
  }

  if (status === "shipped") {
    if (!tracking?.tracking_number && order.delivery_courier === "speedy") {
      order.tracking_number = "63689182611";
      order.tracking_carrier = "speedy";
      order.tracking_url = buildTrackingUrl("speedy", "63689182611");
      order.courier_provider = "speedy";
      order.courier_shipment_number = "63689182611";
      order.courier_sync_status = "waybill_created";
      order.courier_last_synced_at = new Date().toISOString();
      addSpeedyEvent(order.id, "create_waybill", "success", {
        shipment_number: "63689182611",
      });
    } else if (!tracking?.tracking_number || !tracking?.tracking_carrier) {
      mockError(
        "TRACKING_REQUIRED",
        "tracking_number and tracking_carrier are required when shipping",
      );
    } else {
      order.tracking_number = tracking.tracking_number;
      order.tracking_carrier = tracking.tracking_carrier;
      order.tracking_url =
        tracking.tracking_url ??
        buildTrackingUrl(tracking.tracking_carrier, tracking.tracking_number);
    }
  }

  order.status = status;
  order.updated_at = new Date().toISOString();
  return order;
}

// --- Reactions Mock ---

const mockReactions: Map<string, Set<string>> = new Map(); // key: "productId:type", value: set of sessions

export async function toggleReaction(
  productId: string,
  body: ReactionToggleRequest,
): Promise<ReactionToggleResponse> {
  await delay();
  const key = `${productId}:${body.reaction_type}`;
  const sessions = mockReactions.get(key) ?? new Set();
  const mockSessionId = "mock-session";

  let active: boolean;
  if (sessions.has(mockSessionId)) {
    sessions.delete(mockSessionId);
    active = false;
  } else {
    sessions.add(mockSessionId);
    active = true;
  }
  mockReactions.set(key, sessions);

  return { reaction_type: body.reaction_type, active };
}

export async function getReactions(
  productId: string,
): Promise<ReactionCountsResponse> {
  await delay();
  const heartKey = `${productId}:heart`;
  const thumbsKey = `${productId}:thumbs_up`;
  const mockSessionId = "mock-session";

  const heartSessions = mockReactions.get(heartKey) ?? new Set();
  const thumbsSessions = mockReactions.get(thumbsKey) ?? new Set();

  return {
    heart: {
      count: heartSessions.size,
      reacted: heartSessions.has(mockSessionId),
    },
    thumbs_up: {
      count: thumbsSessions.size,
      reacted: thumbsSessions.has(mockSessionId),
    },
  };
}

// --- Comments Mock ---

const mockComments: CommentResponse[] = [
  {
    id: "comment-1",
    display_name: "Marie",
    body: "This candle smells absolutely divine! Perfect for relaxing evenings.",
    created_at: new Date(Date.now() - 86400000).toISOString(),
  },
  {
    id: "comment-2",
    display_name: "Sophie",
    body: "Bought this as a gift and my friend loved it!",
    created_at: new Date(Date.now() - 172800000).toISOString(),
  },
];

export async function postComment(
  productId: string,
  body: CommentCreateRequest,
): Promise<CommentResponse> {
  await delay();
  const product = MOCK_PRODUCTS.find((p) => p.id === productId);
  if (!product) mockError("NOT_FOUND", `Product ${productId} not found`);

  const comment: CommentResponse = {
    id: generateOrderId(),
    display_name: body.display_name ?? "Anonymous",
    body: body.body,
    created_at: new Date().toISOString(),
  };
  mockComments.unshift(comment);
  return comment;
}

export async function getComments(
  _productId: string,
  sort: CommentSort = "newest",
  page: number = 1,
  limit: number = 20,
): Promise<CommentListResponse> {
  await delay();
  const sorted = [...mockComments].sort((a, b) => {
    const cmp = a.created_at.localeCompare(b.created_at);
    return sort === "newest" ? -cmp : cmp;
  });
  const start = (page - 1) * limit;
  const items = sorted.slice(start, start + limit);
  return { items, total: mockComments.length, page, limit };
}

// --- Atelier Story / About Mock ---

export async function getAbout(locale?: string): Promise<AboutPublicResponse> {
  await delay();
  return publicAbout(locale);
}

export async function getAdminAbout(): Promise<AboutAdminResponse> {
  await delay();
  return {
    sections: [...MOCK_ABOUT_SECTIONS].sort(
      (a, b) => a.sort_order - b.sort_order,
    ),
  };
}

export async function updateAboutSection(
  slug: string,
  data: PatchAboutSectionRequest,
): Promise<AboutSectionAdmin> {
  await delay();
  const section = MOCK_ABOUT_SECTIONS.find((s) => s.slug === slug);
  if (!section) mockError("NOT_FOUND", `About section ${slug} not found`);
  Object.assign(section, data, { updated_at: nowIso() });
  return section;
}

export async function createAboutItem(
  slug: string,
  data: CreateAboutItemRequest,
): Promise<AboutItemAdmin> {
  await delay();
  const section = MOCK_ABOUT_SECTIONS.find((s) => s.slug === slug);
  if (!section) mockError("NOT_FOUND", `About section ${slug} not found`);
  const item = mockAboutItem(
    nextAboutItemId++,
    slug,
    section.items.length,
    data.title_en,
    data.title_bg ?? null,
    data.text_en ?? null,
    data.text_bg ?? null,
    data.link_href ?? null,
  );
  item.is_published = data.is_published ?? true;
  section.items.push(item);
  return item;
}

export async function updateAboutItem(
  slug: string,
  itemId: number,
  data: PatchAboutItemRequest,
): Promise<AboutItemAdmin> {
  await delay();
  const item = findAboutItem(slug, itemId);
  Object.assign(item, data, { updated_at: nowIso() });
  return item;
}

export async function deleteAboutItem(
  slug: string,
  itemId: number,
): Promise<void> {
  await delay();
  const section = MOCK_ABOUT_SECTIONS.find((s) => s.slug === slug);
  if (!section) mockError("NOT_FOUND", `About section ${slug} not found`);
  section.items = section.items.filter((item) => item.id !== itemId);
}

export async function reorderAboutSections(
  slugs: string[],
): Promise<AboutSectionAdmin[]> {
  await delay();
  if (new Set(slugs).size !== MOCK_ABOUT_SECTIONS.length) {
    mockError("INVALID_ORDER", "slugs must match all about sections");
  }
  slugs.forEach((slug, index) => {
    const section = MOCK_ABOUT_SECTIONS.find((s) => s.slug === slug);
    if (!section)
      mockError("INVALID_ORDER", "slugs must match all about sections");
    section.sort_order = index;
  });
  return (await getAdminAbout()).sections;
}

export async function reorderAboutItems(
  slug: string,
  ids: number[],
): Promise<AboutItemAdmin[]> {
  await delay();
  const section = MOCK_ABOUT_SECTIONS.find((s) => s.slug === slug);
  if (!section) mockError("NOT_FOUND", `About section ${slug} not found`);
  if (new Set(ids).size !== section.items.length) {
    mockError("INVALID_ORDER", "ids must match all section items");
  }
  ids.forEach((id, index) => {
    const item = section.items.find((i) => i.id === id);
    if (!item) mockError("INVALID_ORDER", "ids must match all section items");
    item.sort_order = index;
  });
  return [...section.items].sort((a, b) => a.sort_order - b.sort_order);
}

export async function setAboutSectionPublished(
  slug: string,
  isPublished: boolean,
): Promise<AboutSectionAdmin> {
  await delay();
  const section = MOCK_ABOUT_SECTIONS.find((s) => s.slug === slug);
  if (!section) mockError("NOT_FOUND", `About section ${slug} not found`);
  section.is_published = isPublished;
  section.updated_at = nowIso();
  return section;
}

export async function setAboutItemPublished(
  slug: string,
  itemId: number,
  isPublished: boolean,
): Promise<AboutItemAdmin> {
  await delay();
  const item = findAboutItem(slug, itemId);
  item.is_published = isPublished;
  item.updated_at = nowIso();
  return item;
}

export async function uploadAboutSectionImage(
  slug: string,
  _file: File,
): Promise<AboutSectionAdmin> {
  await delay();
  const section = MOCK_ABOUT_SECTIONS.find((s) => s.slug === slug);
  if (!section) mockError("NOT_FOUND", `About section ${slug} not found`);
  section.image_id = `mock-${Date.now()}`;
  section.image = `/static/products/about-${slug.replace("_", "-")}_${section.image_id}.webp`;
  return section;
}

export async function clearAboutSectionImage(
  slug: string,
): Promise<AboutSectionAdmin> {
  await delay();
  const section = MOCK_ABOUT_SECTIONS.find((s) => s.slug === slug);
  if (!section) mockError("NOT_FOUND", `About section ${slug} not found`);
  section.image_id = null;
  section.image = null;
  return section;
}

export async function uploadAboutItemImage(
  slug: string,
  itemId: number,
  _file: File,
): Promise<AboutItemAdmin> {
  await delay();
  const item = findAboutItem(slug, itemId);
  item.image_id = `mock-${Date.now()}`;
  item.image = `/static/products/about-item-${itemId}_${item.image_id}.webp`;
  return item;
}

export async function clearAboutItemImage(
  slug: string,
  itemId: number,
): Promise<AboutItemAdmin> {
  await delay();
  const item = findAboutItem(slug, itemId);
  item.image_id = null;
  item.image = null;
  return item;
}

function findAboutItem(slug: string, itemId: number): AboutItemAdmin {
  const section = MOCK_ABOUT_SECTIONS.find((s) => s.slug === slug);
  if (!section) mockError("NOT_FOUND", `About section ${slug} not found`);
  const item = section.items.find((i) => i.id === itemId);
  if (!item) mockError("NOT_FOUND", `About item ${itemId} not found`);
  return item;
}

// --- Taxonomy Mock ---

function localizedName(term: MockTerm, locale?: string): string {
  return locale === "bg" ? (term.name_bg ?? term.name_en) : term.name_en;
}

export async function getTaxonomy(locale?: string): Promise<TaxonomyResponse> {
  await delay();
  const active = (kind: TaxonomyKind) =>
    MOCK_TAXONOMY[kind]
      .filter((t) => t.is_active)
      .sort((a, b) => a.sort_order - b.sort_order)
      .map((t) => ({
        slug: t.slug,
        name: localizedName(t, locale),
        sort_order: t.sort_order,
      }));
  return {
    product_types: active("product-types"),
    categories: active("categories"),
    labels: active("labels"),
  };
}

// --- FAQ Mock ---

function localizedFaqValue(
  en: string,
  bg: string | null,
  locale?: string,
): string {
  return locale === "bg" ? (bg ?? en) : en;
}

export async function getFaq(locale?: string): Promise<FaqResponse> {
  await delay();
  return {
    sections: [...mockFaqSections]
      .sort((a, b) => a.sort_order - b.sort_order)
      .map((section) => ({
        slug: section.slug,
        title: localizedFaqValue(section.title_en, section.title_bg, locale),
        icon: section.icon,
        items: section.items
          .filter((item) => item.is_published)
          .sort((a, b) => a.sort_order - b.sort_order)
          .map((item) => ({
            id: item.id,
            question: localizedFaqValue(
              item.question_en,
              item.question_bg,
              locale,
            ),
            answer: localizedFaqValue(item.answer_en, item.answer_bg, locale),
          })),
      })),
  };
}

export async function getAdminFaq(): Promise<FaqAdminResponse> {
  await delay();
  return cloneAdminFaq();
}

export async function createFaqItem(
  data: CreateFaqItemRequest,
): Promise<FaqItemAdminResponse> {
  await delay();
  const section = findFaqSection(data.section);
  if (!section)
    mockError("INVALID_FAQ", `FAQ section not found: ${data.section}`);
  const now = new Date().toISOString();
  const item: FaqItemAdminResponse = {
    id: mockFaqNextId++,
    section: data.section,
    question_en: data.question_en,
    question_bg: data.question_bg ?? null,
    answer_en: data.answer_en,
    answer_bg: data.answer_bg ?? null,
    sort_order: data.sort_order ?? section.items.length,
    is_published: true,
    created_at: now,
    updated_at: now,
  };
  section.items.push(item);
  return { ...item };
}

export async function updateFaqItem(
  itemId: number,
  data: UpdateFaqItemRequest,
): Promise<FaqItemAdminResponse> {
  await delay();
  const item = findFaqItem(itemId);
  if (!item) mockError("NOT_FOUND", `FAQ item ${itemId} not found`);
  if (data.section !== undefined && data.section !== item.section) {
    const nextSection = findFaqSection(data.section);
    const currentSection = findFaqSection(item.section);
    if (!nextSection || !currentSection)
      mockError("INVALID_FAQ", "FAQ section not found");
    currentSection.items = currentSection.items.filter(
      (candidate) => candidate.id !== itemId,
    );
    nextSection.items.push(item);
    item.section = data.section;
  }
  if (data.question_en !== undefined) item.question_en = data.question_en;
  if (data.question_bg !== undefined) item.question_bg = data.question_bg;
  if (data.answer_en !== undefined) item.answer_en = data.answer_en;
  if (data.answer_bg !== undefined) item.answer_bg = data.answer_bg;
  if (data.sort_order !== undefined) item.sort_order = data.sort_order;
  if (data.is_published !== undefined) item.is_published = data.is_published;
  item.updated_at = new Date().toISOString();
  return { ...item };
}

export async function deleteFaqItem(itemId: number): Promise<void> {
  await delay();
  const section = mockFaqSections.find((candidate) =>
    candidate.items.some((item) => item.id === itemId),
  );
  if (!section) mockError("NOT_FOUND", `FAQ item ${itemId} not found`);
  section.items = section.items.filter((item) => item.id !== itemId);
}

export async function reorderFaqItems(
  data: ReorderFaqItemsRequest,
): Promise<FaqAdminResponse> {
  await delay();
  const section = findFaqSection(data.section);
  if (!section)
    mockError("INVALID_FAQ", `FAQ section not found: ${data.section}`);
  const order = new Map(data.ordered_ids.map((id, index) => [id, index]));
  section.items.forEach((item) => {
    const nextOrder = order.get(item.id);
    if (nextOrder !== undefined) item.sort_order = nextOrder;
  });
  section.items.sort((a, b) => a.sort_order - b.sort_order);
  return cloneAdminFaq();
}

export async function updateFaqSection(
  slug: string,
  data: UpdateFaqSectionRequest,
): Promise<FaqSectionAdminResponse> {
  await delay();
  const section = findFaqSection(slug);
  if (!section) mockError("NOT_FOUND", `FAQ section ${slug} not found`);
  if (data.title_en !== undefined) section.title_en = data.title_en;
  if (data.title_bg !== undefined) section.title_bg = data.title_bg;
  if (data.icon !== undefined) section.icon = data.icon;
  if (data.sort_order !== undefined) section.sort_order = data.sort_order;
  section.updated_at = new Date().toISOString();
  return { ...section, items: section.items.map((item) => ({ ...item })) };
}

export async function getTerms(locale?: string): Promise<TermsResponse> {
  await delay();
  return {
    meta_title: localizedTermsValue(
      mockTermsPage.meta_title_en,
      mockTermsPage.meta_title_bg,
      locale,
    ),
    meta_description: localizedTermsValue(
      mockTermsPage.meta_description_en,
      mockTermsPage.meta_description_bg,
      locale,
    ),
    eyebrow: localizedTermsValue(
      mockTermsPage.eyebrow_en,
      mockTermsPage.eyebrow_bg,
      locale,
    ),
    title: localizedTermsValue(
      mockTermsPage.title_en,
      mockTermsPage.title_bg,
      locale,
    ),
    subtitle: localizedTermsValue(
      mockTermsPage.subtitle_en,
      mockTermsPage.subtitle_bg,
      locale,
    ),
    last_updated: localizedTermsValue(
      mockTermsPage.last_updated_en,
      mockTermsPage.last_updated_bg,
      locale,
    ),
    identity_intro: localizedTermsValue(
      mockTermsPage.identity_intro_en,
      mockTermsPage.identity_intro_bg,
      locale,
    ),
    policy_links_title: localizedTermsValue(
      mockTermsPage.policy_links_title_en,
      mockTermsPage.policy_links_title_bg,
      locale,
    ),
    privacy_link: localizedTermsValue(
      mockTermsPage.privacy_link_en,
      mockTermsPage.privacy_link_bg,
      locale,
    ),
    cookies_link: localizedTermsValue(
      mockTermsPage.cookies_link_en,
      mockTermsPage.cookies_link_bg,
      locale,
    ),
    nav_label: localizedTermsValue(
      mockTermsPage.nav_label_en,
      mockTermsPage.nav_label_bg,
      locale,
    ),
    back_to_top: localizedTermsValue(
      mockTermsPage.back_to_top_en,
      mockTermsPage.back_to_top_bg,
      locale,
    ),
    sections: mockTermsSections
      .slice()
      .sort((a, b) => a.sort_order - b.sort_order)
      .map((section) => ({
        id: section.slug,
        title: localizedTermsValue(section.title_en, section.title_bg, locale),
        nav: localizedTermsValue(section.nav_en, section.nav_bg, locale),
        body:
          localizedTermsLines(section.body_en, section.body_bg, locale) ?? [],
        model_form_title:
          localizedTermsValue(
            section.model_form_title_en ?? "",
            section.model_form_title_bg,
            locale,
          ) || null,
        model_form_intro:
          localizedTermsValue(
            section.model_form_intro_en ?? "",
            section.model_form_intro_bg,
            locale,
          ) || null,
        model_form_lines: localizedTermsLines(
          section.model_form_lines_en,
          section.model_form_lines_bg,
          locale,
        ),
      })),
  };
}

export async function getAdminTerms(): Promise<TermsAdminResponse> {
  await delay();
  return cloneAdminTerms();
}

export async function updateTermsPage(
  data: UpdateTermsPageRequest,
): Promise<TermsPageAdminResponse> {
  await delay();
  mockTermsPage = {
    ...mockTermsPage,
    ...data,
    updated_at: new Date().toISOString(),
  };
  return { ...mockTermsPage };
}

export async function updateTermsSection(
  slug: string,
  data: UpdateTermsSectionRequest,
): Promise<TermsSectionAdminResponse> {
  await delay();
  const section = mockTermsSections.find(
    (candidate) => candidate.slug === slug,
  );
  if (!section)
    mockError("terms_section_not_found", `Terms section ${slug} not found`);
  Object.assign(section, data, { updated_at: new Date().toISOString() });
  return {
    ...section,
    body_en: [...section.body_en],
    body_bg: section.body_bg ? [...section.body_bg] : null,
    model_form_lines_en: section.model_form_lines_en
      ? [...section.model_form_lines_en]
      : null,
    model_form_lines_bg: section.model_form_lines_bg
      ? [...section.model_form_lines_bg]
      : null,
  };
}

export async function getPrivacy(locale?: string): Promise<PrivacyResponse> {
  await delay();
  return {
    meta_title: localizedTermsValue(
      mockPrivacyPage.meta_title_en,
      mockPrivacyPage.meta_title_bg,
      locale,
    ),
    meta_description: localizedTermsValue(
      mockPrivacyPage.meta_description_en,
      mockPrivacyPage.meta_description_bg,
      locale,
    ),
    eyebrow: localizedTermsValue(
      mockPrivacyPage.eyebrow_en,
      mockPrivacyPage.eyebrow_bg,
      locale,
    ),
    title: localizedTermsValue(
      mockPrivacyPage.title_en,
      mockPrivacyPage.title_bg,
      locale,
    ),
    subtitle: localizedTermsValue(
      mockPrivacyPage.subtitle_en,
      mockPrivacyPage.subtitle_bg,
      locale,
    ),
    last_updated: localizedTermsValue(
      mockPrivacyPage.last_updated_en,
      mockPrivacyPage.last_updated_bg,
      locale,
    ),
    controller_title: localizedTermsValue(
      mockPrivacyPage.controller_title_en,
      mockPrivacyPage.controller_title_bg,
      locale,
    ),
    sections: mockPrivacySections
      .slice()
      .sort((a, b) => a.sort_order - b.sort_order)
      .map((section) => ({
        id: section.slug,
        title: localizedTermsValue(section.title_en, section.title_bg, locale),
        nav: localizedTermsValue(section.nav_en, section.nav_bg, locale),
        body:
          localizedTermsLines(section.body_en, section.body_bg, locale) ?? [],
      })),
  };
}

export async function getAdminPrivacy(): Promise<PrivacyAdminResponse> {
  await delay();
  return cloneAdminPrivacy();
}

export async function updatePrivacyPage(
  data: UpdatePrivacyPageRequest,
): Promise<PrivacyPageAdminResponse> {
  await delay();
  mockPrivacyPage = {
    ...mockPrivacyPage,
    ...data,
    updated_at: new Date().toISOString(),
  };
  return { ...mockPrivacyPage };
}

export async function updatePrivacySection(
  slug: string,
  data: UpdatePrivacySectionRequest,
): Promise<PrivacySectionAdminResponse> {
  await delay();
  const section = mockPrivacySections.find(
    (candidate) => candidate.slug === slug,
  );
  if (!section)
    mockError("privacy_section_not_found", `Privacy section ${slug} not found`);
  Object.assign(section, data, { updated_at: new Date().toISOString() });
  return {
    ...section,
    body_en: [...section.body_en],
    body_bg: section.body_bg ? [...section.body_bg] : null,
  };
}

export async function getCookies(locale?: string): Promise<CookiesResponse> {
  await delay();
  return {
    meta_title: localizedTermsValue(
      mockCookiesPage.meta_title_en,
      mockCookiesPage.meta_title_bg,
      locale,
    ),
    meta_description: localizedTermsValue(
      mockCookiesPage.meta_description_en,
      mockCookiesPage.meta_description_bg,
      locale,
    ),
    eyebrow: localizedTermsValue(
      mockCookiesPage.eyebrow_en,
      mockCookiesPage.eyebrow_bg,
      locale,
    ),
    title: localizedTermsValue(
      mockCookiesPage.title_en,
      mockCookiesPage.title_bg,
      locale,
    ),
    subtitle: localizedTermsValue(
      mockCookiesPage.subtitle_en,
      mockCookiesPage.subtitle_bg,
      locale,
    ),
    last_updated: localizedTermsValue(
      mockCookiesPage.last_updated_en,
      mockCookiesPage.last_updated_bg,
      locale,
    ),
    inventory_title: localizedTermsValue(
      mockCookiesPage.inventory_title_en,
      mockCookiesPage.inventory_title_bg,
      locale,
    ),
    headers: {
      name: localizedTermsValue(
        mockCookiesPage.header_name_en,
        mockCookiesPage.header_name_bg,
        locale,
      ),
      purpose: localizedTermsValue(
        mockCookiesPage.header_purpose_en,
        mockCookiesPage.header_purpose_bg,
        locale,
      ),
      type: localizedTermsValue(
        mockCookiesPage.header_type_en,
        mockCookiesPage.header_type_bg,
        locale,
      ),
      duration: localizedTermsValue(
        mockCookiesPage.header_duration_en,
        mockCookiesPage.header_duration_bg,
        locale,
      ),
    },
    cookies: mockCookieInventory
      .slice()
      .sort((a, b) => a.sort_order - b.sort_order)
      .map((item) => ({
        name: item.name,
        purpose: localizedTermsValue(item.purpose_en, item.purpose_bg, locale),
        type: localizedTermsValue(item.type_en, item.type_bg, locale),
        duration: localizedTermsValue(
          item.duration_en,
          item.duration_bg,
          locale,
        ),
      })),
    sections: mockCookieSections
      .slice()
      .sort((a, b) => a.sort_order - b.sort_order)
      .map((section) => ({
        id: section.slug,
        title: localizedTermsValue(section.title_en, section.title_bg, locale),
        body:
          localizedTermsLines(section.body_en, section.body_bg, locale) ?? [],
      })),
  };
}

export async function getAdminCookies(): Promise<CookiesAdminResponse> {
  await delay();
  return cloneAdminCookies();
}

export async function updateCookiesPage(
  data: UpdateCookiesPageRequest,
): Promise<CookiesPageAdminResponse> {
  await delay();
  mockCookiesPage = {
    ...mockCookiesPage,
    ...data,
    updated_at: new Date().toISOString(),
  };
  return { ...mockCookiesPage };
}

export async function updateCookieInventory(
  name: string,
  data: UpdateCookieInventoryRequest,
): Promise<CookieInventoryAdminResponse> {
  await delay();
  const item = mockCookieInventory.find((candidate) => candidate.name === name);
  if (!item)
    mockError("cookie_inventory_not_found", `Cookie ${name} not found`);
  Object.assign(item, data, { updated_at: new Date().toISOString() });
  return { ...item, observed_on: [...item.observed_on] };
}

export async function updateCookieSection(
  slug: string,
  data: UpdateCookieSectionRequest,
): Promise<CookieSectionAdminResponse> {
  await delay();
  const section = mockCookieSections.find(
    (candidate) => candidate.slug === slug,
  );
  if (!section)
    mockError("cookie_section_not_found", `Cookie section ${slug} not found`);
  Object.assign(section, data, { updated_at: new Date().toISOString() });
  return {
    ...section,
    body_en: [...section.body_en],
    body_bg: section.body_bg ? [...section.body_bg] : null,
  };
}

function termProductCount(kind: TaxonomyKind, slug: string): number {
  if (kind === "product-types") {
    return MOCK_PRODUCTS.filter((p) => p.product_type === slug).length;
  }
  if (kind === "categories") {
    return MOCK_PRODUCTS.filter((p) => p.category === slug).length;
  }
  return MOCK_PRODUCTS.filter((p) => p.labels.some((l) => l.slug === slug))
    .length;
}

function toAdminTerm(kind: TaxonomyKind, term: MockTerm): AdminTaxonomyTerm {
  return {
    slug: term.slug,
    name_en: term.name_en,
    name_bg: term.name_bg,
    sort_order: term.sort_order,
    is_active: term.is_active,
    product_count: termProductCount(kind, term.slug),
    created_at: term.created_at,
    updated_at: term.updated_at,
  };
}

export async function getAdminTaxonomy(
  kind: TaxonomyKind,
): Promise<AdminTaxonomyTerm[]> {
  await delay();
  return [...MOCK_TAXONOMY[kind]]
    .sort((a, b) => a.sort_order - b.sort_order)
    .map((t) => toAdminTerm(kind, t));
}

function mockSlugify(value: string): string {
  return (
    value
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "item"
  );
}

export async function createTaxonomyTerm(
  kind: TaxonomyKind,
  data: CreateTaxonomyTermRequest,
): Promise<AdminTaxonomyTerm> {
  await delay();
  const existing = new Set(MOCK_TAXONOMY[kind].map((t) => t.slug));
  let slug = mockSlugify(data.name_en);
  let n = 2;
  while (existing.has(slug)) slug = `${mockSlugify(data.name_en)}-${n++}`;
  const now = new Date().toISOString();
  const term: MockTerm = {
    slug,
    name_en: data.name_en,
    name_bg: data.name_bg ?? null,
    sort_order: data.sort_order ?? 0,
    is_active: true,
    created_at: now,
    updated_at: now,
  };
  MOCK_TAXONOMY[kind].push(term);
  return toAdminTerm(kind, term);
}

export async function updateTaxonomyTerm(
  kind: TaxonomyKind,
  slug: string,
  data: UpdateTaxonomyTermRequest,
): Promise<AdminTaxonomyTerm> {
  await delay();
  const term = MOCK_TAXONOMY[kind].find((t) => t.slug === slug);
  if (!term) mockError("NOT_FOUND", `${kind} ${slug} not found`);
  if (data.name_en !== undefined) term.name_en = data.name_en;
  if (data.name_bg !== undefined) term.name_bg = data.name_bg;
  if (data.sort_order !== undefined) term.sort_order = data.sort_order;
  if (data.is_active !== undefined) term.is_active = data.is_active;
  term.updated_at = new Date().toISOString();
  return toAdminTerm(kind, term);
}

export async function deleteTaxonomyTerm(
  kind: TaxonomyKind,
  slug: string,
): Promise<void> {
  await delay();
  const term = MOCK_TAXONOMY[kind].find((t) => t.slug === slug);
  if (!term) mockError("NOT_FOUND", `${kind} ${slug} not found`);
  if (termProductCount(kind, slug) > 0) {
    mockError(
      "TAXONOMY_IN_USE",
      `${kind} '${slug}' is in use; reassign or deactivate it first`,
    );
  }
  MOCK_TAXONOMY[kind] = MOCK_TAXONOMY[kind].filter((t) => t.slug !== slug);
}

// --- Promotions (campaigns, bulk discount, managed banner) ---

interface AppliedTarget {
  id: string;
  percent: number | null;
  starts_at: string | null;
  ends_at: string | null;
}

const mockCampaigns: CampaignResponse[] = [];
const mockAppliedTargets: Map<string, AppliedTarget[]> = new Map();

let mockBanner: BannerAdminResponse = {
  message_en: "Free shipping on orders over €50 ✨",
  message_bg: "Безплатна доставка за поръчки над 50€ ✨",
  link_label_en: null,
  link_label_bg: null,
  link_url: null,
  is_enabled: true,
  starts_at: null,
  ends_at: null,
  version: 1,
  updated_at: new Date().toISOString(),
};

const MOCK_SITE_MEDIA_BASE: SiteMediaAssetAdmin[] = [
  {
    key: "home_hero",
    label: "Homepage hero image",
    description:
      "Optional direct hero photo. When empty, the homepage keeps using the featured product image.",
    default_url: null,
    image_id: null,
    image_url: null,
    thumbnail_url: null,
    zoom_url: null,
    effective_url: null,
    updated_at: new Date().toISOString(),
  },
  {
    key: "home_hero_fallback",
    label: "Homepage hero fallback",
    description: "Used only when there is no direct hero image and no usable product image.",
    default_url: "/rebrand/error-candle.webp",
    image_id: null,
    image_url: null,
    thumbnail_url: null,
    zoom_url: null,
    effective_url: "/rebrand/error-candle.webp",
    updated_at: new Date().toISOString(),
  },
  ...(
    [
      ["atelier_hero_fallback", "Atelier hero fallback"],
      ["atelier_story_fallback", "Atelier story fallback"],
      ["atelier_atelier_fallback", "Inside atelier fallback"],
      ["atelier_collections_fallback", "Atelier collections fallback"],
      ["atelier_process_fallback", "Atelier process fallback"],
      ["error_page_image", "Error page image"],
    ] as const
  ).map(([key, label]) => ({
    key,
    label,
    description: "Reusable storefront image slot.",
    default_url: "/rebrand/error-candle.webp",
    image_id: null,
    image_url: null,
    thumbnail_url: null,
    zoom_url: null,
    effective_url: "/rebrand/error-candle.webp",
    updated_at: new Date().toISOString(),
  })),
  {
    key: "page_background",
    label: "Page background texture",
    description: "Subtle background image layered behind storefront pages.",
    default_url: "/rebrand/watercolor-page-bg.webp",
    image_id: null,
    image_url: null,
    thumbnail_url: null,
    zoom_url: null,
    effective_url: "/rebrand/watercolor-page-bg.webp",
    updated_at: new Date().toISOString(),
  },
];

let mockSiteMediaAssets: SiteMediaAssetAdmin[] = MOCK_SITE_MEDIA_BASE.map((asset) => ({
  ...asset,
}));

function effectiveMockSiteMedia(asset: SiteMediaAssetAdmin): SiteMediaAssetAdmin {
  return { ...asset, effective_url: asset.image_url ?? asset.default_url };
}

function findMockSiteMedia(key: string): SiteMediaAssetAdmin {
  const asset = mockSiteMediaAssets.find((item) => item.key === key);
  if (!asset) mockError("site_media_not_found", "Site media asset not found");
  return asset;
}

function deriveCampaignStatus(c: CampaignResponse): CampaignResponse["status"] {
  if (c.removed_at) return "removed";
  if (!c.applied_at) return "draft";
  const now = new Date().toISOString();
  if (c.discount_starts_at && now < c.discount_starts_at) return "scheduled";
  if (c.discount_ends_at && now > c.discount_ends_at) return "ended";
  return "active";
}

function resolveMockTargets(
  productIds: string[] | null | undefined,
  filter: BulkDiscountRequest["filter"],
): string[] {
  if (productIds) return Array.from(new Set(productIds));
  if (!filter) return [];
  return MOCK_PRODUCTS.filter((p) => {
    if (filter.q) {
      const q = filter.q.toLowerCase();
      if (!p.name.toLowerCase().includes(q) && !p.id.toLowerCase().includes(q))
        return false;
    }
    if (filter.category && p.category !== filter.category) return false;
    if (filter.is_active != null && p.is_active !== filter.is_active)
      return false;
    if (filter.in_stock && p.stock <= 0) return false;
    return true;
  }).map((p) => p.id);
}

function runMockBulk(
  operation: "apply" | "remove",
  ids: string[],
  percent: number | null,
  startsAt: string | null,
  endsAt: string | null,
): BulkDiscountResponse {
  const results: BulkResultItem[] = [];
  let success = 0;
  for (const id of ids) {
    const product = MOCK_PRODUCTS.find((p) => p.id === id);
    if (!product) {
      results.push({ id, status: "failed", error: `Product not found: ${id}` });
      continue;
    }
    if (operation === "apply") {
      product.discount_percent = percent;
      product.discount_starts_at = startsAt;
      product.discount_ends_at = endsAt;
    } else {
      product.discount_percent = null;
      product.discount_starts_at = null;
      product.discount_ends_at = null;
    }
    results.push({ id, status: "updated" });
    success += 1;
  }
  return {
    success_count: success,
    failure_count: results.length - success,
    results,
  };
}

export async function getCampaigns(): Promise<CampaignListResponse> {
  await delay();
  const items = mockCampaigns.map((c) => ({
    ...c,
    status: deriveCampaignStatus(c),
  }));
  return { items, total: items.length };
}

export async function getCampaign(
  campaignId: string,
): Promise<CampaignResponse> {
  await delay();
  const c = mockCampaigns.find((x) => x.id === campaignId);
  if (!c) mockError("NOT_FOUND", "Campaign not found");
  return { ...c, status: deriveCampaignStatus(c) };
}

export async function createCampaign(
  data: CampaignCreateRequest,
): Promise<CampaignResponse> {
  await delay();
  const now = new Date().toISOString();
  const targetType = data.product_ids ? "ids" : "filter";
  const targetCount = data.product_ids
    ? Array.from(new Set(data.product_ids)).length
    : resolveMockTargets(null, data.filter).length;
  const campaign: CampaignResponse = {
    id: `campaign-${Math.round(Math.random() * 1e9)}`,
    name: data.name,
    note: data.note ?? null,
    discount_percent: data.discount_percent,
    discount_starts_at: data.discount_starts_at ?? null,
    discount_ends_at: data.discount_ends_at ?? null,
    target_type: targetType,
    target_count: targetCount,
    target_ids: data.product_ids ? Array.from(new Set(data.product_ids)) : null,
    target_filter: data.product_ids ? null : (data.filter ?? {}),
    status: "draft",
    applied_at: null,
    removed_at: null,
    created_at: now,
    updated_at: now,
    last_result: null,
  };
  // Store the raw target for later apply resolution.
  mockAppliedTargets.set(`${campaign.id}:targets`, [
    ...(data.product_ids ?? resolveMockTargets(null, data.filter)).map(
      (id) => ({
        id,
        percent: null,
        starts_at: null,
        ends_at: null,
      }),
    ),
  ]);
  mockCampaigns.unshift(campaign);
  return campaign;
}

export async function updateCampaign(
  campaignId: string,
  data: CampaignUpdateRequest,
): Promise<CampaignResponse> {
  await delay();
  const c = mockCampaigns.find((x) => x.id === campaignId);
  if (!c) mockError("NOT_FOUND", "Campaign not found");
  if (data.name != null) c.name = data.name;
  if (data.note !== undefined) c.note = data.note;
  if (data.discount_percent != null) c.discount_percent = data.discount_percent;
  if (data.discount_starts_at !== undefined)
    c.discount_starts_at = data.discount_starts_at;
  if (data.discount_ends_at !== undefined)
    c.discount_ends_at = data.discount_ends_at;
  if (data.product_ids) {
    c.target_type = "ids";
    c.target_count = Array.from(new Set(data.product_ids)).length;
    c.target_ids = Array.from(new Set(data.product_ids));
    c.target_filter = null;
    mockAppliedTargets.set(
      `${c.id}:targets`,
      data.product_ids.map((id) => ({
        id,
        percent: null,
        starts_at: null,
        ends_at: null,
      })),
    );
  } else if (data.filter) {
    c.target_type = "filter";
    const ids = resolveMockTargets(null, data.filter);
    c.target_count = ids.length;
    c.target_ids = null;
    c.target_filter = data.filter;
    mockAppliedTargets.set(
      `${c.id}:targets`,
      ids.map((id) => ({ id, percent: null, starts_at: null, ends_at: null })),
    );
  }
  c.updated_at = new Date().toISOString();
  return { ...c, status: deriveCampaignStatus(c) };
}

export async function deleteCampaign(campaignId: string): Promise<void> {
  await delay();
  const idx = mockCampaigns.findIndex((x) => x.id === campaignId);
  if (idx === -1) mockError("NOT_FOUND", "Campaign not found");
  mockCampaigns.splice(idx, 1);
  mockAppliedTargets.delete(`${campaignId}:targets`);
  mockAppliedTargets.delete(campaignId);
}

export async function applyCampaign(
  campaignId: string,
): Promise<BulkDiscountResponse> {
  await delay();
  const c = mockCampaigns.find((x) => x.id === campaignId);
  if (!c) mockError("NOT_FOUND", "Campaign not found");
  const targets = mockAppliedTargets.get(`${c.id}:targets`) ?? [];
  const ids = targets.map((t) => t.id);
  const result = runMockBulk(
    "apply",
    ids,
    c.discount_percent,
    c.discount_starts_at,
    c.discount_ends_at,
  );
  const updatedIds = result.results
    .filter((r) => r.status === "updated")
    .map((r) => r.id);
  mockAppliedTargets.set(
    campaignId,
    updatedIds.map((id) => ({
      id,
      percent: c.discount_percent,
      starts_at: c.discount_starts_at,
      ends_at: c.discount_ends_at,
    })),
  );
  c.applied_at = new Date().toISOString();
  c.removed_at = null;
  c.last_result = result;
  return result;
}

export async function removeCampaign(
  campaignId: string,
): Promise<BulkDiscountResponse> {
  await delay();
  const c = mockCampaigns.find((x) => x.id === campaignId);
  if (!c) mockError("NOT_FOUND", "Campaign not found");
  const applied = mockAppliedTargets.get(campaignId) ?? [];
  const results: BulkResultItem[] = [];
  let success = 0;
  for (const t of applied) {
    const product = MOCK_PRODUCTS.find((p) => p.id === t.id);
    if (!product) {
      results.push({ id: t.id, status: "failed", error: "Product not found" });
      continue;
    }
    const matches =
      product.discount_percent === t.percent &&
      product.discount_starts_at === t.starts_at &&
      product.discount_ends_at === t.ends_at;
    if (!matches) {
      results.push({
        id: t.id,
        status: "skipped",
        error: "discount changed after campaign apply; left unchanged",
      });
      continue;
    }
    product.discount_percent = null;
    product.discount_starts_at = null;
    product.discount_ends_at = null;
    results.push({ id: t.id, status: "updated" });
    success += 1;
  }
  const result: BulkDiscountResponse = {
    success_count: success,
    failure_count: results.length - success,
    results,
  };
  c.removed_at = new Date().toISOString();
  c.last_result = result;
  return result;
}

export async function bulkDiscount(
  data: BulkDiscountRequest,
): Promise<BulkDiscountResponse> {
  await delay();
  const ids = resolveMockTargets(data.product_ids, data.filter);
  if (ids.length === 0)
    mockError("VALIDATION_ERROR", "target resolves to no products");
  if (ids.length > 500) {
    mockError(
      "BULK_TARGET_LIMIT_EXCEEDED",
      `target resolves to ${ids.length} products; limit is 500`,
    );
  }
  return runMockBulk(
    data.operation,
    ids,
    data.discount_percent ?? null,
    data.discount_starts_at ?? null,
    data.discount_ends_at ?? null,
  );
}

export async function getAdminBanner(): Promise<BannerAdminResponse> {
  await delay();
  return { ...mockBanner };
}

export async function updateBanner(
  data: BannerUpdateRequest,
): Promise<BannerAdminResponse> {
  await delay();
  const changed =
    mockBanner.message_en !== (data.message_en ?? null) ||
    mockBanner.message_bg !== (data.message_bg ?? null) ||
    mockBanner.link_label_en !== (data.link_label_en ?? null) ||
    mockBanner.link_label_bg !== (data.link_label_bg ?? null) ||
    mockBanner.link_url !== (data.link_url ?? null) ||
    mockBanner.is_enabled !== data.is_enabled ||
    mockBanner.starts_at !== (data.starts_at ?? null) ||
    mockBanner.ends_at !== (data.ends_at ?? null);
  mockBanner = {
    message_en: data.message_en ?? null,
    message_bg: data.message_bg ?? null,
    link_label_en: data.link_label_en ?? null,
    link_label_bg: data.link_label_bg ?? null,
    link_url: data.link_url ?? null,
    is_enabled: data.is_enabled,
    starts_at: data.starts_at ?? null,
    ends_at: data.ends_at ?? null,
    version: changed ? mockBanner.version + 1 : mockBanner.version,
    updated_at: new Date().toISOString(),
  };
  return { ...mockBanner };
}

export async function getPublicBanner(
  locale: string = "en",
): Promise<PublicBannerResponse> {
  await delay();
  if (!mockBanner.is_enabled) return { banner: null };
  const now = new Date().toISOString();
  if (mockBanner.starts_at && now < mockBanner.starts_at)
    return { banner: null };
  if (mockBanner.ends_at && now > mockBanner.ends_at) return { banner: null };
  const message =
    locale === "bg" && mockBanner.message_bg
      ? mockBanner.message_bg
      : mockBanner.message_en;
  if (!message) return { banner: null };
  const linkLabel =
    locale === "bg" && mockBanner.link_label_bg
      ? mockBanner.link_label_bg
      : mockBanner.link_label_en;
  return {
    banner: {
      message,
      link_label: linkLabel,
      link_url: mockBanner.link_url,
      dismiss_key: `default:v${mockBanner.version}`,
    },
  };
}

export async function getPublicSiteMedia(): Promise<PublicSiteMediaResponse> {
  await delay();
  const entries = mockSiteMediaAssets.map((asset) => [
    asset.key,
    asset.image_url ?? asset.default_url,
  ]);
  return { assets: Object.fromEntries(entries) as Record<SiteMediaKey, string | null> };
}

export async function getAdminSiteMedia(): Promise<SiteMediaAdminResponse> {
  await delay();
  return { assets: mockSiteMediaAssets.map(effectiveMockSiteMedia) };
}

export async function uploadSiteMediaImage(
  key: string,
  _file: File,
): Promise<SiteMediaAssetAdmin> {
  await delay();
  const asset = findMockSiteMedia(key);
  const imageId = `mock-${Date.now()}`;
  const stem = `site-media-${key.replaceAll("_", "-")}`;
  asset.image_id = imageId;
  asset.image_url = `/static/products/${stem}.webp`;
  asset.thumbnail_url = `/static/products/${stem}_thumb.webp`;
  asset.zoom_url = `/static/products/${stem}_zoom.webp`;
  asset.updated_at = new Date().toISOString();
  return effectiveMockSiteMedia(asset);
}

export async function clearSiteMediaImage(key: string): Promise<SiteMediaAssetAdmin> {
  await delay();
  const asset = findMockSiteMedia(key);
  asset.image_id = null;
  asset.image_url = null;
  asset.thumbnail_url = null;
  asset.zoom_url = null;
  asset.updated_at = new Date().toISOString();
  return effectiveMockSiteMedia(asset);
}
