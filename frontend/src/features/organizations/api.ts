import { queryOptions, useQuery } from "@tanstack/react-query";

import { enc, load } from "@/shared/api/client";
import type { OrgEvent } from "@/shared/api/types";
import { demoOrgEvents } from "@/shared/demo/fixtures";
import { useMode, type AppMode } from "@/shared/mode";

export function orgEventsQuery(mode: AppMode, org: string) {
  return queryOptions({
    queryKey: [mode, "org", org, "events"],
    queryFn: () => load<{ results: OrgEvent[] }>(`/organizations/${enc(org)}/events/`, () => demoOrgEvents(org)),
  });
}

export function useOrgEvents(org: string) {
  return useQuery(orgEventsQuery(useMode(), org));
}

export function orgApiBase(org: string, eventId: string) {
  return `/organizations/${enc(org)}/events/${enc(eventId)}`;
}

