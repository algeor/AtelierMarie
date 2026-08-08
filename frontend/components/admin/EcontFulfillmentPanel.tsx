"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  createAndShipEcontOrder,
  createEcontLabel,
  deleteEcontLabel,
  getEcontOrderReadiness,
  repairEcontOrder,
  refreshEcontTrace,
  syncEcontOrder,
  updateOrderStatus,
} from "@/lib/api";
import { ApiError } from "@/lib/api-client";
import { DeleteIconButton } from "@/components/ui/DeleteIconButton";
import { useLocalizedError } from "@/lib/useLocalizedError";
import { cn } from "@/lib/utils";
import type { EcontOrderFulfillmentResponse, OrderResponse } from "@/lib/types";

interface EcontFulfillmentPanelProps {
  order: OrderResponse;
  onRefreshOrder: () => Promise<void>;
}

type ActionKey =
  | "validate"
  | "repair"
  | "sync"
  | "create"
  | "createShip"
  | "delete"
  | "trace"
  | "ship";

const BLOCKER_KEYS: Record<string, string> = {
  settings_disabled: "settingsDisabled",
  settings_private_key_missing: "privateKeyMissing",
  settings_shop_id_missing: "shopIdMissing",
  settings_sender_office_code_missing: "senderOfficeMissing",
  order_not_econt: "orderNotEcont",
  order_office_code_missing: "officeCodeMissing",
  order_recipient_phone_missing: "phoneMissing",
  order_status_not_supported: "statusNotSupported",
};

export function EcontFulfillmentPanel({ order, onRefreshOrder }: EcontFulfillmentPanelProps) {
  const t = useTranslations("admin.econtFulfillment");
  const getLocalizedError = useLocalizedError();
  const [state, setState] = useState<EcontOrderFulfillmentResponse | null>(null);
  const [loadingState, setLoadingState] = useState(true);
  const [action, setAction] = useState<ActionKey | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [repairOfficeCode, setRepairOfficeCode] = useState("");
  const [repairPhone, setRepairPhone] = useState("");
  const [repairPackCount, setRepairPackCount] = useState("");
  const [repairDescription, setRepairDescription] = useState("");
  const [repairPaymentSide, setRepairPaymentSide] = useState<"" | "sender" | "receiver">("");

  useEffect(() => {
    const details = (order.delivery_details ?? {}) as Record<string, unknown>;
    const overrides = (details.econt_overrides ?? {}) as Record<string, unknown>;
    setRepairOfficeCode(typeof details.office_code === "string" ? details.office_code : "");
    setRepairPhone(typeof details.phone === "string" ? details.phone : "");
    setRepairPackCount(
      typeof overrides.pack_count === "number" ? String(overrides.pack_count) : "",
    );
    setRepairDescription(
      typeof overrides.shipment_description === "string" ? overrides.shipment_description : "",
    );
    setRepairPaymentSide(
      overrides.payment_side === "sender" || overrides.payment_side === "receiver"
        ? overrides.payment_side
        : "",
    );
  }, [order.delivery_details]);

  async function loadReadiness() {
    setLoadingState(true);
    setError(null);
    try {
      const data = await getEcontOrderReadiness(order.id);
      setState(data);
    } catch (err) {
      setError(err instanceof ApiError ? getLocalizedError(err.code) : t("loadError"));
    } finally {
      setLoadingState(false);
    }
  }

  useEffect(() => {
    loadReadiness();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [order.id, order.courier_shipment_number, order.courier_sync_status]);

  async function runAction(key: ActionKey, fn: () => Promise<unknown>) {
    setAction(key);
    setError(null);
    setMessage(null);
    try {
      await fn();
      await onRefreshOrder();
      await loadReadiness();
      setMessage(t(`success.${key}`));
    } catch (err) {
      setError(err instanceof ApiError ? getLocalizedError(err.code) : t("actionError"));
    } finally {
      setAction(null);
    }
  }

  if (order.delivery_courier !== "econt") {
    return (
      <section className="mt-8 border-t border-champagne-beige pt-6">
        <h2 className="mb-2 text-sm font-medium text-charcoal">{t("title")}</h2>
        <p className="text-sm text-soft-brown">{t("notEligible")}</p>
      </section>
    );
  }

  const shipmentNumber = state?.courier_shipment_number ?? order.courier_shipment_number ?? null;
  const labelUrl = state?.courier_label_url ?? null;
  const trackingUrl = state?.tracking_url ?? order.tracking_url ?? null;
  const ready = Boolean(state?.ready);
  const canDelete = Boolean(shipmentNumber) && !["shipped", "delivered"].includes(order.status);
  const canMarkShipped = order.status === "confirmed" && Boolean(shipmentNumber);
  const canCreateAndShip = order.status === "confirmed" && ready && !shipmentNumber;
  const canRepair = !shipmentNumber && !action;

  async function applyRepair() {
    await runAction("repair", () =>
      repairEcontOrder(order.id, {
        office_code: repairOfficeCode.trim() || null,
        recipient_phone: repairPhone.trim() || null,
        pack_count: repairPackCount ? Number(repairPackCount) : null,
        shipment_description: repairDescription.trim() || null,
        payment_side: repairPaymentSide || null,
      }),
    );
  }

  return (
    <section className="mt-8 border-t border-champagne-beige pt-6">
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-sm font-medium text-charcoal">{t("title")}</h2>
          <p className="mt-1 text-xs text-soft-brown">
            {loadingState ? t("checking") : ready ? t("ready") : t("blocked")}
          </p>
        </div>
        <button
          type="button"
          onClick={() => runAction("validate", loadReadiness)}
          disabled={Boolean(action)}
          className="rounded-brand border border-champagne-beige bg-warm-ivory px-3 py-2 text-sm text-charcoal hover:bg-champagne-beige/40 disabled:opacity-50"
        >
          {action === "validate" ? t("working") : t("actions.validate")}
        </button>
      </div>

      {(message || error) && (
        <div
          className={cn(
            "mb-4 rounded-brand border p-3 text-sm",
            message ? "border-green-200 bg-green-50 text-green-800" : "border-red-200 bg-red-50 text-red-700",
          )}
          role="status"
        >
          {message ?? error}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[1fr_1.2fr]">
        <div className="rounded-brand border border-champagne-beige bg-warm-ivory p-4">
          <h3 className="mb-3 text-xs font-semibold uppercase text-soft-brown">
            {t("readiness")}
          </h3>
          {loadingState ? (
            <p className="text-sm text-soft-brown">{t("checking")}</p>
          ) : state?.blockers.length ? (
            <ul className="space-y-2 text-sm text-soft-brown">
              {state.blockers.map((blocker) => (
                <li key={blocker} className="flex gap-2">
                  <span className="text-amber-700">!</span>
                  <span>{t(`blockers.${BLOCKER_KEYS[blocker] ?? "unknown"}`)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-green-700">{t("readyChecklist")}</p>
          )}
        </div>

        <div className="rounded-brand border border-champagne-beige bg-warm-ivory p-4">
          <h3 className="mb-3 text-xs font-semibold uppercase text-soft-brown">
            {t("shipment")}
          </h3>
          <dl className="grid grid-cols-1 gap-x-4 gap-y-2 text-sm sm:grid-cols-[max-content_minmax(0,1fr)]">
            <dt className="text-soft-brown">{t("fields.syncStatus")}</dt>
            <dd className="min-w-0 break-words text-charcoal">{state?.courier_sync_status ?? t("empty")}</dd>
            <dt className="text-soft-brown">{t("fields.courierStatus")}</dt>
            <dd className="min-w-0 break-words text-charcoal">{order.courier_status ?? t("empty")}</dd>
            <dt className="text-soft-brown">{t("fields.shipmentNumber")}</dt>
            <dd className="min-w-0 break-words font-mono text-charcoal">{shipmentNumber ?? t("empty")}</dd>
            <dt className="text-soft-brown">{t("fields.lastSync")}</dt>
            <dd className="min-w-0 break-words text-charcoal">{state?.courier_last_synced_at ?? t("empty")}</dd>
            {state?.courier_last_error && (
              <>
                <dt className="text-soft-brown">{t("fields.lastError")}</dt>
                <dd className="min-w-0 break-words text-red-700">{state.courier_last_error}</dd>
              </>
            )}
          </dl>
          <div className="mt-3 flex flex-wrap gap-3">
            {labelUrl && (
              <a className="text-sm font-medium text-muted-gold underline" href={labelUrl} target="_blank" rel="noopener noreferrer">
                {t("actions.openLabel")}
              </a>
            )}
            {trackingUrl && (
              <a className="text-sm font-medium text-muted-gold underline" href={trackingUrl} target="_blank" rel="noopener noreferrer">
                {t("actions.openTracking")}
              </a>
            )}
          </div>
        </div>
      </div>

      <div className="mt-4 rounded-brand border border-champagne-beige bg-warm-ivory p-4">
        <h3 className="mb-3 text-xs font-semibold uppercase text-soft-brown">
          {t("repair.title")}
        </h3>
        <div className="grid gap-3 md:grid-cols-4">
          {order.delivery_method === "office" && (
            <label className="text-sm">
              <span className="mb-1 block text-soft-brown">{t("repair.officeCode")}</span>
              <input
                value={repairOfficeCode}
                onChange={(event) => setRepairOfficeCode(event.target.value)}
                disabled={!canRepair}
                className="w-full rounded-brand border border-champagne-beige bg-cream px-3 py-2 text-charcoal disabled:opacity-60"
              />
            </label>
          )}
          <label className="text-sm">
            <span className="mb-1 block text-soft-brown">{t("repair.recipientPhone")}</span>
            <input
              value={repairPhone}
              onChange={(event) => setRepairPhone(event.target.value)}
              disabled={!canRepair}
              className="w-full rounded-brand border border-champagne-beige bg-cream px-3 py-2 text-charcoal disabled:opacity-60"
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-soft-brown">{t("repair.packCount")}</span>
            <input
              type="number"
              min={1}
              max={99}
              value={repairPackCount}
              onChange={(event) => setRepairPackCount(event.target.value)}
              disabled={!canRepair}
              className="w-full rounded-brand border border-champagne-beige bg-cream px-3 py-2 text-charcoal disabled:opacity-60"
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-soft-brown">{t("repair.description")}</span>
            <input
              value={repairDescription}
              onChange={(event) => setRepairDescription(event.target.value)}
              disabled={!canRepair}
              className="w-full rounded-brand border border-champagne-beige bg-cream px-3 py-2 text-charcoal disabled:opacity-60"
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-soft-brown">{t("repair.paymentSide")}</span>
            <select
              value={repairPaymentSide}
              onChange={(event) => setRepairPaymentSide(event.target.value as "" | "sender" | "receiver")}
              disabled={!canRepair}
              className="w-full rounded-brand border border-champagne-beige bg-cream px-3 py-2 text-charcoal disabled:opacity-60"
            >
              <option value="">{t("repair.useDefault")}</option>
              <option value="sender">{t("repair.sender")}</option>
              <option value="receiver">{t("repair.receiver")}</option>
            </select>
          </label>
        </div>
        <button
          type="button"
          onClick={applyRepair}
          disabled={!canRepair}
          className="mt-3 rounded-brand border border-champagne-beige bg-cream px-4 py-2 text-sm font-medium text-charcoal hover:bg-champagne-beige/40 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {action === "repair" ? t("working") : t("repair.apply")}
        </button>
      </div>

      <div className="mt-4 flex flex-wrap gap-3">
        <ActionButton
          label={t("actions.sync")}
          busy={action === "sync"}
          disabled={!ready || Boolean(action)}
          onClick={() => runAction("sync", () => syncEcontOrder(order.id))}
        />
        <ActionButton
          label={t("actions.createAndShip")}
          busy={action === "createShip"}
          disabled={!canCreateAndShip || Boolean(action)}
          onClick={() => runAction("createShip", () => createAndShipEcontOrder(order.id))}
        />
        <ActionButton
          label={t("actions.createLabel")}
          busy={action === "create"}
          disabled={!ready || Boolean(action) || Boolean(shipmentNumber)}
          onClick={() => runAction("create", () => createEcontLabel(order.id))}
        />
        <ActionButton
          label={t("actions.refreshTrace")}
          busy={action === "trace"}
          disabled={!shipmentNumber || Boolean(action)}
          onClick={() => runAction("trace", () => refreshEcontTrace(order.id))}
        />
        <ActionButton
          label={t("actions.markShipped")}
          busy={action === "ship"}
          disabled={!canMarkShipped || Boolean(action)}
          onClick={() =>
            runAction("ship", () =>
              updateOrderStatus(order.id, "shipped", {
                tracking_number: shipmentNumber!,
                tracking_carrier: "econt",
                tracking_url: trackingUrl ?? undefined,
              }),
            )
          }
        />
        <ActionButton
          label={t("actions.deleteLabel")}
          busy={action === "delete"}
          disabled={!canDelete || Boolean(action)}
          danger
          onClick={() => runAction("delete", () => deleteEcontLabel(order.id))}
        />
      </div>
    </section>
  );
}

function ActionButton({ label, busy, disabled, danger, onClick }: { label: string; busy: boolean; disabled: boolean; danger?: boolean; onClick: () => void }) {
  if (danger) {
    return (
      <DeleteIconButton
        label={label}
        isLoading={busy}
        disabled={disabled}
        onClick={onClick}
      />
    );
  }

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "rounded-brand px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50",
        danger
          ? "border border-red-200 bg-red-50 text-red-700 hover:bg-red-100"
          : "bg-charcoal text-warm-ivory hover:bg-soft-brown",
      )}
    >
      {busy ? "..." : label}
    </button>
  );
}
