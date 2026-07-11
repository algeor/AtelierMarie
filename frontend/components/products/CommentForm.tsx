"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { postComment } from "@/lib/api";
import { ApiError } from "@/lib/api-client";
import { useLocalizedError } from "@/lib/useLocalizedError";
import type { CommentResponse } from "@/lib/types";

interface CommentFormProps {
  productId: string;
  isLoggedInWithName: boolean;
  onCommentPosted: (comment: CommentResponse) => void;
  className?: string;
}

const MAX_BODY_LENGTH = 500;

export function CommentForm({
  productId,
  isLoggedInWithName,
  onCommentPosted,
  className,
}: CommentFormProps) {
  const t = useTranslations("comments");
  const getLocalizedError = useLocalizedError();
  const [displayName, setDisplayName] = useState("");
  const [body, setBody] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const bodyLength = body.length;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    const trimmedBody = body.trim();
    if (!trimmedBody) {
      setError(t("writeComment"));
      return;
    }

    if (!isLoggedInWithName && !displayName.trim()) {
      setError(t("enterDisplayName"));
      return;
    }

    setSubmitting(true);
    try {
      const comment = await postComment(productId, {
        display_name: isLoggedInWithName ? undefined : displayName.trim() || undefined,
        body: trimmedBody,
      });
      onCommentPosted(comment);
      setBody("");
      setDisplayName("");
    } catch (err: unknown) {
      setError(err instanceof ApiError ? getLocalizedError(err.code) : t("postFailed"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className={cn("space-y-3", className)}>
      {!isLoggedInWithName && (
        <div>
          <label
            htmlFor="comment-display-name"
            className="block text-sm font-medium text-charcoal mb-1"
          >
            {t("displayName")}
          </label>
          <input
            id="comment-display-name"
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            maxLength={50}
            placeholder={t("displayNamePlaceholder")}
            className="w-full rounded-brand border border-warm-gray/30 px-3 py-2 text-sm text-charcoal placeholder:text-muted-charcoal/50 focus:border-soft-brown focus:outline-none focus:ring-1 focus:ring-soft-brown"
          />
        </div>
      )}

      <div>
        <label
          htmlFor="comment-body"
          className="block text-sm font-medium text-charcoal mb-1"
        >
          {t("comment")}
        </label>
        <textarea
          id="comment-body"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          maxLength={MAX_BODY_LENGTH}
          rows={3}
          placeholder={t("commentPlaceholder")}
          className="w-full resize-none rounded-brand border border-warm-gray/30 px-3 py-2 text-sm text-charcoal placeholder:text-muted-charcoal/50 focus:border-soft-brown focus:outline-none focus:ring-1 focus:ring-soft-brown"
        />
        <p className="mt-1 text-xs text-muted-charcoal text-right tabular-nums">
          {bodyLength}/{MAX_BODY_LENGTH}
        </p>
      </div>

      {error && (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={submitting || !body.trim()}
        className={cn(
          "rounded-brand px-4 py-2 text-sm font-medium transition-colors",
          "bg-charcoal text-warm-ivory hover:bg-charcoal/90",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-soft-brown focus-visible:ring-offset-2"
        )}
      >
        {submitting ? t("posting") : t("postComment")}
      </button>
    </form>
  );
}
