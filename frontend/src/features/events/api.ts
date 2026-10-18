import { queryOptions } from "@tanstack/react-query";

import { enc, load } from "@/shared/api/client";
import type { EventDetail, EventSummary } from "@/shared/api/types";
import { demoEventDetail, demoPublicEvents } from "@/shared/demo/fixtures";
import type { AppMode } from "@/shared/mode";

export function publicEventsQuery(mode: AppMode) {
  return queryOptions({
    queryKey: [mode, "public-events"],
    queryFn: () => load<{ results: EventSummary[] }>("/events/", demoPublicEvents),
    enabled: mode !== "unconfigured",
  });
}

export function eventDetailQuery(mode: AppMode, slug: string) {
  return queryOptions({
    queryKey: [mode, "public-event", slug],
    queryFn: () => load<EventDetail>(`/events/${enc(slug)}/`, () => demoEventDetail(slug)),
    enabled: mode !== "unconfigured",
  });
}

