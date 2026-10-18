import { useQueryClient } from "@tanstack/react-query";
import { Link, Outlet, useNavigate, useParams } from "@tanstack/react-router";
import { LogOut, Menu, X } from "lucide-react";
import { useEffect, useState } from "react";

import { buttonVariants } from "@/components/ui/button";
import { logout, useSession } from "@/features/auth/api";
import type { OrgEvent } from "@/shared/api/types";
import { djangoPaths } from "@/shared/backend-links";
import { eventNavFor, orgCan, type EventNavKey } from "@/shared/capabilities";
import { cn } from "@/lib/utils";
import { DemoBanner } from "@/shared/ui/demo-banner";
import { ManagementLink } from "@/shared/ui/management-link";
import { Brand } from "@/shared/ui/public-shell";
import { NoAccess } from "@/shared/ui/states";
import { useOrgEvents } from "./api";

const NAV_ROUTES = {
  overview: "/manage/$orgSlug/events/$eventId",
  orders: "/manage/$orgSlug/events/$eventId/orders",
  attendees: "/manage/$orgSlug/events/$eventId/attendees",
  communications: "/manage/$orgSlug/events/$eventId/communications",
  checkin: "/manage/$orgSlug/events/$eventId/checkin",
} as const satisfies Record<EventNavKey, string>;

const navItem = "flex items-center rounded-md px-3 py-2 text-sm hover:bg-sidebar-accent";
const navActive = "bg-sidebar-accent font-semibold text-sidebar-accent-foreground";

export function WorkspaceLayout({ orgSlug }: { orgSlug: string }) {
  const session = useSession();
  const membership = session.data?.organizations.find((o) => o.slug === orgSlug);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <div className="min-h-screen">
      <DemoBanner />
      <div className="flex items-center justify-between border-b px-4 py-3 md:hidden">
        <Brand />
        <button type="button" aria-expanded={open} aria-controls="workspace-nav" onClick={() => setOpen((v) => !v)} className={buttonVariants({ variant: "outline", size: "sm" })}>
          {open ? <X aria-hidden /> : <Menu aria-hidden />} Menu
        </button>
      </div>
      <div className="md:flex">
        <aside
          id="workspace-nav"
          className={cn(
            "border-r bg-sidebar text-sidebar-foreground md:sticky md:top-0 md:block md:h-screen md:w-72 md:shrink-0 md:overflow-y-auto",
            open ? "block" : "hidden",
          )}
          onClick={(e) => (e.target as HTMLElement).closest("a") && setOpen(false)}
        >
          <SidebarContent orgSlug={orgSlug} />
        </aside>
        <main id="main" className="min-w-0 flex-1 px-4 py-8 md:px-10">
          {membership ? <Outlet /> : <NoAccess>You're not a member of this organization.</NoAccess>}
        </main>
      </div>
    </div>
  );
}

function SidebarContent({ orgSlug }: { orgSlug: string }) {
  const session = useSession();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const params = useParams({ strict: false }) as { eventId?: string };
  const events = useOrgEvents(orgSlug);
  const orgs = session.data?.organizations ?? [];
  const membership = orgs.find((o) => o.slug === orgSlug);
  const list = events.data?.results ?? [];

  async function signOut() {
    try {
      await logout();
    } finally {
      await qc.cancelQueries();
      qc.clear();
      navigate({ to: "/login", replace: true });
    }
  }

  return (
    <div className="flex h-full flex-col gap-6 p-4">
      <div className="hidden md:block"><Brand /></div>

      <div>
        <label htmlFor="org-switch" className="eyebrow">Organization</label>
        <select
          id="org-switch"
          value={orgSlug}
          onChange={(e) => navigate({ to: "/manage/$orgSlug", params: { orgSlug: e.target.value } })}
          className="mt-1.5 w-full rounded-md border border-input bg-card px-3 py-2 text-sm"
        >
          {orgs.map((o) => <option key={o.slug} value={o.slug}>{o.name}</option>)}
        </select>
      </div>

      <nav aria-label="Workspace" className="flex-1 space-y-1">
        <Link to="/manage/$orgSlug" params={{ orgSlug }} activeOptions={{ exact: true }} className={navItem} activeProps={{ className: navActive }}>
          All events
        </Link>
        <p className="eyebrow px-3 pt-4">Events</p>
        {events.isPending && <p className="px-3 text-sm text-muted-foreground">Loading…</p>}
        {list.map((ev) => (
          <EventNav key={ev.id} orgSlug={orgSlug} event={ev} active={String(ev.id) === params.eventId} />
        ))}
        {events.isSuccess && list.length === 0 && <p className="px-3 text-sm text-muted-foreground">No events assigned.</p>}
      </nav>

      <div className="space-y-2 border-t pt-4">
        {orgCan(membership, "manage_events") && (
          <ManagementLink path={djangoPaths.newEvent(orgSlug)} size="sm" className="w-full justify-start">New event</ManagementLink>
        )}
        {orgCan(membership, "manage_team") && (
          <ManagementLink path={djangoPaths.orgTeam(orgSlug)} variant="ghost" size="sm" className="w-full justify-start">Team</ManagementLink>
        )}
        {orgCan(membership, "manage_org") && (
          <ManagementLink path={djangoPaths.orgSettings(orgSlug)} variant="ghost" size="sm" className="w-full justify-start">Organization settings</ManagementLink>
        )}
        <div className="pt-2 text-sm">
          <p className="truncate font-medium">{session.data?.user?.name}</p>
          <p className="truncate text-muted-foreground">{session.data?.user?.email}</p>
        </div>
        <button type="button" onClick={signOut} className={buttonVariants({ variant: "ghost", size: "sm", className: "w-full justify-start" })}>
          <LogOut aria-hidden /> Sign out
        </button>
      </div>
    </div>
  );
}

function EventNav({ orgSlug, event, active }: { orgSlug: string; event: OrgEvent; active: boolean }) {
  const eventId = String(event.id);
  return (
    <div>
      <Link to={NAV_ROUTES.overview} params={{ orgSlug, eventId }} className={cn(navItem, active && "font-semibold")}>
        <span className="truncate">{event.name}</span>
      </Link>
      {active && (
        <ul className="ml-3 mt-1 space-y-0.5 border-l pl-2">
          {eventNavFor(event.capabilities).map((n) => (
            <li key={n.key}>
              <Link to={NAV_ROUTES[n.key]} params={{ orgSlug, eventId }} activeOptions={{ exact: true, includeSearch: false }} className={navItem} activeProps={{ className: navActive }}>
                {n.label}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

