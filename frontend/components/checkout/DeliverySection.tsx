"use client";

/**
 * DeliverySection — orchestrates the multi-step delivery picker for checkout.
 *
 * Composes:
 *   - DeliveryMethodSelector: office vs door radio
 *   - CourierPicker: Speedy vs Econt radio
 *   - OfficePicker: city search + filtered office list
 *   - DoorAddressForm: structured address fields
 *
 * Shipping price (calculate API, courier comparison, free-shipping threshold) is
 * intentionally out of scope — added by the sibling `shipping-pricing` change.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslations, useLocale } from "next-intl";
import { getDeliveryCities, getDeliveryConfig, getDeliveryOffices, getDeliveryPlaces } from "@/lib/api";
import { cn } from "@/lib/utils";
import type {
  CityPlace,
  Courier,
  DeliveryConfigResponse,
  DeliverySettingsResponse,
  DeliveryDoor,
  DeliveryInfo,
  DeliveryMethod,
  DeliveryOffice,
  OfficeResponse,
  OfficeType,
} from "@/lib/types";
import type { Locale } from "@/i18n/routing";

const PHONE_REGEX = /^\+?[0-9]{8,15}$/;
const DEFAULT_ECONT_LOCATOR_URL = "https://delivery.econt.com/customer_info.php";
const DEFAULT_ECONT_LOCATOR_ORIGINS = [
  "https://delivery.econt.com",
  "https://delivery-demo.econt.com",
];

/**
 * Normalize phone input to match backend validation (app/models/delivery.py).
 * Strip everything except digits and a leading '+' before regex-testing,
 * so conventionally-formatted numbers (e.g. "+359 888 123 456", "(0888) 123 456")
 * pass client-side just like they do server-side.
 */
function normalizePhone(value: string): string {
  return value.replace(/[^\d+]/g, "");
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function asString(value: unknown): string | null {
  if (typeof value === "string") return value.trim() || null;
  if (typeof value === "number") return String(value);
  return null;
}

function parseLocatorMessage(data: unknown): Record<string, unknown> | null {
  if (typeof data === "string") {
    try {
      return asRecord(JSON.parse(data));
    } catch {
      return null;
    }
  }
  return asRecord(data);
}

function readAddress(value: unknown): string {
  const direct = asString(value);
  if (direct) return direct;
  const address = asRecord(value);
  if (!address) return "";
  return (
    asString(address.fullAddress) ??
    asString(address.full_address) ??
    asString(address.address) ??
    [address.street, address.number].map(asString).filter(Boolean).join(" ")
  );
}

function readOfficeType(value: unknown, name: string): OfficeType {
  const raw = `${asString(value) ?? ""} ${name}`.toLowerCase();
  return raw.includes("apt") || raw.includes("aps") || raw.includes("locker") || raw.includes("автомат")
    ? "apt"
    : "office";
}

export function normalizeEcontLocatorOfficeMessage(data: unknown): OfficeResponse | null {
  const message = parseLocatorMessage(data);
  if (!message) return null;

  const nested =
    asRecord(message.office) ??
    asRecord(message.selectedOffice) ??
    asRecord(message.selected_office) ??
    asRecord(message.officeData) ??
    asRecord(message.data) ??
    message;

  const rawId =
    asString(nested.id) ?? asString(nested.officeId) ?? asString(nested.office_id) ?? null;
  const code = asString(nested.code) ?? asString(nested.officeCode) ?? asString(nested.office_code);
  const name = asString(nested.name) ?? asString(nested.officeName) ?? asString(nested.office_name);
  if (!rawId || !code || !name) return null;

  const addressRecord = asRecord(nested.address);
  return {
    id: rawId.startsWith("econt-") ? rawId : `econt-${rawId}`,
    code,
    name,
    type: readOfficeType(nested.type ?? nested.officeType ?? nested.office_type, name),
    city:
      asString(nested.city) ??
      asString(nested.cityName) ??
      asString(nested.city_name) ??
      asString(addressRecord?.city) ??
      "",
    address: readAddress(nested.address ?? nested.fullAddress ?? nested.full_address),
    working_hours:
      asString(nested.workingHours) ??
      asString(nested.working_hours) ??
      asString(nested.workTime) ??
      "",
  };
}

function uniqueOrigins(values: string[]): string[] {
  return Array.from(new Set(values.map((value) => value.trim()).filter(Boolean)));
}

type EcontOfficeLocatorConfig = {
  enabled: boolean;
  url: string;
  allowedOrigins: string[];
};

function buildEcontOfficeLocatorConfig(
  enabled: boolean,
  url: string,
  origins: string[],
): EcontOfficeLocatorConfig {
  let urlOrigin: string | null = null;
  try {
    urlOrigin = new URL(url).origin;
  } catch {
    urlOrigin = null;
  }
  return {
    enabled,
    url,
    allowedOrigins: uniqueOrigins([
      ...origins,
      ...(urlOrigin ? [urlOrigin] : []),
      ...DEFAULT_ECONT_LOCATOR_ORIGINS,
    ]),
  };
}

function getEcontOfficeLocatorEnvConfig(): EcontOfficeLocatorConfig {
  const enabled = process.env.NEXT_PUBLIC_ECONT_OFFICE_LOCATOR_ENABLED === "true";
  const url = process.env.NEXT_PUBLIC_ECONT_OFFICE_LOCATOR_URL?.trim() || DEFAULT_ECONT_LOCATOR_URL;
  const origins = process.env.NEXT_PUBLIC_ECONT_OFFICE_LOCATOR_ORIGINS?.split(",") ?? [];
  return buildEcontOfficeLocatorConfig(enabled, url, origins);
}

function getEcontOfficeLocatorApiConfig(
  config: DeliveryConfigResponse,
): EcontOfficeLocatorConfig {
  return buildEcontOfficeLocatorConfig(
    config.econt.office_locator_enabled,
    config.econt.office_locator_url || DEFAULT_ECONT_LOCATOR_URL,
    config.econt.office_locator_origins,
  );
}

function buildLocatorSrc(baseUrl: string, city: string, locale: string): string {
  try {
    const url = new URL(baseUrl);
    if (city.trim()) url.searchParams.set("city", city.trim());
    url.searchParams.set("lang", locale === "bg" ? "bg" : "en");
    url.searchParams.set("office_type", "office");
    url.searchParams.set("delivery_type", "office");
    if (typeof window !== "undefined") {
      url.searchParams.set("shop_url", window.location.origin);
    }
    return url.toString();
  } catch {
    return baseUrl;
  }
}

export interface DeliveryValidationErrors {
  method?: string;
  courier?: string;
  office?: string;
  city?: string;
  postalCode?: string;
  street?: string;
  phone?: string;
}

interface DeliverySectionProps {
  value: Partial<DeliveryInfo>;
  onChange: (delivery: Partial<DeliveryInfo>) => void;
  errors?: DeliveryValidationErrors;
  onErrorsChange?: (errors: DeliveryValidationErrors) => void;
  deliverySettings?: DeliverySettingsResponse | null;
}

const ALL_COURIERS: Courier[] = ["speedy", "econt"];
const ALL_METHODS: DeliveryMethod[] = ["office", "door"];

function methodEnabled(
  settings: DeliverySettingsResponse | null | undefined,
  courier: Courier,
  method: DeliveryMethod,
): boolean {
  if (!settings) return true;
  const key = `${courier}_${method}_enabled` as keyof Pick<
    DeliverySettingsResponse,
    | "speedy_office_enabled"
    | "speedy_door_enabled"
    | "econt_office_enabled"
    | "econt_door_enabled"
  >;
  return settings[key];
}

function availableCouriersForMethod(
  settings: DeliverySettingsResponse | null | undefined,
  method: DeliveryMethod,
): Courier[] {
  return ALL_COURIERS.filter((courier) => methodEnabled(settings, courier, method));
}

// ---------------- DeliveryMethodSelector ----------------

interface DeliveryMethodSelectorProps {
  value: DeliveryMethod | undefined;
  onChange: (method: DeliveryMethod) => void;
  methods: DeliveryMethod[];
  error?: string;
}

function DeliveryMethodSelector({ value, onChange, methods, error }: DeliveryMethodSelectorProps) {
  const t = useTranslations("checkout.delivery.method");

  return (
    <fieldset className="mb-6">
      <legend className="mb-2 block text-sm font-medium text-soft-brown">
        {t("label")} <span className="text-error">*</span>
      </legend>
      <div className="grid gap-3 sm:grid-cols-2" role="radiogroup" aria-label={t("label")}>
        {methods.map((m) => (
          <label
            key={m}
            className={cn(
              "flex cursor-pointer items-center gap-3 rounded-brand border px-4 py-3 transition-colors",
              value === m
                ? "border-muted-gold bg-muted-gold/10"
                : "border-champagne-beige bg-warm-ivory hover:border-soft-brown/40"
            )}
          >
            <input
              type="radio"
              name="delivery-method"
              value={m}
              checked={value === m}
              onChange={() => onChange(m)}
              className="h-4 w-4 accent-muted-gold"
            />
            <span className="text-sm text-charcoal">{t(m)}</span>
          </label>
        ))}
      </div>
      {error && (
        <p className="mt-1.5 text-sm text-error" role="alert">
          {error}
        </p>
      )}
    </fieldset>
  );
}

// ---------------- CourierPicker ----------------

interface CourierPickerProps {
  value: Courier | undefined;
  onChange: (courier: Courier) => void;
  couriers: Courier[];
  error?: string;
}

function CourierPicker({ value, onChange, couriers, error }: CourierPickerProps) {
  const t = useTranslations("checkout.delivery.courier");

  return (
    <fieldset className="mb-6">
      <legend className="mb-2 block text-sm font-medium text-soft-brown">
        {t("label")} <span className="text-error">*</span>
      </legend>
      <div className="grid gap-3 sm:grid-cols-2" role="radiogroup" aria-label={t("label")}>
        {couriers.map((c) => (
          <label
            key={c}
            className={cn(
              "flex cursor-pointer flex-col items-start gap-1 rounded-brand border px-4 py-3 transition-colors",
              value === c
                ? "border-muted-gold bg-muted-gold/10"
                : "border-champagne-beige bg-warm-ivory hover:border-soft-brown/40"
            )}
          >
            <div className="flex items-center gap-3">
              <input
                type="radio"
                name="delivery-courier"
                value={c}
                checked={value === c}
                onChange={() => onChange(c)}
                className="h-4 w-4 accent-muted-gold"
              />
              <span className="font-medium text-charcoal">{t(c)}</span>
            </div>
          </label>
        ))}
      </div>
      {error && (
        <p className="mt-1.5 text-sm text-error" role="alert">
          {error}
        </p>
      )}
    </fieldset>
  );
}

// ---------------- OfficePicker ----------------

interface OfficePickerProps {
  courier: Courier;
  selectedOffice: OfficeResponse | null;
  onSelect: (office: OfficeResponse) => void;
  error?: string;
  locale: Locale;
}

interface EcontOfficeLocatorProps {
  city: string;
  config: EcontOfficeLocatorConfig;
  onSelect: (office: OfficeResponse) => void;
  onUnavailable: () => void;
}

function EcontOfficeLocator({ city, config, onSelect, onUnavailable }: EcontOfficeLocatorProps) {
  const t = useTranslations("checkout.delivery.office");
  const locale = useLocale();
  const [loading, setLoading] = useState(true);
  const allowedOriginsKey = config.allowedOrigins.join("|");

  const iframeSrc = useMemo(
    () => buildLocatorSrc(config.url, city, locale),
    [city, config.url, locale],
  );

  useEffect(() => {
    if (!config.enabled || typeof window === "undefined") return;
    const allowedOrigins = new Set(config.allowedOrigins);
    const handleMessage = (event: MessageEvent) => {
      if (!allowedOrigins.has(event.origin)) return;
      const office = normalizeEcontLocatorOfficeMessage(event.data);
      if (office) onSelect(office);
    };
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [allowedOriginsKey, config.allowedOrigins, config.enabled, onSelect]);

  return (
    <div className="mb-5 rounded-brand border border-champagne-beige bg-warm-ivory">
      <div className="flex items-center justify-between gap-3 border-b border-champagne-beige px-4 py-3">
        <p className="text-sm font-medium text-charcoal">{t("locatorTitle")}</p>
        <button
          type="button"
          onClick={onUnavailable}
          className="text-sm text-soft-brown underline hover:text-charcoal"
        >
          {t("locatorFallback")}
        </button>
      </div>
      <div className="relative h-[420px] overflow-hidden rounded-b-brand bg-champagne-beige/20">
        {loading && (
          <p className="absolute inset-x-0 top-4 text-center text-sm text-soft-brown">
            {t("locatorLoading")}
          </p>
        )}
        <iframe
          title={t("locatorFrameTitle")}
          src={iframeSrc}
          allow="geolocation"
          loading="lazy"
          onLoad={() => setLoading(false)}
          className="h-full w-full border-0"
        />
      </div>
    </div>
  );
}

function OfficePicker({ courier, selectedOffice, onSelect, error, locale }: OfficePickerProps) {
  const t = useTranslations("checkout.delivery.office");
  const tType = useTranslations("checkout.delivery.officeType");

  const [city, setCity] = useState("");
  const [citySuggestions, setCitySuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [offices, setOffices] = useState<OfficeResponse[]>([]);
  const [officeFilter, setOfficeFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState<OfficeType | "all">("all");
  const [loading, setLoading] = useState(false);
  const [confirmedCity, setConfirmedCity] = useState<string | null>(null);
  const [locatorUnavailable, setLocatorUnavailable] = useState(false);
  const [locatorConfig, setLocatorConfig] = useState<EcontOfficeLocatorConfig>(() =>
    buildEcontOfficeLocatorConfig(false, DEFAULT_ECONT_LOCATOR_URL, []),
  );
  const showLocator = courier === "econt" && locatorConfig.enabled && !locatorUnavailable;

  useEffect(() => {
    if (courier !== "econt") return;
    let cancelled = false;
    getDeliveryConfig()
      .then((config) => {
        if (!cancelled) setLocatorConfig(getEcontOfficeLocatorApiConfig(config));
      })
      .catch(() => {
        if (!cancelled) setLocatorConfig(getEcontOfficeLocatorEnvConfig());
      });
    return () => {
      cancelled = true;
    };
  }, [courier]);

  // Reset when courier changes
  useEffect(() => {
    setCity("");
    setConfirmedCity(null);
    setOffices([]);
    setCitySuggestions([]);
    setLocatorUnavailable(false);
  }, [courier]);

  // Load city suggestions as user types
  useEffect(() => {
    if (city.length < 1 || confirmedCity === city) {
      setCitySuggestions([]);
      return;
    }
    let cancelled = false;
    const t = setTimeout(async () => {
      try {
        const results = await getDeliveryCities(courier, city, locale);
        if (!cancelled) setCitySuggestions(results.slice(0, 10));
      } catch {
        if (!cancelled) setCitySuggestions([]);
      }
    }, 200);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [city, courier, confirmedCity, locale]);

  // Load offices when a city is confirmed
  useEffect(() => {
    if (!confirmedCity) {
      setOffices([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    getDeliveryOffices(courier, confirmedCity, undefined, locale)
      .then((res) => {
        if (!cancelled) setOffices(res);
      })
      .catch(() => {
        if (!cancelled) setOffices([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [confirmedCity, courier, locale]);

  const confirmCity = useCallback((c: string) => {
    setCity(c);
    setConfirmedCity(c);
    setShowSuggestions(false);
    setCitySuggestions([]);
  }, []);

  const filteredOffices = offices.filter((o) => {
    if (typeFilter !== "all" && o.type !== typeFilter) return false;
    if (officeFilter && !`${o.name} ${o.address}`.toLowerCase().includes(officeFilter.toLowerCase())) {
      return false;
    }
    return true;
  });

  // If an office is selected, show the confirmation card
  if (selectedOffice) {
    return (
      <div className="mb-6 rounded-brand border border-muted-gold bg-muted-gold/10 p-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-soft-brown">
              {t("selected")}
            </p>
            <p className="mt-1 font-medium text-charcoal">
              {selectedOffice.type === "apt" ? "🔐 " : "📦 "}
              {selectedOffice.name}
            </p>
            <p className="mt-0.5 text-sm text-soft-brown">
              {selectedOffice.address} · {selectedOffice.city}
            </p>
            <p className="mt-0.5 text-xs text-soft-brown">{selectedOffice.working_hours}</p>
            {selectedOffice.type === "apt" && (
              <p className="mt-1 text-xs italic text-soft-brown">{tType("lockerHint")}</p>
            )}
          </div>
          <button
            type="button"
            onClick={() => {
              onSelect({ ...selectedOffice, id: "" }); // Signals a clear; parent will handle
            }}
            className="text-sm text-soft-brown underline hover:text-charcoal"
          >
            {t("change")}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mb-6">
      {showLocator ? (
        <EcontOfficeLocator
          city={confirmedCity ?? city}
          config={locatorConfig}
          onSelect={onSelect}
          onUnavailable={() => setLocatorUnavailable(true)}
        />
      ) : (
        <>
          {locatorUnavailable && (
            <p className="mb-3 text-sm text-soft-brown">{t("locatorUnavailable")}</p>
          )}
          {/* City input with typeahead */}
          <label className="mb-1.5 block text-sm font-medium text-soft-brown">
            {t("cityLabel")} <span className="text-error">*</span>
          </label>
          <div className="relative mb-4">
            <input
              type="text"
              value={city}
              onChange={(e) => {
                setCity(e.target.value);
                setConfirmedCity(null);
                setShowSuggestions(true);
              }}
              onFocus={() => setShowSuggestions(true)}
              onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
              placeholder={t("cityPlaceholder")}
              className="w-full rounded-brand border border-champagne-beige bg-warm-ivory px-4 py-3 text-charcoal focus:outline-none focus:ring-2 focus:ring-soft-brown"
            />
            {showSuggestions && citySuggestions.length > 0 && (
              <ul className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-brand border border-champagne-beige bg-warm-ivory shadow-lg">
                {citySuggestions.map((c) => (
                  <li key={c}>
                    <button
                      type="button"
                      onClick={() => confirmCity(c)}
                      className="block w-full px-4 py-2 text-left text-sm text-charcoal hover:bg-champagne-beige/30"
                    >
                      {c}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {!confirmedCity ? (
            <p className="text-sm italic text-soft-brown">{t("selectCityFirst")}</p>
          ) : (
            <>
              {/* Type filter */}
              <div className="mb-3 flex gap-2" role="tablist">
                {(["all", "office", "apt"] as const).map((f) => (
                  <button
                    key={f}
                    type="button"
                    onClick={() => setTypeFilter(f)}
                    className={cn(
                      "rounded-pill px-3 py-1 text-xs font-medium transition-colors",
                      typeFilter === f
                        ? "bg-muted-gold text-charcoal"
                        : "bg-champagne-beige/50 text-soft-brown hover:bg-champagne-beige"
                    )}
                    aria-pressed={typeFilter === f}
                  >
                    {tType(f)}
                  </button>
                ))}
              </div>

              {/* Search filter */}
              <input
                type="text"
                value={officeFilter}
                onChange={(e) => setOfficeFilter(e.target.value)}
                placeholder={t("searchPlaceholder")}
                aria-label={t("searchLabel")}
                className="mb-3 w-full rounded-brand border border-champagne-beige bg-warm-ivory px-4 py-2 text-sm text-charcoal focus:outline-none focus:ring-2 focus:ring-soft-brown"
              />

              {/* Office list */}
              {loading ? (
                <p className="text-sm text-soft-brown">{t("loading")}</p>
              ) : filteredOffices.length === 0 ? (
                <p className="text-sm text-soft-brown">{t("empty")}</p>
              ) : (
                <ul className="max-h-72 divide-y divide-champagne-beige overflow-auto rounded-brand border border-champagne-beige">
                  {filteredOffices.map((office) => (
                    <li key={office.id}>
                      <button
                        type="button"
                        onClick={() => onSelect(office)}
                        className="block w-full px-4 py-3 text-left transition-colors hover:bg-champagne-beige/30"
                      >
                        <p className="text-sm font-medium text-charcoal">
                          {office.type === "apt" ? "🔐 " : "📦 "}
                          {office.name}
                        </p>
                        <p className="mt-0.5 text-xs text-soft-brown">
                          {office.address} · {office.working_hours}
                        </p>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </>
      )}

      {error && (
        <p className="mt-2 text-sm text-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

// ---------------- DoorAddressForm ----------------

interface DoorAddressFormProps {
  value: Partial<DeliveryDoor>;
  onChange: (patch: Partial<DeliveryDoor>) => void;
  errors: DeliveryValidationErrors;
  locale: Locale;
}

function DoorAddressForm({ value, onChange, errors, locale }: DoorAddressFormProps) {
  const t = useTranslations("checkout.delivery.door");
  const courier = value.courier ?? "speedy";

  const field = (
    key: "city" | "postalCode" | "street" | "building" | "apartment",
    fieldKey: keyof DeliveryDoor,
    required: boolean,
    errorKey?: keyof DeliveryValidationErrors,
    readOnly = false,
  ) => {
    const err = errorKey ? errors[errorKey] : undefined;
    const inputId = `delivery-door-${fieldKey.replace(/_/g, "-")}`;
    const errorId = `${inputId}-error`;
    return (
      <div className="mb-4">
        <label htmlFor={inputId} className="mb-1.5 block text-sm font-medium text-soft-brown">
          {t(`${key}Label`)}
          {required && <span className="text-error"> *</span>}
        </label>
        <input
          id={inputId}
          type="text"
          value={(value[fieldKey] as string | null | undefined) ?? ""}
          onChange={(e) => onChange({ [fieldKey]: e.target.value })}
          placeholder={t(`${key}Placeholder`)}
          readOnly={readOnly}
          maxLength={
            fieldKey === "street"
              ? 200
              : fieldKey === "postal_code"
                ? 10
                : fieldKey === "building" || fieldKey === "apartment"
                  ? 50
                  : 100
          }
          aria-invalid={err ? "true" : undefined}
          aria-describedby={err ? errorId : undefined}
          className={cn(
            "w-full rounded-brand border bg-warm-ivory px-4 py-3 text-charcoal focus:outline-none focus:ring-2 focus:ring-soft-brown",
            readOnly && "cursor-not-allowed opacity-70",
            err ? "border-error" : "border-champagne-beige"
          )}
        />
        {err && (
          <p id={errorId} className="mt-1 text-sm text-error" role="alert">
            {err}
          </p>
        )}
      </div>
    );
  };

  return (
    <div className="mb-6">
      <DoorPlaceField
        courier={courier}
        locale={locale}
        city={value.city ?? ""}
        postalCode={value.postal_code ?? ""}
        onSelect={(place) =>
          onChange({ city: place.name, postal_code: place.postal_code ?? "" })
        }
        onPostalCodeChange={(postal_code) => onChange({ postal_code })}
        error={errors.city}
        postalCodeError={errors.postalCode}
      />
      {field("street", "street", true, "street")}
      <div className="grid gap-4 sm:grid-cols-2">
        {field("building", "building", false)}
        {field("apartment", "apartment", false)}
      </div>
    </div>
  );
}

// ---------------- DoorPlaceField ----------------

interface DoorPlaceFieldProps {
  courier: Courier;
  locale: Locale;
  city: string;
  postalCode: string;
  onSelect: (place: CityPlace) => void;
  onPostalCodeChange: (postalCode: string) => void;
  error?: string;
  postalCodeError?: string;
}

// Debounced place typeahead for courier door delivery — mirrors the OfficePicker
// city typeahead but consumes getDeliveryPlaces so suggestions carry region +
// postcode. Selecting a place autofills a read-only postcode; ambiguous towns
// (e.g. three "Садово") appear as distinct "name — region" rows.
function DoorPlaceField({
  courier,
  locale,
  city,
  postalCode,
  onSelect,
  onPostalCodeChange,
  error,
  postalCodeError,
}: DoorPlaceFieldProps) {
  const t = useTranslations("checkout.delivery.door");
  const [query, setQuery] = useState(city);
  const [suggestions, setSuggestions] = useState<CityPlace[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [confirmed, setConfirmed] = useState<string | null>(city || null);
  const [postalCodeLocked, setPostalCodeLocked] = useState(Boolean(postalCode));

  useEffect(() => {
    if (query.length < 1 || confirmed === query) {
      setSuggestions([]);
      return;
    }
    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const results = await getDeliveryPlaces(courier, query, locale);
        if (!cancelled) setSuggestions(results.slice(0, 10));
      } catch {
        if (!cancelled) setSuggestions([]);
      }
    }, 200);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query, courier, confirmed, locale]);

  const confirmPlace = (place: CityPlace) => {
    setQuery(place.name);
    setConfirmed(place.name);
    setPostalCodeLocked(Boolean(place.postal_code));
    setShowSuggestions(false);
    onSelect(place);
  };

  return (
    <>
      <div className="mb-4">
        <label htmlFor="delivery-door-city" className="mb-1.5 block text-sm font-medium text-soft-brown">
          {t("cityLabel")} <span className="text-error">*</span>
        </label>
        <div className="relative">
          <input
            id="delivery-door-city"
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setConfirmed(null);
              setPostalCodeLocked(false);
              setShowSuggestions(true);
            }}
            onFocus={() => setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
            placeholder={t("cityPlaceholder")}
            maxLength={100}
            aria-invalid={error ? "true" : undefined}
            aria-describedby={error ? "delivery-door-city-error" : undefined}
            className={cn(
              "w-full rounded-brand border bg-warm-ivory px-4 py-3 text-charcoal focus:outline-none focus:ring-2 focus:ring-soft-brown",
              error ? "border-error" : "border-champagne-beige"
            )}
          />
          {showSuggestions && suggestions.length > 0 && (
            <ul className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-brand border border-champagne-beige bg-warm-ivory shadow-lg">
              {suggestions.map((place) => (
                <li key={`${place.name}-${place.postal_code}`}>
                  <button
                    type="button"
                    onClick={() => confirmPlace(place)}
                    className="block w-full px-4 py-2 text-left text-sm text-charcoal hover:bg-champagne-beige/30"
                  >
                    {place.region ? `${place.name} — ${place.region}` : place.name}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        {error && (
          <p id="delivery-door-city-error" className="mt-1 text-sm text-error" role="alert">
            {error}
          </p>
        )}
      </div>
      <div className="mb-4">
        <label htmlFor="delivery-door-postal-code" className="mb-1.5 block text-sm font-medium text-soft-brown">
          {t("postalCodeLabel")} <span className="text-error">*</span>
        </label>
        <input
          id="delivery-door-postal-code"
          type="text"
          value={postalCode}
          readOnly={postalCodeLocked}
          onChange={(e) => onPostalCodeChange(e.target.value)}
          placeholder={t("postalCodePlaceholder")}
          aria-invalid={postalCodeError ? "true" : undefined}
          aria-describedby={postalCodeError ? "delivery-door-postal-code-error" : undefined}
          className={cn(
            "w-full rounded-brand border bg-warm-ivory px-4 py-3 text-charcoal focus:outline-none focus:ring-2 focus:ring-soft-brown",
            postalCodeError ? "border-error" : "border-champagne-beige",
            postalCodeLocked && "cursor-not-allowed opacity-70 focus:ring-0"
          )}
        />
        {postalCodeError && (
          <p id="delivery-door-postal-code-error" className="mt-1 text-sm text-error" role="alert">
            {postalCodeError}
          </p>
        )}
      </div>
    </>
  );
}

// ---------------- PhoneField ----------------

interface PhoneFieldProps {
  value: string;
  onChange: (phone: string) => void;
  error?: string;
}

function PhoneField({ value, onChange, error }: PhoneFieldProps) {
  const t = useTranslations("checkout.delivery");
  return (
    <div className="mb-6">
      <label className="mb-1.5 block text-sm font-medium text-soft-brown">
        {t("phoneLabel")} <span className="text-error">*</span>
      </label>
      <input
        type="tel"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={t("phonePlaceholder")}
        aria-invalid={error ? "true" : undefined}
        className={cn(
          "w-full rounded-brand border bg-warm-ivory px-4 py-3 text-charcoal focus:outline-none focus:ring-2 focus:ring-soft-brown",
          error ? "border-error" : "border-champagne-beige"
        )}
      />
      {error && (
        <p className="mt-1 text-sm text-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

// ---------------- Main DeliverySection ----------------

export function DeliverySection({
  value,
  onChange,
  errors = {},
  deliverySettings = null,
}: DeliverySectionProps) {
  const t = useTranslations("checkout.delivery");
  const locale = useLocale() as Locale;
  const method = value.method;
  const office = value.office ?? undefined;
  const door = value.door ?? undefined;
  const availableMethods = useMemo(
    () => ALL_METHODS.filter((m) => availableCouriersForMethod(deliverySettings, m).length > 0),
    [deliverySettings],
  );
  const availableCouriers = useMemo(
    () => (method ? availableCouriersForMethod(deliverySettings, method) : []),
    [deliverySettings, method],
  );
  // Courier lives inside office/door — track it at the section level for progressive disclosure
  const currentCourier: Courier | undefined = office?.courier ?? door?.courier;

  // Remember the full OfficeResponse (city/address/working_hours) for the selected office.
  // The checkout payload only stores the id/name/type/courier/phone the backend needs,
  // so we cache display fields here to keep the "selected" card populated after selection.
  const [selectedOfficeFull, setSelectedOfficeFull] = useState<OfficeResponse | null>(null);

  useEffect(() => {
    if (!method) return;
    if (!availableMethods.includes(method)) {
      const nextMethod = availableMethods[0];
      setSelectedOfficeFull(null);
      onChange(nextMethod ? { method: nextMethod, office: null, door: null } : {});
      return;
    }
    if (currentCourier && !availableCouriers.includes(currentCourier)) {
      const nextCourier = availableCouriers[0];
      setSelectedOfficeFull(null);
      if (!nextCourier) {
        onChange({ method, office: null, door: null });
      } else if (method === "office") {
        onChange({
          ...value,
          office: { courier: nextCourier, phone: office?.phone ?? "" } as DeliveryOffice,
          door: null,
        });
      } else {
        onChange({
          ...value,
          door: { ...(door ?? {}), courier: nextCourier } as DeliveryDoor,
          office: null,
        });
      }
    }
  }, [
    availableCouriers,
    availableMethods,
    currentCourier,
    door,
    method,
    office?.phone,
    onChange,
    value,
  ]);

  const setMethod = (m: DeliveryMethod) => {
    if (m === value.method) return;
    // Reset sub-state on method change
    setSelectedOfficeFull(null);
    onChange({ method: m, office: null, door: null });
  };

  const setCourier = (c: Courier) => {
    if (method === "office") {
      // Preserve phone across courier change; drop office_id/name/type since
      // the selected office belonged to the previous courier. The rest of the
      // component treats a missing office_id as "not yet selected" — see the
      // `selectedOffice` derivation below.
      const preservedPhone = office?.phone ?? "";
      const next: Partial<DeliveryOffice> =
        office?.courier === c
          ? { ...office, courier: c }
          : { courier: c, phone: preservedPhone };
      if (office?.courier !== c) setSelectedOfficeFull(null);
      onChange({ ...value, office: next as DeliveryOffice, door: null });
    } else if (method === "door") {
      onChange({ ...value, door: { ...(door ?? {}), courier: c } as DeliveryDoor, office: null });
    }
  };

  const selectOffice = (o: OfficeResponse) => {
    // "Change" button signals a clear by passing an office with empty id
    if (!o.id) {
      setSelectedOfficeFull(null);
      onChange({
        ...value,
        office: {
          courier: currentCourier ?? "speedy",
          office_id: "",
          office_code: null,
          office_name: "",
          office_type: "office",
          city: "",
          phone: office?.phone ?? "",
        },
      });
      return;
    }
    setSelectedOfficeFull(o);
    onChange({
      ...value,
      office: {
        courier: currentCourier ?? "speedy",
        office_id: o.id,
        office_code: o.code ?? null,
        office_name: o.name,
        office_type: o.type,
        city: o.city,
        phone: office?.phone ?? "",
      },
    });
  };

  const patchDoor = (patch: Partial<DeliveryDoor>) => {
    onChange({
      ...value,
      door: { ...(door ?? { courier: currentCourier ?? "speedy" }), ...patch } as DeliveryDoor,
    });
  };

  const setPhone = (phone: string) => {
    if (method === "office" && office) {
      onChange({ ...value, office: { ...office, phone } });
    } else if (method === "door" && door) {
      onChange({ ...value, door: { ...door, phone } });
    }
  };

  const phone = method === "office" ? office?.phone ?? "" : door?.phone ?? "";
  // Prefer the cached full record if its id still matches the payload; otherwise
  // fall back to a payload-only reconstruction so a page reload doesn't lose
  // the selected state (address/city/hours will simply be blank until re-picked).
  const selectedOffice: OfficeResponse | null =
    method === "office" && office?.office_id
      ? selectedOfficeFull && selectedOfficeFull.id === office.office_id
          ? selectedOfficeFull
        : {
            id: office.office_id,
            code: office.office_code ?? null,
            name: office.office_name,
            type: office.office_type,
            city: office.city ?? "",
            address: "",
            working_hours: "",
          }
      : null;

  return (
    <section className="mb-8">
      <h2 className="mb-4 font-heading text-xl text-text">{t("sectionTitle")}</h2>

      {availableMethods.length === 0 ? (
        <p className="mb-6 rounded-brand border border-error/20 bg-error/10 px-4 py-3 text-sm text-error">
          {t("unavailable")}
        </p>
      ) : (
        <DeliveryMethodSelector
          value={method}
          onChange={setMethod}
          methods={availableMethods}
          error={errors.method}
        />
      )}

      {method && (
        <CourierPicker
          value={currentCourier}
          onChange={setCourier}
          couriers={availableCouriers}
          error={errors.courier}
        />
      )}

      {method === "office" && currentCourier && (
        <OfficePicker
          courier={currentCourier}
          selectedOffice={selectedOffice}
          onSelect={selectOffice}
          error={errors.office}
          locale={locale}
        />
      )}

      {method === "door" && currentCourier && (
        <DoorAddressForm value={door ?? { courier: currentCourier }} onChange={patchDoor} errors={errors} locale={locale} />
      )}

      {method && currentCourier && (method !== "office" || selectedOffice) && (
        <PhoneField value={phone} onChange={setPhone} error={errors.phone} />
      )}
    </section>
  );
}

// ---------------- Validation ----------------

export function validateDelivery(
  delivery: Partial<DeliveryInfo>,
  t: (key: string) => string,
): { valid: boolean; errors: DeliveryValidationErrors; normalized?: DeliveryInfo } {
  const errors: DeliveryValidationErrors = {};

  if (!delivery.method) {
    errors.method = t("checkout.delivery.method.required");
    return { valid: false, errors };
  }

  if (delivery.method === "office") {
    const o = delivery.office;
    if (!o?.courier) {
      errors.courier = t("checkout.delivery.courier.required");
    }
    if (!o?.office_id) {
      errors.office = t("checkout.delivery.office.required");
    } else if (o.courier === "econt" && !o.office_code) {
      errors.office = t("checkout.delivery.office.econtOfficeCodeRequired");
    }
    const normalizedOfficePhone = o?.phone ? normalizePhone(o.phone) : "";
    if (!o?.phone) {
      errors.phone = t("checkout.delivery.phoneRequired");
    } else if (!PHONE_REGEX.test(normalizedOfficePhone)) {
      errors.phone = t("checkout.delivery.phoneInvalid");
    }
    if (Object.keys(errors).length > 0) return { valid: false, errors };
    return {
      valid: true,
      errors: {},
      normalized: {
        method: "office",
        office: { ...(o as DeliveryOffice), phone: normalizedOfficePhone },
        door: null,
      },
    };
  }

  // door
  const d = delivery.door;
  if (!d?.courier) {
    errors.courier = t("checkout.delivery.courier.required");
  }
  if (!d?.city) errors.city = t("checkout.delivery.door.cityRequired");
  if (!d?.postal_code) errors.postalCode = t("checkout.delivery.door.postalCodeRequired");
  if (!d?.street) errors.street = t("checkout.delivery.door.streetRequired");
  const normalizedDoorPhone = d?.phone ? normalizePhone(d.phone) : "";
  if (!d?.phone) {
    errors.phone = t("checkout.delivery.phoneRequired");
  } else if (!PHONE_REGEX.test(normalizedDoorPhone)) {
    errors.phone = t("checkout.delivery.phoneInvalid");
  }
  if (Object.keys(errors).length > 0) return { valid: false, errors };
  return {
    valid: true,
    errors: {},
    normalized: {
      method: "door",
      door: {
        courier: d!.courier!,
        city: d!.city!,
        postal_code: d!.postal_code!,
        street: d!.street!,
        building: d!.building || null,
        apartment: d!.apartment || null,
        phone: normalizedDoorPhone,
      },
      office: null,
    },
  };
}
