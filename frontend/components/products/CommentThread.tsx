"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { getComments } from "@/lib/api";
import type { CommentResponse, CommentSort } from "@/lib/types";
import { CommentCard } from "./CommentCard";
import { CommentForm } from "./CommentForm";
import { SortDropdown } from "./SortDropdown";

interface CommentThreadProps {
  productId: string;
  isLoggedInWithName: boolean;
  className?: string;
}

const PAGE_SIZE = 20;

export function CommentThread({
  productId,
  isLoggedInWithName,
  className,
}: CommentThreadProps) {
  const t = useTranslations("comments");
  const tCommon = useTranslations("common");
  const [comments, setComments] = useState<CommentResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<CommentSort>("newest");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const fetchComments = useCallback(
    async (newSort: CommentSort, newPage: number) => {
      setLoading(true);
      setError(false);
      try {
        const data = await getComments(productId, newSort, newPage, PAGE_SIZE);
        setComments(data.items);
        setTotal(data.total);
      } catch {
        setError(true);
      } finally {
        setLoading(false);
      }
    },
    [productId]
  );

  useEffect(() => {
    fetchComments(sort, page);
  }, [fetchComments, sort, page]);

  function handleSortChange(newSort: CommentSort) {
    setSort(newSort);
    setPage(1);
  }

  function handleCommentPosted(comment: CommentResponse) {
    // Prepend new comment to list (optimistic — matches newest sort)
    if (sort === "newest") {
      setComments((prev) => [comment, ...prev]);
      setTotal((prev) => prev + 1);
    } else {
      // Reload to get correct position
      fetchComments(sort, page);
    }
  }

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <section className={cn("space-y-6", className)} aria-label={t("title")}>
      <div className="flex items-center justify-between">
        <h2 className="font-heading text-lg text-charcoal">
          {t("title")} {total > 0 && <span className="text-muted-charcoal">({total})</span>}
        </h2>
        {total > 0 && (
          <SortDropdown value={sort} onChange={handleSortChange} />
        )}
      </div>

      <CommentForm
        productId={productId}
        isLoggedInWithName={isLoggedInWithName}
        onCommentPosted={handleCommentPosted}
      />

      {error && (
        <p className="text-sm text-muted-charcoal">
          {t("loadFailed")}
        </p>
      )}

      {!error && !loading && comments.length === 0 && (
        <p className="text-sm text-muted-charcoal py-4">
          {t("empty")}
        </p>
      )}

      {!error && comments.length > 0 && (
        <div className="divide-y divide-warm-gray/20">
          {comments.map((comment) => (
            <CommentCard key={comment.id} comment={comment} />
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-2">
          <button
            type="button"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="rounded-brand px-3 py-1 text-sm border border-warm-gray/30 disabled:opacity-50"
          >
            {tCommon("previous")}
          </button>
          <span className="text-sm text-muted-charcoal tabular-nums">
            {page} / {totalPages}
          </span>
          <button
            type="button"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="rounded-brand px-3 py-1 text-sm border border-warm-gray/30 disabled:opacity-50"
          >
            {tCommon("next")}
          </button>
        </div>
      )}
    </section>
  );
}
