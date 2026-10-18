import type { ReactNode, ThHTMLAttributes, TdHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function DataTable({ caption, children }: { caption: string; children: ReactNode }) {
  return (
    <div className="panel overflow-x-auto">
      <table className="w-full min-w-[640px] border-collapse text-sm">
        <caption className="sr-only">{caption}</caption>
        {children}
      </table>
    </div>
  );
}

export function Th({ className, ...props }: ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      scope="col"
      className={cn("border-b bg-muted px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground", className)}
      {...props}
    />
  );
}

export function Td({ className, ...props }: TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={cn("border-b px-4 py-3 align-top", className)} {...props} />;
}

const TONES: Record<string, string> = {
  paid: "bg-success-soft text-success",
  sent: "bg-success-soft text-success",
  published: "bg-success-soft text-success",
  on_sale: "bg-success-soft text-success",
  valid: "bg-success-soft text-success",
  checked_in: "bg-success-soft text-success",
  pending: "bg-warning-soft text-warning",
  scheduled: "bg-warning-soft text-warning",
  draft: "bg-secondary text-secondary-foreground",
  partially_refunded: "bg-warning-soft text-warning",
  failed: "bg-destructive/10 text-destructive",
  expired: "bg-secondary text-muted-foreground",
  refunded: "bg-secondary text-secondary-foreground",
  cancelled: "bg-secondary text-muted-foreground",
  sold_out: "bg-secondary text-muted-foreground",
};

export function StatusBadge({ status, label }: { status: string; label?: string }) {
  const text = label ?? status.replace(/_/g, " ");
  return (
    <span className={cn("inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium capitalize", TONES[status] ?? "bg-secondary text-secondary-foreground")}>
      {text}
    </span>
  );
}

