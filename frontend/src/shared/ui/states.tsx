import { Link } from "@tanstack/react-router";
import { AlertTriangle, Inbox, Loader2, Lock, SearchX, WifiOff } from "lucide-react";
import type { ReactNode } from "react";

import { buttonVariants } from "@/components/ui/button";
import { toApiError } from "../api/client";

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="flex items-center gap-3 py-16 justify-center text-muted-foreground">
      <Loader2 className="size-5 animate-spin" aria-hidden />
      <span>{label}</span>
    </div>
  );
}

export function EmptyState({ title, children, icon }: { title: string; children?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="panel flex flex-col items-center px-6 py-14 text-center">
      <div className="mb-3 text-muted-foreground" aria-hidden>
        {icon ?? <Inbox className="size-6" />}
      </div>
      <h2 className="text-xl font-semibold">{title}</h2>
      {children && <div className="mt-2 max-w-md text-muted-foreground">{children}</div>}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const e = toApiError(error);
  const icon =
    e.kind === "network" ? <WifiOff className="size-6" /> :
    e.kind === "forbidden" || e.kind === "unauthorized" ? <Lock className="size-6" /> :
    e.kind === "not_found" ? <SearchX className="size-6" /> :
    <AlertTriangle className="size-6" />;
  const title =
    e.kind === "network" ? "Can't reach the conference server" :
    e.kind === "unauthorized" ? "Please sign in" :
    e.kind === "forbidden" ? "You don't have access" :
    e.kind === "not_found" ? "Not found" :
    "Something went wrong";

  return (
    <div role="alert" className="panel flex flex-col items-center px-6 py-14 text-center">
      <div className="mb-3 text-muted-foreground" aria-hidden>{icon}</div>
      <h2 className="text-xl font-semibold">{title}</h2>
      <p className="mt-2 max-w-md text-muted-foreground">{e.message}</p>
      <div className="mt-6 flex flex-wrap justify-center gap-2">
        {e.kind === "unauthorized" && (
          <Link to="/login" className={buttonVariants()}>Sign in</Link>
        )}
        {onRetry && (e.kind === "network" || e.kind === "server") && (
          <button type="button" onClick={onRetry} className={buttonVariants({ variant: "outline" })}>
            Try again
          </button>
        )}
      </div>
    </div>
  );
}

export function NoAccess({ children }: { children?: ReactNode }) {
  return (
    <EmptyState title="Not available for your role" icon={<Lock className="size-6" />}>
      {children ?? "Your role for this event doesn't include this area. Ask an organization admin if you need access."}
    </EmptyState>
  );
}

