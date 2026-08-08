"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { AdminInfoPopover } from "@/components/admin/AdminInfoPopover";

type AdminFieldLabelProps = {
  children: ReactNode;
  extra?: ReactNode;
  htmlFor?: string;
  info?: string;
  className?: string;
};

export function AdminFieldLabel({ children, extra, htmlFor, info, className }: AdminFieldLabelProps) {
  const labelClass = cn("block text-sm font-medium text-soft-brown", className);

  return (
    <div className="mb-1.5 flex items-center gap-2">
      {htmlFor ? (
        <label htmlFor={htmlFor} className={labelClass}>
          {children}
        </label>
      ) : (
        <span className={labelClass}>{children}</span>
      )}
      {info && <AdminInfoPopover content={info} />}
      {extra}
    </div>
  );
}
