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

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { getDeliveryCities, getDeliveryOffices } from "@/lib/api";
import { cn } from "@/lib/utils";
import type {
  Courier,
  DeliveryDoor,
  DeliveryInfo,
  DeliveryMethod,
  DeliveryOffice,
  OfficeResponse,
  OfficeType,
} from "@/lib/types";

const PHONE_REGEX = /^\+?[0-9]{8,15}$/;

/**
 * Normalize phone input to match backend validation (app/models/delivery.py).
 * Strip everything except digits and a leading '+' before regex-testing,
 * so conventionally-formatted numbers (e.g. "+359 888 123 456", "(0888) 123 456")
 * pass client-side just like they do server-side.
 */
function normalizePhone(value: string): string {
  return value.replace(/[^\d+]/g, "");
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
}

// ---------------- DeliveryMethodSelector ----------------

interface DeliveryMethodSelectorProps {
  value: DeliveryMethod | undefined;
  onChange: (method: DeliveryMethod) => void;
  error?: string;
}

function DeliveryMethodSelector({ value, onChange, error }: DeliveryMethodSelectorProps) {
  const t = useTranslations("checkout.delivery.method");
  const methods: DeliveryMethod[] = ["office", "door"];

  return (
    <fieldset className="mb-6">
      <legend className="mb-2 block text-sm font-medium text-soft-brown">
        {t("label")} <span className="text-red-700">*</span>
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
        <p className="mt-1.5 text-sm text-red-700" role="alert">
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
  error?: string;
}

function CourierPicker({ value, onChange, error }: CourierPickerProps) {
  const t = useTranslations("checkout.delivery.courier");
  const couriers: Courier[] = ["speedy", "econt"];

  return (
    <fieldset className="mb-6">
      <legend className="mb-2 block text-sm font-medium text-soft-brown">
        {t("label")} <span className="text-red-700">*</span>
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
        <p className="mt-1.5 text-sm text-red-700" role="alert">
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
}

function OfficePicker({ courier, selectedOffice, onSelect, error }: OfficePickerProps) {
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

  // Reset when courier changes
  useEffect(() => {
    setCity("");
    setConfirmedCity(null);
    setOffices([]);
    setCitySuggestions([]);
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
        const results = await getDeliveryCities(courier, city);
        if (!cancelled) setCitySuggestions(results.slice(0, 10));
      } catch {
        if (!cancelled) setCitySuggestions([]);
      }
    }, 200);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [city, courier, confirmedCity]);

  // Load offices when a city is confirmed
  useEffect(() => {
    if (!confirmedCity) {
      setOffices([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    getDeliveryOffices(courier, confirmedCity)
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
  }, [confirmedCity, courier]);

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
      {/* City input with typeahead */}
      <label className="mb-1.5 block text-sm font-medium text-soft-brown">
        {t("cityLabel")} <span className="text-red-700">*</span>
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

      {error && (
        <p className="mt-2 text-sm text-red-700" role="alert">
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
}

function DoorAddressForm({ value, onChange, errors }: DoorAddressFormProps) {
  const t = useTranslations("checkout.delivery.door");

  const field = (
    key: "city" | "postalCode" | "street" | "building" | "apartment",
    fieldKey: keyof DeliveryDoor,
    required: boolean,
    errorKey?: keyof DeliveryValidationErrors,
  ) => {
    const err = errorKey ? errors[errorKey] : undefined;
    return (
      <div className="mb-4">
        <label className="mb-1.5 block text-sm font-medium text-soft-brown">
          {t(`${key}Label`)}
          {required && <span className="text-red-700"> *</span>}
        </label>
        <input
          type="text"
          value={(value[fieldKey] as string | null | undefined) ?? ""}
          onChange={(e) => onChange({ [fieldKey]: e.target.value })}
          placeholder={t(`${key}Placeholder`)}
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
          className={cn(
            "w-full rounded-brand border bg-warm-ivory px-4 py-3 text-charcoal focus:outline-none focus:ring-2 focus:ring-soft-brown",
            err ? "border-red-700" : "border-champagne-beige"
          )}
        />
        {err && (
          <p className="mt-1 text-sm text-red-700" role="alert">
            {err}
          </p>
        )}
      </div>
    );
  };

  return (
    <div className="mb-6">
      {field("city", "city", true, "city")}
      {field("postalCode", "postal_code", true, "postalCode")}
      {field("street", "street", true, "street")}
      <div className="grid gap-4 sm:grid-cols-2">
        {field("building", "building", false)}
        {field("apartment", "apartment", false)}
      </div>
    </div>
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
        {t("phoneLabel")} <span className="text-red-700">*</span>
      </label>
      <input
        type="tel"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={t("phonePlaceholder")}
        aria-invalid={error ? "true" : undefined}
        className={cn(
          "w-full rounded-brand border bg-warm-ivory px-4 py-3 text-charcoal focus:outline-none focus:ring-2 focus:ring-soft-brown",
          error ? "border-red-700" : "border-champagne-beige"
        )}
      />
      {error && (
        <p className="mt-1 text-sm text-red-700" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

// ---------------- Main DeliverySection ----------------

export function DeliverySection({ value, onChange, errors = {} }: DeliverySectionProps) {
  const t = useTranslations("checkout.delivery");
  const method = value.method;
  const office = value.office ?? undefined;
  const door = value.door ?? undefined;
  // Courier lives inside office/door — track it at the section level for progressive disclosure
  const currentCourier: Courier | undefined = office?.courier ?? door?.courier;

  // Remember the full OfficeResponse (city/address/working_hours) for the selected office.
  // The checkout payload only stores the id/name/type/courier/phone the backend needs,
  // so we cache display fields here to keep the "selected" card populated after selection.
  const [selectedOfficeFull, setSelectedOfficeFull] = useState<OfficeResponse | null>(null);

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
        office: { courier: currentCourier ?? "speedy", office_id: "", office_name: "", office_type: "office", phone: office?.phone ?? "" },
      });
      return;
    }
    setSelectedOfficeFull(o);
    onChange({
      ...value,
      office: {
        courier: currentCourier ?? "speedy",
        office_id: o.id,
        office_name: o.name,
        office_type: o.type,
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
            name: office.office_name,
            type: office.office_type,
            city: "",
            address: "",
            working_hours: "",
          }
      : null;

  return (
    <section className="mb-8">
      <h2 className="mb-4 font-heading text-xl text-charcoal">{t("sectionTitle")}</h2>

      <DeliveryMethodSelector value={method} onChange={setMethod} error={errors.method} />

      {method && (
        <CourierPicker value={currentCourier} onChange={setCourier} error={errors.courier} />
      )}

      {method === "office" && currentCourier && (
        <OfficePicker
          courier={currentCourier}
          selectedOffice={selectedOffice}
          onSelect={selectOffice}
          error={errors.office}
        />
      )}

      {method === "door" && currentCourier && (
        <DoorAddressForm value={door ?? { courier: currentCourier }} onChange={patchDoor} errors={errors} />
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
