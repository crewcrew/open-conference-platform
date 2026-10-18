import { useQuery } from "@tanstack/react-query";

import { useMode } from "@/shared/mode";
import { PublicShell } from "@/shared/ui/public-shell";
import { SetupScreen } from "@/shared/ui/setup-screen";
import { EmptyState, ErrorState, LoadingState } from "@/shared/ui/states";
import { publicEventsQuery } from "./api";
import { EventCard } from "./EventCard";

export function EventsIndexPage() {
  const mode = useMode();
  const events = useQuery(publicEventsQuery(mode));

  if (mode === "unconfigured") {
    return (
      <PublicShell>
        <SetupScreen />
      </PublicShell>
    );
  }

  return (
    <PublicShell>
      <section className="mx-auto max-w-6xl px-4 py-14">
        <p className="eyebrow">Upcoming</p>
        <h1 className="mt-2 text-4xl font-semibold md:text-5xl">Conferences & events</h1>
        <p className="mt-3 max-w-2xl text-lg text-muted-foreground">
          Browse published events, read the schedule and get tickets through each event's secure checkout.
        </p>
        <div className="mt-10">
          {events.isPending ? (
            <LoadingState label="Loading events…" />
          ) : events.isError ? (
            <ErrorState error={events.error} onRetry={() => events.refetch()} />
          ) : events.data.results.length === 0 ? (
            <EmptyState title="No published events yet">Check back soon — new events appear here once organizers publish them.</EmptyState>
          ) : (
            <div className="grid gap-5 md:grid-cols-2">
              {events.data.results.map((ev) => (
                <EventCard key={ev.id} event={ev} />
              ))}
            </div>
          )}
        </div>
      </section>
    </PublicShell>
  );
}

