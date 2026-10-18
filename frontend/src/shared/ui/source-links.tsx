import { Download, Github } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { getRepoLinks, PROJECT } from "../config";

/** "View source / Self-host" and "Download source". Renders no dead links when the repo isn't configured. */
export function SourceLinks({ size = "sm", className, stacked }: { size?: "sm" | "default" | "lg"; className?: string; stacked?: boolean }) {
  const repo = getRepoLinks();
  if (!repo) {
    return (
      <p className={cn("text-sm text-muted-foreground", className)}>
        {PROJECT.license}-licensed source code — public repository coming soon.
      </p>
    );
  }
  return (
    <div className={cn("flex flex-wrap gap-2", stacked && "flex-col", className)}>
      <a href={repo.sourceUrl} className={buttonVariants({ size, className: stacked ? "justify-start" : "" })} rel="noopener">
        <Github aria-hidden /> View source / Self-host
      </a>
      <a href={repo.downloadUrl} className={buttonVariants({ size, variant: "outline", className: stacked ? "justify-start" : "" })} rel="noopener">
        <Download aria-hidden /> Download source
      </a>
    </div>
  );
}

