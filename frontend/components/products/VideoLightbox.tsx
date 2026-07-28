"use client";

import { BASE_URL } from "@/lib/api-client";
import { Portal } from "@/components/ui/Portal";
import { useFocusTrap } from "@/lib/useFocusTrap";

interface VideoLightboxProps {
  name: string;
  videoUrl: string;
  posterUrl: string | null;
  onClose: () => void;
}

function resolveStaticUrl(url: string | null): string | null {
  return url?.startsWith("/static/") ? `${BASE_URL}${url}` : url;
}

export function VideoLightbox({ name, videoUrl, posterUrl, onClose }: VideoLightboxProps) {
  // Mounted only while open, so the trap is engaged for the component's lifetime.
  const containerRef = useFocusTrap<HTMLDivElement>({ active: true, onClose });

  const resolvedVideoUrl = resolveStaticUrl(videoUrl);
  const resolvedPosterUrl = resolveStaticUrl(posterUrl);

  return (
    <Portal>
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-label={name}
        className="fixed inset-0 z-50 flex items-center justify-center bg-charcoal/90 p-4"
        onClick={onClose}
      >
        <button
          type="button"
          aria-label="Close"
          onClick={onClose}
          className="absolute right-4 top-4 flex h-10 w-10 items-center justify-center rounded-full bg-warm-ivory text-2xl leading-none text-charcoal shadow-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-warm-ivory focus-visible:ring-offset-2 focus-visible:ring-offset-charcoal"
        >
          ×
        </button>
        <video
          src={resolvedVideoUrl ?? undefined}
          poster={resolvedPosterUrl ?? undefined}
          controls
          autoPlay
          playsInline
          className="max-h-[88vh] w-full max-w-5xl rounded-brand bg-black object-contain"
          onClick={(event) => event.stopPropagation()}
        />
      </div>
    </Portal>
  );
}
