import { ArrowUpRight } from "lucide-react";
import type { ReactNode } from "react";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { backendUrl } from "../backend-links";

type Variant = "default" | "outline" | "ghost" | "link";

/**
 * Full-page navigation to an existing Django server page. In the demo there is no
 * server, so it renders a clearly non-interactive control with a plain explanation.
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
        title="In a self-hosted install this opens the management screen. The demo doesn't save changes."
      >
        {children}
        <span className="sr-only"> (not available in the demo — in a self-hosted install this opens the management screen)</span>
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

