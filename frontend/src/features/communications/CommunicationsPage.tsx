import { useQuery } from "@tanstack/react-query";

import { EventGate } from "@/features/organizations/EventGate";
import type { OrgEvent } from "@/shared/api/types";
import { djangoPaths } from "@/shared/backend-links";
import { formatDateTime, humanize } from "@/shared/format";
import { useMode } from "@/shared/mode";
import { ManagementLink } from "@/shared/ui/management-link";
import { Pagination } from "@/shared/ui/pagination";
import { EmptyState, ErrorState, LoadingState } from "@/shared/ui/states";
import { DataTable, StatusBadge, Td, Th } from "@/shared/ui/table";
import { communicationsQuery } from "./api";

type Props = { orgSlug: string; eventId: string; page: number; onPage: (p: number) => void };

export function CommunicationsPage(props: Props) {
  return (
    <EventGate orgSlug={props.orgSlug} eventId={props.eventId} requires="send_comms" title="Communications"
      actions={(ev) => <ManagementLink variant="default" path={djangoPaths.eventSection(props.orgSlug, ev.id, "emails")}>Compose email in management</ManagementLink>}>
      {(event) => <CommsTable {...props} event={event} />}
    </EventGate>
  );
}

function CommsTable({ orgSlug, event, page, onPage }: Props & { event: OrgEvent }) {
  const mode = useMode();
  const q = useQuery(communicationsQuery(mode, orgSlug, String(event.id), page));
  if (q.isPending) return <LoadingState label="Loading messages…" />;
  if (q.isError) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  if (q.data.results.length === 0) return <EmptyState title="No messages yet">Emails you compose in management will be listed here.</EmptyState>;
  return (
    <>
      <DataTable caption="Communications">
        <thead><tr><Th>Subject</Th><Th>Type</Th><Th>Status</Th><Th>When</Th><Th className="text-right">Recipients</Th></tr></thead>
        <tbody>
          {q.data.results.map((c) => (
            <tr key={c.id}>
              <Td className="font-medium">{c.subject}</Td>
              <Td>{humanize(c.kind)}</Td>
              <Td><StatusBadge status={c.status} /></Td>
              <Td className="whitespace-nowrap">
                {c.sent_at ? `Sent ${formatDateTime(c.sent_at, event.timezone)}` : c.scheduled_for ? `Scheduled ${formatDateTime(c.scheduled_for, event.timezone)}` : "—"}
              </Td>
              <Td className="text-right tabular-nums">{c.recipient_count.toLocaleString("en-GB")}</Td>
            </tr>
          ))}
        </tbody>
      </DataTable>
      <Pagination page={q.data.page} pageSize={q.data.page_size} count={q.data.count} hasNext={q.data.has_next} onPage={onPage} />
    </>
  );
}

