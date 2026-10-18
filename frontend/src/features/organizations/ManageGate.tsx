import { Navigate, Outlet, useRouterState } from "@tanstack/react-router";

import { useSession } from "@/features/auth/api";
import { useMode } from "@/shared/mode";
import { PublicShell } from "@/shared/ui/public-shell";
import { ErrorState, LoadingState } from "@/shared/ui/states";

/** Requires a configured backend (or preview) and an authenticated Django session. */
export function ManageGate() {
  const mode = useMode();
  const session = useSession();
  const href = useRouterState({ select: (s) => s.location.href });

  if (session.isPending) return <LoadingState label="Checking your session…" />;
  if (session.isError) return <PublicShell><div className="mx-auto max-w-2xl px-4 py-16"><ErrorState error={session.error} onRetry={() => session.refetch()} /></div></PublicShell>;
  if (!session.data.authenticated) return <Navigate to="/login" search={{ redirect: href }} replace />;
  return <Outlet />;
}

