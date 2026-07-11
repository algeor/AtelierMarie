import type { CommentResponse } from "@/lib/types";

interface CommentCardProps {
  comment: CommentResponse;
}

/**
 * Format a timestamp as a relative time (e.g., "2 hours ago").
 * Falls back to the raw string if parsing fails.
 */
function formatRelativeTime(dateString: string): string {
  try {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSeconds = Math.floor(diffMs / 1000);

    if (diffSeconds < 60) return "just now";
    const diffMinutes = Math.floor(diffSeconds / 60);
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 30) return `${diffDays}d ago`;
    const diffMonths = Math.floor(diffDays / 30);
    if (diffMonths < 12) return `${diffMonths}mo ago`;
    return `${Math.floor(diffMonths / 12)}y ago`;
  } catch {
    return dateString;
  }
}

export function CommentCard({ comment }: CommentCardProps) {
  return (
    <article className="py-4 border-b border-warm-gray/20 last:border-b-0">
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-sm font-medium text-charcoal">
          {comment.display_name}
        </p>
        <time
          dateTime={comment.created_at}
          className="text-xs text-muted-charcoal whitespace-nowrap"
        >
          {formatRelativeTime(comment.created_at)}
        </time>
      </div>
      <p className="mt-1 text-sm text-charcoal/80 leading-relaxed">
        {comment.body}
      </p>
    </article>
  );
}
