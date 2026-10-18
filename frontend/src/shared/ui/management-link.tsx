import { ArrowUpRight } from "lucide-react";
import type { ReactNode } from "react";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { backendUrl } from "../backend-links";

type Variant = "default" | "outline" | "ghost" | "link";

/**
 * Full-page navigation to an existing Django server page. When no backend is
 * configured (preview mode) it renders an honest, non-interactive note instead.
 */
export function ManagementLink({
  path,
  children,
  variant = "outline",
  className,
  size,
}: {
  path: string | null | undefined;
  children: ReactNode;
  variant?: Variant;
  className?: string;
  size?: "sm" | "default";
}) {
  const href = backendUrl(path);
  if (!href) {
    return (
      <span
        className={cn(buttonVariants({ variant: "outline", size }), "cursor-not-allowed opacity-60", className)}
        title="Available once a Django backend is connected"
      >
        {children}
        <span className="sr-only"> (unavailable in preview — requires a connected backend)</span>
      </span>
    );
  }
  return (
    <a href={href} className={cn(buttonVariants({ variant, size }), className)}>
      {children}
      <ArrowUpRight aria-hidden />
      <span className="sr-only"> (opens the management site)</span>
    </a>
  );
}

