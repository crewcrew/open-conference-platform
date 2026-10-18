import { useQuery } from "@tanstack/react-query";

import { EventGate } from "@/features/organizations/EventGate";
import type { Dashboard, OrgEvent } from "@/shared/api/types";
import { djangoPaths, managementSectionsFor } from "@/shared/backend-links";
import { can } from "@/shared/capabilities";
import { formatMoney } from "@/shared/format";
import { useMode } from "@/shared/mode";
import { ManagementLink } from "@/shared/ui/management-link";
import { ErrorState, LoadingState } from "@/shared/ui/states";
import { dashboardQuery } from "./api";

const MONEY_LABELS: [keyof NonNullable<Dashboard["money"]>, string][] = [
  ["revenue", "Gross revenue"],
  ["discounts", "Discounts"],
  ["fees", "Fees"],
  ["collected", "Collected"],
  ["refunds", "Refunds"],
  ["net", "Net"],
  ["tax", "Tax"],
];

export function EventOverviewPage({ orgSlug, eventId }: { orgSlug: string; eventId: string }) {
  return (
    <EventGate orgSlug={orgSlug} eventId={eventId} title="Overview">
      {(event) => <Overview orgSlug={orgSlug} event={event} />}
    </EventGate>
  );
}

function Overview({ orgSlug, event }: { orgSlug: string; event: OrgEvent }) {
  const mode = useMode();
  const reports = can(event, "view_reports");
  const dash = useQuery(dashboardQuery(mode, orgSlug, String(event.id), reports));
  const sections = managementSectionsFor(event.capabilities);

  return (
    <div className="space-y-10">
      {reports && (
        <section aria-labelledby="metrics">
          <div className="mb-4 flex items-baseline justify-between">
            <h2 id="metrics" className="text-xl font-semibold">Figures</h2>
            {mode === "demo" && <span className="text-sm text-notice-foreground">Sample figures — not real</span>}
          </div>
          {dash.isPending ? <LoadingState /> : dash.isError ? <ErrorState error={dash.error} onRetry={() => dash.refetch()} /> : <Metrics data={dash.data} />}
        </section>
      )}

      {can(event, "check_in") && (
        <section aria-labelledby="checkin-h" className="panel flex flex-wrap items-center justify-between gap-4 p-5">
          <div>
            <h2 id="checkin-h" className="text-lg font-semibold">Check-in</h2>
            <p className="text-sm text-muted-foreground">Scan and admit attendees using the check-in station.</p>
          </div>
          <ManagementLink path={event.scanner_url || djangoPaths.checkin(event.id)} variant="default">Open check-in station</ManagementLink>
        </section>
      )}

      {sections.length > 0 && (
        <section aria-labelledby="manage-h">
          <h2 id="manage-h" className="text-xl font-semibold">Open in management</h2>
          <p className="mt-1 text-sm text-muted-foreground">Changes, refunds and emails are made on the management site.</p>
          <ul className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {sections.map((s) => (
              <li key={s.label} className="panel flex flex-col p-4">
                <p className="font-medium">{s.label}</p>
                <p className="mb-3 text-sm text-muted-foreground">{s.description}</p>
                <ManagementLink
                  size="sm"
                  className="mt-auto self-start"
                  path={s.section ? djangoPaths.eventSection(orgSlug, event.id, s.section) : event.manage_url || djangoPaths.eventDashboard(orgSlug, event.id)}
                >
                  Open in management
                </ManagementLink>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function Metrics({ data }: { data: Dashboard }) {
  const items: { label: string; value: string }[] = [];
  if (typeof data.tickets_issued === "number") items.push({ label: "Tickets issued", value: data.tickets_issued.toLocaleString("en-GB") });
  if (typeof data.checked_in === "number") items.push({ label: "Checked in", value: data.checked_in.toLocaleString("en-GB") });
  for (const [key, label] of MONEY_LABELS) {
    const v = data.money?.[key];
    if (v !== undefined && v !== null) items.push({ label, value: formatMoney(v, data.currency) });
  }
  if (items.length === 0) return <p className="text-muted-foreground">No figures available yet.</p>;
  return (
    <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((m) => (
        <div key={m.label} className="panel p-4">
          <dt className="text-sm text-muted-foreground">{m.label}</dt>
          <dd className="mt-1 font-display text-2xl tabular-nums">{m.value}</dd>
        </div>
      ))}
    </dl>
  );
}

