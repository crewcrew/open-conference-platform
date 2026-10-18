import { Link } from "@tanstack/react-router";

import { useSession } from "@/features/auth/api";
import { djangoPaths } from "@/shared/backend-links";
import { orgCan } from "@/shared/capabilities";
import { formatEventDates } from "@/shared/format";
import { ManagementLink } from "@/shared/ui/management-link";
import { EmptyState, ErrorState, LoadingState } from "@/shared/ui/states";
import { DataTable, StatusBadge, Td, Th } from "@/shared/ui/table";
import { useOrgEvents } from "./api";

export function OrgEventsPage({ orgSlug }: { orgSlug: string }) {
  const session = useSession();
  const membership = session.data?.organizations.find((o) => o.slug === orgSlug);
  const events = useOrgEvents(orgSlug);
  const list = events.data?.results ?? [];

  return (
    <div className="mx-auto max-w-6xl">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow">{membership?.name}</p>
          <h1 className="mt-1 text-3xl font-semibold">Events</h1>
        </div>
        {orgCan(membership, "manage_events") && (
          <ManagementLink path={djangoPaths.newEvent(orgSlug)} variant="default">Create event in management</ManagementLink>
        )}
      </div>
      <div className="mt-8">
        {events.isPending ? (
          <LoadingState label="Loading events…" />
        ) : events.isError ? (
          <ErrorState error={events.error} onRetry={() => events.refetch()} />
        ) : list.length === 0 ? (
          <EmptyState title="No events here yet">Events you're assigned to will appear here.</EmptyState>
        ) : (
          <DataTable caption="Organization events">
            <thead>
              <tr><Th>Event</Th><Th>Dates</Th><Th>Status</Th><Th><span className="sr-only">Actions</span></Th></tr>
            </thead>
            <tbody>
              {list.map((ev) => (
                <tr key={ev.id}>
                  <Td>
                    <Link to="/manage/$orgSlug/events/$eventId" params={{ orgSlug, eventId: String(ev.id) }} className="font-medium text-primary hover:underline">
                      {ev.name}
                    </Link>
                    <p className="text-muted-foreground">{ev.venue_name}</p>
                  </Td>
                  <Td>{formatEventDates(ev.starts_at, ev.ends_at, ev.timezone)}</Td>
                  <Td><StatusBadge status={ev.status} /></Td>
                  <Td className="text-right">
                    <Link to="/manage/$orgSlug/events/$eventId" params={{ orgSlug, eventId: String(ev.id) }} className="text-sm underline underline-offset-2">Open</Link>
                  </Td>
                </tr>
              ))}
            </tbody>
          </DataTable>
        )}
      </div>
    </div>
  );
}

