"use client";

import type { CommentSort } from "@/lib/types";
import { cn } from "@/lib/utils";

interface SortDropdownProps {
  value: CommentSort;
  onChange: (sort: CommentSort) => void;
  className?: string;
}

export function SortDropdown({ value, onChange, className }: SortDropdownProps) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as CommentSort)}
      aria-label="Sort comments"
      className={cn(
        "rounded-brand border border-warm-gray/30 bg-white px-3 py-1.5 text-sm text-charcoal",
        "focus:border-soft-brown focus:outline-none focus:ring-1 focus:ring-soft-brown",
        className
      )}
    >
      <option value="newest">Newest first</option>
      <option value="oldest">Oldest first</option>
    </select>
  );
}
