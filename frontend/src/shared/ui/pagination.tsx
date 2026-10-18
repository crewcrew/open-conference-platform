import { ChevronLeft, ChevronRight } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";

export function Pagination({
  page,
  pageSize,
  count,
  hasNext,
  onPage,
}: {
  page: number;
  pageSize: number;
  count: number;
  hasNext: boolean;
  onPage: (page: number) => void;
}) {
  const from = count === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, count);
  return (
    <nav aria-label="Pagination" className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm">
      <p className="text-muted-foreground" aria-live="polite">
        {count === 0 ? "No results" : `Showing ${from}–${to} of ${count}`}
      </p>
      <div className="flex gap-2">
        <button type="button" className={buttonVariants({ variant: "outline", size: "sm" })} disabled={page <= 1} onClick={() => onPage(page - 1)}>
          <ChevronLeft aria-hidden /> Previous
        </button>
        <button type="button" className={buttonVariants({ variant: "outline", size: "sm" })} disabled={!hasNext} onClick={() => onPage(page + 1)}>
          Next <ChevronRight aria-hidden />
        </button>
      </div>
    </nav>
  );
}

