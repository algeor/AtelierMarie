"use client";

import { useEffect, useMemo, useState, useRef, type CSSProperties } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import {
  createAndShipEcontOrder,
  getAdminOrders,
  updateOrderStatus,
} from "@/lib/api";
import { ApiError } from "@/lib/api-client";
import { useLocalizedError } from "@/lib/useLocalizedError";
import { cn, formatPrice } from "@/lib/utils";
import { Skeleton } from "@/components/ui/Skeleton";
import { Portal } from "@/components/ui/Portal";
import {
  ShipOrderModal,
  type ShipTrackingInput,
} from "@/components/admin/ShipOrderModal";
import type {
  AdminOrderAccountingFilter,
  OrderResponse,
  OrderStatus,
  PaymentMethod,
  PaymentStatus,
} from "@/lib/types";

const STATUS_FILTERS: (OrderStatus | "")[] = [
  "",
  "pending",
  "confirmed",
  "shipped",
  "delivered",
  "return_in_transit",
  "returned",
  "cancelled",
];

const PAYMENT_STATUS_FILTERS: (PaymentStatus | "")[] = [
  "",
  "pending",
  "paid",
  "cod_pending",
  "failed",
  "review_required",
  "refund_pending",
  "partially_refunded",
  "refunded",
  "dispute_open",
  "dispute_won",
  "dispute_lost",
];

const PAYMENT_METHOD_FILTERS: (PaymentMethod | "")[] = [
  "",
  "card",
  "cod",
  "bank_transfer",
];

const ACCOUNTING_FILTERS: (AdminOrderAccountingFilter | "")[] = [
  "",
  "missing_document_reference",
  "unresolved_exception",
  "payout_mismatch",
  "cod_settlement_pending",
  "refund_document_missing",
  "vat_review_required",
  "missing_batch_assignment",
  "missing_inventory_movement",
  "missing_cogs_row",
  "valuation_exception",
  "return_inventory_review_pending",
];

type OrderView = "all" | "needs_attention" | "awaiting_payment" | "returns" | "accounting" | "custom";

type DateRangeFilter = "" | "today" | "last_7_days" | "last_30_days";

const ORDER_VIEWS: Exclude<OrderView, "custom">[] = [
  "all",
  "needs_attention",
  "awaiting_payment",
  "returns",
  "accounting",
];

const DATE_RANGE_FILTERS: DateRangeFilter[] = ["", "today", "last_7_days", "last_30_days"];

const STATUS_COLORS: Record<OrderStatus, string> = {
  pending: "bg-amber-100 text-amber-800",
  confirmed: "bg-blue-100 text-blue-800",
  shipped: "bg-purple-100 text-purple-800",
  delivered: "bg-green-100 text-green-800",
  return_in_transit: "bg-orange-100 text-orange-800",
  returned: "bg-slate-100 text-slate-700",
  cancelled: "bg-red-100 text-red-800",
};

const VALID_TRANSITIONS: Record<OrderStatus, OrderStatus[]> = {
  pending: ["confirmed", "cancelled"],
  confirmed: ["shipped", "cancelled"],
  shipped: ["delivered", "return_in_transit"],
  delivered: ["return_in_transit"],
  return_in_transit: ["returned"],
  returned: [],
  cancelled: [],
};

const PAYMENT_STATUS_COLORS: Record<PaymentStatus, string> = {
  pending: "bg-amber-100 text-amber-800",
  paid: "bg-green-100 text-green-800",
  cod_pending: "bg-gray-100 text-gray-700",
  failed: "bg-red-100 text-red-800",
  review_required: "bg-amber-100 text-amber-800",
  refund_pending: "bg-blue-100 text-blue-800",
  partially_refunded: "bg-blue-100 text-blue-800",
  refunded: "bg-blue-100 text-blue-800",
  dispute_open: "bg-red-100 text-red-800",
  dispute_won: "bg-green-100 text-green-800",
  dispute_lost: "bg-red-100 text-red-800",
};

type DropdownOption<Value extends string> = {
  value: Value;
  label: string;
};

interface DropdownMenuProps<Value extends string> {
  ariaLabel: string;
  buttonClassName?: string;
  containerClassName?: string;
  disabled?: boolean;
  label: string;
  menuItemClassName?: string;
  onSelect: (value: Value) => void;
  openButtonClassName?: string;
  options: DropdownOption<Value>[];
  selectedValue?: Value;
}

function DropdownMenu<Value extends string>({
  ariaLabel,
  buttonClassName,
  containerClassName,
  disabled,
  label,
  menuItemClassName,
  options,
  openButtonClassName,
  onSelect,
  selectedValue,
}: DropdownMenuProps<Value>) {
  const [isOpen, setIsOpen] = useState(false);
  const [menuStyle, setMenuStyle] = useState<CSSProperties>({});
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (disabled) setIsOpen(false);
  }, [disabled]);

  useEffect(() => {
    if (!isOpen) return;

    function updateMenuPosition() {
      const trigger = triggerRef.current;
      if (!trigger) return;

      const rect = trigger.getBoundingClientRect();
      const menuWidth = rect.width;
      const menuHeight = Math.min(options.length * 40 + 12, 260);
      const viewportWidth = window.innerWidth || menuWidth;
      const viewportHeight = window.innerHeight || 720;
      const left = Math.min(
        Math.max(8, rect.left),
        Math.max(8, viewportWidth - menuWidth - 8)
      );
      const shouldOpenUp = rect.bottom + menuHeight > viewportHeight && rect.top > menuHeight;
      const top = shouldOpenUp ? rect.top - menuHeight + 1 : rect.bottom - 1;

      setMenuStyle({
        left,
        position: "fixed",
        top: Math.max(8, top),
        width: menuWidth,
      });
    }

    function handlePointerDown(event: MouseEvent) {
      const target = event.target as Node;
      if (triggerRef.current?.contains(target) || menuRef.current?.contains(target)) {
        return;
      }
      setIsOpen(false);
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
        triggerRef.current?.focus();
      }
    }

    updateMenuPosition();
    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    window.addEventListener("resize", updateMenuPosition);
    window.addEventListener("scroll", updateMenuPosition, true);

    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("resize", updateMenuPosition);
      window.removeEventListener("scroll", updateMenuPosition, true);
    };
  }, [isOpen, options.length]);

  return (
    <div className={cn("inline-flex", containerClassName)}>
      <button
        ref={triggerRef}
        type="button"
        disabled={disabled}
        aria-haspopup="menu"
        aria-expanded={isOpen}
        aria-label={ariaLabel}
        onClick={() => setIsOpen((open) => !open)}
        className={cn(
          buttonClassName,
          disabled && "cursor-not-allowed opacity-50",
          isOpen && openButtonClassName
        )}
      >
        <span className="truncate">{label}</span>
        <span
          aria-hidden="true"
          className={cn(
            "text-[10px] text-soft-brown/70 transition-transform duration-fast",
            isOpen && "rotate-180"
          )}
        >
          ▾
        </span>
      </button>

      {isOpen && (
        <Portal>
          <div
            ref={menuRef}
            role="menu"
            aria-label={ariaLabel}
            style={menuStyle}
            className="z-50 overflow-hidden rounded-b-brand border border-soft-brown/35 bg-warm-ivory py-1 shadow-xl ring-1 ring-charcoal/5"
          >
            {options.map((option) => (
              <button
                key={option.value || "all"}
                type="button"
                role={selectedValue === undefined ? "menuitem" : "menuitemradio"}
                aria-checked={selectedValue === undefined ? undefined : selectedValue === option.value}
                data-value={option.value}
                onClick={() => {
                  setIsOpen(false);
                  onSelect(option.value);
                }}
                className={cn(
                  "flex h-9 w-full items-center gap-2 px-3 text-left text-xs font-medium text-soft-brown transition-colors duration-fast hover:bg-cream/55 hover:text-charcoal focus-visible:bg-cream/55 focus-visible:text-charcoal focus-visible:outline-none",
                  selectedValue === option.value && "bg-cream/55 text-charcoal",
                  menuItemClassName
                )}
              >
                {selectedValue !== undefined && (
                  <span aria-hidden="true" className="w-4 shrink-0 text-center">
                    {selectedValue === option.value ? "✓" : ""}
                  </span>
                )}
                <span className="truncate">{option.label}</span>
              </button>
            ))}
          </div>
        </Portal>
      )}
    </div>
  );
}

type TransitionOption = {
  status: OrderStatus;
  label: string;
};

interface StatusTransitionMenuProps {
  ariaLabel: string;
  disabled: boolean;
  label: string;
  options: TransitionOption[];
  onSelect: (status: OrderStatus) => void;
}

function StatusTransitionMenu({
  ariaLabel,
  disabled,
  label,
  options,
  onSelect,
}: StatusTransitionMenuProps) {
  return (
    <DropdownMenu
      ariaLabel={ariaLabel}
      disabled={disabled}
      label={label}
      options={options.map((option) => ({ value: option.status, label: option.label }))}
      onSelect={onSelect}
      buttonClassName={cn(
        "inline-flex h-9 min-w-[11.5rem] items-center justify-between gap-2 rounded-brand border border-champagne-beige/80 bg-warm-ivory px-3 text-xs font-medium text-soft-brown shadow-sm",
        "transition-colors duration-fast hover:border-soft-brown/30 hover:bg-cream hover:text-charcoal",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory",
        "disabled:cursor-not-allowed disabled:opacity-50"
      )}
      openButtonClassName="rounded-b-none border-soft-brown/35 bg-warm-ivory shadow-none"
    />
  );
}

interface FilterDropdownProps<Value extends string> {
  label: string;
  onSelect: (value: Value) => void;
  options: DropdownOption<Value>[];
  value: Value;
}

function FilterDropdown<Value extends string>({
  label,
  onSelect,
  options,
  value,
}: FilterDropdownProps<Value>) {
  const selectedLabel = options.find((option) => option.value === value)?.label ?? label;

  return (
    <div className="space-y-1">
      <p className="text-xs font-semibold uppercase text-soft-brown">{label}</p>
      <DropdownMenu
        ariaLabel={label}
        containerClassName="w-full"
        label={selectedLabel}
        options={options}
        selectedValue={value}
        onSelect={onSelect}
        buttonClassName={cn(
          "inline-flex h-10 w-full items-center justify-between gap-2 rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm font-normal text-charcoal shadow-sm",
          "transition-colors duration-fast hover:border-soft-brown/30 hover:bg-cream",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2 focus-visible:ring-offset-warm-ivory"
        )}
        openButtonClassName="rounded-b-none border-soft-brown/35 bg-warm-ivory shadow-none"
        menuItemClassName="text-sm"
      />
    </div>
  );
}

function formatDate(iso: string, locale: string): string {
  return new Date(iso).toLocaleDateString(locale === "bg" ? "bg-BG" : "en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function maskEmail(email: string): string {
  const [local, domain] = email.split("@");
  if (!domain || !local) return email;
  const visible = local.slice(0, 1);
  return `${visible}***@${domain}`;
}

function orderMatchesSearch(order: OrderResponse, query: string): boolean {
  const normalizedQuery = query.trim().toLowerCase();
  if (!normalizedQuery) return true;

  const deliveryDetails = order.delivery_details;
  const deliveryText = deliveryDetails
    ? Object.values(deliveryDetails)
        .filter((value): value is string | number =>
          typeof value === "string" || typeof value === "number"
        )
        .join(" ")
    : "";

  return [
    order.id,
    order.order_number,
    order.customer_email,
    order.customer_name,
    order.status,
    order.payment_status,
    order.payment_method,
    deliveryText,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase()
    .includes(normalizedQuery);
}

function orderMatchesDateRange(order: OrderResponse, range: DateRangeFilter): boolean {
  if (!range) return true;

  const createdAt = new Date(order.created_at);
  if (Number.isNaN(createdAt.getTime())) return true;

  const now = new Date();
  if (range === "today") {
    return (
      createdAt.getFullYear() === now.getFullYear() &&
      createdAt.getMonth() === now.getMonth() &&
      createdAt.getDate() === now.getDate()
    );
  }

  const days = range === "last_7_days" ? 7 : 30;
  const cutoff = new Date(now);
  cutoff.setDate(now.getDate() - days);
  return createdAt >= cutoff;
}

export default function AdminOrdersPage() {
  const t = useTranslations("admin");
  const tStatus = useTranslations("orders.status");
  const tPayment = useTranslations("orders.payment");
  const tMethod = useTranslations("checkout.delivery.method");
  const tCourier = useTranslations("checkout.delivery.courier");
  const tDisplay = useTranslations("checkout.delivery.display");
  const locale = useLocale();
  const getLocalizedError = useLocalizedError();
  const [orders, setOrders] = useState<OrderResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [orderView, setOrderView] = useState<OrderView>("all");
  const [orderSearch, setOrderSearch] = useState("");
  const [dateRangeFilter, setDateRangeFilter] = useState<DateRangeFilter>("");
  const [statusFilter, setStatusFilter] = useState<OrderStatus | "">("");
  const [paymentStatusFilter, setPaymentStatusFilter] = useState<PaymentStatus | "">("");
  const [paymentMethodFilter, setPaymentMethodFilter] = useState<PaymentMethod | "">("");
  const [accountingFilter, setAccountingFilter] = useState<AdminOrderAccountingFilter | "">("");
  const [isAdvancedFiltersOpen, setIsAdvancedFiltersOpen] = useState(false);
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  // Order awaiting the shipping form (tracking is required before we ship).
  const [shippingOrder, setShippingOrder] = useState<OrderResponse | null>(null);
  const isInitialLoad = useRef(true);

  const displayedOrders = useMemo(
    () =>
      orders.filter(
        (order) =>
          orderMatchesSearch(order, orderSearch) &&
          orderMatchesDateRange(order, dateRangeFilter)
      ),
    [orders, orderSearch, dateRangeFilter]
  );

  const isPresetView = orderView !== "all" && orderView !== "custom";
  const activeFilterLabels = [
    isPresetView
      ? t(`orderViews.${orderView}` as Parameters<typeof t>[0])
      : null,
    !isPresetView && statusFilter ? tStatus(statusFilter) : null,
    !isPresetView && paymentStatusFilter
      ? tPayment(`status.${paymentStatusFilter}` as Parameters<typeof tPayment>[0])
      : null,
    !isPresetView && paymentMethodFilter
      ? tPayment(`method.${paymentMethodFilter}` as Parameters<typeof tPayment>[0])
      : null,
    !isPresetView && accountingFilter
      ? t(`accountingFilters.${accountingFilter}` as Parameters<typeof t>[0])
      : null,
    dateRangeFilter ? t(`dateRanges.${dateRangeFilter}` as Parameters<typeof t>[0]) : null,
    orderSearch.trim() ? `${t("search")}: ${orderSearch.trim()}` : null,
  ].filter((label): label is string => Boolean(label));

  const dateRangeOptions: DropdownOption<DateRangeFilter>[] = DATE_RANGE_FILTERS.map((filter) => ({
    value: filter,
    label: filter ? t(`dateRanges.${filter}` as Parameters<typeof t>[0]) : t("dateRanges.all"),
  }));

  const statusOptions: DropdownOption<OrderStatus | "">[] = STATUS_FILTERS.map((filter) => ({
    value: filter,
    label: filter ? tStatus(filter) : t("all"),
  }));

  const paymentStatusOptions: DropdownOption<PaymentStatus | "">[] = PAYMENT_STATUS_FILTERS.map((filter) => ({
    value: filter,
    label: filter ? tPayment(`status.${filter}` as Parameters<typeof tPayment>[0]) : t("all"),
  }));

  const paymentMethodOptions: DropdownOption<PaymentMethod | "">[] = PAYMENT_METHOD_FILTERS.map((filter) => ({
    value: filter,
    label: filter ? tPayment(`method.${filter}` as Parameters<typeof tPayment>[0]) : t("all"),
  }));

  const accountingOptions: DropdownOption<AdminOrderAccountingFilter | "">[] = ACCOUNTING_FILTERS.map((filter) => ({
    value: filter,
    label: filter ? t(`accountingFilters.${filter}` as Parameters<typeof t>[0]) : t("all"),
  }));

  function handleViewChange(view: Exclude<OrderView, "custom">) {
    setOrderView(view);
    setStatusFilter("");
    setPaymentStatusFilter("");
    setPaymentMethodFilter("");
    setAccountingFilter("");

    if (view === "needs_attention") {
      setPaymentStatusFilter("review_required");
    } else if (view === "awaiting_payment") {
      setPaymentStatusFilter("pending");
    } else if (view === "returns") {
      setStatusFilter("return_in_transit");
    } else if (view === "accounting") {
      setAccountingFilter("unresolved_exception");
    }
  }

  function clearFilters() {
    setOrderView("all");
    setOrderSearch("");
    setDateRangeFilter("");
    setStatusFilter("");
    setPaymentStatusFilter("");
    setPaymentMethodFilter("");
    setAccountingFilter("");
  }

  useEffect(() => {
    async function loadOrders() {
      try {
        if (isInitialLoad.current) {
          setIsLoading(true);
        } else {
          setIsRefreshing(true);
        }
        setError(null);
        const args: Parameters<typeof getAdminOrders> = [1, 100];
        if (statusFilter) args[2] = statusFilter;
        if (paymentStatusFilter || paymentMethodFilter || accountingFilter) {
          args[2] = statusFilter || undefined;
          args[3] = paymentStatusFilter || undefined;
          args[4] = paymentMethodFilter || undefined;
          args[5] = accountingFilter || undefined;
        }
        const data = await getAdminOrders(...args);
        setOrders(data.items);
      } catch (err) {
        setError(err instanceof ApiError ? getLocalizedError(err.code) : t("errors.loadOrders"));
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
        isInitialLoad.current = false;
      }
    }
    loadOrders();
  }, [statusFilter, paymentStatusFilter, paymentMethodFilter, accountingFilter, getLocalizedError, t]);

  async function handleStatusChange(
    order: OrderResponse,
    newStatus: OrderStatus,
    tracking?: ShipTrackingInput
  ) {
    const previousStatus = order.status;
    setUpdatingId(order.id);
    setError(null);

    // Optimistic update (include tracking so the row reflects it immediately)
    setOrders((prev) =>
      prev.map((o) =>
        o.id === order.id ? { ...o, status: newStatus, ...(tracking ?? {}) } : o
      )
    );

    try {
      await updateOrderStatus(order.id, newStatus, tracking);
      setShippingOrder(null);
      // Remove order from view if it no longer matches the active filter
      if (statusFilter && newStatus !== statusFilter) {
        setOrders((prev) => prev.filter((o) => o.id !== order.id));
      }
    } catch (err) {
      // Rollback
      setOrders((prev) =>
        prev.map((o) =>
          o.id === order.id ? { ...o, status: previousStatus } : o
        )
      );
      setError(
        err instanceof ApiError ? getLocalizedError(err.code) : t("errors.updateOrderStatus")
      );
    } finally {
      setUpdatingId(null);
    }
  }

  async function handleEcontCreateAndShip(order: OrderResponse) {
    const previousStatus = order.status;
    setUpdatingId(order.id);
    setError(null);

    try {
      const result = await createAndShipEcontOrder(order.id);
      setShippingOrder(null);
      setOrders((prev) =>
        prev.map((o) =>
          o.id === order.id
            ? {
                ...o,
                status: "shipped",
                tracking_number: result.shipment_number ?? o.tracking_number,
                tracking_carrier: "econt",
                tracking_url: result.tracking_url ?? o.tracking_url,
                courier_provider: "econt",
                courier_shipment_number: result.shipment_number ?? o.courier_shipment_number,
                courier_label_url: result.label_url ?? o.courier_label_url,
                courier_sync_status: "label_created",
              }
            : o,
        ),
      );
      if (statusFilter && statusFilter !== "shipped") {
        setOrders((prev) => prev.filter((o) => o.id !== order.id));
      }
    } catch (err) {
      setOrders((prev) =>
        prev.map((o) => (o.id === order.id ? { ...o, status: previousStatus } : o)),
      );
      setError(
        err instanceof ApiError ? getLocalizedError(err.code) : t("errors.updateOrderStatus"),
      );
    } finally {
      setUpdatingId(null);
    }
  }

  // Known courier integrations can create/reuse shipment numbers themselves;
  // manual carriers still need tracking data before the shipped transition.
  function handleTransitionSelected(order: OrderResponse, newStatus: OrderStatus) {
    if (newStatus === "shipped") {
      if (order.delivery_courier === "speedy") {
        handleStatusChange(order, newStatus);
        return;
      }
      if (order.delivery_courier === "econt") {
        if (order.tracking_number || order.courier_shipment_number) {
          handleStatusChange(order, newStatus);
          return;
        }
        handleEcontCreateAndShip(order);
        return;
      }
      setShippingOrder(order);
      return;
    }
    handleStatusChange(order, newStatus);
  }

  return (
    <div>
      <div className="mb-8">
        <div className="flex items-center gap-2">
          <h1 className="font-heading text-2xl font-semibold text-charcoal">
            {t("orders")}
          </h1>
        </div>
      </div>

      <div className="mb-6 space-y-3">
        <div className="flex flex-wrap gap-2" aria-label={t("orderViewsLabel")}>
          {ORDER_VIEWS.map((view) => (
            <button
              key={view}
              type="button"
              onClick={() => handleViewChange(view)}
              className={cn(
                "rounded-pill px-4 py-1.5 text-sm font-medium transition-colors duration-fast",
                orderView === view
                  ? "bg-muted-gold text-charcoal"
                  : "bg-champagne-beige/50 text-soft-brown hover:bg-champagne-beige"
              )}
              aria-pressed={orderView === view}
            >
              {t(`orderViews.${view}` as Parameters<typeof t>[0])}
            </button>
          ))}
        </div>

        <div className="rounded-brand border border-champagne-beige bg-cream p-4">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-[minmax(16rem,1fr)_minmax(9rem,11rem)_minmax(10rem,12rem)_minmax(11rem,13rem)_auto] xl:items-end">
            <label className="text-xs font-semibold uppercase text-soft-brown">
              {t("search")}
              <input
                type="search"
                value={orderSearch}
                onChange={(event) => setOrderSearch(event.target.value)}
                placeholder={t("searchOrdersPlaceholder")}
                className="mt-1 h-10 w-full rounded-brand border border-champagne-beige bg-warm-ivory px-3 text-sm font-normal normal-case text-charcoal placeholder:text-soft-brown/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown"
              />
            </label>

            <FilterDropdown
              label={t("dateRange")}
              value={dateRangeFilter}
              options={dateRangeOptions}
              onSelect={setDateRangeFilter}
            />

            <FilterDropdown
              label={t("status")}
              value={statusFilter}
              options={statusOptions}
              onSelect={(value) => {
                setOrderView("custom");
                setStatusFilter(value);
              }}
            />

            <FilterDropdown
              label={t("paymentStatus")}
              value={paymentStatusFilter}
              options={paymentStatusOptions}
              onSelect={(value) => {
                setOrderView("custom");
                setPaymentStatusFilter(value);
              }}
            />

            <button
              type="button"
              onClick={() => setIsAdvancedFiltersOpen((open) => !open)}
              aria-expanded={isAdvancedFiltersOpen}
              className="inline-flex h-10 items-center justify-center gap-2 rounded-brand border border-champagne-beige bg-warm-ivory px-4 text-sm font-medium text-charcoal transition-colors duration-fast hover:bg-champagne-beige/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown"
            >
              {t("filters")}
              {activeFilterLabels.length > 0 && (
                <span className="rounded-pill bg-muted-gold px-2 py-0.5 text-xs text-charcoal">
                  {activeFilterLabels.length}
                </span>
              )}
            </button>
          </div>

          {isAdvancedFiltersOpen && (
            <div className="mt-4 grid gap-3 border-t border-champagne-beige pt-4 md:grid-cols-2">
              <FilterDropdown
                label={t("paymentMethod")}
                value={paymentMethodFilter}
                options={paymentMethodOptions}
                onSelect={(value) => {
                  setOrderView("custom");
                  setPaymentMethodFilter(value);
                }}
              />

              <FilterDropdown
                label={t("accountingFilter")}
                value={accountingFilter}
                options={accountingOptions}
                onSelect={(value) => {
                  setOrderView("custom");
                  setAccountingFilter(value);
                }}
              />
            </div>
          )}

          {activeFilterLabels.length > 0 && (
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold uppercase text-soft-brown">
                {t("activeFilters")}
              </span>
              {activeFilterLabels.map((label) => (
                <span
                  key={label}
                  className="rounded-pill bg-champagne-beige/60 px-3 py-1 text-xs font-medium text-soft-brown"
                >
                  {label}
                </span>
              ))}
              <button
                type="button"
                onClick={clearFilters}
                className="rounded-pill px-3 py-1 text-xs font-medium text-charcoal underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown"
              >
                {t("clearFilters")}
              </button>
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="mb-6 rounded-brand border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Orders Table */}
      <div className="relative overflow-x-auto rounded-brand border border-champagne-beige bg-cream">
        {isRefreshing && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-cream/50">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-muted-gold border-t-transparent" />
          </div>
        )}
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-champagne-beige bg-champagne-beige/30">
              <th className="px-4 py-3 font-medium text-charcoal">{t("orderId")}</th>
              <th className="px-4 py-3 font-medium text-charcoal">{t("customer")}</th>
              <th className="px-4 py-3 font-medium text-charcoal">{tDisplay("sectionTitle")}</th>
              <th className="px-4 py-3 font-medium text-charcoal">{t("total")}</th>
              <th className="px-4 py-3 font-medium text-charcoal">{t("status")}</th>
              <th className="px-4 py-3 font-medium text-charcoal">{tPayment("sectionTitle")}</th>
              <th className="px-4 py-3 font-medium text-charcoal">{t("accountingColumn")}</th>
              <th className="px-4 py-3 font-medium text-charcoal">{t("date")}</th>
              <th className="px-4 py-3 font-medium text-charcoal">{t("actions")}</th>
            </tr>
          </thead>
          <tbody className={cn(isRefreshing && "opacity-50 pointer-events-none")}>
            {isLoading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <tr key={i} className="border-b border-champagne-beige/50">
                  <td className="px-4 py-3"><Skeleton className="h-4 w-20" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-32" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-28" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-16" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-5 w-20" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-5 w-20" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-5 w-24" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-24" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-8 w-28" /></td>
                </tr>
              ))
            ) : displayedOrders.length === 0 ? (
              <tr>
                <td colSpan={9} className="px-4 py-8 text-center text-soft-brown">
                  {t("noOrders")}
                </td>
              </tr>
            ) : (
              displayedOrders.map((order) => (
                <tr
                  key={order.id}
                  className="border-b border-champagne-beige/50 last:border-0"
                >
                  <td className="px-4 py-3 font-mono text-xs text-soft-brown">
                    <Link
                      href={`/admin/orders/${order.id}`}
                      className="transition-colors duration-fast hover:text-charcoal hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown"
                    >
                      {order.order_number || `${order.id.slice(0, 8)}...`}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-charcoal">
                    <span title={order.customer_email}>
                      {maskEmail(order.customer_email)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-soft-brown">
                    {order.delivery_method ? (
                      <div className="flex flex-col gap-0.5">
                        <span className="text-charcoal">
                          {tMethod(order.delivery_method)}
                          {order.delivery_courier && (
                            <span className="text-soft-brown"> · {tCourier(order.delivery_courier)}</span>
                          )}
                        </span>
                        {order.delivery_details && "office_name" in order.delivery_details && (
                          <span className="truncate max-w-[16rem]" title={order.delivery_details.office_name}>
                            {order.delivery_details.office_type === "apt" ? "🔐 " : "📦 "}
                            {order.delivery_details.office_name}
                          </span>
                        )}
                        {order.delivery_details && "street" in order.delivery_details && (
                          <span className="truncate max-w-[16rem]" title={`${order.delivery_details.street}, ${order.delivery_details.city}`}>
                            {order.delivery_details.street}, {order.delivery_details.city}
                          </span>
                        )}
                        {(order.delivery_courier === "speedy" || order.tracking_carrier === "speedy") && (
                          <Link
                            href={`/admin/speedy?order_id=${order.id}`}
                            className="text-xs font-medium text-charcoal underline-offset-2 hover:underline"
                          >
                            {t("speedyDiagnostics")}
                          </Link>
                        )}
                      </div>
                    ) : (
                      <span className="text-soft-brown/50">{tDisplay("none")}</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-soft-brown">
                    {formatPrice(order.total_cents)}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        "inline-flex items-center rounded-pill px-2.5 py-0.5 text-xs font-medium capitalize",
                        STATUS_COLORS[order.status]
                      )}
                    >
                      {tStatus(order.status)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col gap-1">
                      <span className="text-xs text-soft-brown">
                        {tPayment(`method.${order.payment_method}` as Parameters<typeof tPayment>[0])}
                      </span>
                      {order.payment_status && (
                        <span className={cn(
                          "inline-flex items-center rounded-pill px-2 py-0.5 text-xs font-medium",
                          PAYMENT_STATUS_COLORS[order.payment_status]
                        )}>
                          {tPayment(`status.${order.payment_status}` as Parameters<typeof tPayment>[0])}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-xs text-soft-brown">
                    <div className="flex flex-col gap-1">
                      <span className={cn(
                        "inline-flex w-fit rounded-pill px-2 py-0.5 font-medium",
                        order.accounting_readiness_status === "blocked"
                          ? "bg-red-100 text-red-800"
                          : order.accounting_readiness_status === "ready"
                            ? "bg-green-100 text-green-800"
                            : "bg-amber-100 text-amber-800"
                      )}>
                        {order.accounting_readiness_status ?? "unreviewed"}
                      </span>
                      <span>{order.document_reference_status ?? "not_required"}</span>
                      {Boolean(order.blocking_exception_count) && (
                        <span>{t("blockingExceptions", { count: order.blocking_exception_count ?? 0 })}</span>
                      )}
                      {order.finance_hub_links?.period_href && (
                        <Link href={order.finance_hub_links.period_href} className="font-medium text-charcoal underline-offset-2 hover:underline">
                          {t("openFinanceHub")}
                        </Link>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-soft-brown">
                    {formatDate(order.created_at, locale)}
                  </td>
                  <td className="px-4 py-3">
                    {VALID_TRANSITIONS[order.status].length > 0 ? (
                      <StatusTransitionMenu
                        ariaLabel={t("updateStatusForOrder", { id: order.id.slice(0, 8) })}
                        disabled={updatingId === order.id}
                        label={t("updateStatus")}
                        options={VALID_TRANSITIONS[order.status].map((status) => ({
                          status,
                          label: tStatus(status),
                        }))}
                        onSelect={(status) => handleTransitionSelected(order, status)}
                      />
                    ) : (
                      <span className="text-xs text-soft-brown/50">
                        {t("noActions")}
                      </span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {shippingOrder && (
        <ShipOrderModal
          orderId={shippingOrder.id}
          deliveryCourier={shippingOrder.delivery_courier}
          isSubmitting={updatingId === shippingOrder.id}
          onCancel={() => setShippingOrder(null)}
          onConfirm={(tracking) =>
            handleStatusChange(shippingOrder, "shipped", tracking)
          }
        />
      )}
    </div>
  );
}
