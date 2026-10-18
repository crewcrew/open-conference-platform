import { Link } from "@tanstack/react-router";
import { CalendarDays, MapPin } from "lucide-react";

import type { EventSummary } from "@/shared/api/types";
import { formatEventDates } from "@/shared/format";

export function EventCard({ event }: { event: EventSummary }) {
  return (
    <article className="panel group relative flex flex-col p-6 transition-colors hover:border-primary/40">
      <h2 className="text-2xl font-semibold">
        <Link to="/events/$slug" params={{ slug: event.slug }} className="after:absolute after:inset-0 focus-visible:underline">
          {event.name}
        </Link>
      </h2>
      {event.summary && <p className="mt-2 text-muted-foreground">{event.summary}</p>}
      <dl className="mt-5 space-y-1.5 text-sm">
        <div className="flex items-start gap-2">
          <dt className="sr-only">When</dt>
          <CalendarDays className="mt-0.5 size-4 text-muted-foreground" aria-hidden />
          <dd>{formatEventDates(event.starts_at, event.ends_at, event.timezone)}</dd>
        </div>
        {event.venue_name && (
          <div className="flex items-start gap-2">
            <dt className="sr-only">Where</dt>
            <MapPin className="mt-0.5 size-4 text-muted-foreground" aria-hidden />
            <dd>{event.venue_name}</dd>
          </div>
        )}
      </dl>
      <span className="mt-6 text-sm font-medium text-primary group-hover:underline" aria-hidden>
        View event →
      </span>
    </article>
  );
}

