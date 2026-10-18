import { keepPreviousData, queryOptions } from "@tanstack/react-query";

import { load } from "@/shared/api/client";
import type { Attendee, Paginated } from "@/shared/api/types";
import { demoAttendees } from "@/shared/demo/fixtures";
import type { AppMode } from "@/shared/mode";
import { orgApiBase } from "@/features/organizations/api";

export function attendeesQuery(mode: AppMode, org: string, eventId: string, page: number, q?: string) {
  const params = new URLSearchParams({ page: String(page) });
  if (q) params.set("q", q);
  return queryOptions({
    queryKey: [mode, "org", org, "event", eventId, "attendees", page, q ?? ""],
    queryFn: () => load<Paginated<Attendee>>(`${orgApiBase(org, eventId)}/attendees/?${params}`, () => demoAttendees(page, q)),
    placeholderData: keepPreviousData,
  });
}

