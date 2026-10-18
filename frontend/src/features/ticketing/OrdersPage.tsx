import { useQuery } from "@tanstack/react-query";

import { EventGate } from "@/features/organizations/EventGate";
import type { OrgEvent } from "@/shared/api/types";
import { djangoPaths } from "@/shared/backend-links";
import { can } from "@/shared/capabilities";
import { formatDateTime, formatMoney, humanize, isZero } from "@/shared/format";
import { useMode } from "@/shared/mode";
import { ManagementLink } from "@/shared/ui/management-link";
import { Pagination } from "@/shared/ui/pagination";
import { EmptyState, ErrorState, LoadingState } from "@/shared/ui/states";
import { DataTable, StatusBadge, Td, Th } from "@/shared/ui/table";
import { ORDER_STATUSES, ordersQuery } from "./api";

export interface OrdersSearch {
  page?: number | undefined;
  status?: string | undefined;
}

export function OrdersPage(props: { orgSlug: string; eventId: string; search: OrdersSearch; onSearch: (s: OrdersSearch) => void }) {
  return (
    <EventGate orgSlug={props.orgSlug} eventId={props.eventId} requires="view_attendees" title="Orders"
      actions={(ev) => <ManagementLink path={djangoPaths.eventSection(props.orgSlug, ev.id, "orders")}>Open orders in management</ManagementLink>}>
      {(event) => <OrdersTable {...props} event={event} />}
    </EventGate>
  );
}

function OrdersTable({ orgSlug, event, search, onSearch }: { orgSlug: string; event: OrgEvent; search: OrdersSearch; onSearch: (s: OrdersSearch) => void }) {
  const mode = useMode();
  const page = search.page ?? 1;
  const q = useQuery(ordersQuery(mode, orgSlug, String(event.id), page, search.status));
  const canRefund = can(event, "refund");

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <label htmlFor="status" className="text-sm font-medium">Status</label>
        <select id="status" value={search.status ?? ""} onChange={(e) => onSearch({ status: e.target.value || undefined, page: 1 })}
          className="rounded-md border border-input bg-card px-3 py-2 text-sm">
          <option value="">All statuses</option>
          {ORDER_STATUSES.map((s) => <option key={s} value={s}>{humanize(s)}</option>)}
        </select>
        {q.isFetching && !q.isPending && <span role="status" className="text-sm text-muted-foreground">Updating…</span>}
      </div>
      {q.isPending ? <LoadingState label="Loading orders…" /> : q.isError ? <ErrorState error={q.error} onRetry={() => q.refetch()} /> :
        q.data.results.length === 0 ? <EmptyState title="No orders found">{search.status ? "Try a different status filter." : "Orders will appear here once tickets are sold."}</EmptyState> : (
        <>
          <DataTable caption="Orders">
            <thead><tr><Th>Order</Th><Th>Purchaser</Th><Th>Status</Th><Th className="text-right">Total</Th><Th className="text-right">Refunded</Th><Th>Placed</Th><Th><span className="sr-only">Actions</span></Th></tr></thead>
            <tbody>
              {q.data.results.map((o) => (
                <tr key={o.id}>
                  <Td className="font-medium tabular-nums">{o.number}</Td>
                  <Td>{o.purchaser_first_name} {o.purchaser_last_name}<p className="text-muted-foreground">{o.purchaser_email}</p></Td>
                  <Td><StatusBadge status={o.status} /></Td>
                  <Td className="text-right tabular-nums">{formatMoney(o.total, o.currency)}</Td>
                  <Td className="text-right tabular-nums">{isZero(o.refunded_total) ? "—" : formatMoney(o.refunded_total, o.currency)}</Td>
                  <Td className="whitespace-nowrap">{formatDateTime(o.created_at, event.timezone)}</Td>
                  <Td className="text-right">
                    <ManagementLink size="sm" variant="ghost" path={djangoPaths.order(orgSlug, event.id, o.id)}>
                      {canRefund ? "Open / refund" : "Open"}<span className="sr-only"> order {o.number}</span>
                    </ManagementLink>
                  </Td>
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

