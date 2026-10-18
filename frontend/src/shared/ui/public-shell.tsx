import { Link } from "@tanstack/react-router";
import type { ReactNode } from "react";

import { buttonVariants } from "@/components/ui/button";
import { useSession } from "@/features/auth/api";
import { djangoPaths, backendUrl } from "../backend-links";
import { getRepoLinks, PROJECT } from "../config";
import { useMode } from "../mode";
import { DemoBanner } from "./demo-banner";
import { SourceLinks } from "./source-links";

export function Brand() {
  return (
    <Link to="/" className="flex items-center gap-2 font-display text-lg font-semibold">
      <span aria-hidden className="inline-block size-3 rounded-full bg-primary" />
      Open Conference Platform
    </Link>
  );
}

export function PublicShell({ children }: { children: ReactNode }) {
  const mode = useMode();
  const session = useSession();
  const booking = mode === "live" ? backendUrl(djangoPaths.bookingLookup()) : null;
  const signedIn = session.data?.authenticated;
  const repo = getRepoLinks();

  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-card focus:px-3 focus:py-2">
        Skip to content
      </a>
      <DemoBanner />
      <header className="border-b">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-4">
          <Brand />
          <nav aria-label="Main" className="flex flex-wrap items-center gap-1 text-sm">
            <Link to="/" className={buttonVariants({ variant: "ghost", size: "sm" })} activeOptions={{ exact: true }}>
              Events
            </Link>
            {booking && <a href={booking} className={buttonVariants({ variant: "ghost", size: "sm" })}>Find my booking</a>}
            {repo && <a href={repo.sourceUrl} className={buttonVariants({ variant: "ghost", size: "sm" })} rel="noopener">View source / Self-host</a>}
            {signedIn ? (
              <Link to="/manage" className={buttonVariants({ size: "sm" })}>Organizer workspace</Link>
            ) : (
              <Link to="/login" className={buttonVariants({ size: "sm", variant: mode === "demo" ? "default" : "outline" })}>
                {mode === "demo" ? "Explore organizer demo" : "Organizer sign in"}
              </Link>
            )}
          </nav>
        </div>
      </header>
      <main id="main" className="flex-1">{children}</main>
      <footer className="border-t">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-6 text-sm text-muted-foreground">
          <p>{PROJECT.name} · Open source under the {PROJECT.license} license · Self-hosted</p>
          <SourceLinks />
        </div>
      </footer>
    </div>
  );
}

