"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Cropper, { type Area } from "react-easy-crop";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/Button";
import { getCroppedImg } from "@/lib/cropImage";

interface ImageCropEditorProps {
  /** The originally selected file to frame. */
  file: File;
  /** Crop frame aspect ratio. Defaults to the product card shape. */
  aspect?: number;
  /** Optional dialog title for non-product upload flows. */
  title?: string;
  /** Optional dialog hint for non-product upload flows. */
  hint?: string;
  /** Called with the framed JPEG File when the admin confirms. */
  onConfirm: (file: File) => void;
  /** Called when the admin discards this file. */
  onCancel: () => void;
}

// Storefront cards render images at a 4/5 aspect (ProductImage.tsx). Locking the
// crop frame to the same ratio makes the editor a true WYSIWYG preview.
const PRODUCT_CARD_ASPECT = 4 / 5;

/**
 * Crop / rotate / zoom editor shown before a product image is uploaded. The
 * framed result is exported to a JPEG blob that enters the existing upload
 * flow, so what the admin frames here is exactly what the storefront shows.
 */
export function ImageCropEditor({
  file,
  aspect = PRODUCT_CARD_ASPECT,
  title,
  hint,
  onConfirm,
  onCancel,
}: ImageCropEditorProps) {
  const t = useTranslations("admin");
  const dialogTitle = title ?? t("cropTitle");
  const dialogHint = hint ?? t("cropHint");
  const [imageSrc, setImageSrc] = useState<string>("");
  const [crop, setCrop] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [croppedAreaPixels, setCroppedAreaPixels] = useState<Area | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  const confirmRef = useRef<HTMLButtonElement>(null);

  // Object URL for the selected file; revoked on unmount / file change.
  useEffect(() => {
    const url = URL.createObjectURL(file);
    setImageSrc(url);
    // Reset framing for each new file in the queue.
    setCrop({ x: 0, y: 0 });
    setZoom(1);
    setRotation(0);
    setCroppedAreaPixels(null);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  // Focus management + Escape to cancel + scroll lock while open.
  useEffect(() => {
    const previousActive =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    confirmRef.current?.focus();
    document.body.style.overflow = "hidden";

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.stopPropagation();
        onCancel();
        return;
      }
      if (event.key !== "Tab") return;
      const dialog = dialogRef.current;
      if (!dialog) return;
      const focusable = Array.from(
        dialog.querySelectorAll<HTMLElement>(
          'button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])'
        )
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (!first || !last) return;
      if (!dialog.contains(document.activeElement)) {
        event.preventDefault();
        first.focus();
      } else if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
      previousActive?.focus();
    };
    // onCancel is stable enough for this dialog's lifetime.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onCropComplete = useCallback((_area: Area, areaPixels: Area) => {
    setCroppedAreaPixels(areaPixels);
  }, []);

  async function handleConfirm() {
    if (!croppedAreaPixels || !imageSrc) return;
    setIsSaving(true);
    try {
      const baseName = file.name.replace(/\.[^./\\]+$/, "");
      const framed = await getCroppedImg(
        imageSrc,
        croppedAreaPixels,
        rotation,
        `${baseName || "product-image"}.jpg`
      );
      onConfirm(framed);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={dialogTitle}
      className="fixed inset-0 z-50 flex items-center justify-center bg-charcoal/80 p-4"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onCancel();
      }}
    >
      <div
        ref={dialogRef}
        className="flex max-h-[90vh] w-full max-w-2xl flex-col gap-4 rounded-brand bg-warm-ivory p-5 shadow-soft"
      >
        <div>
          <h2 className="font-heading text-lg text-charcoal">{dialogTitle}</h2>
          <p className="mt-0.5 text-sm text-soft-brown">{dialogHint}</p>
        </div>

        <div className="relative h-[55vh] w-full overflow-hidden rounded-brand bg-charcoal">
          {imageSrc && (
            <Cropper
              image={imageSrc}
              crop={crop}
              zoom={zoom}
              rotation={rotation}
              aspect={aspect}
              minZoom={1}
              maxZoom={4}
              restrictPosition
              onCropChange={setCrop}
              onZoomChange={setZoom}
              onRotationChange={setRotation}
              onCropComplete={onCropComplete}
            />
          )}
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <label className="flex items-center gap-2 text-sm text-soft-brown">
            <span className="w-16 shrink-0">{t("cropZoom")}</span>
            <input
              type="range"
              min={1}
              max={4}
              step={0.01}
              value={zoom}
              aria-label={t("cropZoom")}
              onChange={(event) => setZoom(Number(event.target.value))}
              className="w-full accent-soft-brown"
            />
          </label>
          <label className="flex items-center gap-2 text-sm text-soft-brown">
            <span className="w-16 shrink-0">{t("cropRotate")}</span>
            <input
              type="range"
              min={0}
              max={360}
              step={1}
              value={rotation}
              aria-label={t("cropRotate")}
              onChange={(event) => setRotation(Number(event.target.value))}
              className="w-full accent-soft-brown"
            />
          </label>
        </div>

        <div className="flex justify-end gap-3">
          <Button type="button" variant="secondary" onClick={onCancel} disabled={isSaving}>
            {t("cropCancel")}
          </Button>
          <Button
            type="button"
            ref={confirmRef}
            onClick={handleConfirm}
            disabled={isSaving || !croppedAreaPixels}
          >
            {t("cropConfirm")}
          </Button>
        </div>
      </div>
    </div>
  );
}
