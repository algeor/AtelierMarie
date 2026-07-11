"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { getReactions, toggleReaction } from "@/lib/api";
import type { ReactionCountsResponse } from "@/lib/types";

interface ReactionBarProps {
  productId: string;
  className?: string;
}

export function ReactionBar({ productId, className }: ReactionBarProps) {
  const t = useTranslations("comments");
  const [data, setData] = useState<ReactionCountsResponse | null>(null);
  const [error, setError] = useState(false);
  const debounceRef = useRef<{ heart: NodeJS.Timeout | null; thumbs_up: NodeJS.Timeout | null }>({
    heart: null,
    thumbs_up: null,
  });

  useEffect(() => {
    getReactions(productId)
      .then(setData)
      .catch(() => setError(true));
  }, [productId]);

  const handleToggle = useCallback(
    (type: "heart" | "thumbs_up") => {
      if (!data) return;

      // Debounce: ignore clicks within 300ms
      if (debounceRef.current[type]) return;
      debounceRef.current[type] = setTimeout(() => {
        debounceRef.current[type] = null;
      }, 300);

      // Optimistic update
      const current = data[type];
      const newReacted = !current.reacted;
      const newCount = newReacted ? current.count + 1 : current.count - 1;

      setData({
        ...data,
        [type]: { count: Math.max(0, newCount), reacted: newReacted },
      });

      // Fire API call
      toggleReaction(productId, { reaction_type: type }).catch(() => {
        // Rollback on error
        setData((prev) =>
          prev ? { ...prev, [type]: current } : prev
        );
      });
    },
    [data, productId]
  );

  if (error || !data) {
    // Graceful degradation — hide reactions if API fails
    return null;
  }

  return (
    <div className={cn("flex items-center gap-3", className)}>
      <ReactionButton
        emoji="❤️"
        count={data.heart.count}
        active={data.heart.reacted}
        onClick={() => handleToggle("heart")}
        label={t("loveProduct")}
      />
      <ReactionButton
        emoji="👍"
        count={data.thumbs_up.count}
        active={data.thumbs_up.reacted}
        onClick={() => handleToggle("thumbs_up")}
        label={t("likeProduct")}
      />
    </div>
  );
}

interface ReactionButtonProps {
  emoji: string;
  count: number;
  active: boolean;
  onClick: () => void;
  label: string;
}

function ReactionButton({ emoji, count, active, onClick, label }: ReactionButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      aria-pressed={active}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm",
        "border transition-colors duration-150",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2",
        active
          ? "border-soft-brown bg-soft-brown/10 text-charcoal"
          : "border-warm-gray/30 bg-white text-muted-charcoal hover:border-soft-brown/50"
      )}
    >
      <span aria-hidden="true">{emoji}</span>
      {count > 0 && (
        <span className="min-w-[1ch] text-center font-medium tabular-nums">
          {count}
        </span>
      )}
    </button>
  );
}
