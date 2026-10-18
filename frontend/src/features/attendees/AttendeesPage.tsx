import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";

import { buttonVariants } from "@/components/ui/button";
import { EventGate } from "@/features/organizations/EventGate";
import type { OrgEvent } from "@/shared/api/types";
import { djangoPaths } from "@/shared/backend-links";
import { can } from "@/shared/capabilities";
import { formatDateTime } from "@/shared/format";
import { useMode } from "@/shared/mode";
import { ManagementLink } from "@/shared/ui/management-link";
import { Pagination } from "@/shared/ui/pagination";
import { EmptyState, ErrorState, LoadingState } from "@/shared/ui/states";
import { DataTable, StatusBadge, Td, Th } from "@/shared/ui/table";
import { attendeesQuery } from "./api";

export interface AttendeesSearch {
  page?: number | undefined;
  q?: string | undefined;
}

type Props = { orgSlug: string; eventId: string; search: AttendeesSearch; onSearch: (s: AttendeesSearch) => void };

export function AttendeesPage(props: Props) {
  return (
    <EventGate orgSlug={props.orgSlug} eventId={props.eventId} requires="view_attendees" title="Attendees"
      actions={(ev) => can(ev, "edit_attendees") ? <ManagementLink path={djangoPaths.eventSection(props.orgSlug, ev.id, "attendees")}>Edit attendees in management</ManagementLink> : null}>
      {(event) => <AttendeesTable {...props} event={event} />}
    </EventGate>
  );
}

function AttendeesTable({ orgSlug, event, search, onSearch }: Props & { event: OrgEvent }) {
  const mode = useMode();
  const page = search.page ?? 1;
  const [draft, setDraft] = useState(search.q ?? "");
  useEffect(() => setDraft(search.q ?? ""), [search.q]);
  const q = useQuery(attendeesQuery(mode, orgSlug, String(event.id), page, search.q));

  function submit(e: FormEvent) {
    e.preventDefault();
    onSearch({ q: draft.trim() || undefined, page: 1 });
  }

  return (
    <div>
      <form role="search" onSubmit={submit} className="mb-4 flex max-w-lg gap-2">
        <label htmlFor="attendee-search" className="sr-only">Search attendees</label>
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <input id="attendee-search" type="search" value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Name, email or order number"
            className="w-full rounded-md border border-input bg-card py-2 pl-9 pr-3 text-sm" />
        </div>
        <button type="submit" className={buttonVariants({ variant: "outline" })}>Search</button>
      </form>
      {q.isPending ? <LoadingState label="Loading attendees…" /> : q.isError ? <ErrorState error={q.error} onRetry={() => q.refetch()} /> :
        q.data.results.length === 0 ? <EmptyState title={search.q ? "No matching attendees" : "No attendees yet"}>{search.q ? `Nothing matched “${search.q}”.` : "Attendees appear once tickets are issued."}</EmptyState> : (
        <>
          <DataTable caption="Attendees">
            <thead><tr><Th>Name</Th><Th>Ticket</Th><Th>Order</Th><Th>Ticket status</Th><Th>Checked in</Th></tr></thead>
            <tbody>
              {q.data.results.map((a) => (
                <tr key={a.id}>
                  <Td className="font-medium">{a.first_name} {a.last_name}<p className="font-normal text-muted-foreground">{a.email}</p></Td>
                  <Td>{a.ticket_type__name}</Td>
                  <Td className="tabular-nums">{a.order__number}</Td>
                  <Td><StatusBadge status={a.ticket__status} /></Td>
                  <Td className="whitespace-nowrap">{a.ticket__checked_in_at ? formatDateTime(a.ticket__checked_in_at, event.timezone) : <span className="text-muted-foreground">Not yet</span>}</Td>
                </tr>
              ))}
            </tbody>
          </DataTable>
          <Pagination page={q.data.page} pageSize={q.data.page_size} count={q.data.count} hasNext={q.data.has_next} onPage={(p) => onSearch({ ...search, page: p })} />
        </>
      )}
    </div>
  );
}

