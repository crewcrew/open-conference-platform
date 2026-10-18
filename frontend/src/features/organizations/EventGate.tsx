import type { ReactNode } from "react";

import type { Capability, OrgEvent } from "@/shared/api/types";
import { formatEventDates } from "@/shared/format";
import { ErrorState, LoadingState, NoAccess } from "@/shared/ui/states";
import { StatusBadge } from "@/shared/ui/table";
import { ApiError } from "@/shared/api/client";
import { useOrgEvents } from "./api";

/** Resolves the event from the org list and enforces a capability before rendering children. */
export function EventGate({
  orgSlug,
  eventId,
  requires,
  title,
  actions,
  children,
}: {
  orgSlug: string;
  eventId: string;
  requires?: Capability;
  title: string;
  actions?: (event: OrgEvent) => ReactNode;
  children: (event: OrgEvent) => ReactNode;
}) {
  const events = useOrgEvents(orgSlug);
  if (events.isPending) return <LoadingState />;
  if (events.isError) return <ErrorState error={events.error} onRetry={() => events.refetch()} />;
  const event = events.data.results.find((e) => String(e.id) === eventId);
  if (!event) return <ErrorState error={new ApiError(404, "This event isn't in your organization or isn't assigned to you.", "not_found")} />;

  return (
    <div className="mx-auto max-w-6xl">
      <header className="mb-8 flex flex-wrap items-end justify-between gap-4 border-b pb-6">
        <div>
          <p className="eyebrow flex items-center gap-2">
            {event.name} <StatusBadge status={event.status} />
          </p>
          <h1 className="mt-1 text-3xl font-semibold">{title}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{formatEventDates(event.starts_at, event.ends_at, event.timezone)}</p>
        </div>
        {(!requires || event.capabilities.includes(requires)) && actions && <div className="flex flex-wrap gap-2">{actions(event)}</div>}
      </header>
      {requires && !event.capabilities.includes(requires) ? <NoAccess /> : children(event)}
    </div>
  );
}

