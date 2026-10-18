import { keepPreviousData, queryOptions } from "@tanstack/react-query";

import { load } from "@/shared/api/client";
import type { Communication, Paginated } from "@/shared/api/types";
import { demoCommunications } from "@/shared/demo/fixtures";
import type { AppMode } from "@/shared/mode";
import { orgApiBase } from "@/features/organizations/api";

export function communicationsQuery(mode: AppMode, org: string, eventId: string, page: number) {
  return queryOptions({
    queryKey: [mode, "org", org, "event", eventId, "communications", page],
    queryFn: () => load<Paginated<Communication>>(`${orgApiBase(org, eventId)}/communications/?page=${page}`, () => demoCommunications(page)),
    placeholderData: keepPreviousData,
    enabled: mode !== "unconfigured",
  });
}

