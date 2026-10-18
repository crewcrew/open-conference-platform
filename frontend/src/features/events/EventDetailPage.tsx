import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { ArrowUpRight } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import { Schedule } from "@/features/schedule/Schedule";
import { TicketCards } from "@/features/ticketing/TicketCards";
import { backendUrl, djangoPaths } from "@/shared/backend-links";
import { formatEventDates } from "@/shared/format";
import { useMode } from "@/shared/mode";
import { PublicShell } from "@/shared/ui/public-shell";
import { SetupScreen } from "@/shared/ui/setup-screen";
import { ErrorState, LoadingState } from "@/shared/ui/states";
import { eventDetailQuery } from "./api";

export function EventDetailPage({ slug }: { slug: string }) {
  const mode = useMode();
  const q = useQuery(eventDetailQuery(mode, slug));

  if (mode === "unconfigured") return <PublicShell><SetupScreen /></PublicShell>;

  return (
    <PublicShell>
      <div className="mx-auto max-w-6xl px-4 py-10">
        <Link to="/" className="text-sm text-muted-foreground hover:text-foreground">← All events</Link>
        {q.isPending ? (
          <LoadingState label="Loading event…" />
        ) : q.isError ? (
          <div className="mt-6"><ErrorState error={q.error} onRetry={() => q.refetch()} /></div>
        ) : (
          <EventBody event={q.data} />
        )}
      </div>
    </PublicShell>
  );
}

function EventBody({ event }: { event: import("@/shared/api/types").EventDetail }) {
  const buyUrl = backendUrl(event.public_url);
  const booking = backendUrl(djangoPaths.bookingLookup());
  return (
    <article className="mt-6">
      <header className="border-b pb-8">
        <p className="eyebrow">{formatEventDates(event.starts_at, event.ends_at, event.timezone)}</p>
        <h1 className="mt-3 text-4xl font-semibold md:text-5xl">{event.name}</h1>
        {event.summary && <p className="mt-3 max-w-3xl text-lg text-muted-foreground">{event.summary}</p>}
        <div className="mt-6 flex flex-wrap items-center gap-3">
          {buyUrl ? (
            <a href={buyUrl} className={buttonVariants({ size: "lg" })}>
              Buy tickets <ArrowUpRight aria-hidden />
            </a>
          ) : (
            <span className={buttonVariants({ size: "lg", variant: "outline" }) + " cursor-not-allowed opacity-60"}>
              Ticket checkout unavailable in preview
            </span>
          )}
          {booking && <a href={booking} className={buttonVariants({ variant: "ghost" })}>Find an existing booking</a>}
        </div>
        {buyUrl && <p className="mt-2 text-sm text-muted-foreground">You'll complete payment on the event's secure checkout.</p>}
      </header>

      <div className="mt-10 grid gap-12 lg:grid-cols-[1fr_20rem]">
        <div className="space-y-12">
          {event.description && (
            <section aria-labelledby="about">
              <h2 id="about" className="mb-3 text-2xl font-semibold">About</h2>
              <div className="max-w-prose space-y-3 whitespace-pre-line">{event.description}</div>
            </section>
          )}
          <section aria-labelledby="tickets">
            <h2 id="tickets" className="mb-4 text-2xl font-semibold">Tickets</h2>
            <TicketCards event={event} />
          </section>
          <section aria-labelledby="schedule">
            <h2 id="schedule" className="mb-4 text-2xl font-semibold">Schedule</h2>
            <Schedule sessions={event.sessions} timezone={event.timezone} />
          </section>
        </div>
        <aside className="space-y-6 text-sm">
          <InfoBlock title="Venue">
            <p className="font-medium">{event.venue_name}</p>
            {event.venue_address && <p className="whitespace-pre-line text-muted-foreground">{event.venue_address}</p>}
          </InfoBlock>
          {event.accessibility_info && <InfoBlock title="Accessibility"><p className="whitespace-pre-line">{event.accessibility_info}</p></InfoBlock>}
          {event.refund_policy && <InfoBlock title="Refund policy"><p className="whitespace-pre-line">{event.refund_policy}</p></InfoBlock>}
          {event.contact_email && (
            <InfoBlock title="Contact">
              <a className="text-primary underline underline-offset-2" href={`mailto:${event.contact_email}`}>{event.contact_email}</a>
            </InfoBlock>
          )}
        </aside>
      </div>
    </article>
  );
}

function InfoBlock({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="panel p-4">
      <h2 className="eyebrow mb-2">{title}</h2>
      {children}
    </div>
  );
}

